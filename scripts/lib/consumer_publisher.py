"""Serialized VM batches, truthful provenance and recovery after partial API success."""
from __future__ import annotations

import hashlib
import json
import sys

from lib.consumer_github import AccessFailure
from lib.consumer_intake import CENTRAL, CONSUMER, GENERATORS, command, comparison
from lib.consumer_intake_store import atomic_json
from publish_operational_update import selected_paths


def publish(store, staging, reader, publisher, base):
    active = store.active_batch()
    # Existing Actions-owned PRs must be reconciled before a VM batch is prepared.
    for page in reader.pages(f'/repos/{CENTRAL}/pulls?state=open'):
        if any(pr.get('head', {}).get('ref', '').startswith('automation/devsecops/') for pr in page):
            raise AccessFailure('legacy_intake_pr_open')
        for pr in page:
            branch = pr.get('head', {}).get('ref', '')
            if branch.startswith('automation/vm-consumer/') and (not active or branch != 'automation/vm-consumer/' + active['id']):
                raise AccessFailure('unreconciled_vm_pr_open')
    for status in ('queued', 'in_progress', 'waiting', 'pending', 'requested'):
        endpoint = f'/repos/{CENTRAL}/actions/workflows/intake-governance-result.yml/runs?status={status}'
        if any(page for page in reader.pages(endpoint, 'workflow_runs')):
            raise AccessFailure('legacy_intake_running')
    if active and active['state'] == 'open':
        pr = reader.request('GET', f'/repos/{CENTRAL}/pulls/{active["pr"]}', cache=False)
        if pr['state'] != 'closed':
            return
        terminal = 'merged' if pr.get('merged_at') else 'not_accepted'
        store.batch(active['id'], state=terminal)
        with store.db:
            store.db.execute('UPDATE jobs SET state=? WHERE batch=?',
                             ('accepted_pending_sync' if terminal == 'merged' else 'not_accepted', active['id']))
        # Do not publish another batch until a subsequent accepted-main sync.
        return
    if active is None:
        jobs = store.jobs('verified')[:25]
        if not jobs:
            return
        manifest = [{'repository': row['repository'], 'domain': row['domain'], 'run_id': row['run_id'],
                     'attempt': row['attempt'], 'path': row['snapshot_path'],
                     'sha256': hashlib.sha256(row['snapshot'].encode()).hexdigest()} for row in jobs]
        batch_id = hashlib.sha256(json.dumps({'base': base, 'jobs': manifest}, sort_keys=True).encode()).hexdigest()[:24]
        with store.db:
            store.db.execute('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)',
                             (batch_id, base, 'prepared', json.dumps(manifest)))
            for job in jobs:
                store.db.execute('UPDATE jobs SET state=\'batched\',batch=? WHERE repository=? AND domain=? AND run_id=? AND attempt=?',
                                 (batch_id, job['repository'], job['domain'], job['run_id'], job['attempt']))
        active = store.active_batch()
    branch = 'automation/vm-consumer/' + active['id']
    endpoint = f'/repos/{CENTRAL}'
    # Find a previously-created PR before any mutation, including closed/unmerged PRs.
    prs = reader.request('GET', endpoint + '/pulls?state=all&head=' + quote_head(branch), cache=False)
    if prs:
        pr = prs[0]
        store.batch(active['id'], state='open', pr=pr['number'], url=pr['html_url'])
        return
    sha = active['commit_sha']
    if not sha:
        # Frozen batch base: never rebuild on an unrelated newer main after a restart.
        if base != active['base']:
            raise AccessFailure('batch_base_advanced_manual_reconcile')
        for item in json.loads(active['manifest']):
            job = next(row for row in store.jobs() if row['run_id'] == item['run_id'] and row['attempt'] == item['attempt'])
            if hashlib.sha256(job['snapshot'].encode()).hexdigest() != item['sha256']:
                raise AccessFailure('batch_manifest_mismatch')
            path = staging / item['path']
            if path.exists():
                if comparison(json.loads(path.read_text())) != comparison(json.loads(job['snapshot'])):
                    raise AccessFailure('historical_snapshot_conflict')
            else:
                atomic_json(path, json.loads(job['snapshot']))
        for script in GENERATORS:
            command([sys.executable, 'scripts/' + script], staging)
        command(['./scripts/validate_all.sh'], staging)
        paths = selected_paths(staging, 'devsecops')
        # VM telemetry never enters GitHub-Actions-only event ledgers.
        if any(path.startswith(('status/intake-events/', 'status/collection-attempts/', 'status/intake-conflicts/')) for path in paths):
            raise AccessFailure('vm_publication_scope_violation')
        commit = reader.request('GET', endpoint + '/git/commits/' + base, cache=False)
        tree = publisher.request('POST', endpoint + '/git/trees', {
            'base_tree': commit['tree']['sha'], 'tree': [
                {'path': path, 'mode': '100644', 'type': 'blob', 'content': (staging / path).read_text()}
                for path in paths]})
        result = publisher.request('POST', endpoint + '/git/commits', {
            'message': 'Propose VM consumer evidence batch ' + active['id'],
            'tree': tree['sha'], 'parents': [base]})
        sha = result['sha']
        store.batch(active['id'], commit_sha=sha)
    try:
        ref = reader.request('GET', endpoint + '/git/ref/heads/' + branch, cache=False)
        if ref['object']['sha'] != sha:
            raise AccessFailure('batch_branch_conflict')
    except AccessFailure as error:
        if error.code != 'http_404':
            raise
        publisher.request('POST', endpoint + '/git/refs', {'ref': 'refs/heads/' + branch, 'sha': sha})
    items = json.loads(active['manifest'])
    sources = '\n'.join(f'- https://github.com/{CONSUMER}/actions/runs/{item["run_id"]}/attempts/{item["attempt"]}' for item in items)
    pr = publisher.request('POST', endpoint + '/pulls', {
        'title': 'Review VM consumer evidence batch ' + active['id'], 'head': branch, 'base': 'main',
        'body': ('VM collector batch `' + active['id'] + '`, based on `' + active['base'] + '`.\n\n'
                 'Collected and validated on the VM; the VM is not a GitHub Actions workflow run. '
                 'Official state changes only after review and merge. No automatic merge.\n\n'
                 'Producer runs:\n' + sources + '\n\nManifest:\n```json\n' + json.dumps(items, indent=2) + '\n```')})
    store.batch(active['id'], state='open', pr=pr['number'], url=pr['html_url'])


def quote_head(branch):
    from urllib.parse import quote
    return quote(CENTRAL.split('/')[0] + ':' + branch, safe='')
