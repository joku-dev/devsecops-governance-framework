"""Installed source inspection versus exact original V1 tools on identical inputs."""
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix',type=Path);parser.add_argument('fixtures',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--expected-source',required=True);parser.add_argument('--real-repo',type=Path)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_text())
    assert settings['source_revision']==args.expected_source and not settings['development']
    bindings=json.loads((fixtures/'bindings.json').read_text());reference=fixtures/'source-inspection'
    for path in reference.iterdir():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings['source-inspection/'+path.name]
    spec=importlib.util.spec_from_file_location('pinned_v1_source_oracle',reference/'oracle.py')
    oracle=importlib.util.module_from_spec(spec)
    previous_bytecode=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(oracle)
    finally:sys.dont_write_bytecode=previous_bytecode
    contract=oracle.load_fixture(reference)
    def command(*arguments,expected=0):
        run=subprocess.run([str(prefix/'axiom-v2'),'source-inspection',*map(str,arguments)],capture_output=True,text=True,timeout=180)
        assert run.returncode==expected,run.stderr
        return json.loads(run.stdout if expected in (0,1) else run.stderr)
    results={};raw_results={};source_bindings={};paths=contract['logical_outputs']
    with tempfile.TemporaryDirectory(prefix='source-inspection-oracle-',dir=output.parent) as temporary:
        base=Path(temporary).resolve();rows=[]
        for case in contract['cases']:
            repository=base/case['id'];revision=oracle.make_repository(repository,case)
            rows.append((case['id'],repository,revision,'synthetic/'+case['id'],case))
        if args.real_repo:
            repository=args.real_repo.resolve();revision='5c3b5cb50d2260bfbde736c9ac80667271406d99'
            assert oracle.git(repository,'rev-parse','HEAD')==revision and not oracle.git(repository,'status','--porcelain')
            rows.append(('ha-CPsWMS',repository,revision,'joku-dev/ha-CPsWMS',None))
        for name,repository,revision,repository_id,case in rows:
            original,exits=oracle.original_files(reference,base/('original-'+name),repository,repository_id,contract['at'])
            if case:assert list(exits)==case['expected_exits']
            raw_results[name]={path:raw.decode() for path,raw in original.items()}
            before=oracle.git(repository,'status','--porcelain');assessment=None
            for kind,selected in [('integration',{paths['integration']}),('onboarding',{paths['onboarding_json'],paths['onboarding_markdown']}),('all',set(original))]:
                arguments=['create','--kind',kind,'--repo',repository,'--revision',revision,'--repository-id',repository_id,
                           '--profile','legacy-ci-signatures-v1','--at',contract['at']]
                receipt=command(*arguments);inspected=command('inspect','--id',receipt['assessment_id']);assessment=inspected['assessment']
                assert inspected['retained_git_source_and_complete_outputs_reverified'] and not inspected['native_metadata_rechecked']
                assert assessment['node_id']==settings['node_id'] and assessment['source_revision']==args.expected_source
                assert assessment['runtime_source_digest']==settings['runtime_source_digest'] and assessment['source_worktree_clean']
                assert assessment['consumer_commit']==revision and assessment['consumer_tree']==oracle.git(repository,'rev-parse',revision+'^{tree}')
                assert assessment['evidence_trust']=='unverified' and not assessment['repository_identity_verified']
                assert not any(assessment[k] for k in ('working_tree_used','provider_invoked','official_acceptance',
                    'production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published'))
                assert set(assessment['files'])==selected and assessment['source_inspection_profile']['source_signature_only'] is True
                for path in selected:assert (Path(receipt['artifact_directory'])/path).read_bytes()==original[path]
                expected_exit=exits[0] if kind=='integration' else exits[1] if kind=='onboarding' else max(exits)
                assert receipt['original_finding_exit']==expected_exit and not receipt['finding_exit_requested']
                finding_receipt=command(*arguments,'--fail-on-findings',expected=expected_exit)
                assert finding_receipt['assessment_id']==receipt['assessment_id'] and finding_receipt['finding_exit_requested']
            assert oracle.git(repository,'status','--porcelain')==before
            source_bindings[name]={'commit':revision,'tree':assessment['consumer_tree'],'retained_input_id':assessment['input_id']}
            # Complete physical wire equality was checked above. Validate only the
            # three descriptive context fields before the explicit host comparison.
            integration=json.loads(original[paths['integration']]);onboarding=json.loads(original[paths['onboarding_json']])
            assert integration['target_repo']==repository.name and onboarding['target_repo']==repository.name
            assert onboarding['target_path']==str(repository)
            integration['target_repo']=onboarding['target_repo']='<validated-operator-repository-name>'
            onboarding['target_path']='<validated-operator-repository-path>'
            markdown=original[paths['onboarding_markdown']].decode();line='- Target path: `'+str(repository)+'`'
            assert markdown.count(line)==1
            projection={paths['integration']:json.dumps(integration,indent=2)+'\n',
                paths['onboarding_json']:json.dumps(onboarding,indent=2)+'\n',
                paths['onboarding_markdown']:markdown.replace(line,'- Target path: `<validated-operator-repository-path>`')}
            results[name]={'complete_original_physical_wires_equal':True,'original_exits':list(exits),'files':projection,
                           'official_acceptance':False}
            if case:
                # The final all-kind retained input survives source disappearance.
                import shutil
                shutil.rmtree(repository)
                assert command('inspect','--id',receipt['assessment_id'])['retained_git_source_and_complete_outputs_reverified']
                artifact=Path(receipt['artifact_directory'])/paths['integration'];saved=artifact.read_bytes();artifact.write_bytes(b'changed')
                assert command('inspect','--id',receipt['assessment_id'],expected=2)['diagnostics']==['source_inspection_output_changed']
                artifact.write_bytes(saved)
                assert command('inspect','--id',receipt['assessment_id'])['retained_git_source_and_complete_outputs_reverified']
    business=hashlib.sha256(json.dumps(results,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    value={'schema_version':1,'source_revision':settings['source_revision'],'node_id':settings['node_id'],
        'runtime_source_digest':settings['runtime_source_digest'],'source_signature_only':True,'provider_invoked':False,
        'official_acceptance':False,'full_functional_parity':False,'normalized_fields':[
            'integration.target_repo','onboarding.target_repo','onboarding.target_path','onboarding_markdown.target_path'],
        'normalization_contract':'Only bound operator basename/path validated after complete physical V1/V2 byte equality; no finding/control/status normalization',
        'source_bindings':source_bindings,'raw_original_equal_files':raw_results,'results':results,'business_digest':business}
    output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');output.chmod(0o600)
    print(json.dumps({k:v for k,v in value.items() if k not in ('results','raw_original_equal_files','source_bindings')},sort_keys=True))


if __name__=='__main__':main()
