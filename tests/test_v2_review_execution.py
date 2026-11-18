"""Whole original runner wires, controlled processes, private replay and failure boundaries."""
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(os.environ.get('AXIOM_TEST_PRODUCT_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT/'scripts'))
from lib import review_git,review_planning
from lib.review_execution_application import ReviewExecutionContext,run
from lib.provider_ports import review_plan_profile
from lib.portable.contracts import canonical_digest
from lib.review_planning_application import wire
spec=importlib.util.spec_from_file_location('native_execution_oracle',Path(__file__).resolve().parent/'acceptance/v1_review_execution_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
FIXTURES=Path(os.environ.get('AXIOM_TEST_FIXTURES',ROOT/'tests/fixtures'));PROFILE='legacy-codex-role-review-v1';AT='2026-11-18T00:00:00Z'


class ReviewExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files=oracle.planning.target_files(FIXTURES/'v2-review-planning')

    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve()
        self.repo=self.base/'target';self.base_commit=oracle.planning.repository_from_files(self.repo,self.files)
        (self.repo/'docs/review-example.md').write_text('branch change\n');self.commit()
        self.instance=self.base/'instance';self.instance.mkdir(mode=0o700);self.settings={'node_id':'synthetic-execution-node'}
        self.app=ReviewExecutionContext(self.instance,self.settings)
        self.output=self.base/'operator-selected'/'private-run';self.planfile=self.base/'plan.json'
        self.bin=self.base/'synthetic-bin';self.bin.mkdir(mode=0o700)
        raw=(FIXTURES/'v2-review-execution/synthetic_provider.py.txt').read_bytes()
        self.executable=self.bin/'codex';self.executable.write_bytes(('#!'+sys.executable+'\n').encode()+raw);self.executable.chmod(0o700)
        self.executable_sha=hashlib.sha256(self.executable.read_bytes()).hexdigest()
        self.old=oracle.OriginalExecution(self.repo,FIXTURES);self.addCleanup(self.old.close)
        self.plan=self.packet()

    def commit(self):
        oracle.planning.git(self.repo,'add','--all');oracle.planning.git(self.repo,'commit','-qm','synthetic branch revision')

    def packet(self):
        facts,raw=review_git.capture(self.repo,self.base_commit,[],review_plan_profile('legacy-role-review-v1'))
        plan,_=review_planning.plan(facts,raw,'Synthetic original optional runner comparison',review_plan_profile('legacy-role-review-v1'))
        self.planfile.write_bytes(wire(plan));return plan

    def environment(self,mode='success'):
        # Prove this is the controlled fixture before allowing process tests in CI.
        self.assertEqual(hashlib.sha256(self.executable.read_bytes()).hexdigest(),self.executable_sha)
        env={**os.environ,'PATH':str(self.bin)+os.pathsep+os.environ.get('PATH',''),'AXIOM_REVIEW_TEST_MODE':mode};env.pop('CI',None)
        self.assertEqual(Path(shutil.which('codex',path=env['PATH'])).resolve(),self.executable)
        return patch.dict(os.environ,env,clear=True)

    def create(self,execute=False,mode='success',**kwargs):
        with self.environment(mode):return self.app.create(self.repo,self.planfile.read_bytes(),self.output,PROFILE,AT,execute=execute,**kwargs)

    def compare_original(self,value,native,execute=False,mode='success',validations=None):
        candidate=oracle.snapshot(self.output)
        self.assertEqual(self.output.stat().st_mode&0o777,0o700)
        for p in self.output.rglob('*'):self.assertEqual(p.stat().st_mode&0o777,0o700 if p.is_dir() else 0o600)
        shutil.rmtree(self.output)
        with self.environment(mode),self.old.native_clock(native):
            result=self.old.execution.run_reviews(self.repo,self.plan,self.output,execute=execute,validations=validations)
        self.assertEqual(result,native);self.assertEqual(oracle.snapshot(self.output),candidate)
        # V1 response-file mode follows the parent umask; V2 deliberately pins 0600.
        self.assertTrue(self.app.inspect(value['assessment_id'])['native_control_outputs_rederived'])

    def test_default_prepare_whole_original_files_no_provider_and_private_external_directory(self):
        with patch('lib.review_execution_application.execute_review_process',side_effect=AssertionError('preparation called provider')):
            value,native=self.create()
        self.assertEqual(value['exit_code'],0);self.assertFalse(value['provider_invoked']);self.assertFalse(value['declared_ready'])
        self.assertEqual(len(oracle.snapshot(self.output)),5)  # one Steward, three inputs + two root files
        self.compare_original(value,native)

    def test_execute_zero_specialists_whole_original_wires_with_actual_synthetic_process(self):
        validations=oracle.planning.declared_results(self.plan)['validations']
        value,native=self.create(True,validation_bytes=wire({'validations':validations}))
        self.assertEqual(value['exit_code'],0);self.assertTrue(value['provider_invoked']);self.assertTrue(value['declared_ready'])
        self.assertFalse(value['agent_execution_verified']);self.assertFalse(value['human_approval_verified'])
        self.assertEqual(native['roles'][0]['observed_model'],'synthetic-unverified-model')
        self.compare_original(value,native,True,validations=validations)

    def test_successful_process_without_recorded_validations_stays_incomplete_like_original(self):
        value,native=self.create(True);self.assertEqual(value['exit_code'],1)
        self.assertTrue(value['provider_invoked']);self.assertFalse(value['declared_ready']);self.compare_original(value,native,True)

    def test_original_failure_modes_preserve_all_native_files_and_no_automatic_retry(self):
        for mode in ('exit','invalid','incomplete','declared-failed','wrong-event'):
            with self.subTest(mode=mode):
                self.output=self.base/mode;value,native=self.create(True,mode)
                self.assertEqual(value['exit_code'],1);self.assertEqual(len(value['observations']),1)
                self.compare_original(value,native,True,mode)

    def test_specialists_then_steward_with_actual_responses_and_skip_on_failure(self):
        path=self.repo/'model/controls/synthetic.yaml';path.parent.mkdir(parents=True);path.write_text('synthetic: true\n');self.commit();self.plan=self.packet()
        self.assertGreater(len(self.plan['reviews']),1)
        for mode in ('success','exit'):
            self.output=self.base/('roles-'+mode);value,native=self.create(True,mode)
            roles=[r['role_id'] for r in self.plan['reviews']]
            self.assertEqual(list(value['observations']),roles if mode=='success' else roles[:-1])
            if mode=='success':
                prompt=json.loads((self.output/'repo-steward/execution-prompt.json').read_bytes())
                self.assertEqual([r['role_id'] for r in prompt['specialist_results']],roles[:-1])
            else:self.assertFalse((self.output/'repo-steward/events.jsonl').exists())
            self.compare_original(value,native,True,mode)

    def test_replay_without_target_output_caller_or_executable_and_tampered_artifact_rejected(self):
        value,_=self.create(True);shutil.rmtree(self.repo);shutil.rmtree(self.output);self.planfile.unlink();self.executable.unlink()
        with patch('lib.review_execution_application.execute_review_process',side_effect=AssertionError('inspect launched provider')):
            checked=self.app.inspect(value['assessment_id']);self.assertTrue(checked['native_control_outputs_rederived']);self.assertFalse(checked['target_current_state_rechecked'])
        row=next(iter(value['files'].values()));path=self.app.artifacts/value['assessment_id']/(row['sha256']+'.bin');path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):self.app.inspect(value['assessment_id'])

    def test_foreign_node_and_rehashed_authority_or_process_claims_rejected(self):
        value,_=self.create();aid=value['assessment_id']
        with self.assertRaisesRegex(ValueError,'binding_changed'):ReviewExecutionContext(self.instance,{'node_id':'foreign-node'}).inspect(aid)
        record=json.loads((self.app.assessments/(aid+'.json')).read_bytes())
        for mutation in (lambda v:v.update(official_acceptance=True),lambda v:v.update(provider_invoked=True),lambda v:v.update(started_roles=['repo-steward'])):
            bad=deepcopy(record);mutation(bad);identity=canonical_digest(bad)
            (self.app.assessments/(identity+'.json')).write_bytes(wire(bad))
            shutil.copytree(self.app.artifacts/aid,self.app.artifacts/identity)
            with self.assertRaises(ValueError):self.app.inspect(identity)

    def test_ci_and_dirty_explicit_or_stale_plan_rejected_before_native_output(self):
        with patch.dict(os.environ,{'CI':'true'}):
            with self.assertRaisesRegex(ValueError,'forbidden_in_ci'):self.app.create(self.repo,self.planfile.read_bytes(),self.output,PROFILE,AT,execute=True)
        (self.repo/'untracked.txt').write_text('dirty\n')
        with self.assertRaisesRegex(ValueError,'clean_committed'):self.create()
        (self.repo/'untracked.txt').unlink();bad=deepcopy(self.plan);bad['head_commit']='0'*40
        with self.assertRaisesRegex(ValueError,'stale_plan'):self.app.create(self.repo,wire(bad),self.output,PROFILE,AT)
        self.assertFalse(self.output.exists())

    def test_timeout_response_and_stream_budgets_produce_failed_trace_and_private_retention(self):
        for mode in ('timeout','oversize-response','oversize-stream'):
            self.output=self.base/mode;before=time.monotonic();value,native=self.create(True,mode,timeout=1)
            self.assertLess(time.monotonic()-before,12);self.assertEqual(value['exit_code'],1)
            self.assertTrue(native['roles'][0]['process_started']);self.assertTrue(self.app.inspect(value['assessment_id'])['retained_raw_artifacts_reverified'])
            if mode=='timeout':self.assertTrue(native['roles'][0]['timed_out'])

    def test_source_mutation_is_preserved_and_recorded_partial_without_retry(self):
        value,native=self.create(True,'source-mutate');self.assertEqual(value['exit_code'],2)
        self.assertEqual(value['error_type'],'ValueError');self.assertTrue(value['provider_invoked'])
        self.assertIn('synthetic concurrent source mutation',(self.repo/'docs/review-example.md').read_text())
        self.assertFalse(value['native_control_outputs_rederived']);self.assertIn('execution.json',value['files'])
        self.assertEqual(self.app.status(value['operation_id'])['state'],'completed')

    def test_native_output_symlink_hardlink_and_checkout_destinations_cannot_capture_secret(self):
        secret=self.base/'secret.txt';secret.write_text('private unrelated secret')
        for mode in ('symlink-response','hardlink-response'):
            self.output=self.base/mode
            with patch.dict(os.environ,{'AXIOM_REVIEW_TEST_SECRET':str(secret)}):value,native=self.create(True,mode)
            self.assertEqual(value['exit_code'],2);self.assertIsNotNone(value['capture_error']);self.assertEqual(value['files'],{})
            self.assertNotIn('private unrelated secret',json.dumps(value))
        value,native=self.app.create(self.repo,self.planfile.read_bytes(),self.repo/'forbidden-output',PROFILE,AT)
        self.assertEqual(value['exit_code'],2);self.assertFalse((self.repo/'forbidden-output').exists())

    def test_original_typed_yaml_prompt_failure_retains_actual_partial_empty_file(self):
        path=self.repo/'.agents/roles/repo-steward.yaml';path.write_text(path.read_text()+'extension: 2026-11-17\n');self.commit()
        self.old.close();self.old=oracle.OriginalExecution(self.repo,FIXTURES);self.addCleanup(self.old.close);self.plan=self.packet()
        value,native=self.create();candidate=oracle.snapshot(self.output)
        self.assertEqual(value['exit_code'],2);self.assertEqual(value['error_type'],'TypeError');self.assertEqual(candidate['repo-steward/prompt.json'],b'')
        shutil.rmtree(self.output)
        with self.assertRaises(TypeError):self.old.execution.run_reviews(self.repo,self.plan,self.output)
        self.assertEqual(oracle.snapshot(self.output),candidate)

    def test_cli_legacy_summary_and_original_exit_codes_without_extra_native_files(self):
        stdout=io.StringIO()
        with self.environment(),redirect_stdout(stdout):
            code=run(['run','--repo',str(self.repo),'--plan',str(self.planfile),'--output-dir',str(self.output),'--profile',PROFILE,'--at',AT],self.instance,self.settings)
        self.assertEqual(code,0);summary=json.loads(stdout.getvalue())
        self.assertEqual(set(summary),{'run_id','mode','provider_invoked','eligible_for_human_review'})

    def test_parallel_specialists_are_aggregated_in_plan_order_and_steward_sees_every_result(self):
        for name in ('model/controls/synthetic.yaml','docs/governance/source-documents/synthetic.md','policies/opa/synthetic.rego'):
            path=self.repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic fixture\n')
        self.commit();self.plan=self.packet();self.assertGreaterEqual(len(self.plan['reviews']),4)
        value,native=self.create(True,parallel=3)
        self.assertEqual(value['exit_code'],1)
        self.assertEqual([r['role_id'] for r in native['roles']],[t['role_id'] for t in self.plan['reviews']])
        prompt=json.loads((self.output/'repo-steward/execution-prompt.json').read_bytes())
        self.assertEqual([r['role_id'] for r in prompt['specialist_results']],[t['role_id'] for t in self.plan['reviews'][:-1]])
        self.assertTrue(self.app.inspect(value['assessment_id'])['native_control_outputs_rederived'])

    def test_missing_binary_records_no_actual_start_and_original_failure_trace(self):
        with self.environment(),patch('lib.providers.review_execution.shutil.which',return_value=None):
            value,native=self.app.create(self.repo,self.planfile.read_bytes(),self.output,PROFILE,AT,execute=True)
        self.assertFalse(value['provider_invoked']);self.assertEqual(value['exit_code'],1)
        self.assertEqual(native['roles'][0]['error_type'],'FileNotFoundError')
        self.assertFalse(native['roles'][0]['process_started']);candidate=oracle.snapshot(self.output);shutil.rmtree(self.output)
        original_popen=self.old.execution.subprocess.Popen
        def controlled(*args,**kwargs):
            if args[0][0]=='codex':raise FileNotFoundError
            return original_popen(*args,**kwargs)
        with self.environment(),self.old.native_clock(native),patch.object(self.old.execution.subprocess,'Popen',side_effect=controlled):
            expected=self.old.execution.run_reviews(self.repo,self.plan,self.output,execute=True)
        self.assertEqual(expected,native);self.assertEqual(oracle.snapshot(self.output),candidate)

    def test_preparation_adapter_and_recorded_validation_failures_preserve_original_partial_outputs(self):
        for kind in ('validation','adapter'):
            self.output=self.base/kind
            if kind=='adapter':
                path=self.repo/'.codex/agents/repo-steward.toml';path.write_text('model = "only one required field"\n');self.commit()
                self.old.close();self.old=oracle.OriginalExecution(self.repo,FIXTURES);self.addCleanup(self.old.close);self.plan=self.packet()
            validations={'validations':[{'command':'unknown command','status':'passed','evidence':'synthetic'}]} if kind=='validation' else None
            value,native=self.create(validation_bytes=wire(validations) if validations else None)
            self.assertEqual(value['exit_code'],2);self.assertFalse(value['provider_invoked'])
            if kind=='validation':self.assertEqual(value['files'],{})
            candidate=oracle.snapshot(self.output);shutil.rmtree(self.output)
            with self.assertRaises(ValueError):self.old.execution.run_reviews(self.repo,self.plan,self.output,validations=validations['validations'] if validations else None)
            self.assertEqual(oracle.snapshot(self.output),candidate)

    def test_interruption_retains_pending_intent_without_resume_or_process_relaunch(self):
        with patch('lib.review_execution_application.ReviewExecutionOutput',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.create()
        operations=list(self.app.intents.glob('*.json'));self.assertEqual(len(operations),1)
        with patch('lib.review_execution_application.execute_review_process',side_effect=AssertionError('pending status retried execution')):
            value=self.app.status(operations[0].stem)
        self.assertEqual(value['state'],'in_progress');self.assertFalse(value['automatic_resume']);self.assertIsNone(value['assessment_id'])

    def test_child_processes_are_terminated_before_artifact_capture(self):
        value,native=self.create(True,'child');self.assertEqual(value['exit_code'],1)
        time.sleep(2.1)
        self.assertFalse((self.output/'repo-steward/late-child.txt').exists())
        self.assertTrue(value['native_artifact_capture_complete']);self.assertTrue(self.app.inspect(value['assessment_id'])['native_control_outputs_rederived'])

    def test_contract_budgets_existing_output_and_symlink_destination_do_not_start_provider(self):
        for kwargs in ({'parallel':0},{'parallel':4},{'timeout':0},{'timeout':601}):
            with self.assertRaisesRegex(ValueError,'budget'):self.create(True,**kwargs)
        self.output.mkdir(parents=True,mode=0o700);marker=self.output/'preserved';marker.write_bytes(b'keep')
        value,_=self.create(True);self.assertEqual(value['exit_code'],2);self.assertFalse(value['provider_invoked']);self.assertEqual(marker.read_bytes(),b'keep')
        self.output=self.base/'linked-output';self.output.symlink_to(marker.parent,target_is_directory=True)
        value,_=self.create(True);self.assertEqual(value['exit_code'],2);self.assertFalse(value['provider_invoked'])

    def test_sha256_target_prepare_and_execute_match_whole_original_wires(self):
        shutil.rmtree(self.repo/'.git');oracle.planning.git(self.repo,'init','-q','-b','main','--object-format=sha256')
        self.commit();self.base_commit=oracle.planning.git(self.repo,'rev-parse','HEAD')
        (self.repo/'docs/review-example.md').write_text('native SHA256 proposal\n');self.commit()
        self.old.close();self.old=oracle.OriginalExecution(self.repo,FIXTURES);self.addCleanup(self.old.close);self.plan=self.packet()
        self.assertEqual(len(self.plan['head_commit']),64)
        for execute in (False,True):
            self.output=self.base/('sha256-execute' if execute else 'sha256-prepare');value,native=self.create(execute)
            self.compare_original(value,native,execute)

    def test_native_cli_summary_and_exit_one_and_two_match_original(self):
        for mode in ('success','invalid'):
            self.output=self.base/('cli-'+mode);out=io.StringIO()
            arguments=['--plan',str(self.planfile),'--output-dir',str(self.output),'--execute']
            with self.environment(mode),redirect_stdout(out):
                code=run(['run','--repo',str(self.repo),*arguments,'--profile',PROFILE,'--at',AT],self.instance,self.settings)
            self.assertEqual(code,1);native=json.loads((self.output/'execution.json').read_bytes())
            candidate=oracle.snapshot(self.output);shutil.rmtree(self.output);old_out=io.StringIO()
            with self.environment(mode),self.old.native_clock(native),redirect_stdout(old_out):old_code=self.old.cli['main'](arguments)
            self.assertEqual((code,out.getvalue()),(old_code,old_out.getvalue()));self.assertEqual(candidate,oracle.snapshot(self.output))
        self.output=self.base/'cli-invalid-validations';validation=self.base/'invalid-validations.json';validation.write_text('{"validations":[]}')
        # A schema-invalid plan stops at the common input boundary with original exit2.
        bad=deepcopy(self.plan);bad['head_commit']='0'*40;self.planfile.write_bytes(wire(bad))
        old_out,old_err=io.StringIO(),io.StringIO()
        with redirect_stdout(old_out),redirect_stderr(old_err):self.assertEqual(self.old.cli['main'](['--plan',str(self.planfile),'--output-dir',str(self.output)]),2)
        with self.assertRaises(ValueError):run(['run','--repo',str(self.repo),'--plan',str(self.planfile),'--output-dir',str(self.output),'--profile',PROFILE,'--at',AT],self.instance,self.settings)


if __name__=='__main__':unittest.main()
