"""Installed real receipt exports against fingerprinted V1 APIs/main and explicit test clock."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    reference=fixtures/'review-planning';metadata=fixtures/'review-metadata';receipts=fixtures/'review-receipts';bindings=json.loads((fixtures/'bindings.json').read_text())
    for directory in (reference,metadata,receipts):
        for path in directory.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[directory.name+'/'+path.name]
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);before=sys.dont_write_bytecode;sys.dont_write_bytecode=True
        try:spec.loader.exec_module(value)
        finally:sys.dont_write_bytecode=before
        return value
    oracle=module('original_v1_receipt_plan',reference/'oracle.py');receipt_oracle=module('original_v1_receipts',receipts/'oracle.py')
    at='2026-11-17T14:00:00Z';later='2026-11-18T14:00:00Z';goal='Synthetic installed receipt declaration; no review execution';results={}
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')
    def wire(value):return json.dumps(value,sort_keys=True,indent=2)+'\n'
    def command(family,*arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),family,*map(str,arguments)],capture_output=True,text=True,timeout=180)
        assert run.returncode==expected,run.stderr
        value=json.loads(run.stderr if expected==2 else run.stdout)
        if expected!=2:
            assert value['source_revision']==args.expected_source and value['runtime_source_digest']==settings['runtime_source_digest'] and value['node_id']==settings['node_id']
            assert not any(value[k] for k in flags)
        return value
    with tempfile.TemporaryDirectory(prefix='receipt-oracle-',dir=output.parent) as temporary:
        base=Path(temporary);repository=base/'target';revision=oracle.repository_from_files(repository,oracle.target_files(reference))
        target=repository/'docs/review-example.md';target.write_text('committed branch change\n');target.chmod(0o644)
        oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','reviewed branch change');assert not oracle.git(repository,'status','--porcelain')
        original=oracle.OriginalReview(reference,metadata,repository)
        try:
            old=receipt_oracle.load(original,metadata,receipts);plan,_,template,_=original.prepare(revision,goal);ready=oracle.declared_results(plan)
            source=base/'results.json';plan_file=base/'plan.json';goal_file=base/'goal.txt';plan_file.write_text(wire(plan));goal_file.write_text(goal)
            prepared=command('review-plan','prepare','--repo',repository,'--base-commit',revision,'--goal-file',goal_file,'--profile','legacy-role-review-v1','--at',at)
            assert (Path(prepared['data_directory'])/'review-plan.json').read_text()==wire(plan)
            old_out=base/'v1/receipt.json';new_out=base/'v2/receipt.json';old_log=base/'v1/usage.jsonl';new_log=base/'v2/usage.jsonl'
            def export(dest=new_out,log=new_log,time=at,node=False,expected=0):
                arguments=['--repo',repository,'--plan',prepared['assessment_id']] if node else ['--repo',repository,'--plan-file',plan_file]
                arguments+=['--results',source,'--output',dest,'--profile','legacy-role-review-v1','--at',time]
                if log is not None:arguments+=['--usage-log',log]
                return command('review-receipts','export',*arguments,expected=expected)
            def original_export(dest=old_out,log=old_log,time=at):
                stream=io.StringIO();arguments=['--plan',plan_file,'--results',source,'--output',dest]
                if log is not None:arguments+=['--usage-log',log]
                with redirect_stdout(stream):assert old.main(arguments,recorded_at=time)==0
                return stream.getvalue()
            first=None
            for name,time,node in [('first',at,True),('retry',later,False)]:
                source.write_text(wire(ready));stdout=original_export(time=time);value=export(time=time,node=node)
                if first is None:first=value
                assert value['receipt_created']==(name=='first') and value['usage_appended']==(name=='first') and value['target_current_state_rechecked'] and value['external_files_rechecked']
                directory=Path(value['data_directory']);assert new_out.read_bytes()==old_out.read_bytes()==(directory/'review-receipt.json').read_bytes();assert new_log.read_bytes()==old_log.read_bytes()
                assert (directory/'review-export-result.json').read_text()==stdout
                results[name]={'complete_original_receipt_and_log_equal':True,'files':{'review-receipt.json':new_out.read_text(),'review-export-result.json':stdout,'usage.jsonl':new_log.read_text()}}
            stream=io.StringIO()
            with redirect_stdout(stream):assert old.main(['--summary','--usage-log',old_log],recorded_at=at)==0
            summary=command('review-receipts','summary','--usage-log',new_log,'--at',at);assert (Path(summary['data_directory'])/'review-usage-summary.json').read_text()==stream.getvalue()
            results['summary']={'complete_original_stdout_equal':True,'files':{'review-usage-summary.json':stream.getvalue()}}
            assert new_out.stat().st_mode&0o777==0o600 and new_out.parent.stat().st_mode&0o777==0o700
            assert len(old.load_review_usage(new_log))==1 and json.loads(new_out.read_bytes())['recorded_at']==at
            results['privacy']={'new_file_mode':384,'new_parent_mode':448,'private_goal_and_declared_outputs_absent':goal not in new_out.read_text() and 'synthetic declared output' not in new_out.read_text()}
            assert results['privacy']['private_goal_and_declared_outputs_absent']
            high=deepcopy(ready);high['reviews'][0]['findings']=[{'severity':'high','path':'docs/review-example.md','issue':'synthetic private finding','status':'open'}]
            for name,value in [('pending',template),('open-high',high)]:
                source.write_text(wire(value));a=base/('v1/'+name+'.json');b=base/('v2/'+name+'.json');stdout=original_export(a,None);record=export(b,None)
                assert not record['declared_ready'] and not record['usage_appended'] and a.read_bytes()==b.read_bytes()
                assert (Path(record['data_directory'])/'review-export-result.json').read_text()==stdout
                results[name]={'complete_original_wires_equal':True,'files':{'receipt.json':b.read_text(),'result.json':stdout}}
            source.write_text(wire(ready));lock=new_log.with_name(new_log.name+'.lock');lock.write_text('held by another exporter');partial=base/'v2/partial.json'
            assert export(partial,expected=2)['diagnostics']==['review_usage_locked_retry_after_exporter'];assert partial.exists() and lock.read_text()=='held by another exporter'
            first_bytes=partial.read_bytes();lock.unlink();retried=export(partial,time=later);assert partial.read_bytes()==first_bytes and not retried['receipt_created'] and not retried['usage_appended']
            results['real-lock-and-retry']={'partial_receipt_preserved':True,'foreign_lock_not_removed':True,'retry_adds_no_duplicate':True}
            # V1 concatenates these two JSON objects; V2 deliberately adds only the missing separator.
            eof=base/'v2/no-final-newline.jsonl';prefix_bytes=new_log.read_bytes().rstrip(b'\n');eof.write_bytes(prefix_bytes);source.write_text(wire(high));second=export(base/'v2/eof.json',eof)
            assert second['usage_appended'] and eof.read_bytes().startswith(prefix_bytes+b'\n') and len(old.load_review_usage(eof))==2
            results['unterminated-jsonl-correction']={'existing_prefix_unchanged':True,'separator_appended':True,'valid_events':2}
            source.write_text(wire(ready));rejected=base/'v2/rejected.json';saved=target.read_bytes();target.write_text('uncommitted\n')
            assert export(rejected,expected=2)['diagnostics']==['receipt_clean_checkout_required'];target.write_bytes(saved);assert not rejected.exists()
            for name,change in [('explicit',{'selection_mode':'explicit_paths'}),('baseless',{'base_commit':None})]:
                plan_file.write_text(wire({**plan,**change}));assert export(rejected,expected=2)['diagnostics']==['receipt_full_branch_with_base_required'];assert not rejected.exists()
            plan_file.write_text(wire(plan));invalid=deepcopy(ready);invalid['reviews'][0]['status']='PRIVATE_SCHEMA_SENTINEL';source.write_text(wire(invalid))
            failure=export(rejected,expected=2);assert failure['diagnostics']==['invalid_review_result_schema'] and 'PRIVATE_SCHEMA_SENTINEL' not in json.dumps(failure) and not rejected.exists()
            results['negative-preconditions']={'dirty_checkout_rejected':True,'explicit_or_baseless_scope_rejected':True,'schema_error_redacted':True,'receipt_created':False}
            artifact=Path(first['data_directory'])/'review-receipt.json';saved=artifact.read_bytes();artifact.write_bytes(b'{}')
            assert command('review-receipts','inspect','--assessment',first['assessment_id'],expected=2)['diagnostics']==['review_receipt_output_changed'];artifact.write_bytes(saved)
            source.unlink();plan_file.unlink();goal_file.unlink();shutil.rmtree(repository);shutil.rmtree(base/'v1');shutil.rmtree(base/'v2')
            for value in (first,summary,second):
                inspected=command('review-receipts','inspect','--assessment',value['assessment_id']);assert inspected['retained_complete_outputs_reverified'] and not inspected['target_current_state_rechecked'] and not inspected['external_files_rechecked']
            results['offline-replay']={'target_caller_files_external_outputs_deleted':True,'retained_outputs_rederived':True,'tampered_output_rejected':True,'live_target_or_files_rechecked':False}
        finally:original.close()
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],
        'oracle_mode':'original_receipt_functions_and_main_with_explicit_fixed_clock','provider_invoked':False,'agent_execution_verified':False,'independent_human_approval':False,'full_functional_parity':False,'normalized_fields':[],
        'results':results,'business_digest':hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()}
    output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
