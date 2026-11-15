"""Fresh private V2 instances and explicit application routing, without V1 state."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess

from lib.private_credentials import check_private_file
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import ROOT
from lib.portable.runtime import source_digest, file_digest, approved_opa_hashes, read_json
from lib.v2_boundary import validate_boundaries
from lib.v2_source import active_fingerprints, verify_active_scripts
from lib.portable.contracts import canonical_digest

PRODUCT='axiom-v2'
VERSION='2.0.0-candidate'


def revision():
    return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),
                                    'rev-parse','HEAD'],text=True).strip()


def initialize(path, *, port=8875, opa, development=False):
    path=Path(path)
    if path.is_symlink() or path.exists():raise ValueError('fresh_v2_instance_required')
    if not 1024<=port<=65535:raise ValueError('invalid_v2_workbench_port')
    opa=Path(opa).resolve()
    if not opa.is_file() or file_digest(opa) not in approved_opa_hashes('1.18.2'):
        raise ValueError('v2_pinned_opa_required')
    if not validate_boundaries(ROOT)['passed']:raise ValueError('v2_architecture_boundary_failed')
    if not development and subprocess.check_output(['git','-c','safe.directory='+str(ROOT),
            '-C',str(ROOT),'status','--porcelain','--untracked-files=all']).strip():
        raise ValueError('v2_clean_source_required')
    path.mkdir(mode=0o700,parents=True,exist_ok=False)
    path=path.resolve()
    for name in ('state','state/consumers','state/evidence','credentials','projection'):
        (path/name).mkdir(mode=0o700)
    node=secrets.token_hex(16)
    instance={'schema_version':2,'product':PRODUCT,'version':VERSION,'node_id':node,
        'source_root':str(ROOT),'source_revision':revision(),'runtime_source_digest':source_digest(),
        'application_source_digest':canonical_digest(active_fingerprints(ROOT)),
        'port':port,'opa':str(opa),'opa_sha256':file_digest(opa),'development':development,
        'created_at':datetime.now(timezone.utc).isoformat()}
    atomic_json(path/'consumer.json',{'schema_version':1,'mode':'paused',
        'registry':str(ROOT/'config/portable-consumer-profiles.json'),
        'credentials_directory':str(path/'credentials'),'request_budget':300,'node_id':node})
    atomic_json(path/'workbench-key.json',{'key':secrets.token_urlsafe(32)})
    # The admission marker is last: an interrupted setup cannot be resumed.
    atomic_json(path/'instance.json',instance)
    return instance


def instance(path):
    if (ROOT/'.git/info/sparse-checkout').is_file():verify_active_scripts(ROOT)
    path=Path(path)
    if path.is_symlink() or not path.is_dir() or path.stat().st_mode&0o077:
        raise ValueError('private_v2_instance_required')
    check_private_file(path/'instance.json')
    value=read_json(path/'instance.json')
    expected={'schema_version','product','version','node_id','source_root','source_revision',
              'runtime_source_digest','application_source_digest','port','opa','opa_sha256','development','created_at'}
    if (set(value)!=expected or value['schema_version']!=2 or value['product']!=PRODUCT
            or value['source_root']!=str(ROOT) or value['source_revision']!=revision()
            or value['runtime_source_digest']!=source_digest()
            or value['application_source_digest']!=canonical_digest(active_fingerprints(ROOT))):
        raise ValueError('v2_instance_source_or_generation_mismatch')
    if file_digest(value['opa'])!=value['opa_sha256'] or value['opa_sha256'] not in approved_opa_hashes('1.18.2'):
        raise ValueError('v2_instance_tool_drift')
    for name in ('state/consumers','state/evidence','credentials'):
        target=path/name
        if target.is_symlink() or not target.is_dir() or target.stat().st_mode&0o077:
            raise ValueError('private_v2_instance_state_required')
    return path.resolve(),value


def set_option(arguments, name, value):
    """Bind instance-owned paths before invoking shared CLIs; no alternate V1 root."""
    result=list(arguments)
    found=False
    for i,item in enumerate(result):
        if item==name:
            if i+1>=len(result) or result[i+1]!=str(value):raise ValueError('v2_instance_path_override_rejected')
            found=True
        if item.startswith(name+'='):
            if item!=name+'='+str(value):raise ValueError('v2_instance_path_override_rejected')
            found=True
    return result if found else [*result,name,str(value)]


def run(command, arguments, *, instance_path=None):
    """An explicit allowlist, never a script-name or shell-command dispatcher."""
    if command=='parity':
        import argparse
        from lib.functional_parity import audit
        parser=argparse.ArgumentParser(prog='axiom-v2 parity',allow_abbrev=False)
        parser.add_argument('--reference',type=Path)
        parser.add_argument('--evidence-directory',type=Path)
        parser.add_argument('--require-complete',action='store_true')
        args=parser.parse_args(arguments)
        report=audit(ROOT,reference=args.reference,evidence_root=args.evidence_directory)
        print(json.dumps(report,indent=2))
        return 1 if args.require_complete and not report['functional_parity_complete'] else 0
    if command=='runtime':
        import governance_runtime
        return governance_runtime.main(arguments)
    if command=='check':
        if (ROOT/'.git/info/sparse-checkout').is_file():verify_active_scripts(ROOT)
        report=validate_boundaries(ROOT);print(json.dumps(report,indent=2))
        return 0 if report['passed'] else 1
    if command not in ('evidence','collector','workbench','evaluate','requirements','dcr'):
        raise ValueError('v2_entrypoint_not_supported')
    if not instance_path:raise ValueError('explicit_v2_instance_required')
    root,settings=instance(instance_path)
    if command=='dcr':
        from lib.dcr_application import run as dcr_run
        return dcr_run(arguments,root,settings)
    if command=='requirements':
        from lib.requirement_application import run as requirements_run
        return requirements_run(arguments,root,settings)
    if command=='evaluate':
        import argparse
        from lib.full_evaluation import evaluate, persist
        parser=argparse.ArgumentParser(prog='axiom-v2 evaluate',allow_abbrev=False)
        parser.add_argument('--domain',choices=('controls','architecture'),required=True)
        parser.add_argument('--input',type=Path,required=True)
        parser.add_argument('--at',required=True)
        args=parser.parse_args(arguments)
        assessment=evaluate(args.domain,args.input,opa=settings['opa'],at=args.at,source_revision=revision())
        print(json.dumps(persist(assessment,root),indent=2))
        return 0 if assessment['execution']=='complete' else 2
    if command=='collector':
        import portable_consumer_intake
        check_private_file(root/'consumer.json')
        config=read_json(root/'consumer.json')
        if config['node_id']!=settings['node_id']:raise ValueError('v2_instance_node_mismatch')
        if settings['development'] and config.get('mode')!='paused':
            raise ValueError('development_v2_instance_must_remain_paused')
        args=set_option(arguments,'--config',root/'consumer.json')
        args=set_option(args,'--root',root/'state/consumers')
        args=set_option(args,'--projection',root/'projection')
        return portable_consumer_intake.main(set_option(args,'--opa',settings['opa']))
    if command=='evidence':
        import intake_portable_evidence
        if not arguments or arguments[0] not in ('bundle','verify-local','collect','status','backup','verify-backup','restore'):
            raise ValueError('v1_migration_entrypoint_retired_in_v2')
        slot=root/('state/evidence-restore-candidate' if arguments[0]=='restore' else 'state/evidence')
        args=arguments if arguments[0]=='bundle' else set_option(arguments,'--root',slot)
        if arguments[0] in ('verify-local','collect'):args=set_option(args,'--opa',settings['opa'])
        return intake_portable_evidence.main(args)
    import serve_governance_workbench
    if settings['development'] and '--enable-pr' in arguments:
        raise ValueError('development_v2_instance_cannot_publish')
    check_private_file(root/'workbench-key.json')
    key=read_json(root/'workbench-key.json')['key']
    args=set_option(arguments,'--port',settings['port'])
    args=set_option(args,'--state-dir',ROOT/'.local/governance-workbench'/settings['node_id'])
    args=set_option(args,'--consumer-projection',root/'projection')
    previous=os.environ.get('AXIOM_WORKBENCH_KEY')
    os.environ['AXIOM_WORKBENCH_KEY']=key
    try:return serve_governance_workbench.main(args)
    finally:
        if previous is None:os.environ.pop('AXIOM_WORKBENCH_KEY',None)
        else:os.environ['AXIOM_WORKBENCH_KEY']=previous
