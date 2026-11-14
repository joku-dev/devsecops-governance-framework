#!/usr/bin/env python3
"""Private VM operator entrypoint; default shadow mode cannot publish."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

from lib.consumer_github import AppToken, Client, AccessFailure
from lib.consumer_intake import CENTRAL, CONSUMER, discover, process, project
from lib.consumer_intake_store import Store, backup, verify_backup, lock

ROOT = Path(__file__).resolve().parents[1]


def configuration(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError('Operator configuration must be a private regular file')
    value = json.loads(path.read_text())
    allowed = {'reader_app_id', 'reader_installation_id', 'publisher_app_id', 'publisher_installation_id', 'mode'}
    if not isinstance(value, dict) or set(value) - allowed or value.get('mode', 'shadow') not in {'shadow', 'publish', 'paused'}:
        raise ValueError('Invalid operator configuration')
    return value


def client(config, role, store):
    credentials = Path(os.environ.get('CREDENTIALS_DIRECTORY', '/nonexistent'))
    if role == 'reader':
        repositories = [CENTRAL.split('/')[1], CONSUMER.split('/')[1]]
        permissions = {'metadata': 'read', 'contents': 'read', 'actions': 'read', 'pull_requests': 'read'}
    else:
        repositories = [CENTRAL.split('/')[1]]
        permissions = {'metadata': 'read', 'contents': 'write', 'pull_requests': 'write'}
    token = AppToken(config.get(role + '_app_id', ''), config.get(role + '_installation_id', ''),
                     credentials / (role + '-key'), repositories, permissions)
    return Client(token, store=store)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['poll', 'work', 'status', 'retry', 'resume', 'reconcile-batch', 'backup', 'verify-backup', 'restore', 'route'])
    parser.add_argument('--root', type=Path, default=Path('/var/lib/axiom/consumers'))
    parser.add_argument('--projection', type=Path, default=Path('/var/lib/axiom/consumer-view'))
    parser.add_argument('--config', type=Path, default=Path('/etc/axiom/consumer-intake.json'))
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--run-id', type=int)
    parser.add_argument('--attempt', type=int)
    parser.add_argument('--batch-id')
    parser.add_argument('--repository', default=CONSUMER)
    parser.add_argument('--domain', default='devsecops')
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.action == 'route':
        from lib.consumer_intake import owner
        print(owner(ROOT, args.repository, args.domain))
        return 0
    if args.action in {'verify-backup', 'restore'}:
        if not args.destination:
            parser.error('--destination backup directory is required')
        verify_backup(args.destination)
        if args.action == 'restore':
            if args.root.exists():
                raise ValueError('Restore requires a new empty operations root and stopped services')
            shutil.copytree(args.destination, args.root)
            (args.root / 'manifest.json').unlink()
        print(json.dumps({'verified': True}))
        return 0
    store = Store(args.root)
    try:
        if args.action == 'status':
            print(json.dumps({'accepted': store.get('accepted'), 'last_poll': store.get('last_poll'),
                              'poll_error': store.get('poll_error'), 'sync_error': store.get('sync_error'),
                              'counts': dict(store.db.execute('SELECT state,count(*) FROM jobs GROUP BY state'))}))
            return 0
        if args.action == 'backup':
            if not args.destination:
                parser.error('--destination required')
            with lock(args.root / 'poll.lock'), lock(args.root / 'worker.lock'):
                backup(store, args.destination)
                verify_backup(args.destination)
            print(json.dumps({'backup_verified': True}))
            return 0
        with lock(args.root / ('poll.lock' if args.action == 'poll' else 'worker.lock')):
            config = configuration(args.config)
            mode = config.get('mode', 'shadow')
            if args.action == 'reconcile-batch':
                active = store.active_batch()
                if (mode != 'paused' or not active or active['id'] != args.batch_id
                        or active['state'] != 'prepared' or store.get('accepted_commit') == active['base']):
                    raise ValueError('Reconciliation requires paused mode, exact prepared batch and newer accepted main')
                with store.db:
                    store.db.execute("UPDATE batches SET state='abandoned' WHERE id=?", (active['id'],))
                    store.db.execute("UPDATE jobs SET state='verified',batch=NULL WHERE batch=?", (active['id'],))
            elif args.action == 'resume':
                for kind in ('poll', 'worker'):
                    store.put(kind + '_after', 0)
                    store.put(kind + '_failures', 0)
                store.put('poll_error', None)
                store.put('sync_error', None)
            elif args.action == 'retry':
                if not args.run_id or not args.attempt:
                    parser.error('retry requires --run-id and --attempt')
                job = next((row for row in store.jobs('held') if row['run_id'] == args.run_id and row['attempt'] == args.attempt), None)
                if not job:
                    raise ValueError('No held job matches this identity')
                store.update(job, state='queued', retries=0, next_at=0, error=None)
            elif mode != 'paused':
                reader = client(config, 'reader', store)
                if args.action == 'poll':
                    discover(store, reader)
                elif store.get('worker_after', 0) <= time.time():
                    publisher = client(config, 'publisher', store) if mode == 'publish' else None
                    process(store, ROOT, reader, publisher, mode)
                    store.put('sync_error', None)
                    store.put('worker_failures', 0)
                    store.put('worker_after', 0)
            project(store, args.projection, mode)
        return 0
    except AccessFailure as error:
        field = 'poll_error' if args.action == 'poll' else 'sync_error'
        store.put(field, error.code)
        kind = 'poll' if args.action == 'poll' else 'worker'
        failures = store.get(kind + '_failures', 0) + 1
        store.put(kind + '_failures', failures)
        store.put(kind + '_after', time.time() + error.delay * 2 ** min(failures - 1, 3)
                  if error.retryable and failures <= 3 else float('1e20'))
        project(store, args.projection, locals().get('mode', 'shadow'))
        print(json.dumps({'error': error.code}), file=sys.stderr)
        return 1
    finally:
        store.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as error:
        # No exception text: files, credentials and API bodies are private.
        print(json.dumps({'error': 'operator_configuration_or_state_invalid'}), file=sys.stderr)
        raise SystemExit(2)
