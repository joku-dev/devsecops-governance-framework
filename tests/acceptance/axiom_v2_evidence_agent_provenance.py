"""Installed private declared associations versus original V1 record/index/check wires."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expected-source',required=True);args=parser.parse_args()
    prefix=args.prefix.resolve();settings=json.loads((prefix/'instance/instance.json').read_text())
    assert settings['source_revision']==args.expected_source and not settings['development']
    path=args.fixtures/'evidence-agent-provenance-cases.json';bindings=json.loads((args.fixtures/'bindings.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[path.name]
    fixture=json.loads(path.read_text());assert fixture['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred',
           'operating_acceptance_inherited','published','agent_execution_verified','human_approval_verified','subject_authenticity_verified')
    def command(workspace,*arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'provenance','--workspace',workspace,*map(str,arguments)],
                           capture_output=True,text=True,timeout=180)
        assert run.returncode==expected,run.stderr
        return json.loads(run.stdout if expected in (0,1) else run.stderr)
    results={};workspace='host-evidence-associations'
    initialized=command(workspace,'init');assert initialized['node_id']==settings['node_id']
    assert initialized['runtime_source_digest']==settings['runtime_source_digest']
    assert all(initialized[key] is False for key in flags)
    with tempfile.TemporaryDirectory(prefix='association-input-',dir=args.output.resolve().parent) as temporary:
        root=Path(temporary).resolve();metadata=root/'metadata.json';source=root/'source.json';source.write_text(json.dumps(fixture['source']))
        for case in fixture['cases']:
            metadata.write_text(json.dumps(case['metadata']))
            receipt=command(workspace,'record','--metadata',metadata,'--source',source,'--at',case['at'])
            value=receipt['result'];assert all(value[key] is False for key in flags)
            assert value['incoming_record']==case['incoming_record'] and value['record_path']==case['record_path']
            data=Path(receipt['data_directory']);assert (data/value['record_path']).read_bytes()==case['record_wire'].encode()
            conflicts={p.relative_to(data).as_posix():p.read_text() for p in sorted((data/'status/intake-conflicts/evidence-agent-provenance').rglob('*.json'))}
            assert conflicts==case['conflict_wires']
            inspected=command(workspace,'inspect','--generation',receipt['generation'])
            assert all(inspected[key] is False for key in flags)
            report=command(workspace,'index','--scope','all','--at',fixture['at']);data=Path(report['data_directory'])
            name='status/evidence-agent-provenance-index.json'
            assert (data/name).read_bytes()==case['index_wire'].encode()
            assert command(workspace,'inspect')['reports']['index']=='current'
            results[case['id']]={'incoming_record':value['incoming_record'],'record_path':value['record_path'],
                'attempted_path':value['attempted_path'],'record_wire':case['record_wire'],'conflict_wires':conflicts,
                'index_wire':case['index_wire'],'outcome':value['outcome'],'original_wire_bytes_equal':True}
        empty=command(workspace,'index','--scope','committed','--at',fixture['at'])
        assert (Path(empty['data_directory'])/'status/evidence-agent-provenance-index.json').read_bytes()==fixture['empty_index_wire'].encode()
        results['committed-empty']={'index_wire':fixture['empty_index_wire'],'original_wire_bytes_equal':True}
        records=json.loads(fixture['cases'][-1]['index_wire'])['records'];paths=sorted({c['record_path'] for c in fixture['cases']})
        for case in fixture['validation_cases']:
            name='host-association-check-'+case['id'];command(name,'init')
            for label in paths:
                record=next(r for r in records if r['provenance_id'][:12] in label)
                raw=case.get('record_overrides',{}).get(label,json.dumps(record,indent=2)+'\n')
                record_file=root/'record.json';record_file.write_text(raw)
                arguments=['import-record','--name',label.removeprefix('status/evidence-agent-provenance/'),'--record',record_file,'--at',fixture['at']]
                if case['source_override'] is not None and label not in case.get('record_overrides',{}):
                    source.write_text(json.dumps(case['source_override']));arguments.extend(['--source',source])
                command(name,*arguments)
            checked=command(name,'check','--scope','all','--at',fixture['at']);data=Path(checked['data_directory'])
            stdout=(data/'generated/reports/evidence-agent-provenance-validation.stdout.txt').read_bytes()
            stderr=(data/'generated/reports/evidence-agent-provenance-validation.stderr.txt').read_bytes()
            assert stdout==case['expected_stdout'].encode() and stderr==case['expected_stderr'].encode()
            assert checked['result']['original_exit']==case['expected_original_exit']
            explicit=command(name,'check','--scope','all','--at',fixture['at'],'--fail-on-findings',expected=case['expected_original_exit'])
            assert explicit['generation']==checked['generation']
            assert command(name,'inspect')['reports']['check']=='current'
            results['check-'+case['id']]={'stdout':stdout.decode(),'stderr':stderr.decode(),'original_exit':case['expected_original_exit'],
                'original_wire_bytes_equal':True,'agent_execution_verified':False,'human_approval_verified':False}
    inspected=command(workspace,'inspect');assert all(inspected[key] is False for key in flags)
    data=Path(inspected['data_directory']);target=data/'status/evidence-agent-provenance-index.json';saved=target.read_bytes()
    target.write_bytes(b'changed')
    assert command(workspace,'inspect',expected=2)['diagnostics']==['candidate_generation_changed']
    target.write_bytes(saved);assert command(workspace,'inspect')['evidence_trust']=='unverified'
    business=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    value={'schema_version':1,'source_revision':settings['source_revision'],'runtime_source_digest':settings['runtime_source_digest'],
        'node_id':settings['node_id'],'provider_invoked':False,'official_acceptance':False,'full_functional_parity':False,
        'normalized_fields':[],'agent_execution_verified':False,'human_approval_verified':False,
        'results':results,'business_digest':business}
    args.output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');args.output.chmod(0o600)
    print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))


if __name__=='__main__':main()
