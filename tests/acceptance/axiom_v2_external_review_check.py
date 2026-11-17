"""Installed external review files against unchanged original V1 CLI reports/exits."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
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
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prefix','fixtures','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--expected-source',required=True);parser.add_argument('--real-repo',type=Path)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    reference=fixtures/'review-planning';metadata=fixtures/'review-metadata';bindings=json.loads((fixtures/'bindings.json').read_text())
    for directory in (reference,metadata):
        for path in directory.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[directory.name+'/'+path.name]
    spec=importlib.util.spec_from_file_location('external_check_original',reference/'oracle.py');oracle=importlib.util.module_from_spec(spec)
    before=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(oracle)
    finally:sys.dont_write_bytecode=before
    results={};at='2026-11-17T22:20:00Z'
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')
    def wire(value):return json.dumps(value,sort_keys=True,indent=2)+'\n'
    def command(*arguments,expected=0):
        process=subprocess.run([str(prefix/'axiom-v2'),'review-plan',*map(str,arguments)],capture_output=True,text=True,timeout=180)
        assert process.returncode==expected,process.stderr
        value=json.loads(process.stderr if expected==2 else process.stdout)
        if expected!=2:
            assert value['source_revision']==args.expected_source and value['runtime_source_digest']==settings['runtime_source_digest'] and value['node_id']==settings['node_id']
            assert not any(value[k] for k in flags)
        return value
    with tempfile.TemporaryDirectory(prefix='external-review-check-',dir=output.parent) as temporary:
        base=Path(temporary);planfile=base/'external-plan.json';resultsfile=base/'external-results.json'
        def save(plan,declared):
            planfile.write_text(json.dumps(plan,indent=3)+'\n');resultsfile.write_text(wire(declared))
        def original(old):
            out,err=io.StringIO(),io.StringIO()
            with redirect_stdout(out),redirect_stderr(err):code=old.check_files(reference,planfile,resultsfile)
            return code,out.getvalue()
        def check(repository,expected=0):
            return command('check-file','--repo',repository,'--plan-file',planfile,'--results',resultsfile,'--profile','legacy-role-review-v1','--at',at,expected=expected)
        for object_format in ('sha1','sha256'):
            repository=base/object_format;repository.mkdir(mode=0o700)
            for name,row in oracle.target_files(reference).items():
                path=repository/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(row['bytes']);path.chmod(row['mode'])
            path=repository/'docs/review-example.md';path.parent.mkdir(exist_ok=True);path.write_text('original\n');path.chmod(0o644)
            oracle.git(repository,'init','-q','-b','main','--object-format='+object_format)
            oracle.git(repository,'config','core.precomposeunicode','true')
            oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','synthetic external check base')
            target=oracle.git(repository,'rev-parse','HEAD');path.write_text('changed\n')
            old=oracle.OriginalReview(reference,metadata,repository);retained=[]
            try:
                for scope,selected_base,paths in [('based',target,None),('baseless',None,None),('explicit',target,['docs/review-example.md'])]:
                    plan,_,template,_=old.prepare(selected_base,'Synthetic external review packet',paths)
                    ready=oracle.declared_results(plan);high=deepcopy(ready)
                    high['reviews'][0]['findings']=[{'severity':'high','path':'docs/review-example.md','issue':'Synthetic unresolved finding','status':'open'}]
                    for status,declared in [('complete',ready),('pending',template),('open-high',high)]:
                        save(plan,declared);expected,stdout=original(old);assert expected==(0 if status=='complete' else 1)
                        checked=check(repository,expected)
                        assert (Path(checked['data_directory'])/'review-check.json').read_text()==stdout
                        assert checked['schema_version']==2 and checked['plan_origin']=='external_operator_file' and checked['plan_assessment_id'] is None
                        assert checked['target_current_state_rechecked'] and checked['declared_ready']==(expected==0)
                        results[object_format+'-'+scope+'-'+status]={'comparison_kind':'whole_original_report_and_exit','original_exit':expected,'complete_original_report_equal':True,'report_stdout':stdout}
                        retained.append(checked)
                # Re-capture working-tree scope for stale source/index/mode/contract checks.
                plan,_,_,_=old.prepare(target,'Synthetic external review packet');ready=oracle.declared_results(plan);save(plan,ready)
                saved=path.read_bytes();skill=repository/'.agents/skills/repo-steward/SKILL.md';skill_raw=skill.read_bytes()
                for change in ('source','index','mode','contract'):
                    if change=='source':path.write_text('different\n')
                    elif change=='index':oracle.git(repository,'add','docs/review-example.md')
                    elif change=='mode':path.chmod(0o755)
                    else:skill.write_bytes(skill_raw+b'\nchanged\n')
                    assert original(old)[0]==2
                    assert check(repository,2)['diagnostics']==['external_review_plan_stale_target_revision_source_index_or_contract']
                    results[object_format+'-stale-'+change]={'comparison_kind':'original_negative_guard','original_and_v2_exit':2}
                    path.write_bytes(saved);path.chmod(0o644);skill.write_bytes(skill_raw)
                    if change=='index':oracle.git(repository,'reset','-q','HEAD','--','docs/review-example.md')
                extra=repository/'untracked-extra.txt';extra.write_text('new scope\n')
                assert original(old)[0]==2;check(repository,2)
                results[object_format+'-scope-added']={'comparison_kind':'original_negative_guard','original_and_v2_exit':2}
                extra.unlink()
                for label,mutate in [('authority',lambda p:p['authority'].update(independent_human_approval=True)),('roles',lambda p:p['reviews'][0].update(access='write'))]:
                    bad=deepcopy(plan);mutate(bad)
                    unsigned={key:value for key,value in bad.items() if key!='plan_digest'}
                    bad['plan_digest']=hashlib.sha256(json.dumps(unsigned,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
                    declared=deepcopy(ready);declared['plan_digest']=bad['plan_digest'];save(bad,declared)
                    assert original(old)[0]==2;check(repository,2)
                    results[object_format+'-rehashed-'+label]={'comparison_kind':'original_negative_guard','original_and_v2_exit':2}
                planfile.unlink();resultsfile.unlink();shutil.rmtree(repository)
                for checked in retained:
                    replay=command('inspect','--assessment',checked['assessment_id'])
                    assert replay['retained_complete_outputs_reverified'] and not replay['target_current_state_rechecked']
                results[object_format+'-retained-replay']={'comparison_kind':'retained_replay','caller_and_target_deleted':True,'all_nine_complete_reports_rederived':True,'current_state_claimed':False}
            finally:old.close()
        if args.real_repo:
            real=args.real_repo.resolve();assert oracle.git(real,'rev-parse','HEAD')=='5c3b5cb50d2260bfbde736c9ac80667271406d99' and not oracle.git(real,'status','--porcelain')
            native=oracle.OriginalReview.__new__(oracle.OriginalReview)
            try:
                try:native.__init__(reference,metadata,real)
                except ValueError:pass
                else:raise AssertionError('Original unexpectedly accepted missing review roles')
            finally:native.close()
            # An explicit synthetic file is only a trigger for the actual target check;
            # no role contracts or plan are written into the real consumer.
            boundary=deepcopy(plan);boundary.update(base_commit=None,selection_mode='explicit_paths',changed_files=['README.md'])
            save(boundary,ready)
            assert check(real,2)['diagnostics']==['review_target_role_contracts_required']
            results['real-consumer-contracts']={'comparison_kind':'original_missing_contract','unchanged_consumer_commit':'5c3b5cb50d2260bfbde736c9ac80667271406d99','original_and_v2_reject_missing_roles':True,'contracts_injected':False}
            assert not oracle.git(real,'status','--porcelain')
    counts={kind:sum(row['comparison_kind']==kind for row in results.values()) for kind in ('whole_original_report_and_exit','original_negative_guard','retained_replay','original_missing_contract')}
    assert sum(counts.values())==len(results)
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],
        'oracle_mode':'fingerprint_bound_unchanged_original_cli_file_checks','case_counts':counts,'provider_invoked':False,'agent_execution_verified':False,'independent_human_approval':False,
        'full_functional_parity':False,'normalized_fields':[],'results':results,'business_digest':hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()}
    output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');output.chmod(0o600)
    print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
