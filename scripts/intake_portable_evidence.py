#!/usr/bin/env python3
"""Versioned local/native evidence intake. No accepted index or remote publication."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
import uuid
from jsonschema import ValidationError

from lib.provider_errors import AccessFailure
from lib.consumer_intake_store import atomic_json, lock, verify_backup
from lib.portable.runtime import read_json
from lib.portable_intake.bundle import export_bundle, unpack, verify_bundle, validate_policy, require_storage
from lib.portable_intake.store import Store, migrate_legacy, backup_v2, restore_legacy
from lib.provider_ports import Reader, capture, BoundedAudit
from lib.private_credentials import check_private_file


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['bundle','verify-local','collect','status','migrate-legacy','backup','verify-backup','restore','restore-legacy'])
    parser.add_argument('--assessment',type=Path)
    parser.add_argument('--checkout',type=Path)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--policy',type=Path)
    parser.add_argument('--context',type=Path)
    parser.add_argument('--candidate-directory',type=Path,help='Explicit public candidate export for native collect only')
    parser.add_argument('--root',type=Path)
    parser.add_argument('--legacy-mapping',type=Path)
    parser.add_argument('--opa',type=Path)
    parser.add_argument('--at')
    args=parser.parse_args(argv)
    os.umask(0o077)
    at=args.at or datetime.now(timezone.utc).isoformat()
    if args.candidate_directory and args.action!='collect':parser.error('--candidate-directory requires native collect')
    if args.action=='bundle':
        if not all((args.assessment,args.checkout,args.destination)):
            parser.error('bundle requires --assessment --checkout --destination')
        export_bundle(args.assessment,args.checkout,args.destination)
        # A separate ZIP file makes Bamboo's artifact URL a concrete downloadable file.
        archive=args.destination.with_suffix('.zip')
        with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as output:
            for path in sorted(args.destination.rglob('*')):
                if path.is_file():
                    output.write(path,str(path.relative_to(args.destination)))
        print(json.dumps({'bundle_created':True}))
        return 0
    if not args.root:
        parser.error('--root is required for explicit local/VM state separation')
    if args.action in ('verify-backup','restore','restore-legacy'):
        if not args.destination:parser.error('--destination backup directory required')
        verify_backup(args.destination)
        if args.action=='restore':
            if args.root.exists():raise ValueError('restore_requires_fresh_root')
            shutil.copytree(args.destination,args.root)
            (args.root/'manifest.json').unlink()
            restored=Store(args.root,create=False);restored.close()
        elif args.action=='restore-legacy':
            restore_legacy(args.destination,args.root)
        print(json.dumps({'backup_verified':True}));return 0
    if args.action=='migrate-legacy':
        if not args.destination or not args.legacy_mapping:
            parser.error('migration requires a fresh --destination and --legacy-mapping')
        check_private_file(args.legacy_mapping)
        with lock(args.root/'poll.lock'),lock(args.root/'worker.lock'):
            migrate_legacy(args.root,read_json(args.legacy_mapping),args.destination)
        print(json.dumps({'migration_candidate_created':True,'activated':False}))
        return 0
    store=Store(args.root)
    try:
        if args.action=='backup':
            if not args.destination:parser.error('--destination required')
            with lock(args.root/'poll.lock'),lock(args.root/'worker.lock'):
                backup_v2(store,args.destination)
            print(json.dumps({'backup_verified':True}));return 0
        if args.action=='status':
            print(json.dumps({'schema_version':2,'counts':store.counts(),'publisher_active':False}))
            return 0
        if not args.policy or not args.opa:
            parser.error('--policy and --opa required')
        check_private_file(args.policy)
        policy=read_json(args.policy)
        validate_policy(policy)
        require_storage(args.root,policy)
        observation=None
        with lock(args.root/'worker.lock'),tempfile.TemporaryDirectory(prefix='capture-',dir=args.root) as temporary:
            temporary=Path(temporary)
            if args.action=='collect':
                if not args.context:
                    parser.error('collect requires --context')
                transport=policy['transport']
                token=os.environ.get(transport.get('token_env',''),'')
                reader=Reader(transport['api_url'],token,budget=transport.get('request_budget',100))
                scm_reader=None
                if policy.get('scm_transport'):
                    scm=policy['scm_transport']
                    scm_reader=Reader(scm['api_url'],os.environ.get(scm.get('token_env',''),''),budget=scm.get('request_budget',100))
                audit=BoundedAudit()
                try:
                    observation,audit=capture(read_json(args.context),policy,reader,temporary/'artifact.zip',at=at,audit_sink=audit,scm_reader=scm_reader)
                    bundle=unpack(temporary/'artifact.zip',temporary/'bundle')
                except (AccessFailure,ValueError,OSError,KeyError,TypeError,ValidationError,zipfile.BadZipFile):
                    failure=args.root/'raw'/'failures'/uuid.uuid4().hex
                    failure.mkdir(parents=True,mode=0o700)
                    atomic_json(failure/'diagnostics.json',{'execution':'error','diagnostics':['native_capture_failed']})
                    atomic_json(failure/'native-responses.json',audit)
                    if (temporary/'artifact.zip').is_file():
                        shutil.copyfile(temporary/'artifact.zip',failure/'artifact.zip')
                    raise
                prefix=transport.get('bundle_prefix','')
                if prefix:
                    bundle=bundle/prefix
            else:
                if not args.bundle:
                    parser.error('verify-local requires --bundle')
                bundle=unpack(args.bundle,temporary/'bundle') if args.bundle.is_file() else args.bundle
            try:
                receipt=verify_bundle(bundle,policy,opa=args.opa,at=at,history=store.history(),observation=observation)
            except (ValueError,OSError,KeyError,TypeError,ValidationError,subprocess.SubprocessError):
                if observation:
                    # Rejected native evidence is still a private immutable forensic capture.
                    failure=args.root/'raw'/'failures'/uuid.uuid4().hex
                    failure.mkdir(parents=True,mode=0o700)
                    shutil.copyfile(temporary/'artifact.zip',failure/'artifact.zip')
                    atomic_json(failure/'native-capture.json',{'observation':asdict(observation),'responses':audit})
                    atomic_json(failure/'diagnostics.json',{'execution':'error','diagnostics':['bundle_verification_failed']})
                raise
            key=receipt['execution_key']
            # Preserve raw/candidate bytes first. A crash leaves evidence, not a consumed slot.
            raw=args.root/'raw'/key/receipt['bundle_digest']
            raw.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
            if not raw.exists():
                with tempfile.TemporaryDirectory(prefix='pending-',dir=raw.parent) as staged:
                    staged=Path(staged)
                    shutil.copytree(bundle,staged/'bundle')
                    if observation:
                        shutil.copyfile(temporary/'artifact.zip',staged/'native-artifact.zip')
                        atomic_json(staged/'native-capture.json',{'observation':asdict(observation),'responses':audit})
                    atomic_json(staged/'receipt.json',receipt)
                    # Rename a complete subdirectory; TemporaryDirectory still cleans its parent.
                    ready=staged/'ready';ready.mkdir()
                    for path in list(staged.iterdir()):
                        if path!=ready:path.rename(ready/path.name)
                    ready.rename(raw)
            elif not (raw/'receipt.json').is_file():
                raise ValueError('incomplete_raw_capture')
            saved,inserted=store.record(receipt)
            if args.candidate_directory:
                from lib.portable_intake.publisher import candidate,path_for
                if (not observation.native_job_id or not saved['candidate_eligible'] or saved['verifier']!=receipt['verifier'] or receipt['freshness']!='fresh'
                        or receipt['execution']!='complete' or any(not passed for name,passed in receipt['checks'].items() if name!='replay_key_unique')):
                    raise ValueError('native_candidate_export_not_eligible')
                manifest=read_json(bundle/'bundle.json')
                result_path=next(row['path'] for row in manifest['files'] if row['role']=='result')
                generated=read_json(bundle/result_path)['generated_at']
                locator={'run_id':saved['producer']['ci']['run_id'],'job_id':observation.native_job_id,
                         'attempt':saved['producer']['ci']['attempt']}
                document=candidate(saved,locator,generated)
                destination=args.candidate_directory/path_for(document)
                if destination.exists():
                    if destination.is_symlink() or read_json(destination)!=document:raise ValueError('immutable_candidate_export_conflict')
                else:atomic_json(destination,document)
            # Original result and Trust are immutable; replay is a new processing observation.
            print(json.dumps({'receipt':saved,'recorded':inserted,'processing_replay':receipt['replay']}))
            return 0 if receipt['execution']=='complete' and receipt['freshness']=='fresh' and receipt['replay']!='conflict' else 2
    finally:
        store.close()


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except AccessFailure as error:
        print(json.dumps({'error':error.code,'retryable':error.retryable,'retry_after':error.delay}),file=sys.stderr)
        raise SystemExit(2)
    except (ValueError,OSError,KeyError,TypeError,ValidationError,zipfile.BadZipFile,sqlite3.DatabaseError,subprocess.SubprocessError):
        # Provider bodies, local paths, private configuration and credential values stay private.
        print(json.dumps({'error':'portable_intake_invalid'}),file=sys.stderr)
        raise SystemExit(2)
