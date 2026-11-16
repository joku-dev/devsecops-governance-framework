"""Installed original agent-selection metadata wires; no agents/models invoked."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True);args=parser.parse_args()
    prefix=args.prefix.resolve();settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    fixture_path=args.fixtures/'agent-usage-cases.json';bindings=json.loads((args.fixtures/'bindings.json').read_text());assert hashlib.sha256(fixture_path.read_bytes()).hexdigest()==bindings[fixture_path.name]
    fixture=json.loads(fixture_path.read_text());assert fixture['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','agent_execution_verified','human_approval_verified')
    names={'result.json':'generated/agent-usage/agent-usage-summary.json','result.md':'docs/operations/agent-usage-snapshot-latest.md'}
    def command(arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'agent-usage',*map(str,arguments)],capture_output=True,text=True,timeout=180);assert run.returncode==expected,run.stderr
        value=json.loads(run.stdout if expected==0 else run.stderr)
        if expected==0:assert all(value[k] is False for k in flags)
        return value
    results={}
    with tempfile.TemporaryDirectory(prefix='agent-usage-input-',dir=args.output.resolve().parent) as temporary:
        root=Path(temporary);log=root/'events.jsonl'
        for c in fixture['cases']:
            log.write_text(c['usage_log_wire']);arguments=['create','--usage-log',log,'--source-log-label',c['source_log_label'],'--latest-count',c['latest_count'],'--at',c['generated_at']]
            value=command(arguments);assert value['source_origin']=={'kind':'operator','present':True}
            actual={name:(Path(value['data_directory'])/label).read_text() for name,label in names.items()};assert actual==c['expected_wires']
            assert command(arguments)['assessment_id']==value['assessment_id'];log.unlink();assert command(['inspect','--assessment',value['assessment_id']])['files']==value['files']
            results[c['id']]={'wires':actual,'latest_count_requested':value['latest_count_requested'],'latest_count_effective':value['latest_count_effective'],'original_wire_bytes_equal':True,'agent_execution_verified':False,'human_approval_verified':False}
        default=command(['create','--at',fixture['cases'][0]['generated_at']]);assert default['source_origin']['kind']=='committed';assert default['source_origin']['revision']==settings['source_revision']
        snapshot=json.loads((Path(default['data_directory'])/names['result.json']).read_text());assert snapshot['source_log']=='generated/agent-usage/agent-usage.jsonl'
        results['committed-legacy-origin']={'source_origin_kind':default['source_origin']['kind'],'source_log':snapshot['source_log'],'event_count':snapshot['event_count'],'agent_execution_verified':False,'current_private_execution_history':False}
        missing=command(['create','--usage-log',log,'--source-log-label','missing-log','--at',fixture['cases'][0]['generated_at']]);assert missing['source_origin']['present'] is False
        snapshot=json.loads((Path(missing['data_directory'])/names['result.json']).read_text());assert snapshot['event_count']==0
        results['missing-operator-log']={'event_count':0,'source_present':False,'agent_execution_verified':False}
        path=Path(value['data_directory'])/names['result.json'];saved=path.read_bytes();path.write_bytes(b'changed')
        assert command(['inspect','--assessment',value['assessment_id']],expected=2)['diagnostics']==['agent_usage_output_changed'];path.write_bytes(saved);command(['inspect','--assessment',value['assessment_id']])
    digest=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    value={'schema_version':1,'source_revision':settings['source_revision'],'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],'normalized_fields':[],'provider_invoked':False,'official_acceptance':False,'full_functional_parity':False,'agent_execution_verified':False,'human_approval_verified':False,'results':results,'business_digest':digest}
    args.output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');args.output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))

if __name__=='__main__':main()
