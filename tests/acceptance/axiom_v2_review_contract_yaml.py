"""Installed original YAML contract review wires and explicit resource boundaries."""
import argparse
from contextlib import redirect_stdout
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
    reference=fixtures/'review-planning';metadata=fixtures/'review-metadata';receipts=fixtures/'review-receipts';bindings=json.loads((fixtures/'bindings.json').read_text())
    for directory in (reference,metadata,receipts):
        for path in directory.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[directory.name+'/'+path.name]
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);before=sys.dont_write_bytecode;sys.dont_write_bytecode=True
        try:spec.loader.exec_module(value)
        finally:sys.dont_write_bytecode=before
        return value
    oracle=module('yaml_original_plan',reference/'oracle.py');receipt_oracle=module('yaml_original_receipt',receipts/'oracle.py')
    metadata_oracle=module('yaml_original_metadata',metadata/'oracle.py');pr_oracle=module('yaml_original_pr',reference/'pr-oracle.py')
    results={};at='2026-11-17T23:00:00Z';goal='Synthetic original YAML contract compatibility'
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')
    def wire(value):return json.dumps(value,sort_keys=True,indent=2)+'\n'
    def command(application,*arguments,expected=0):
        process=subprocess.run([str(prefix/'axiom-v2'),application,*map(str,arguments)],capture_output=True,text=True,timeout=180)
        assert process.returncode==expected,process.stderr
        value=json.loads(process.stderr if expected==2 else process.stdout)
        if expected!=2:
            assert value['source_revision']==args.expected_source and value['runtime_source_digest']==settings['runtime_source_digest'] and value['node_id']==settings['node_id']
            assert not any(value[k] for k in flags)
        return value
    with tempfile.TemporaryDirectory(prefix='yaml-contract-oracle-',dir=output.parent) as temporary:
        base=Path(temporary);goalfile=base/'goal.txt';goalfile.write_text(goal)
        for object_format in ('sha1','sha256'):
            for kind in ('scalar','sequence','mapping','safe-values'):
                label=object_format+'-'+kind;repository=base/label;repository.mkdir(mode=0o700)
                for name,row in oracle.target_files(reference).items():
                    path=repository/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(row['bytes']);path.chmod(row['mode'])
                path=repository/'docs/review-example.md';path.parent.mkdir(exist_ok=True);path.write_text('original\n');path.chmod(0o644)
                oracle.contract_variant(repository,kind)
                oracle.git(repository,'init','-q','-b','main','--object-format='+object_format);oracle.git(repository,'config','core.precomposeunicode','true')
                oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','synthetic YAML base');target=oracle.git(repository,'rev-parse','HEAD')
                path.write_text('committed proposal\n');oracle.git(repository,'add','--all');oracle.git(repository,'commit','-qm','synthetic YAML proposal')
                old=oracle.OriginalReview(reference,metadata,repository)
                try:
                    plan,dispatch,template,text=old.prepare(target,goal)
                    prepared=command('review-plan','prepare','--repo',repository,'--base-commit',target,'--goal-file',goalfile,'--profile','legacy-role-review-v1','--at',at)
                    expected={'review-plan.json':wire(plan),'review-dispatch.json':wire(dispatch),'review-results-template.json':wire(template),'review-dispatch.md':text}
                    assert {name:(Path(prepared['data_directory'])/name).read_text() for name in expected}==expected
                    declared=oracle.declared_results(plan);planfile=base/(label+'-plan.json');resultsfile=base/(label+'-results.json');planfile.write_text(wire(plan));resultsfile.write_text(wire(declared))
                    checked=command('review-plan','check-file','--repo',repository,'--plan-file',planfile,'--results',resultsfile,'--profile','legacy-role-review-v1','--at',at)
                    stdout=io.StringIO()
                    with redirect_stdout(stdout):assert old.check_files(reference,planfile,resultsfile)==0
                    assert (Path(checked['data_directory'])/'review-check.json').read_text()==stdout.getvalue();expected['review-check.json']=stdout.getvalue()
                    workspace='yaml-'+label
                    command('review-dispatch','init','--workspace',workspace,'--profile','legacy-role-dispatch-v1')
                    selected=command('review-dispatch','run','--workspace',workspace,'--repo',repository,'--base-ref',target,'--json','--format','receipt','--at',at)
                    assert Path(selected['stdout_file']).read_text()==wire(dispatch);expected['ordinary-dispatch-stdout.json']=wire(dispatch)
                    receipt=receipt_oracle.load(old,metadata,receipts);location=base/(label+'-exports');before=location/'old/receipt.json';old_log=location/'old/usage.jsonl';stdout=io.StringIO()
                    with redirect_stdout(stdout):assert receipt.main(['--plan',planfile,'--results',resultsfile,'--output',before,'--usage-log',old_log],recorded_at=at)==0
                    after=location/'new/receipt.json';new_log=location/'new/usage.jsonl'
                    exported=command('review-receipts','export','--repo',repository,'--plan-file',planfile,'--results',resultsfile,'--output',after,'--usage-log',new_log,'--profile','legacy-role-review-v1','--at',at)
                    assert before.read_bytes()==after.read_bytes() and old_log.read_bytes()==new_log.read_bytes()
                    assert (Path(exported['data_directory'])/'review-export-result.json').read_text()==stdout.getvalue()
                    expected.update(receipt=after.read_text(),usage=new_log.read_text(),export_stdout=stdout.getvalue())
                    original=pr_oracle.load(old,metadata,metadata_oracle);ancestor,paths=original['committed_scope'](repository,target,plan['head_commit'])
                    subject={'target_commit':target,'head_commit':plan['head_commit'],'merge_base_commit':ancestor,'changed_paths':paths,'target':original['expected_reviews'](repository,target,paths),'proposed':original['expected_reviews'](repository,plan['head_commit'],paths)}
                    event=metadata_oracle.event(original['receipt_block'](json.loads(before.read_text())),subject);report=original['inspect_pr'](repository,event);eventfile=base/(label+'-event.json');eventfile.write_text(wire(event))
                    status=command('review-pr','status','--repo',repository,'--event',eventfile,'--profile','legacy-role-review-v1','--event-profile','legacy-pr-review-event-v1','--at',at)
                    expected.update(pr_json=json.dumps(report,indent=2)+'\n',pr_md=original['render_status'](report))
                    assert (Path(status['data_directory'])/'review-status.json').read_text()==expected['pr_json']
                    assert (Path(status['data_directory'])/'review-status.md').read_text()==expected['pr_md'] and report['status']=='declared_complete'
                    results[label]={'comparison_kind':'whole_original_output_bundle','original_files_and_exits_equal':True,'files':expected}
                    for path in (planfile,resultsfile,eventfile,before,old_log,after,new_log):path.unlink()
                    shutil.rmtree(repository)
                    for application,value in [('review-plan',prepared),('review-plan',checked),('review-receipts',exported),('review-pr',status)]:
                        read=command(application,'inspect','--assessment',value['assessment_id']);assert read['retained_complete_outputs_reverified']
                        assert not read.get('target_current_state_rechecked',False) and not read.get('local_committed_scope_rechecked',False)
                    read=command('review-dispatch','inspect','--workspace',workspace,'--generation',selected['generation'])
                    assert read['retained_complete_outputs_reverified'] and not read['target_current_state_rechecked']
                    results[label+'-replay']={'comparison_kind':'retained_replay','five_product_operations_rederived':True,'caller_and_target_deleted':True,'live_check_claimed':False}
                finally:old.close()
        repository=base/'guards';target=oracle.repository_from_files(repository,oracle.target_files(reference));role=repository/'.agents/roles/repo-steward.yaml';saved_role=role.read_bytes();protocol=repository/'.agents/review-protocol.yaml';saved_protocol=protocol.read_bytes()
        original_guards={'duplicate':b'id: duplicate\n','merge':b'extension: &a {x: y}\nmerged: {<<: *a}\n','unsafe-tag':b'extension: !!python/object/apply:os.system [never-executed]\n'}
        safety_guards={'cycle':b'extension: &a [*a]\n','expanded-nodes':b'extension:\n  a: &a [x,x,x,x,x,x]\n'+b''.join(('  '+chr(98+i)+': &'+chr(98+i)+' ['+','.join(['*'+chr(97+i)]*6)+']\n').encode() for i in range(8)),
                       'expanded-bytes':b'a: &large '+b'x'*10000+b'\nextension: ['+b','.join([b'*large']*1000)+b']\n',
                       'depth':b'extension: '+b'['*65+b'x'+b']'*65+b'\n'}
        for label,extra in {**original_guards,**safety_guards}.items():
            role.write_bytes(saved_role+extra)
            if label in original_guards:
                old=oracle.OriginalReview.__new__(oracle.OriginalReview)
                try:
                    try:old.__init__(reference,metadata,repository)
                    except ValueError:pass
                    else:raise AssertionError('Original unexpectedly accepted '+label)
                finally:old.close()
            failed=command('review-plan','prepare','--repo',repository,'--base-commit',target,'--goal-file',goalfile,'--profile','legacy-role-review-v1','--at',at,expected=2)
            assert failed['diagnostics'][0] in ('review_contract_unique_string_keys_required','invalid_review_contract','review_contract_recursive_alias_not_supported','review_contract_expanded_node_budget','review_contract_expanded_byte_budget','review_contract_depth_budget')
            results['guard-'+label]={'comparison_kind':'original_negative_contract' if label in original_guards else 'application_resource_guard','v2_exit':2,'original_rejection_claimed':label in original_guards,'diagnostics':failed['diagnostics']}
        role.write_bytes(saved_role);protocol.write_bytes(saved_protocol.replace(b'independent_human_approval: false',b'independent_human_approval: &grant true'))
        assert command('review-plan','prepare','--repo',repository,'--base-commit',target,'--goal-file',goalfile,'--profile','legacy-role-review-v1','--at',at,expected=2)['diagnostics']==['review_protocol_cannot_grant_authority']
        results['guard-authority']={'comparison_kind':'application_resource_guard','v2_exit':2,'existing_authority_protection_retained':True,'original_rejection_claimed':False}
        if args.real_repo:
            real=args.real_repo.resolve();assert oracle.git(real,'rev-parse','HEAD')=='5c3b5cb50d2260bfbde736c9ac80667271406d99' and not oracle.git(real,'status','--porcelain')
            original=oracle.OriginalReview.__new__(oracle.OriginalReview)
            try:
                try:original.__init__(reference,metadata,real)
                except ValueError:pass
                else:raise AssertionError('Original unexpectedly accepted missing roles')
            finally:original.close()
            failed=command('review-plan','prepare','--repo',real,'--base-commit','5c3b5cb50d2260bfbde736c9ac80667271406d99','--path','README.md','--goal-file',goalfile,'--profile','legacy-role-review-v1','--at',at,expected=2)
            assert failed['diagnostics']==['review_target_role_contracts_required'];assert not oracle.git(real,'status','--porcelain')
            results['real-consumer-contracts']={'comparison_kind':'original_missing_contract','original_and_v2_reject':True,'contracts_injected':False,'unchanged_consumer_commit':'5c3b5cb50d2260bfbde736c9ac80667271406d99'}
    counts={kind:sum(row['comparison_kind']==kind for row in results.values()) for kind in ('whole_original_output_bundle','original_negative_contract','application_resource_guard','retained_replay','original_missing_contract')}
    assert sum(counts.values())==len(results)
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],'case_counts':counts,
        'oracle_mode':'fingerprint_bound_unchanged_original_yaml_review_functions_and_main','normalized_fields':[],'provider_invoked':False,'independent_human_approval':False,'full_functional_parity':False,
        'results':results,'business_digest':hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()}
    output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
