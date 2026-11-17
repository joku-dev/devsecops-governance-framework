"""Installed actual local-Git planning/check wires against fingerprinted original V1."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True);parser.add_argument('--real-repo',type=Path)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    reference=fixtures/'review-planning';metadata=fixtures/'review-metadata';bindings=json.loads((fixtures/'bindings.json').read_text())
    for directory in (reference,metadata):
        for path in directory.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[directory.name+'/'+path.name]
    spec=importlib.util.spec_from_file_location('original_v1_review_planning',reference/'oracle.py');oracle=importlib.util.module_from_spec(spec)
    before=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(oracle)
    finally:sys.dont_write_bytecode=before
    at='2026-11-17T14:00:00Z';goal='Synthetic installed whole-wire review';results={}
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')
    def wire(value):return json.dumps(value,sort_keys=True,indent=2)+'\n'
    def command(*arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'review-plan',*map(str,arguments)],capture_output=True,text=True,timeout=180)
        assert run.returncode==expected,run.stderr
        value=json.loads(run.stderr if expected==2 else run.stdout)
        if expected!=2:
            assert value['source_revision']==args.expected_source and value['runtime_source_digest']==settings['runtime_source_digest'] and value['node_id']==settings['node_id']
            assert not any(value[k] for k in flags)
        return value
    with tempfile.TemporaryDirectory(prefix='local-review-oracle-',dir=output.parent) as temporary:
        base=Path(temporary);repository=base/'target';revision=oracle.repository_from_files(repository,oracle.target_files(reference))
        (repository/'docs/review-example.md').write_text('changed\n');path=repository/'model/controls/synthetic.yaml';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic: true\n');path.chmod(0o644)
        (repository/'docs/review-example.md').chmod(0o644);goal_path=base/'goal.txt';goal_path.write_text(goal)
        original=oracle.OriginalReview(reference,metadata,repository)
        try:
            plan,dispatch,template,text=original.prepare(revision,goal)
            prepared=command('prepare','--repo',repository,'--base-commit',revision,'--goal-file',goal_path,'--profile','legacy-role-review-v1','--at',at)
            assert prepared['target_current_state_rechecked']
            expected={'review-plan.json':wire(plan),'review-dispatch.json':wire(dispatch),'review-results-template.json':wire(template),'review-dispatch.md':text}
            assert {n:(Path(prepared['data_directory'])/n).read_text() for n in expected}==expected
            results['prepared']={'complete_original_files_equal':True,'files':expected}
            directory=command('prepare','--repo',repository,'--base-commit',revision,'--goal-file',goal_path,'--profile','legacy-role-review-v1','--path','docs/','--at',at,expected=2)
            assert directory['diagnostics']==['review_regular_file_required']
            alias_plan,alias_dispatch,alias_template,alias_text=original.prepare(revision,goal,['docs/review-example.md/'])
            alias=command('prepare','--repo',repository,'--base-commit',revision,'--goal-file',goal_path,'--profile','legacy-role-review-v1','--path','docs/review-example.md/','--at',at)
            alias_files={'review-plan.json':wire(alias_plan),'review-dispatch.json':wire(alias_dispatch),'review-results-template.json':wire(alias_template),'review-dispatch.md':alias_text}
            assert {n:(Path(alias['data_directory'])/n).read_text() for n in alias_files}==alias_files
            results['directory-and-file-alias']={'existing_directory_rejected':True,'original_trailing_slash_file_wires_equal':True,'files':alias_files}
            ready=oracle.declared_results(plan);high=deepcopy(ready);high['reviews'][0]['findings']=[{'severity':'high','path':'model/controls/synthetic.yaml','issue':'synthetic unresolved finding','status':'open'}]
            checked=None
            for name,value in [('pending',template),('declared-complete',ready),('open-high',high)]:
                source=base/(name+'.json');source.write_text(wire(value));report=original.review.check_results(repository,plan,value)
                checked=command('check','--repo',repository,'--plan',prepared['assessment_id'],'--results',source,'--at',at,expected=0 if report['eligible_for_human_review'] else 1)
                assert checked['target_current_state_rechecked'] and checked['declared_ready']==report['eligible_for_human_review']
                assert (Path(checked['data_directory'])/'review-check.json').read_text()==wire(report)
                results[name]={'complete_original_report_equal':True,'files':{'review-check.json':wire(report)}};source.unlink()
            source=base/'results.json';source.write_text(wire(ready));target=repository/'docs/review-example.md';saved=target.read_bytes()
            for name in ('source','index','mode','contract'):
                contract=repository/'.agents/skills/repo-steward/SKILL.md';contract_saved=contract.read_bytes()
                if name=='source':target.write_text('changed again\n')
                elif name=='index':oracle.git(repository,'add','docs/review-example.md')
                elif name=='mode':target.chmod(0o755)
                else:contract.write_bytes(contract_saved+b'\nchanged\n')
                failed=command('check','--repo',repository,'--plan',prepared['assessment_id'],'--results',source,'--at',at,expected=2)
                assert failed['diagnostics']==['review_plan_stale_target_revision_source_index_or_contract']
                target.write_bytes(saved);target.chmod(0o644);contract.write_bytes(contract_saved)
                if name=='index':oracle.git(repository,'reset','-q','HEAD','--','docs/review-example.md')
                results['stale-'+name]={'fresh_local_git_check_rejected':True}
            artifact=Path(prepared['data_directory'])/'review-plan.json';saved_artifact=artifact.read_bytes();artifact.write_bytes(b'changed')
            assert command('inspect','--assessment',prepared['assessment_id'],expected=2)['diagnostics']==['review_planning_output_changed'];artifact.write_bytes(saved_artifact)
            source.unlink();goal_path.unlink();shutil.rmtree(repository)
            for value in (prepared,checked):
                inspected=command('inspect','--assessment',value['assessment_id']);assert inspected['retained_complete_outputs_reverified'] and not inspected['target_current_state_rechecked']
            results['private-replay']={'caller_and_target_deleted':True,'complete_retained_outputs_rederived':True,'tampered_output_rejected':True,'live_git_rechecked_by_inspect':False}
        finally:original.close()
        if args.real_repo:
            real=args.real_repo.resolve();assert oracle.git(real,'rev-parse','HEAD')=='5c3b5cb50d2260bfbde736c9ac80667271406d99' and not oracle.git(real,'status','--porcelain')
            goal_path.write_text(goal)
            if not (real/'.agents/roles').is_dir():
                native=oracle.OriginalReview.__new__(oracle.OriginalReview)
                try:
                    try:native.__init__(reference,metadata,real)
                    except ValueError:pass
                    else:raise AssertionError('Original V1 unexpectedly accepted missing roles')
                finally:native.close()
                failure=command('prepare','--repo',real,'--base-commit','5c3b5cb50d2260bfbde736c9ac80667271406d99','--goal-file',goal_path,'--profile','legacy-role-review-v1','--path','README.md','--at',at,expected=2)
                assert failure['diagnostics']==['review_target_role_contracts_required']
                results['real-consumer-contracts']={'unchanged_consumer_commit':'5c3b5cb50d2260bfbde736c9ac80667271406d99','original_and_v2_reject_missing_governance_roles':True,'contracts_injected':False}
            else:raise AssertionError('Real consumer role-contract profile needs explicit review')
            assert not oracle.git(real,'status','--porcelain')
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],
        'oracle_mode':'unchanged_original_local_git_plan_check_functions','provider_invoked':False,'agent_execution_verified':False,'independent_human_approval':False,'full_functional_parity':False,'normalized_fields':[],
        'results':results,'business_digest':hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()}
    output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
