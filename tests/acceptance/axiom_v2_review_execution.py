"""Installed optional runner: whole original wires and controlled synthetic processes."""
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
    parser.add_argument('--expected-source',required=True)
    args=parser.parse_args();prefix=args.prefix.resolve();fixtures=args.fixtures.resolve();output=args.output.resolve()
    settings=json.loads((prefix/'instance/instance.json').read_bytes())
    assert settings['source_revision']==args.expected_source and not settings['development']
    source=Path(settings['source_root']);assert source.is_dir() and source.is_relative_to(prefix)
    bindings=json.loads((fixtures/'bindings.json').read_bytes())
    for name in ('review-execution','review-planning','review-metadata'):
        for path in (fixtures/name).iterdir():assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[name+'/'+path.name]
    with tempfile.TemporaryDirectory(prefix='installed-review-runner-',dir=output.parent) as temporary:
        base=Path(temporary);tests=base/'tests';tests.mkdir(mode=0o700);(tests/'acceptance').mkdir(mode=0o700)
        data=tests/'fixtures';data.mkdir(mode=0o700)
        for native,original in [('v2-review-execution','review-execution'),('v2-review-planning','review-planning'),('v2-review-metadata','review-metadata')]:
            shutil.copytree(fixtures/original,data/native)
        path=tests/'test_v2_review_execution.py';shutil.copyfile(fixtures/'review-execution/test_v2_review_execution.py',path)
        shutil.copyfile(fixtures/'review-execution/oracle.py',tests/'acceptance/v1_review_execution_oracle.py')
        shutil.copyfile(fixtures/'review-planning/oracle.py',tests/'acceptance/v1_review_planning_oracle.py')
        # These knobs select trusted test inputs only; the product has no execution
        # test switches and never imports its source checkout's test modules.
        os.environ.update(AXIOM_TEST_PRODUCT_ROOT=str(source),AXIOM_TEST_FIXTURES=str(data))
        sys.dont_write_bytecode=True;sys.path.insert(0,str(source/'scripts'))
        spec=importlib.util.spec_from_file_location('installed_runner_tests',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        names=unittest.defaultTestLoader.getTestCaseNames(module.ReviewExecution)
        log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(module.ReviewExecution))
        if not result.wasSuccessful():raise AssertionError(log.getvalue())
        assert result.testsRun==len(names)==21 and not result.skipped
        # Exercise the actual installed router/wrapper with an operator-selected
        # directory, and then inspect after deleting all caller/target outputs.
        repo=base/'wrapper-target';revision=module.oracle.planning.repository_from_files(repo,module.ReviewExecution.files)
        (repo/'docs/review-example.md').write_text('synthetic wrapper branch\n');module.oracle.planning.git(repo,'add','--all');module.oracle.planning.git(repo,'commit','-qm','synthetic wrapper proposal')
        original=module.oracle.OriginalExecution(repo,data)
        try:plan=original.prepare(revision,'Synthetic installed wrapper')[0]
        finally:original.close()
        planfile=base/'plan.json';planfile.write_text(json.dumps(plan));external=base/'wrapper-output'
        process=subprocess.run([str(prefix/'axiom-v2'),'review-run','run','--repo',str(repo),'--plan-file',str(planfile),'--output-dir',str(external),
            '--profile','legacy-codex-role-review-v1','--at','2026-11-18T00:00:00Z','--format','receipt'],capture_output=True,text=True,timeout=180)
        assert process.returncode==0,process.stderr;receipt=json.loads(process.stdout)
        assert receipt['source_revision']==args.expected_source and receipt['runtime_source_digest']==settings['runtime_source_digest'] and receipt['node_id']==settings['node_id']
        assert not receipt['provider_invoked'] and receipt['native_control_outputs_rederived'] and receipt['native_artifact_capture_complete']
        shutil.rmtree(repo);shutil.rmtree(external);planfile.unlink()
        process=subprocess.run([str(prefix/'axiom-v2'),'review-run','inspect','--assessment',receipt['assessment_id']],capture_output=True,text=True,timeout=180)
        assert process.returncode==0,process.stderr;checked=json.loads(process.stdout)
        assert checked['native_control_outputs_rederived'] and not checked['target_current_state_rechecked'] and not checked['provider_model_identity_verified']
        cases={name:{'passed':True,'scope':'controlled_local_synthetic_process_or_original_wire_guard'} for name in names}
        cases['installed_wrapper_and_deleted_caller_replay']={'passed':True,'scope':'actual_installed_cli_prepare_inspect'}
    value={'schema_version':1,'source_revision':args.expected_source,'runtime_source_digest':settings['runtime_source_digest'],'node_id':settings['node_id'],
        'case_count':len(cases),'cases':cases,'whole_original_native_wires_compared_per_host':True,
        'cross_host_native_raw_byte_identity_claimed':False,'synthetic_provider_processes_executed':True,'live_provider_invoked':False,
        'agent_execution_verified':False,'human_approval_verified':False,'full_functional_parity':False,
        'business_digest':hashlib.sha256(json.dumps(cases,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n');output.chmod(0o600)
    print(json.dumps({k:v for k,v in value.items() if k!='cases'},sort_keys=True))


if __name__=='__main__':main()
