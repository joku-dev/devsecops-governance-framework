"""Installed metadata wire comparison against original V1 function bodies; no review execution."""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve();settings=json.loads((prefix/'instance/instance.json').read_text())
    assert settings['source_revision']==args.expected_source and not settings['development']
    reference=fixtures/'review-metadata';bindings=json.loads((fixtures/'bindings.json').read_text())
    for path in reference.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings['review-metadata/'+path.name]
    spec=importlib.util.spec_from_file_location('original_v1_review_metadata',reference/'oracle.py');oracle=importlib.util.module_from_spec(spec)
    before=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(oracle)
    finally:sys.dont_write_bytecode=before
    contract,old=oracle.load(reference);at='2026-11-17T12:30:00Z';receipt=oracle.receipt(old);subject=oracle.subject();results={}
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')
    def command(*arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'review-metadata',*map(str,arguments)],capture_output=True,text=True,timeout=180)
        assert run.returncode==expected,run.stderr
        return json.loads(run.stdout if expected==0 else run.stderr)
    def exercise(base,name,operation,files,expected,profile=None):
        paths={}
        for filename,raw in files.items():
            path=base/(name+'-'+filename);path.write_bytes(raw);paths[filename]=path
        arguments=[operation,'--at',at]
        for flag,filename in {'--receipt':'receipt.json','--body':'description.txt','--usage-log':'usage.jsonl','--event':'event.json','--subject':'subject.json'}.items():
            if filename in paths:arguments.extend([flag,paths[filename]])
        if profile:arguments.extend(['--event-profile',profile])
        value=command(*arguments);assert value['source_revision']==args.expected_source and value['runtime_source_digest']==settings['runtime_source_digest'] and value['node_id']==settings['node_id']
        assert not any(value[k] for k in flags)
        actual={key:(Path(value['data_directory'])/key).read_text() for key in expected};assert actual==expected
        for path in paths.values():path.unlink()
        assert command('inspect','--assessment',value['assessment_id'])['retained_complete_outputs_reverified']
        artifact=Path(value['data_directory'])/next(iter(expected));saved=artifact.read_bytes();artifact.write_bytes(b'changed')
        assert command('inspect','--assessment',value['assessment_id'],expected=2)['execution']=='error'
        artifact.write_bytes(saved);assert command('inspect','--assessment',value['assessment_id'])['retained_complete_outputs_reverified']
        results[name]={'complete_original_metadata_wires_equal':True,'current_revision_checked':False,'agent_execution_verified':False,'files':actual}
    def raw(v):return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
    with tempfile.TemporaryDirectory(prefix='review-metadata-fixture-',dir=output.parent) as temporary:
        base=Path(temporary)
        for name,eligible,kind in [('completed',True,'role_lens'),('pending',False,'human'),('declared-human',True,'human')]:
            value=oracle.receipt(old,identity=name,eligible=eligible,kind=kind)
            exercise(base,'receipt-'+name,'receipt',{'receipt.json':raw(value)},{'review-receipt.md':old['receipt_block'](value)+'\n'})
        block=old['receipt_block'](receipt)
        exercise(base,'parsed-receipt','parse-body',{'description.txt':('description\n'+block+'\n').encode()},{'parsed-review-receipt.json':json.dumps(old['parse_receipt'](block),indent=2)+'\n'})
        for name,rows in [('empty',[]),('two',[receipt,oracle.receipt(old,identity='other',eligible=False,kind='subagent')])]:
            exercise(base,'summary-'+name,'usage-summary',{'usage.jsonl':b''.join((json.dumps(r)+'\n').encode() for r in rows)},{'review-usage-summary.json':json.dumps(old['summarize_review_usage'](rows),indent=2)+'\n'})
        stale=deepcopy(receipt);stale['head_commit']='d'*40;oracle.seal(stale,old)
        for name,body in [('missing',''),('valid',block),('incomplete',old['receipt_block'](oracle.receipt(old,eligible=False))),('stale',old['receipt_block'](stale)),('invalid',block*2)]:
            event=oracle.event(body,subject);report=old['status_with_declared_inputs'](event,subject)
            exercise(base,'status-'+name,'status',{'event.json':raw(event),'subject.json':raw(subject)},
                {'review-status.json':json.dumps(report,indent=2)+'\n','review-status.md':old['render_status'](report)},'legacy-pr-review-event-v1')
        invalid=base/'invalid.json';invalid.write_text('{}');assert command('receipt','--receipt',invalid,'--at',at,expected=2)['execution']=='error'
        duplicate=base/'duplicate.jsonl';duplicate.write_text((json.dumps(receipt)+'\n')*2)
        assert command('usage-summary','--usage-log',duplicate,'--at',at,expected=2)['execution']=='error'
        missing=command('usage-summary','--usage-log',base/'never-created.jsonl','--at',at);assert missing['source_origin']=={'kind':'operator','present':False}
        assert (Path(missing['data_directory'])/'review-usage-summary.json').read_text()==json.dumps(old['summarize_review_usage']([]),indent=2)+'\n'
        results['negative-and-missing']={'invalid_receipt_rejected':True,'duplicate_receipt_rejected':True,'missing_log_original_empty_summary_equal':True,'no_agent_or_native_reader_invoked':True}
    canonical=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],'oracle_mode':contract['oracle_mode'],'subject_scope':'operator_declaration_only','current_revision_checked':False,'native_reader_invoked':False,'independent_human_approval':False,'full_functional_parity':False,'normalized_fields':[],'results':results,'business_digest':canonical(results)}
    output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
