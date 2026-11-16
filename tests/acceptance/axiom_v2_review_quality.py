"""Installed original offline review packet/score hashes; no model/provider invocation."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True);args=parser.parse_args()
    prefix=args.prefix.resolve();settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    file=args.fixtures/'review-quality-cases.json';bindings=json.loads((args.fixtures/'bindings.json').read_text());assert hashlib.sha256(file.read_bytes()).hexdigest()==bindings[file.name]
    fixture=json.loads(file.read_text());assert fixture['synthetic'] and fixture['raw_private_packets_exported'] is False
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','model_execution_verified','trace_authenticity_verified','independent_human_approval')
    def command(arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'review-quality',*map(str,arguments)],capture_output=True,text=True,timeout=180);assert run.returncode==expected,run.stderr
        value=json.loads(run.stdout if expected==0 else run.stderr)
        if expected==0:assert all(value[k] is False for k in flags)
        return value
    def descriptors(root):return {p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in root.iterdir()}
    results={};at='2026-11-15T12:00:00Z'
    with tempfile.TemporaryDirectory(prefix='review-quality-input-',dir=args.output.resolve().parent) as temporary:
        root=Path(temporary);dataset=root/'dataset.json';responses=root/'responses.json'
        for name,data,expected in [('default',fixture['dataset'],fixture['prepared_file_hashes']),('operator',fixture['operator_dataset']['dataset'],fixture['operator_dataset']['prepared_file_hashes'])]:
            arguments=['prepare','--at',at]
            if name=='operator':dataset.write_text(json.dumps(data));arguments.extend(['--dataset',dataset])
            value=command(arguments);assert descriptors(Path(value['data_directory']))==expected;assert command(arguments)['assessment_id']==value['assessment_id'];assert command(['inspect','--assessment',value['assessment_id']])['files']==value['files']
            results[name+'-prepare']={'complete_original_file_hashes':expected,'original_whole_file_hashes_equal':True,'provider_invoked':False,'raw_private_packets_exported':False}
        cases=[*fixture['cases'],{'id':'operator-perfect','response_bundle':fixture['operator_dataset']['response_bundle'],'traces':{},'original_exit':0,'expected_grade':fixture['operator_dataset']['expected_grade']}]
        for case in cases:
            responses.write_text(json.dumps(case['response_bundle']));arguments=['grade','--responses',responses,'--at',at];paths=[]
            if case['id']=='operator-perfect':dataset.write_text(json.dumps(fixture['operator_dataset']['dataset']));arguments.extend(['--dataset',dataset])
            for index,(label,text) in enumerate(case['traces'].items()):
                path=root/('trace-'+str(index)+'.json');path.write_text(text);paths.append(path);arguments.extend(['--trace',label,path])
            value=command(arguments,expected=case['original_exit'])
            if case['original_exit']==0:
                raw=(Path(value['data_directory'])/'evaluation-grade.json').read_bytes();assert {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}==case['expected_grade'];report=json.loads(raw);assert report['provider_invoked'] is False and report['independent_human_approval'] is False
                assert command(['inspect','--assessment',value['assessment_id']])['files']==value['files']
                results[case['id']]={'original_whole_file_hash':case['expected_grade'],'original_whole_file_hash_equal':True,'provider_invoked':False,'complete_coverage':report['complete_coverage'],'trace_authenticity_verified':False}
            else:results[case['id']]={'original_exit':case['original_exit'],'new_exit':2,'accepted_assessment_created':False}
            for path in paths:path.unlink()
        for case in fixture['invalid_datasets']:
            dataset.write_text(json.dumps(case['dataset']));command(['prepare','--dataset',dataset,'--at',at],expected=2);results[case['id']]={'original_exit':case['original_exit'],'new_exit':2,'accepted_assessment_created':False}
        # Last successful score remains verifiable after all caller files disappear.
        dataset.unlink();responses.unlink();inspected=command(['inspect','--assessment',value['assessment_id']]);target=Path(inspected['data_directory'])/'evaluation-grade.json';saved=target.read_bytes();target.write_bytes(b'changed')
        assert command(['inspect','--assessment',value['assessment_id']],expected=2)['diagnostics']==['review_quality_output_changed'];target.write_bytes(saved);command(['inspect','--assessment',value['assessment_id']])
    digest=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    receipt={'schema_version':1,'source_revision':settings['source_revision'],'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],'normalized_fields':[],'provider_invoked':False,'model_execution_verified':False,'trace_authenticity_verified':False,'official_acceptance':False,'full_functional_parity':False,'raw_private_packets_exported':False,'results':results,'business_digest':digest}
    args.output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');args.output.chmod(0o600);print(json.dumps({k:v for k,v in receipt.items() if k!='results'},sort_keys=True))

if __name__=='__main__':main()
