#!/usr/bin/env python3
"""Bounded portable collector service; private SQLite/raw state and public counts only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import hashlib
import re
import sqlite3
import subprocess
import sys
import zipfile

from lib.consumer_github import AccessFailure
from lib.consumer_intake_store import atomic_json, lock
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json
from lib.portable_intake.controller import Queue, ReaderPool, poll, validate_profiles, work, instant
from lib.portable_intake.store import Store
from lib.portable_intake.operations import GitWorkspace, SCM, Writer, require_compatible, run_link
from lib.portable_intake.publisher import observe_committed, publish, route_owned, active_batch
from lib.private_credentials import check_private_file


def configuration(path):
    check_private_file(path)
    value=read_json(path)
    if (set(value)!={'schema_version','mode','registry','credentials_directory','request_budget','node_id'}
            or value['schema_version']!=1 or value['mode'] not in ('paused','shadow','publish')
            or not isinstance(value['node_id'],str) or not re.fullmatch('[a-f0-9]{32}',value['node_id'])
            or type(value['request_budget']) is not int or not 10<=value['request_budget']<=1000):
        raise ValueError('invalid_portable_service_configuration')
    for name in ('registry','credentials_directory'):
        if name=='credentials_directory' and value[name]=='systemd':
            value[name]=os.environ.get('CREDENTIALS_DIRECTORY','')
        if not Path(value[name]).is_absolute():raise ValueError('absolute_service_path_required')
    # Registry is reviewed installed source; no untracked operator-supplied code/policy.
    registry=Path(value['registry'])
    if registry.is_symlink() or registry.resolve()!=ROOT/'config/portable-consumer-profiles.json':
        raise ValueError('installed_portable_registry_required')
    return value,validate_profiles(read_json(registry))


def central_operations(queue,profiles,config,pool,*,at,allow_publish=True):
    """Always read-only in shadow. Fetched source is compared, never executed."""
    import tempfile
    from urllib.parse import urlsplit
    from lib.portable.contracts import endpoint
    from lib.portable_intake.transport import Reader
    routing=read_json(ROOT/'config/portable-operations.json')
    if set(routing)!={'schema_version','default_owner','central','routes'} or routing['schema_version']!=1:
        raise ValueError('invalid_portable_operations_configuration')
    central=routing['central']
    if central is None:
        if config['mode']=='publish':raise AccessFailure('portable_central_not_configured')
        return
    if set(central)!={'scm','api_url','remote','target','reader_credential','git_reader_credential',
                     'publisher_credential','git_publisher_credential','git_username'}:
        raise ValueError('invalid_portable_central_configuration')
    for name in ('reader_credential','git_reader_credential'):
        if not re.fullmatch(r'reader-[a-zA-Z0-9_-]{1,80}',central[name]):raise ValueError('central_reader_reference_required')
    for name in ('publisher_credential','git_publisher_credential'):
        if not re.fullmatch(r'publisher-[a-zA-Z0-9_-]{1,80}',central[name]):raise ValueError('central_publisher_reference_required')
    origin=endpoint(central['scm']['instance'])
    for name in ('remote','api_url'):
        parsed=urlsplit(central[name])
        allowed={origin}|({'https://api.github.com'} if origin=='https://github.com' and name=='api_url' else set())
        if endpoint('https://'+parsed.netloc) not in allowed:raise ValueError('central_credential_issuer_mismatch')
    def token(name):
        path=Path(config['credentials_directory'])/central[name];check_private_file(path)
        value=path.read_text().strip()
        if not value or any(ord(c)<32 for c in value):raise ValueError('invalid_central_credential')
        return value
    reader=pool.reader({'api_url':central['api_url']},central['reader_credential'])
    scm=SCM(central['scm'],reader)
    scm.check_identity();base=scm.branch_sha(central['target'])
    git_reader=token('git_reader_credential')
    with tempfile.TemporaryDirectory(prefix='central-read-',dir=queue.store.root) as temporary:
        workspace=GitWorkspace(Path(temporary)/'checkout',central['remote'],git_reader,central['git_username'])
        workspace.prepare(base);require_compatible(ROOT,workspace.root)
        observe_committed(queue,workspace.root,at=at)
    if config['mode']=='publish' and allow_publish:
        # Mode selection cannot assert source ownership or shadow completion.
        from lib.portable_intake.controller import profile_key
        from lib.portable_intake.bundle import verifier_digest
        if not any(route_owned(routing,p,config['node_id']) and
                   (queue.get('shadow_match:'+profile_key(p)) or {}).get('verifier_source_digest')==verifier_digest() for p in profiles):
            raise AccessFailure('portable_handoff_not_ready')
        publisher=token('publisher_credential');git_publisher=token('git_publisher_credential')
        scm.writer=Writer(central['api_url'],publisher,budget=25)
        publish(queue,profiles,routing,config['node_id'],scm,installed=ROOT,
            workspace_factory=lambda path:GitWorkspace(path,central['remote'],git_reader,central['git_username'],publisher_token=git_publisher),
            base=base,target=central['target'],at=at)


def projection(queue,config,*,at):
    jobs=[]
    for row in queue.db.execute('SELECT * FROM native_tasks ORDER BY discovered DESC,key DESC LIMIT 100'):
        locator=json.loads(row['locator'])
        item={**locator,'state':row['state'],'error':row['error']}
        if row['receipt_key']:
            receipt_row=queue.db.execute('SELECT receipt FROM receipts WHERE key=?',(row['receipt_key'],)).fetchone()
            receipt=json.loads(receipt_row[0]);context=receipt['producer']
            item.update(repository=context['scm']['path'],ci_provider=context['ci']['provider'],
                ci_instance=context['ci']['instance'],run_url=run_link(context),
                governance_status=receipt['decision'],evidence_trust=receipt['trust'],
                produced_at=queue.get('produced:'+row['key']),official_acceptance=False)
        jobs.append(item)
    routing=read_json(ROOT/'config/portable-operations.json');central=routing['central']
    batch=active_batch(queue)
    if batch:
        batch={name:batch[name] for name in ('id','state','change_id','url')}
        batch['instance']=central['scm']['instance'] if central else None
    return {**queue.summary(at=at),'schema_version':1,'engine':'portable-v1','configured':True,
        'generated_at':instant(at),'mode':config['mode'],'jobs':jobs,'batch':batch,
        'queue_count':sum(queue.summary(at=at)['counts'].values()),'accepted':None,
        'sync_error':queue.get('sync_error'),'last_poll':queue.get('last_poll'),
        'installed_revision':subprocess.run(['git','-c','safe.directory='+str(ROOT),'rev-parse','HEAD'],cwd=ROOT,
            check=True,capture_output=True,text=True).stdout.strip()}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['poll','work','status'])
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--projection',type=Path)
    parser.add_argument('--opa',type=Path)
    args=parser.parse_args(argv)
    os.umask(0o077)
    config,profiles=configuration(args.config)
    at=datetime.now(timezone.utc).timestamp()
    args.root.mkdir(parents=True,mode=0o700,exist_ok=True)
    if args.root.is_symlink() or args.root.stat().st_mode&0o077:
        raise ValueError('private_operations_root_required')
    with lock(args.root/('poll.lock' if args.action=='poll' else 'worker.lock')):
        store=Store(args.root)
        try:
            queue=Queue(store)
            machine=Path('/etc/machine-id')
            host=hashlib.sha256((platform.node()+(machine.read_text().strip() if machine.is_file() else '')).encode()).hexdigest()
            with store.transaction():
                bound=queue.get('node_binding')
                binding={'node_id':config['node_id'],'host_digest':host}
                if args.action!='status' and config['mode']!='paused':
                    if bound is not None and bound!=binding:raise ValueError('restored_node_reconciliation_required')
                    store.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('portable:node_binding',json.dumps(binding,sort_keys=True)))
            pool=ReaderPool(queue,config['credentials_directory'],at=at,budget=config['request_budget'])
            pending_error=None
            if config['mode']=='paused':result={**queue.summary(at=at),'paused':True}
            elif args.action=='poll':
                result=poll(queue,profiles,pool,at=at);queue.put('last_poll',instant(at))
            elif args.action=='work':
                opa=args.opa or Path(os.environ.get('VALIDATION_VENV',ROOT/'.venv'))/'bin/opa'
                try:
                    central_operations(queue,profiles,config,pool,at=at,allow_publish=False)
                    result=work(queue,profiles,pool,opa=opa,at=at)
                    if config['mode']=='publish':central_operations(queue,profiles,config,pool,at=at)
                    queue.put('sync_error',None)
                except AccessFailure as error:
                    queue.put('sync_error',error.code);pending_error=error;result=queue.summary(at=at)
            else:result=queue.summary(at=at)
            if args.projection:
                # Never export native response bodies, SQLite, credential subjects or raw paths.
                if args.projection.resolve().is_relative_to(args.root.resolve()) or args.root.resolve().is_relative_to(args.projection.resolve()):
                    raise ValueError('public_projection_requires_separate_root')
                atomic_json(args.projection/'consumers.json',projection(queue,config,at=at),mode=0o640)
            if pending_error:raise pending_error
            print(json.dumps(result,sort_keys=True));return 0
        finally:store.close()


if __name__=='__main__':
    try:raise SystemExit(main())
    except AccessFailure as error:
        print(json.dumps({'error':error.code,'retryable':error.retryable}),file=sys.stderr);raise SystemExit(2)
    except (ValueError,OSError,KeyError,TypeError,sqlite3.DatabaseError,zipfile.BadZipFile,subprocess.SubprocessError):
        print(json.dumps({'error':'portable_service_invalid'}),file=sys.stderr);raise SystemExit(2)
