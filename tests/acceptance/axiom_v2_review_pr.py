"""Installed actual committed PR scope and whole original V1 status wires."""
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
import yaml


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True);parser.add_argument('--real-repo',type=Path)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    reference=fixtures/'review-planning';metadata=fixtures/'review-metadata';bindings=json.loads((fixtures/'bindings.json').read_text())
    for directory in (reference,metadata):
        for path in directory.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[directory.name+'/'+path.name]
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);before=sys.dont_write_bytecode;sys.dont_write_bytecode=True
        try:spec.loader.exec_module(value)
        finally:sys.dont_write_bytecode=before
        return value
    oracle=module('native_pr_plan_oracle',reference/'oracle.py');metadata_oracle=module('native_pr_metadata_oracle',metadata/'oracle.py');native_oracle=module('native_pr_oracle',reference/'pr-oracle.py')
    at='2026-11-17T16:30:00Z';results={};flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')
    def wire(value):return json.dumps(value,sort_keys=True,indent=2)+'\n'
    def command(*arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'review-pr',*map(str,arguments)],capture_output=True,text=True,timeout=180);assert run.returncode==expected,run.stderr
        value=json.loads(run.stderr if expected==2 else run.stdout)
        if expected!=2:
            assert value['source_revision']==args.expected_source and value['runtime_source_digest']==settings['runtime_source_digest'] and value['node_id']==settings['node_id'] and not any(value[k] for k in flags)
        return value
    with tempfile.TemporaryDirectory(prefix='committed-pr-oracle-',dir=output.parent) as temporary:
        base=Path(temporary);repository=base/'target';target=oracle.repository_from_files(repository,oracle.target_files(reference));oracle.git(repository,'config','core.precomposeunicode','true')
        path=repository/'docs/review-example.md';path.write_text('committed branch change\n');path.chmod(0o644);oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','reviewed branch change');head=oracle.git(repository,'rev-parse','HEAD')
        original=oracle.OriginalReview(reference,metadata,repository);source=base/'event.json';assessments=[]
        try:
            old=native_oracle.load(original,metadata,metadata_oracle)
            def subject(repo=repository,base_commit=target,head_commit=head):
                ancestor,paths=old['committed_scope'](repo,base_commit,head_commit)
                return {'target_commit':base_commit,'head_commit':head_commit,'merge_base_commit':ancestor,'changed_paths':paths,'target':old['expected_reviews'](repo,base_commit,paths),'proposed':old['expected_reviews'](repo,head_commit,paths)}
            def receipt(scope,eligible=True):
                value=metadata_oracle.receipt(old,identity='committed-installed',eligible=eligible);union=set(scope['target']['roles'])|set(scope['proposed']['roles']);roles=sorted(union-{'repo-steward'})+(['repo-steward'] if union else [])
                value.update(head_commit=scope['head_commit'],base_commit=scope['merge_base_commit'],changed_paths=scope['changed_paths'],roles=[{'role_id':r,'status':'completed' if eligible else 'pending','execution_kind':'role_lens','execution_declared':eligible} for r in roles],validations=[{'command':c,'status':'passed' if eligible else 'not_run'} for c in sorted(set(scope['target']['validations'])|set(scope['proposed']['validations']))])
                return metadata_oracle.seal(value,old)
            def check(name,event,repo=repository):
                expected=old['inspect_pr'](repo,event);source.write_text(wire(event));value=command('status','--repo',repo,'--event',source,'--profile','legacy-role-review-v1','--event-profile','legacy-pr-review-event-v1','--at',at)
                assert value['local_committed_scope_rechecked'] and value['declared_status']==expected['status'];files={'review-status.json':json.dumps(expected,indent=2)+'\n','review-status.md':old['render_status'](expected)}
                assert {n:(Path(value['data_directory'])/n).read_text() for n in files}==files
                results[name]={'complete_original_files_equal':True,'files':files};assessments.append(value);return value
            scope=subject();ready=receipt(scope);stale=deepcopy(ready);stale['head_commit']='a'*40;metadata_oracle.seal(stale,old)
            for name,body in [('missing',''),('declared-complete',old['receipt_block'](ready)),('incomplete',old['receipt_block'](receipt(scope,False))),('stale',old['receipt_block'](stale)),('invalid','<!-- agent-review-receipt:start -->bad<!-- agent-review-receipt:end -->'),('invalid-type',{'private':'SYNTHETIC_PRIVATE_BODY'}),('oversize-body','x'*(1048576+1))]:check(name,metadata_oracle.event(body,scope))
            (repository/'docs/review-example.md').write_text('dirty checkout\n');(repository/'untracked').write_text('ignored working file\n');check('dirty-checkout',metadata_oracle.event(old['receipt_block'](ready),scope))
            oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','unrelated later current head');check('unrelated-current-head',metadata_oracle.event(old['receipt_block'](ready),scope))
            current=oracle.git(repository,'rev-parse','HEAD');check('empty-diff',metadata_oracle.event('',subject(base_commit=current,head_commit=current)))
            routing=repository/'.agents/routing/governance-agent-routing.yaml';data=yaml.safe_load(routing.read_text());role=yaml.safe_load((repository/'.agents/roles/repo-steward.yaml').read_text());role.update(id='synthetic-reviewer',skill='synthetic-reviewer')
            (repository/'.agents/roles/synthetic-reviewer.yaml').write_text(yaml.safe_dump(role));skill=repository/'.agents/skills/synthetic-reviewer/SKILL.md';skill.parent.mkdir();skill.write_text('Synthetic test data; no execution.\n');target_routing=deepcopy(data);target_routing['always_select'].append('synthetic-reviewer');routing.write_text(yaml.safe_dump(target_routing));oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','target extra role');union_base=oracle.git(repository,'rev-parse','HEAD')
            routing.write_text(yaml.safe_dump(data));(repository/'.agents/review-protocol.yaml').unlink();oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','proposed removes selection and execution protocol');union_head=oracle.git(repository,'rev-parse','HEAD');scope=subject(base_commit=union_base,head_commit=union_head)
            assert 'synthetic-reviewer' in scope['target']['roles'] and 'synthetic-reviewer' not in scope['proposed']['roles'];check('target-contract-union-without-execution-protocol',metadata_oracle.event(old['receipt_block'](receipt(scope)),scope))
            # Both paths of a real rename are observed without executing inspected code.
            oracle.git(repository,'mv','docs/review-example.md','docs/review renamed ü.md');oracle.git(repository,'commit','-qm','rename');rename_head=oracle.git(repository,'rev-parse','HEAD');scope=subject(base_commit=union_head,head_commit=rename_head);assert len(scope['changed_paths'])==2;check('rename-unicode',metadata_oracle.event('',scope))
            sha_repository=base/'sha256';sha_repository.mkdir()
            for name,row in oracle.target_files(reference).items():
                path=sha_repository/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(row['bytes']);path.chmod(row['mode'])
            oracle.git(sha_repository,'init','-q','-b','main','--object-format=sha256');oracle.git(sha_repository,'add','--all');oracle.git(sha_repository,'commit','-qm','original sha256 fixture');sha_base=oracle.git(sha_repository,'rev-parse','HEAD')
            (sha_repository/'example.txt').write_text('committed sha256 change\n');oracle.git(sha_repository,'add','--all');oracle.git(sha_repository,'commit','-qm','sha256 head');sha_head=oracle.git(sha_repository,'rev-parse','HEAD');assert len(sha_head)==64
            scope=subject(repo=sha_repository,base_commit=sha_base,head_commit=sha_head);check('sha256-git-objects',metadata_oracle.event(old['receipt_block'](receipt(scope)),scope),sha_repository)
            artifact=Path(assessments[0]['data_directory'])/'review-status.json';saved=artifact.read_bytes();artifact.write_bytes(b'{}')
            assert command('inspect','--assessment',assessments[0]['assessment_id'],expected=2)['diagnostics']==['review_pr_output_changed'];artifact.write_bytes(saved)
            source.unlink();shutil.rmtree(repository);shutil.rmtree(sha_repository)
            for value in assessments:
                inspected=command('inspect','--assessment',value['assessment_id']);assert inspected['retained_complete_outputs_reverified'] and not inspected['local_committed_scope_rechecked']
            results['private-replay']={'caller_and_target_deleted':True,'all_complete_outputs_rederived':True,'tampered_artifact_rejected':True,'live_scope_rechecked_by_inspect':False}
            if args.real_repo:
                real=args.real_repo.resolve();pin='5c3b5cb50d2260bfbde736c9ac80667271406d99';assert oracle.git(real,'rev-parse','HEAD')==pin and not oracle.git(real,'status','--porcelain')
                event={'pull_request':{'base':{'sha':pin},'head':{'sha':pin},'body':''}}
                try:old['inspect_pr'](real,event)
                except ValueError:pass
                else:raise AssertionError('Original unexpectedly accepted missing consumer roles')
                source.write_text(wire(event));failure=command('status','--repo',real,'--event',source,'--profile','legacy-role-review-v1','--event-profile','legacy-pr-review-event-v1','--at',at,expected=2);assert failure['diagnostics']==['review_steward_contract_required'];assert not oracle.git(real,'status','--porcelain')
                results['real-consumer-contract-boundary']={'unchanged_consumer_commit':pin,'original_and_product_reject_missing_roles':True,'contracts_injected':False}
        finally:original.close()
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],'oracle_mode':'unchanged_original_committed_git_scope_contract_union_status_functions','provider_invoked':False,'agent_execution_verified':False,'independent_human_approval':False,'full_functional_parity':False,'normalized_fields':[],
        'results':results,'business_digest':hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()}
    output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
