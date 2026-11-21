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
        parser.add_argument('--reference',type=Path,help='Local Git source containing the immutable V1 reference.')
        parser.add_argument('--evidence-directory',type=Path,help='Use operator receipt metadata instead of the packaged evidence directory.')
        parser.add_argument('--require-complete',action='store_true',help='Fail unless every original subject and the frozen source scope are verified.')
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
    if command=='pilot-action-intake' and not instance_path and arguments[:1]==['replay']:
        from lib.pilot_action_intake_application import run as action_intake_run
        return action_intake_run(arguments)
    if command=='pilot-action-requests' and not instance_path and arguments[:1]==['replay']:
        from lib.pilot_action_preparation_application import run as preparation_run
        return preparation_run(arguments)
    if command=='personal-channel' and not instance_path and arguments[:1]==['replay']:
        from lib.personal_channel_application import run as personal_channel_run
        return personal_channel_run(arguments)
    if command=='pilot-projections' and not instance_path and arguments[:1]==['replay']:
        from lib.pilot_projection_application import run as pilot_projection_run
        return pilot_projection_run(arguments)
    if command=='lifecycle-candidates' and not instance_path and arguments[:1]==['replay']:
        from lib.lifecycle_candidate_preparation_application import run as candidate_preparation_run
        return candidate_preparation_run(arguments)
    if command=='documentation-reconciliation' and not instance_path and arguments[:1]==['replay']:
        from lib.documentation_reconciliation_application import run as documentation_run
        return documentation_run(arguments)
    if command=='synthetic-ledger' and not instance_path and arguments[:1]==['replay']:
        from lib.synthetic_ledger_application import run as ledger_run
        return ledger_run(arguments)
    if command=='synthetic-lifecycle' and not instance_path and arguments[:1]==['replay']:
        from lib.synthetic_lifecycle_application import run as lifecycle_run
        return lifecycle_run(arguments)
    if command=='document-rendering' and not instance_path and arguments[:1]==['replay']:
        from lib.document_rendering_application import run as document_rendering_run
        return document_rendering_run(arguments)
    if command=='workbook-import' and not instance_path and arguments[:1]==['replay']:
        from lib.workbook_import_application import run as workbook_import_run
        return workbook_import_run(arguments)
    if command=='requirement-review' and not instance_path and arguments[:1]==['replay']:
        from lib.requirement_review_application import run as review
        return review(arguments)
    if command=='requirement-validation' and not instance_path and arguments[:1]==['replay']:
        from lib.requirement_validation_application import run as requirement_validation_run
        return requirement_validation_run(arguments)
    if command=='operations-report' and not instance_path and arguments[:1]==['replay']:
        from lib.operations_application import run as operations_run
        return operations_run(arguments)
    if command not in ('evidence','collector','workbench','evaluate','requirements','dcr','collect-source','measured','supplement','typed','results','reports','source-inspection','provenance','pipeline-evidence','agent-usage','review-quality','vulnerability-evidence','review-metadata','review-plan','review-receipts','review-pr','review-dispatch','review-run','attestation','intake-records','validation','artifact-hygiene','candidate-index','self-security','sbom','operations-report','requirement-validation','requirement-review','workbook-import','document-rendering','synthetic-lifecycle','synthetic-ledger','documentation-reconciliation','lifecycle-candidates','pilot-projections','personal-channel','pilot-action-requests','pilot-action-intake'):
        raise ValueError('v2_entrypoint_not_supported')
    if not instance_path:raise ValueError('explicit_v2_instance_required')
    root,settings=instance(instance_path)
    if command=='pilot-action-intake':
        from lib.pilot_action_intake_application import run as action_intake_run
        return action_intake_run(arguments,root,settings)
    if command=='pilot-action-requests':
        from lib.pilot_action_preparation_application import run as preparation_run
        return preparation_run(arguments,root,settings)
    if command=='personal-channel':
        from lib.personal_channel_application import run as personal_channel_run
        return personal_channel_run(arguments,root,settings)
    if command=='pilot-projections':
        from lib.pilot_projection_application import run as pilot_projection_run
        return pilot_projection_run(arguments,instance_path,settings)
    if command=='lifecycle-candidates':
        from lib.lifecycle_candidate_preparation_application import run as candidate_preparation_run
        return candidate_preparation_run(arguments,root,settings)
    if command=='documentation-reconciliation':
        from lib.documentation_reconciliation_application import run as documentation_run
        return documentation_run(arguments,root,settings)
    if command=='synthetic-ledger':
        from lib.synthetic_ledger_application import run as ledger_run
        return ledger_run(arguments,root,settings)
    if command=='synthetic-lifecycle':
        from lib.synthetic_lifecycle_application import run as lifecycle_run
        return lifecycle_run(arguments,root,settings)
    if command=='document-rendering':
        from lib.document_rendering_application import run as document_rendering_run
        return document_rendering_run(arguments,root,settings)
    if command=='workbook-import':
        from lib.workbook_import_application import run as workbook_import_run
        return workbook_import_run(arguments,root,settings)
    if command=='requirement-review':
        from lib.requirement_review_application import run as review
        return review(arguments,root,settings)
    if command=='requirement-validation':
        from lib.requirement_validation_application import run as requirement_validation_run
        return requirement_validation_run(arguments,root,settings)
    if command=='operations-report':
        from lib.operations_application import run as operations_run
        return operations_run(arguments,root,settings)
    if command=='sbom':
        from export_axiom_v2_sbom import main as sbom_main
        node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
        return sbom_main(arguments,instance_root=root,node=node)
    if command=='self-security':
        from lib.self_security_application import run as security_run
        return security_run(arguments,root,settings)
    if command=='candidate-index':
        from lib.candidate_index_application import run as candidate_index_run
        return candidate_index_run(arguments,root,settings)
    if command=='artifact-hygiene':
        from lib.artifact_hygiene_application import run as hygiene_run
        return hygiene_run(arguments,root,settings)
    if command=='validation':
        from lib.validation_application import run as validation_run
        return validation_run(arguments,root,settings)
    if command=='intake-records':
        from lib.intake_recording_application import run as intake_record_run
        return intake_record_run(arguments,root,settings)
    if command=='attestation':
        from lib.attestation_application import run as attestation_run
        return attestation_run(arguments,root,settings)
    if command=='review-run':
        from lib.review_execution_application import run as execution_run
        return execution_run(arguments,root,settings)
    if command=='review-dispatch':
        from lib.review_dispatch_application import run as dispatch_run
        return dispatch_run(arguments,root,settings)
    if command=='review-pr':
        from lib.review_pr_application import run as review_pr_run
        return review_pr_run(arguments,root,settings)
    if command=='review-receipts':
        from lib.review_receipts_application import run as receipt_run
        return receipt_run(arguments,root,settings)
    if command=='review-plan':
        from lib.review_planning_application import run as review_plan_run
        return review_plan_run(arguments,root,settings)
    if command=='review-metadata':
        from lib.review_metadata_application import run as review_run
        return review_run(arguments,root,settings)
    if command=='vulnerability-evidence':
        from lib.vulnerability_application import run as vulnerability_run
        return vulnerability_run(arguments,root,settings)
    if command=='review-quality':
        from lib.review_quality_application import run as quality_run
        return quality_run(arguments,root,settings)
    if command=='agent-usage':
        from lib.agent_usage_application import run as usage_run
        return usage_run(arguments,root,settings)
    if command=='pipeline-evidence':
        from lib.pipeline_application import run as pipeline_run
        return pipeline_run(arguments,root,settings)
    if command=='provenance':
        from lib.provenance_application import run as provenance_run
        return provenance_run(arguments,root,settings)
    if command=='source-inspection':
        from lib.source_inspection_application import run as inspection_run
        return inspection_run(arguments,root,settings)
    if command=='reports':
        from lib.report_application import run as reports_run
        return reports_run(arguments,root,settings)
    if command=='results':
        from lib.result_application import run as results_run
        return results_run(arguments,root,settings)
    if command=='typed':
        from lib.typed_evidence_application import run as typed_run
        return typed_run(arguments,root,settings)
    if command=='supplement':
        from lib.supplement_application import run as supplement_run
        return supplement_run(arguments,root,settings)
    if command=='measured':
        from lib.measured_application import run as measured_run
        return measured_run(arguments,root)
    if command=='collect-source':
        from lib.source_collection import run as collection_run
        return collection_run(arguments,root)
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
        parser.add_argument('--domain',choices=('controls','architecture','devsecops-release'),required=True)
        parser.add_argument('--input',type=Path,required=True)
        parser.add_argument('--at',required=True)
        parser.add_argument('--fail-on-findings',action='store_true')
        args=parser.parse_args(arguments)
        assessment=evaluate(args.domain,args.input,opa=settings['opa'],at=args.at,source_revision=revision())
        print(json.dumps(persist(assessment,root),indent=2))
        if assessment['execution']!='complete':return 2
        summary=assessment['report']['summary']
        return 1 if args.fail_on_findings and summary.get('finding_count',summary.get('fail',0)) else 0
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
    from lib.workbench_application import run as workbench
    return workbench(root, settings, arguments)
