"""Installed declared-context/pipeline wires against complete original V1 fixtures."""
import argparse,base64,hashlib,json,subprocess,tempfile
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--expected-source',required=True);args=parser.parse_args()
    prefix=args.prefix.resolve();settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    fixture_path=args.fixtures/'context-pipeline-cases.json';bindings=json.loads((args.fixtures/'bindings.json').read_text());assert hashlib.sha256(fixture_path.read_bytes()).hexdigest()==bindings[fixture_path.name]
    fixture=json.loads(fixture_path.read_text());assert fixture['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
    defaults={'artifact_path':'dist/application-source.tar.gz','sbom_path':'security/sbom.cyclonedx.json','vulnerability_scan_path':'security/vulnerability-scan.json','signature_path':'','governance_mode':'report-only','max_allowed_severity':'high','release_candidate':False,'artifact_type':'application-build-output','protected_branch':'','direct_push_allowed':'','review_required':'','branch_protection_status':'not_checked_by_platform_adapter'}
    flags=('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','pipeline_execution_verified','branch_protection_verified','waiver_approval_verified','signature_verified','native_metadata_rechecked')
    outputs={'context-output.json':'generated/evidence/platform-context.json','evidence.json':'generated/evidence/pipeline-evidence.json','gate.json':'generated/evidence/baseline-gate-result.json'}
    def command(arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'pipeline-evidence',*map(str,arguments)],capture_output=True,text=True,timeout=180);assert run.returncode==expected,run.stderr
        value=json.loads(run.stdout if expected in (0,1) else run.stderr)
        if expected in (0,1):assert all(value[k] is False for k in flags)
        return value
    results={}
    with tempfile.TemporaryDirectory(prefix='pipeline-input-',dir=args.output.resolve().parent) as temporary:
        root=Path(temporary)
        for c in fixture['cases']:
            p=argparse.ArgumentParser();p.add_argument('--platform');p.add_argument('--output');p.add_argument('--gate-output');p.add_argument('--platform-context-file',default='')
            for key,value in defaults.items():p.add_argument('--'+key.replace('_','-'),**({'action':'store_true'} if isinstance(value,bool) else {'default':value}))
            old=vars(p.parse_args(c['arguments']));metadata={k:old[k] for k in defaults}
            environment=root/'environment.json';environment.write_text(json.dumps(c['environment']));meta=root/'metadata.json';meta.write_text(json.dumps(metadata))
            arguments=['create','--kind','all','--profile',c['platform'],'--environment',environment,'--metadata',meta,'--at',c['at']]
            for slot,key in [('artifact','artifact_path'),('sbom','sbom_path'),('scan','vulnerability_scan_path'),('signature','signature_path')]:
                if metadata[key] in c['input_files']:
                    path=root/slot;path.write_bytes(base64.b64decode(c['input_files'][metadata[key]]));arguments.extend(['--'+slot,path])
            if c['context_override'] is not None:
                path=root/'override.json';path.write_text(json.dumps(c['context_override']));arguments.extend(['--context-override',path])
            value=command(arguments);data=Path(value['data_directory']);actual={name:(data/label).read_text() for name,label in outputs.items()};assert actual==c['expected_wires']
            expected_exit=1 if value['declared_gate_status']=='fail' else 0
            explicit=command([*arguments,'--fail-on-findings'],expected=expected_exit);assert explicit['assessment_id']==value['assessment_id']
            inspected=command(['inspect','--assessment',value['assessment_id']]);assert inspected['files']==value['files']
            results[c['id']]={'wires':actual,'original_exit':c['original_exit'],'explicit_local_finding_exit':expected_exit,'original_wire_bytes_equal':True}
        path=data/outputs['gate.json'];saved=path.read_bytes();path.write_bytes(b'changed')
        assert command(['inspect','--assessment',value['assessment_id']],expected=2)['diagnostics']==['declared_pipeline_output_changed'];path.write_bytes(saved)
        command(['inspect','--assessment',value['assessment_id']])
    digest=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    value={'schema_version':1,'source_revision':settings['source_revision'],'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],'normalized_fields':[],'provider_invoked':False,'official_acceptance':False,'full_functional_parity':False,'pipeline_execution_verified':False,'results':results,'business_digest':digest}
    args.output.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');args.output.chmod(0o600);print(json.dumps({k:v for k,v in value.items() if k!='results'},sort_keys=True))

if __name__=='__main__':main()
