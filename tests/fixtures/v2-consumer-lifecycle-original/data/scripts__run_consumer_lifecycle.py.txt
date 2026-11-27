#!/usr/bin/env python3
"""Prepare, verify or operate the bounded consumer lifecycle through reviewed PRs."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import subprocess
import tempfile
from lib.governance_lifecycle.adapter import strict_json,json_bytes
from lib.governance_lifecycle.contracts import ROOT,require
from lib.governance_lifecycle.live_preparation import revision_ref
from lib.governance_lifecycle.consumer_contracts import MODEL,load_model
from lib.governance_lifecycle.consumer_admission import VALIDATION_LEDGER,append_capture
from lib.governance_lifecycle.consumer_evidence import collect_preflight
from lib.governance_lifecycle.consumer_actions import ACTION_LEDGER,collect_action,append_action_snapshot
from lib.governance_lifecycle.consumer_acceptance import (
    capture,verify_provider,generate,validate,validate_publication,check_prefix,manifest,REQUEST_PATH,
)
from lib.governance_lifecycle.store import load_transactions


def prepare_acceptance(discussion_number,repo=ROOT):
    root=Path(repo);profile,binding=load_model(root)
    value={'schema_version':'0.1.0','repository_id':'joku-dev/devsecops-governance-framework',
        'scope':profile['scope'],'operating_profile_ref':revision_ref(profile),'role_binding_ref':revision_ref(binding),
        'created_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
        'discussion_number':discussion_number,'required_subject_id':binding['assignments']['role_registry_owner'],
        'required_role':'role_registry_owner','request_type':'consumer-lifecycle-operating-acceptance',
        'purpose':'accept_manual_demo_operation_readiness_pilot_with_individual_personal_action_consent',
        'permitted_operations':['manual_observation_intake','personal_action_intake','pilot_state_publication_via_pr'],
        'excluded_operations':['automatic_remediation','blocking_enforcement','direct_main_writes','waiver_authority',
                               'baseline_changes','other_consumers','bitbucket_operation'],
        'promotion_scope':'new_verified_demo_operation_readiness_receipts_and_personal_actions_only',
        'implementation_manifest':manifest(root),
        'channel_probe_comment':'https://github.com/joku-dev/devsecops-governance-framework/pull/87#issuecomment-5653982008'}
    path=root/REQUEST_PATH;require(not path.exists(),'Existing acceptance request cannot be overwritten')
    path.write_bytes(json_bytes(value));generate(root)
    return value


def run(operation,*,run_id=None,request_path=None,repo=ROOT):
    root=Path(repo)
    if operation=='acceptance':capture(root)
    else:
        verify_provider(root)
        if operation=='observe':
            require(run_id is not None and run_id.isdigit() and int(run_id)>0,'Positive source run ID required')
            with tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)/'capture';collect_preflight(run_id,directory,repo_root=root)
                at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
                append_capture(root/VALIDATION_LEDGER,directory,load_model(root)[0],recorded_at=at,
                    expected_sequence=len(load_transactions(root/VALIDATION_LEDGER)))
        elif operation=='action':
            require(bool(request_path),'Committed consumer action request required')
            path=(root/request_path).resolve()
            require(path.is_relative_to((root/MODEL/'action-requests').resolve()) and path.is_file(),'Request outside consumer action directory')
            subprocess.run(['git','ls-files','--error-unmatch','--',str(path.relative_to(root.resolve()))],cwd=root,check=True,capture_output=True)
            snapshot=collect_action(strict_json(path.read_bytes()),repo=root)
            require(snapshot['capture_method']=='github_api_get_via_gh','Actual provider capture required')
            at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
            append_action_snapshot(root,snapshot,recorded_at=at,expected_sequence=len(load_transactions(root/ACTION_LEDGER)))
        elif operation!='refresh':raise ValueError('Unknown consumer operation')
    generate(root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation',choices=('acceptance','observe','action','refresh','validate','prepare-acceptance','preflight'),required=True)
    parser.add_argument('--source-run-id');parser.add_argument('--request-path');parser.add_argument('--base-ref')
    parser.add_argument('--verify-provider',action='store_true');parser.add_argument('--discussion-number',type=int)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.operation=='prepare-acceptance':
        require(type(args.discussion_number) is int and args.discussion_number>0,'Positive discussion number required')
        prepare_acceptance(args.discussion_number)
    elif args.operation=='preflight':
        require(args.output is not None and args.source_run_id is not None,'Preflight requires run and output')
        print(collect_preflight(args.source_run_id,args.output)['criterion'])
    elif args.operation=='validate':
        if args.base_ref:check_prefix(ROOT,args.base_ref)
        if args.verify_provider:
            require(bool(args.base_ref),'Independent publication verification requires immutable base')
            validate_publication(ROOT,args.base_ref)
        else:validate(ROOT)
        print('Consumer lifecycle validated')
    else:run(args.operation,run_id=args.source_run_id,request_path=args.request_path)
