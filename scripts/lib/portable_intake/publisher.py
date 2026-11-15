"""Frozen, serialized candidate proposals. No merge, accepted index or CI dispatch."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile

from lib.consumer_github import AccessFailure
from lib.consumer_intake_store import file_digest
from lib.portable.contracts import canonical_digest, repository_key
from lib.portable.runtime import read_json
from .bundle import safe_path, timestamp, verifier_digest
from .controller import instant, profile_key, task_key
from .operations import GitWorkspace, require_compatible, run_link


def candidate(receipt,locator,generated_at):
    """Public allowlist: no provider bodies, private paths, scan strings or native reference."""
    context=receipt['producer']
    return {'schema_version':1,'native_execution_key':task_key({'scm':context['scm'],'ci':context['ci']},locator),
        'producer_execution_key':receipt['execution_key'],'repository_key':receipt['repository_key'],
        'scm':{name:context['scm'][name] for name in ('provider','instance','native_id','path')},
        'ci':{'provider':context['ci']['provider'],'instance':context['ci']['instance'],**locator},
        'revision':context['revision'],'event':context['ci']['event'],'synthetic':context['synthetic'],
        'domain':context['governance']['domain'],'scope':context['governance']['scope'],
        'baseline_id':context['governance']['baseline_id'],'baseline_digest':context['governance']['baseline_digest'],
        'runtime_source_digest':context['governance']['runtime_source_digest'],
        'verifier_source_digest':receipt['verifier']['source_digest'],
        'bundle_digest':receipt['bundle_digest'],'generated_at':generated_at,'run_url':run_link(context),
        'decision':receipt['decision'],'execution':receipt['execution'],'trust':receipt['trust'],
        'full_baseline_assessment':False,'official_acceptance':False,'blocks_merge':None}


def path_for(document):
    return 'status/portable/v2/candidates/'+document['repository_key']+'/'+document['native_execution_key']+'.json'


def canonical_text(document):return json.dumps(document,sort_keys=True,indent=2,ensure_ascii=False)+'\n'


def local_candidate(queue,task):
    row=queue.db.execute('SELECT receipt FROM receipts WHERE key=?',(task['receipt_key'],)).fetchone()
    if not row or not task['raw_path']:raise ValueError('candidate_receipt_missing')
    receipt=json.loads(row[0]);raw=queue.store.root/task['raw_path']
    metadata=read_json(safe_path(raw,'native-capture.json'))
    bundle_path=metadata['bundle_path']
    manifest=read_json(safe_path(raw,bundle_path+'/bundle.json'))
    if canonical_digest(manifest)!=receipt['bundle_digest']:raise ValueError('raw_bundle_changed')
    bundle=raw/bundle_path
    for member in manifest['files']:
        path=safe_path(bundle,member['path'])
        if path.stat().st_size!=member['size'] or file_digest(path)!=member['sha256']:
            raise ValueError('raw_candidate_bytes_changed')
    result_row=next(row for row in manifest['files'] if row['role']=='result')
    result=read_json(safe_path(bundle,result_row['path']))
    if result['context']!=receipt['producer']:raise ValueError('raw_candidate_context_changed')
    return candidate(receipt,json.loads(task['locator']),result['generated_at']),receipt


def shadow_match(queue,task,document,committed_root,*,at):
    """Only exact committed candidate content can supply a shadow comparison.

    A timer or a freely supplied `approved` flag does not establish readiness. Require
    >=24h plus a newly produced matching mainline result after that full window.
    """
    started=queue.get('shadow_started:'+task['profile'])
    path=Path(committed_root)/path_for(document)
    if not path.is_file() or path.is_symlink():return False
    path=safe_path(committed_root,path_for(document))
    if read_json(path)!=document:return False
    if (started is None or at-started<86400 or timestamp(document['generated_at']).timestamp()<started+86400
            or document['event']!='push' or document['revision']['mode']!='branch' or document['synthetic']
            or document['trust']!='provenance_verified' or document['execution']!='complete'
            or document['verifier_source_digest']!=verifier_digest()):
        return False
    queue.put('shadow_match:'+task['profile'],{'task_key':task['key'],'bundle_digest':document['bundle_digest'],
        'at':at,'generated_at':document['generated_at'],'verifier_source_digest':document['verifier_source_digest']})
    return True


def route_owned(config,profile,node_id):
    if config.get('schema_version')!=1 or config.get('default_owner')!='ci':
        raise ValueError('invalid_portable_routing')
    seen=set();owned=False
    for route in config.get('routes',[]):
        if set(route)!={'profile_digest','node_id','owner','domain','scope'}:
            raise ValueError('invalid_portable_route')
        key=(route['profile_digest'],route['domain'],route['scope'])
        if key in seen:raise ValueError('duplicate_portable_route')
        seen.add(key)
        if route['owner'] not in ('ci','vm') or not re.fullmatch('[a-f0-9]{64}',route['profile_digest']):
            raise ValueError('invalid_portable_route')
        if key==(profile_key(profile),'devsecops','pipeline-l1'):
            owned=route['owner']=='vm' and route['node_id']==node_id
    return owned


def observe_committed(queue,committed_root,*,at,limit=25):
    cursor=queue.get('shadow_cursor','')
    rows=list(queue.db.execute("SELECT * FROM native_tasks WHERE state='verified' AND key>? ORDER BY key LIMIT ?",(cursor,limit)))
    if not rows:
        queue.put('shadow_cursor','');return 0
    matches=0
    for row in rows:
        document,_=local_candidate(queue,dict(row))
        if shadow_match(queue,dict(row),document,committed_root,at=at):
            matches+=1
            with queue.db:queue.db.execute("UPDATE native_tasks SET state='shadow_matched' WHERE key=?",(row['key'],))
    queue.put('shadow_cursor',rows[-1]['key'])
    return matches


def active_batch(queue):
    rows=list(queue.db.execute("SELECT * FROM portable_batches WHERE state IN ('prepared','open','accepted_pending_sync')"))
    if len(rows)>1:raise AccessFailure('multiple_portable_batches_require_reconciliation')
    return dict(rows[0]) if rows else None


def update_batch(queue,batch_id,**fields):
    if not set(fields)<={'state','commit_sha','change_id','url'}:raise ValueError('invalid_batch_update')
    with queue.db:
        queue.db.execute('UPDATE portable_batches SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',(*fields.values(),batch_id))


def reject_legacy_activity(queue,scm,installed):
    tables={r[0] for r in queue.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'batches' in tables and queue.db.execute("SELECT 1 FROM batches WHERE state IN ('prepared','open','accepted_pending_sync') LIMIT 1").fetchone():
        raise AccessFailure('legacy_publication_requires_reconciliation')
    for change in scm.changes(prefixes=('automation/devsecops/','automation/vm-consumer/')):
        if change['state']=='open' and change['source'].startswith(('automation/devsecops/','automation/vm-consumer/')):
            raise AccessFailure('legacy_intake_pr_open')
    # Preserve the existing GitHub workflow's in-flight guard on a same-host handoff.
    if scm.profile['provider']=='github':
        for status in ('queued','in_progress','waiting','pending','requested'):
            path=scm.route+'/actions/workflows/intake-governance-result.yml/runs?status='+status
            if any(scm.reader.pages(path,'workflow_runs')):raise AccessFailure('legacy_intake_running')


def freeze(queue,profiles,routing,node_id,*,base,target,at,committed_root):
    if active_batch(queue):return active_batch(queue)
    by_digest={profile_key(p):p for p in profiles};selected=[];files={}
    owned=[key for key,profile in by_digest.items() if route_owned(routing,profile,node_id)]
    if not owned:return None
    rows=list(queue.db.execute("SELECT * FROM native_tasks WHERE state='verified' AND batch IS NULL AND profile IN ("+
        ','.join('?' for _ in owned)+") ORDER BY discovered,key LIMIT 25",owned))
    for row in rows:
        task=dict(row);profile=by_digest.get(task['profile'])
        if profile is None or not route_owned(routing,profile,node_id):continue
        document,receipt=local_candidate(queue,task)
        if receipt['verifier']['source_digest']!=verifier_digest():
            with queue.db:queue.db.execute("UPDATE native_tasks SET state='held',error='proposal_verifier_update_required' WHERE key=?",(task['key'],))
            continue
        # A previous receipt's freshness flag cannot renew evidence at proposal time.
        age=at-timestamp(document['generated_at']).timestamp()
        if not receipt['candidate_eligible'] or not 0<=age<=profile['policy']['max_age_seconds']:
            with queue.db:queue.db.execute("UPDATE native_tasks SET state='held',error='proposal_evidence_expired' WHERE key=?",(task['key'],))
            continue
        # Already committed data is a shadow comparison, never another proposal.
        if (Path(committed_root)/path_for(document)).exists():
            path=Path(committed_root)/path_for(document)
            if path.is_symlink() or read_json(safe_path(committed_root,path_for(document)))!=document:
                with queue.db:queue.db.execute("UPDATE native_tasks SET state='held',error='historical_candidate_conflict' WHERE key=?",(task['key'],))
            elif shadow_match(queue,task,document,committed_root,at=at):
                with queue.db:queue.db.execute("UPDATE native_tasks SET state='shadow_matched' WHERE key=?",(task['key'],))
            continue
        match=queue.get('shadow_match:'+task['profile'])
        started=queue.get('shadow_started:'+task['profile'])
        if (not match or started is None or at-started<86400 or match['at']<started+86400
                or match.get('verifier_source_digest')!=verifier_digest()):continue
        if receipt['producer']['scm']['provider']=='github':
            # The retained legacy route must also relinquish the same consumer.
            from lib.consumer_intake import owner
            if owner(committed_root,receipt['producer']['scm']['path'])!='vm':continue
        selected.append(task['key']);files[path_for(document)]=canonical_text(document)
    if not selected:return None
    manifest={'schema_version':1,'at':instant(at),'tasks':selected,'files':files,
              'files_digest':canonical_digest(files),'target':target,'node_id':node_id}
    batch_id=canonical_digest({'base':base,'manifest':manifest})[:24]
    with queue.store.transaction():
        # Serialize with a second coordinator and legacy state within the same DB.
        if active_batch(queue):raise AccessFailure('portable_batch_already_active')
        tables={r[0] for r in queue.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'batches' in tables and queue.db.execute("SELECT 1 FROM batches WHERE state IN ('prepared','open','accepted_pending_sync')").fetchone():
            raise AccessFailure('legacy_publication_requires_reconciliation')
        queue.db.execute('INSERT INTO portable_batches(id,base,state,manifest,target) VALUES (?,?,?,?,?)',
                         (batch_id,base,'prepared',json.dumps(manifest,sort_keys=True),target))
        for key in selected:queue.db.execute("UPDATE native_tasks SET state='batched',batch=? WHERE key=?",(batch_id,key))
    return active_batch(queue)


def reconcile(queue,batch,scm):
    source='automation/portable-consumer/'+batch['id']
    changes=scm.changes(source,batch['target'])
    if not changes:return False
    if len(changes)!=1 or not batch['commit_sha'] or changes[0]['sha']!=batch['commit_sha']:
        raise AccessFailure('portable_remote_publication_conflict')
    change=changes[0]
    if batch['change_id'] is not None and change['id']!=batch['change_id']:
        raise AccessFailure('portable_remote_publication_conflict')
    state='accepted_pending_sync' if change['state']=='merged' else 'not_accepted' if change['state']=='closed' else 'open'
    update_batch(queue,batch['id'],state=state,change_id=change['id'],url=change['url'])
    if state=='not_accepted':
        with queue.db:queue.db.execute("UPDATE native_tasks SET state='not_accepted' WHERE batch=?",(batch['id'],))
    return True


def publish(queue,profiles,routing,node_id,scm,*,installed,workspace_factory,base,target,at):
    """Caller holds worker.lock. Explicit invocation is not a routing/credential bypass."""
    batch=active_batch(queue)
    if batch and batch['state']=='accepted_pending_sync':
        with tempfile.TemporaryDirectory(prefix='sync-',dir=queue.store.root) as scratch:
            workspace=workspace_factory(Path(scratch)/'checkout');workspace.prepare(base)
            require_compatible(installed,workspace.root)
            files=json.loads(batch['manifest'])['files']
            if any(not (workspace.root/path).is_file() or (workspace.root/path).is_symlink()
                   or safe_path(workspace.root,path).read_text()!=content for path,content in files.items()):
                raise AccessFailure('portable_accepted_sync_required')
            update_batch(queue,batch['id'],state='reviewed')
            with queue.db:queue.db.execute("UPDATE native_tasks SET state='reviewed_candidate' WHERE batch=?",(batch['id'],))
        return None
    if batch and reconcile(queue,batch,scm):return active_batch(queue)
    reject_legacy_activity(queue,scm,installed)
    # Global open automation scope, including unknown batches from another node.
    for change in scm.changes(prefixes=('automation/portable-consumer/',)):
        if change['state']=='open' and change['source'].startswith('automation/portable-consumer/'):
            raise AccessFailure('unreconciled_portable_pr_open')
    with tempfile.TemporaryDirectory(prefix='proposal-',dir=queue.store.root) as scratch:
        workspace=workspace_factory(Path(scratch)/'checkout')
        workspace.prepare(batch['base'] if batch else base)
        require_compatible(installed,workspace.root)
        if batch and batch['state']=='accepted_pending_sync':
            # Reconcile against current central HEAD, never rebuild against another base.
            raise AccessFailure('portable_accepted_sync_required')
        if batch is None:
            batch=freeze(queue,profiles,routing,node_id,base=base,target=target,at=at,committed_root=workspace.root)
        if batch is None:return None
        manifest=json.loads(batch['manifest'])
        if manifest['files_digest']!=canonical_digest(manifest['files']) or manifest['node_id']!=node_id:
            raise AccessFailure('portable_frozen_manifest_conflict')
        # Recheck current route/profile pins and freshness after any restart.
        by_digest={profile_key(p):p for p in profiles}
        for key in manifest['tasks']:
            row=queue.db.execute('SELECT * FROM native_tasks WHERE key=?',(key,)).fetchone()
            if not row or row['profile'] not in by_digest or not route_owned(routing,by_digest[row['profile']],node_id):
                raise AccessFailure('portable_frozen_owner_changed')
            document,receipt=local_candidate(queue,dict(row))
            if canonical_text(document)!=manifest['files'].get(path_for(document)):
                raise AccessFailure('portable_frozen_evidence_changed')
            if (receipt['verifier']['source_digest']!=verifier_digest() or not receipt['candidate_eligible']
                    or not 0<=at-timestamp(document['generated_at']).timestamp()<=by_digest[row['profile']]['policy']['max_age_seconds']):
                raise AccessFailure('portable_frozen_evidence_expired')
        sha=workspace.commit(manifest['files'],'Propose portable evidence batch '+batch['id'],at=manifest['at'])
        if batch['commit_sha'] and batch['commit_sha']!=sha:raise AccessFailure('portable_frozen_commit_conflict')
        update_batch(queue,batch['id'],commit_sha=sha)
        source='automation/portable-consumer/'+batch['id']
        workspace.push(source,sha)
        change=scm.propose(source,batch['target'],sha,'Review portable evidence batch '+batch['id'],
            'Collected by the portable collector. Candidate evidence only; no official compliance or automatic merge.\n\n'+
            '\n'.join('- '+json.loads(content)['run_url'] for content in manifest['files'].values()))
        update_batch(queue,batch['id'],state='open' if change['state']=='open' else 'accepted_pending_sync' if change['state']=='merged' else 'not_accepted',
                     change_id=change['id'],url=change['url'])
        return active_batch(queue)
