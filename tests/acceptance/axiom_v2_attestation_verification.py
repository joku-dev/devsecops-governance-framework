"""Installed real-signature/original-wire tests, no active Trust or external providers."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prefix','fixtures','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--expected-source',required=True);parser.add_argument('--crypto-tool',type=Path,required=True)
    parser.add_argument('--crypto-sha256',required=True)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve();tool=args.crypto_tool.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_text());assert settings['source_revision']==args.expected_source and not settings['development']
    assert tool.is_file() and hashlib.sha256(tool.read_bytes()).hexdigest()==args.crypto_sha256
    version=subprocess.check_output([str(tool),'version'],text=True,timeout=10).strip()
    assert version.startswith(('OpenSSL 3.','OpenSSL 4.')),version
    directory=fixtures/'attestation-verification';bindings=json.loads((fixtures/'bindings.json').read_text())
    for path in directory.iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings['attestation-verification/'+path.name]
    source=Path(settings['source_root']);assert source.is_relative_to(prefix)
    with tempfile.TemporaryDirectory(prefix='installed-attestation-',dir=output.parent) as temporary:
        base=Path(temporary);tests=base/'tests';tests.mkdir(mode=0o700);(tests/'acceptance').mkdir(mode=0o700)
        testfile=tests/'test_v2_attestation_verification.py';shutil.copyfile(directory/testfile.name,testfile)
        shutil.copyfile(directory/'oracle.py',tests/'acceptance/v1_attestation_oracle.py')
        tools=base/'native-tools';tools.mkdir(mode=0o700);(tools/'openssl').symlink_to(tool)
        original_path=os.environ.get('PATH','');os.environ.update(PATH=str(tools)+os.pathsep+original_path,
            AXIOM_TEST_PRODUCT_ROOT=str(source),AXIOM_TEST_ATTESTATION_FIXTURES=str(directory))
        sys.dont_write_bytecode=True;sys.path.insert(0,str(source/'scripts'))
        spec=importlib.util.spec_from_file_location('installed_attestation_tests',testfile);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        names=unittest.defaultTestLoader.getTestCaseNames(module.AttestationVerification);log=io.StringIO()
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(module.AttestationVerification))
        if not result.wasSuccessful():raise AssertionError(log.getvalue())
        assert result.testsRun==len(names)==23 and not result.skipped
        native=base/'native';native.mkdir(mode=0o700);attestation=native/'source.json';destination=native/'report.json'
        attestation.write_bytes((directory/'docs__examples__evidence-attestation.example.json.txt').read_bytes())
        destination.write_bytes(b'previous controlled output\n');destination.chmod(0o600)
        command=[str(prefix/'axiom-v2'),'attestation','verify',str(attestation),'--output',str(destination),'--profile','legacy-attestation-pilot-v1',
            '--evaluated-at','2026-11-18T00:00:00Z','--format','receipt']
        checked=subprocess.run(command,capture_output=True,text=True,timeout=90);assert checked.returncode==0,checked.stderr
        receipt=json.loads(checked.stdout)
        assert receipt['source_revision']==args.expected_source and receipt['runtime_source_digest']==settings['runtime_source_digest'] and receipt['node_id']==settings['node_id']
        assert receipt['crypto']['process_started'] and receipt['crypto']['signature_valid'] and receipt['crypto']['tool_sha256']==args.crypto_sha256
        assert not receipt['registry_authority_activated'] and receipt['evidence_trust']=='unverified' and receipt['retained_complete_outputs_reverified']
        original=module.oracle.Original(directory,source);stdout=io.StringIO()
        from contextlib import redirect_stdout
        native_bytes=destination.read_bytes()
        with redirect_stdout(stdout):assert original.cli([attestation,'--output',destination,'--evaluated-at','2026-11-18T00:00:00Z'])==0
        assert destination.read_bytes()==native_bytes and (Path(receipt['data_directory'])/'native-stdout.txt').read_text()==stdout.getvalue()
        attestation.unlink();destination.unlink()
        checked=subprocess.run([str(prefix/'axiom-v2'),'attestation','inspect','--assessment',receipt['assessment_id']],capture_output=True,text=True,timeout=90)
        assert checked.returncode==0,checked.stderr;inspected=json.loads(checked.stdout)
        assert inspected['retained_complete_outputs_reverified'] and not inspected['cryptographic_signature_reverified'] and not inspected['current_input_or_destination_rechecked']
        cases={name:{'passed':True,'scope':'whole_original_wire_or_actual_crypto_file_replay_guard'} for name in names}
        cases['installed_wrapper_overwrite_and_deleted_caller_replay']={'passed':True,'scope':'actual_installed_cli_original_file_stdout_and_inspect'}
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],
        'case_count':len(cases),'cases':cases,'whole_original_native_wires_compared_per_host':True,'cross_host_native_raw_byte_identity_claimed':False,
        'compatible_crypto_tool_version':version,'crypto_tool_sha256':args.crypto_sha256,'actual_local_crypto_executed':True,'live_provider_invoked':False,
        'registry_authority_activated':False,'effective_trust':'unverified','independent_human_approval':False,'full_functional_parity':False,
        'business_digest':hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');output.chmod(0o600)
    print(json.dumps({key:value for key,value in value.items() if key!='cases'},sort_keys=True))


if __name__=='__main__':main()
