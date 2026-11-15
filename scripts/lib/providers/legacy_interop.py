"""V1 handoff observations; never grant V2 operating authority."""
from pathlib import Path
import json
from lib.provider_errors import AccessFailure


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



def legacy_consumer_relinquished(root, scm):
    if scm['provider']!='github':return True
    path=Path(root)/'config/consumer-intake-routing.json'
    value=json.loads(path.read_text())
    if value.get('schema_version')!=1 or value.get('default_owner')!='github-actions':
        raise ValueError('invalid_legacy_routing_contract')
    routes=value['routes'];keys=[(r['repository'],r['domain']) for r in routes]
    if len(keys)!=len(set(keys)) or any(r['owner'] not in {'github-actions','vm'} for r in routes):
        raise ValueError('invalid_legacy_routing_contract')
    return next((r['owner'] for r in routes if (r['repository'],r['domain'])==(scm['path'],'devsecops')),value['default_owner'])=='vm'


def validate_legacy_profiles(profiles):
    from lib.portable.contracts import repository_key,endpoint
    for name,identity in profiles.items():
        if (identity['scm']['provider']!='github' or identity['ci_provider']!='github-actions'
                or identity.get('legacy_scope')!='workflow-aggregate' or name!=identity['scm']['path']):
            raise ValueError('unproven_legacy_identity')
        repository_key(identity['scm']);endpoint(identity['ci_instance'])
