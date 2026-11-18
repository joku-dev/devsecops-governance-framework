"""Real local signatures, whole original files/CLI, native effects and private replay."""
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
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
import time
import unittest
from unittest.mock import patch

ROOT=Path(os.environ.get('AXIOM_TEST_PRODUCT_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT/'scripts'))
from lib import attestation_assessment as logic,attestation_files as effects,review_planning
from lib.attestation_application import AttestationContext,run
from lib.portable.contracts import canonical_digest
spec=importlib.util.spec_from_file_location('original_attestation',Path(__file__).resolve().parent/'acceptance/v1_attestation_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
FIXTURES=Path(os.environ.get('AXIOM_TEST_ATTESTATION_FIXTURES',ROOT/'tests/fixtures/v2-attestation-verification'))
PROFILE='legacy-attestation-pilot-v1';AT='2026-11-18T00:00:00Z'


class AttestationVerification(unittest.TestCase):
    def setUp(self):
        # Fixtures satisfy the private-output contract independently of the
        # invoking shell's umask (the VM operator commonly uses 0002).
        previous_umask=os.umask(0o077);self.addCleanup(os.umask,previous_umask)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve()
        self.instance=self.base/'instance';self.instance.mkdir(mode=0o700);self.settings={'node_id':'synthetic-attestation-node'}
        self.app=AttestationContext(self.instance,self.settings);self.old=oracle.Original(FIXTURES,ROOT)
        self.attestation=self.base/'attestation.json';self.registry=self.base/'registry.yaml';self.output=self.base/'external'/'assessment.json'
        self.attestation.write_bytes((FIXTURES/'docs__examples__evidence-attestation.example.json.txt').read_bytes())
        self.registry.write_bytes((FIXTURES/'model__evidence__evidence-trust-roots.yaml.txt').read_bytes())
        self.data=logic.input_object(self.attestation.read_bytes());self.roots=logic.registry(self.registry.read_bytes())

    def assess(self,**kwargs):return self.app.verify(self.attestation,self.output,PROFILE,trust_roots=self.registry,evaluated_at=AT,**kwargs)

    def compare_cli(self,value,*,default_registry=False,automatic_time=False):
        candidate=self.output.read_bytes();stdout=io.StringIO()
        args=[self.attestation,'--output',self.output]
        if not default_registry:args+=['--trust-roots',self.registry]
        if not automatic_time:args+=['--evaluated-at',AT]
        with redirect_stdout(stdout):code=self.old.cli(args,at=value['evaluated_at'] if automatic_time else None)
        self.assertEqual(code,0);self.assertEqual(self.output.read_bytes(),candidate)
        checked=self.app.inspect(value['assessment_id']);self.assertTrue(checked['retained_complete_outputs_reverified'])
        self.assertEqual((Path(value['data_directory'])/'native-stdout.txt').read_text(),stdout.getvalue())

    def test_real_valid_signature_complete_original_cli_file_and_no_authority_transfer(self):
        value,result=self.assess();self.assertEqual(result['status'],'pass');self.assertEqual(value['exit_code'],0)
        self.assertTrue(value['crypto']['process_started']);self.assertTrue(value['crypto']['signature_valid'])
        self.assertEqual(result['effective_level'],'integrity_verified');self.assertEqual(value['evidence_trust'],'unverified')
        for key in ('registry_authority_activated','declared_context_independently_verified','key_algorithm_enforced','registry_dates_enforced','authority_transferred','official_acceptance','human_approval_verified','provider_invoked'):self.assertFalse(value[key])
        self.compare_cli(value)

    def test_original_negative_attestation_files_stdout_and_exit_zero(self):
        for kind in ('unknown-key','unknown-issuer','wrong-repo','modified-statement','bad-base64','empty-signature','null-signature'):
            data=deepcopy(self.data)
            if kind=='unknown-key':data['key_id']='unknown'
            elif kind=='unknown-issuer':data['issuer']='unknown'
            elif kind=='wrong-repo':data['statement']['repository_id']='synthetic/unregistered'
            elif kind=='modified-statement':data['statement']['commit_id']='different'
            elif kind=='bad-base64':data['signature']='%%%'
            elif kind=='empty-signature':data['signature']=''
            else:data['signature']=None
            self.attestation.write_text(json.dumps(data));self.output=self.base/kind/'report.json';value,result=self.assess()
            self.assertEqual(result['status'],'fail');self.assertEqual(value['exit_code'],0);self.compare_cli(value)
            if kind in ('unknown-key','unknown-issuer','wrong-repo','bad-base64','null-signature'):self.assertFalse(value['crypto']['attempted'])

    def test_explicit_context_subject_and_effective_level_match_original_helper(self):
        context={key:self.data['statement'][key] for key in logic.CONTEXT_FIELDS};subject=self.data['statement']['subject']
        for kind in ('same','context','subject'):
            expected=deepcopy(context);selected=deepcopy(subject)
            if kind=='context':expected['run_attempt']+=1
            if kind=='subject':selected['digest']='b'*64
            contextfile=self.base/'context.json';subjectfile=self.base/'subject.json';contextfile.write_text(json.dumps(expected));subjectfile.write_text(json.dumps(selected))
            for level in ('unverified','integrity_verified','provenance_verified'):
                self.output=self.base/kind/level/'report.json';value,result=self.assess(context=contextfile,subject=subjectfile,level=level)
                original=self.old.module.assess_attestation(attestation=self.data,registry=self.old.module.load_trust_roots(self.registry),
                    expected_context=expected,expected_subject=selected,evaluated_at=AT,attestation_ref=str(self.attestation),current_effective_level=level)
                self.assertEqual(result,original);self.assertEqual(self.output.read_bytes(),logic.wire(original));self.assertEqual(value['evidence_trust'],'unverified')

    def test_overwrite_preserves_prior_bytes_actual_output_mode_and_original_file_wire(self):
        self.output.parent.mkdir(mode=0o700);self.output.write_bytes(b'previous operator report\n');self.output.chmod(0o644)
        os.utime(self.output,(-1,-1))
        value,result=self.assess();metadata,files=self.app.input_data(value['input_id']);self.assertEqual(files['output-before.bin'],b'previous operator report\n')
        self.assertEqual(metadata['output_before_metadata']['st_mode']&0o777,0o644);self.assertEqual(self.output.stat().st_mode&0o777,0o644)
        self.compare_cli(value);value2,_=self.assess();self.assertNotEqual(value['operation_id'],value2['operation_id']);self.assertEqual(self.app.input_data(value2['input_id'])[1]['output-before.bin'],logic.wire(result))

    def test_missing_local_tool_matches_original_explicit_not_performed_result(self):
        directory=self.base/'only-git';directory.mkdir();(directory/'git').symlink_to(shutil.which('git'))
        with patch.dict(os.environ,{'PATH':str(directory)}):
            value,result=self.assess();self.assertEqual(result['status'],'fail');self.assertFalse(value['crypto']['process_started']);self.assertFalse(value['crypto']['signature_valid'])
            self.compare_cli(value)
        self.assertIn('not performed',result['checks'][1]['reason'])

    def test_default_product_registry_and_system_clock_keep_original_cli_semantics(self):
        value,result=self.app.verify(self.attestation,self.output,PROFILE)
        self.assertEqual(value['assessment_time_source'],'system_clock');self.assertEqual(self.app.input_data(value['input_id'])[0]['registry_origin'],'product_default_diagnostic_data')
        self.compare_cli(value,default_registry=True,automatic_time=True)

    def test_safe_yaml_alias_merge_duplicate_and_inert_typed_metadata_match_original(self):
        original=self.registry.read_text()
        for kind in ('scalar-alias','merge','duplicates','safe-metadata'):
            text=original
            if kind=='scalar-alias':text=text.replace('status: pilot_report_only','status: &status pilot_report_only')+'extra_status: *status\n'
            elif kind=='merge':text='defaults: &defaults\n  status: pilot_report_only\n  enforcement: report_only\n<<: *defaults\n'+text.replace('status: pilot_report_only\n','').replace('enforcement: report_only\n','')
            elif kind=='duplicates':text='status: ignored_prior_value\n'+text
            else:text+='extension:\n  date: 2026-11-17\n  binary: !!binary c3ludGhldGlj\n  labels: !!set {synthetic: null}\n  nonfinite: .nan\n'
            self.registry.write_text(text);self.output=self.base/kind/'report.json';value,_=self.assess();self.compare_cli(value)
        with self.assertRaises(ValueError):review_planning.yaml_object(b'x: one\nx: two\n')

    def test_original_does_not_enforce_registry_dates_or_declared_algorithm(self):
        text=self.registry.read_text().replace('algorithm: ed25519','algorithm: uninterpreted_legacy_label').replace('2026-07-17','2999-07-17')
        self.registry.write_text(text);value,result=self.assess();self.assertEqual(result['status'],'pass');self.compare_cli(value)
        self.assertFalse(value['registry_dates_enforced']);self.assertFalse(value['key_algorithm_enforced'])

    def test_replay_after_inputs_output_and_tool_disappear_runs_no_crypto(self):
        value,_=self.assess();self.attestation.unlink();self.registry.unlink();self.output.unlink()
        with patch('lib.attestation_application.verify_attestation_signature',side_effect=AssertionError('offline inspection invoked crypto')):
            checked=self.app.inspect(value['assessment_id'])
        self.assertTrue(checked['retained_complete_outputs_reverified']);self.assertFalse(checked['cryptographic_signature_reverified']);self.assertFalse(checked['current_input_or_destination_rechecked'])

    def test_node_input_artifact_and_rehashed_authority_tampering_rejected(self):
        value,_=self.assess();aid=value['assessment_id']
        with self.assertRaises(ValueError):AttestationContext(self.instance,{'node_id':'other-node'}).inspect(aid)
        path=self.app.inputs/value['input_id']/'attestation.json';before=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'input_bytes_changed'):self.app.inspect(aid)
        path.write_bytes(before);artifact=Path(value['data_directory'])/'native-assessment.json';raw=artifact.read_bytes();artifact.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'artifact_bytes_changed'):self.app.inspect(aid)
        artifact.write_bytes(raw);record=json.loads((self.app.assessments/(aid+'.json')).read_text());record['official_acceptance']=True;changed=canonical_digest(record)
        (self.app.assessments/(changed+'.json')).write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'invalid_attestation_assessment'):self.app.record(changed)

    def test_write_race_preserves_other_actor_and_records_native_result_without_success(self):
        self.output.parent.mkdir(mode=0o700);self.output.write_bytes(b'before')
        real=effects.apply
        def race(*args):self.output.write_bytes(b'other writer');return real(*args)
        with patch('lib.attestation_application.effects.apply',side_effect=race):value,result=self.assess()
        self.assertEqual(value['exit_code'],2);self.assertTrue(value['native_result_available']);self.assertEqual(self.output.read_bytes(),b'other writer')
        self.assertFalse(value['retained_complete_outputs_reverified']);self.assertTrue(value['retained_native_result_rederived'])
        self.assertEqual((Path(value['data_directory'])/'output-after.bin').read_bytes(),b'other writer')

    def test_pending_interruption_never_retries_or_replaces_output(self):
        with patch('lib.attestation_application.effects.apply',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.assess()
        operations=list(self.app.intents.glob('*.json'));self.assertEqual(len(operations),1)
        with patch('lib.attestation_application.verify_attestation_signature',side_effect=AssertionError('pending status started crypto')):value=self.app.status(operations[0].stem)
        self.assertEqual(value['state'],'pending');self.assertFalse(value['automatic_resume']);self.assertFalse(self.output.exists())

    def test_invalid_registry_json_and_resource_inputs_have_no_external_write(self):
        for raw in (b'[]',b'{invalid',b'x'*(logic.MAX_INPUT+1)):
            self.attestation.write_bytes(raw)
            if len(raw)>logic.MAX_INPUT:
                with self.assertRaises(ValueError):self.assess()
            else:
                value,_=self.assess();self.assertEqual(value['exit_code'],2);self.assertFalse(value['output_write_attempted']);self.assertFalse(value['crypto']['process_started'])
        self.attestation.write_text(json.dumps(self.data));self.registry.write_text('status: production\nenforcement: blocking\nroots: []\n')
        value,_=self.assess();self.assertEqual(value['exit_code'],2);self.assertFalse(value['output_write_attempted']);self.assertFalse(self.output.exists())

    def test_native_cli_stdout_and_zero_finding_exit_match_original(self):
        out=io.StringIO()
        with redirect_stdout(out):code=run(['verify',str(self.attestation),'--output',str(self.output),'--trust-roots',str(self.registry),'--evaluated-at',AT,'--profile',PROFILE],self.instance,self.settings)
        self.assertEqual(code,0);candidate=self.output.read_bytes();old=io.StringIO()
        with redirect_stdout(old):oldcode=self.old.cli([self.attestation,'--output',self.output,'--trust-roots',self.registry,'--evaluated-at',AT])
        self.assertEqual((code,out.getvalue()),(oldcode,old.getvalue()));self.assertEqual(candidate,self.output.read_bytes())

    def test_real_generated_signature_unicode_and_json_legacy_values_match_original(self):
        key=self.base/'private-key';public=self.base/'public-key';statement=self.base/'statement';signature=self.base/'signature'
        subprocess.run(['openssl','genpkey','-algorithm','Ed25519','-out',str(key)],check=True,capture_output=True);key.chmod(0o600)
        subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(public)],check=True,capture_output=True)
        for kind in ('unicode','nonfinite','duplicate-key'):
            value=deepcopy(self.data);value['statement']['extension']='Grüße — 安全'
            if kind=='nonfinite':value['statement']['extension']={'value':float('nan')}
            statement.write_bytes(self.old.module.canonical_statement(value['statement']))
            subprocess.run(['openssl','pkeyutl','-sign','-rawin','-inkey',str(key),'-in',str(statement),'-out',str(signature)],check=True,capture_output=True)
            value['signature']=__import__('base64').b64encode(signature.read_bytes()).decode()
            registry=deepcopy(self.roots);registry['roots'][0]['public_key_pem']=public.read_text()
            self.registry.write_text(__import__('yaml').safe_dump(registry));raw=json.dumps(value)
            if kind=='duplicate-key':raw=raw.replace('"key_id":','"key_id":"ignored_duplicate", "key_id":',1)
            self.attestation.write_text(raw);self.output=self.base/kind/'report.json';checked,result=self.assess()
            self.assertEqual(result['status'],'pass');self.compare_cli(checked)

    def test_bounded_controlled_crypto_failures_do_not_write_a_false_native_verdict(self):
        directory=self.base/'controlled-tools';directory.mkdir();tool=directory/'openssl'
        source=('#!'+sys.executable+'\n'+"import os,sys,time\nfrom pathlib import Path\nassert sys.argv[1:5]==['pkeyutl','-verify','-pubin','-rawin']\nmode=os.environ['AXIOM_CRYPTO_TEST_MODE']\nif mode=='timeout':time.sleep(30)\nif mode=='stream':sys.stdout.write('x'*70000);sys.stdout.flush();time.sleep(30)\nif mode=='changed-tool':Path(__file__).write_text('changed controlled fixture')\n").encode()
        for mode in ('timeout','stream','changed-tool'):
            tool.write_bytes(source);tool.chmod(0o700);self.output=self.base/mode/'report.json'
            self.assertEqual(hashlib.sha256(tool.read_bytes()).hexdigest(),hashlib.sha256(source).hexdigest())
            with patch.dict(os.environ,{'PATH':str(directory)+os.pathsep+os.environ['PATH'],'AXIOM_CRYPTO_TEST_MODE':mode}),patch('lib.providers.attestation_verification.TIMEOUT',1):
                checked,result=self.assess()
            self.assertEqual(checked['exit_code'],2);self.assertTrue(checked['crypto']['process_started']);self.assertIsNone(result)
            self.assertFalse(self.output.exists());self.assertFalse(checked['retained_complete_outputs_reverified'])
            self.assertIsNone(checked['crypto']['signature_valid']);self.assertTrue(checked['retained_artifacts_reverified'])
            if mode=='timeout':self.assertTrue(checked['crypto']['timed_out'])

    def test_output_symlink_hardlink_fifo_and_product_paths_leave_other_files_untouched(self):
        secret=self.base/'secret';secret.write_bytes(b'controlled unrelated secret')
        for kind in ('symlink','hardlink','fifo','group-writable'):
            self.output=self.base/kind/'report.json';self.output.parent.mkdir(mode=0o700)
            if kind=='symlink':self.output.symlink_to(secret)
            elif kind=='hardlink':os.link(secret,self.output)
            elif kind=='fifo':os.mkfifo(self.output,0o600)
            else:self.output.write_bytes(b'controlled unsafe output');self.output.chmod(0o660)
            with self.assertRaises((ValueError,OSError)):self.assess()
            self.assertEqual(secret.read_bytes(),b'controlled unrelated secret')
        self.output=ROOT/'forbidden-attestation-test.json'
        with self.assertRaisesRegex(ValueError,'outside_product'):self.assess()
        self.assertFalse(self.output.exists());self.output=self.instance/'forbidden.json'
        with self.assertRaisesRegex(ValueError,'outside_product'):self.assess()
        self.assertFalse(self.output.exists())

    def test_registry_resource_guards_reject_before_value_construction(self):
        original=self.registry.read_bytes()
        cases=[b'extension: &cycle [*cycle]\n',b'extension: !!python/object/apply:os.system [never_executed]\n',b'extension: '+b'['*70+b'0'+b']'*70+b'\n']
        for extra in cases:
            self.registry.write_bytes(original+extra);value,result=self.assess();self.assertEqual(value['exit_code'],2);self.assertIsNone(result)
            self.assertFalse(value['crypto']['attempted']);self.assertFalse(self.output.exists())

    def test_pending_after_actual_output_write_preserves_effect_without_automatic_retry(self):
        real=effects.apply
        def interrupt(*args):real(*args);raise KeyboardInterrupt
        with patch('lib.attestation_application.effects.apply',side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):self.assess()
        native=self.output.read_bytes();operation=next(self.app.intents.glob('*.json')).stem
        with patch('lib.attestation_application.verify_attestation_signature',side_effect=AssertionError('pending operation retried')):status=self.app.status(operation)
        self.assertEqual(status['state'],'pending');self.assertTrue(status['pending_may_have_external_effects']);self.assertEqual(self.output.read_bytes(),native)
        self.assertFalse(status['automatic_resume']);self.assertIsNone(status['assessment_id'])

    def test_input_alias_and_literal_relative_reference_preserve_native_original_bytes(self):
        alias=self.base/'input-alias.json';alias.symlink_to(self.attestation);self.attestation=alias
        checked,_=self.assess();self.compare_cli(checked)
        saved=Path.cwd()
        try:
            os.chdir(self.base);self.attestation=Path('input-alias.json');self.output=Path('relative-output/report.json')
            checked,_=self.assess();self.compare_cli(checked)
            report=json.loads(self.output.read_bytes());self.assertEqual(report['attestation_ref'],'input-alias.json')
        finally:os.chdir(saved)

    def test_explicit_input_output_same_path_keeps_original_effect_and_private_input_lineage(self):
        raw=self.attestation.read_bytes();self.output=self.attestation;checked,result=self.assess();native=self.output.read_bytes()
        self.assertEqual(self.app.input_data(checked['input_id'])[1]['attestation.json'],raw)
        self.assertEqual(self.app.input_data(checked['input_id'])[1]['output-before.bin'],raw)
        self.attestation.write_bytes(raw);stdout=io.StringIO()
        with redirect_stdout(stdout):self.assertEqual(self.old.cli([self.attestation,'--output',self.attestation,'--trust-roots',self.registry,'--evaluated-at',AT]),0)
        self.assertEqual(self.attestation.read_bytes(),native);self.assertTrue(self.app.inspect(checked['assessment_id'])['retained_complete_outputs_reverified'])

    def test_post_write_change_is_reported_without_a_broken_completed_record_or_rollback(self):
        real=effects.apply
        def race(*args):
            result=real(*args);self.output.write_bytes(b'other actor after write');return result
        with patch('lib.attestation_application.effects.apply',side_effect=race):checked,result=self.assess()
        self.assertEqual(checked['exit_code'],2);self.assertTrue(checked['native_result_available'])
        self.assertEqual(self.output.read_bytes(),b'other actor after write');self.assertFalse(checked['retained_complete_outputs_reverified'])
        self.assertEqual(self.app.status(checked['operation_id'])['diagnostic_exit_code'],2)

    def test_cleanup_failure_closes_crypto_pipes_without_claiming_a_signature_verdict(self):
        from lib.providers import attestation_verification as adapter
        original_popen=adapter.subprocess.Popen;original_stop=adapter.stop;started=[]
        def capture(*args,**kwargs):
            process=original_popen(*args,**kwargs)
            if Path(args[0][0]).name=='openssl':
                started.append(process)
                for stream in (process.stdout,process.stderr):self.addCleanup(stream.close)
            return process
        def failed_cleanup(process):
            original_stop(process)
            raise OSError('controlled cleanup observation failure after actual termination')
        with patch.object(adapter.subprocess,'Popen',side_effect=capture),patch.object(adapter,'stop',side_effect=failed_cleanup):
            checked,result=self.assess()
        self.assertEqual(checked['exit_code'],2);self.assertIsNone(result);self.assertFalse(self.output.exists())
        self.assertTrue(checked['crypto']['process_started']);self.assertIsNone(checked['crypto']['signature_valid'])
        self.assertFalse(checked['retained_complete_outputs_reverified']);self.assertFalse(checked['automatic_resume'])
        self.assertEqual(len(started),1);self.assertIsNotNone(started[0].poll())
        self.assertTrue(all(stream.closed for stream in (started[0].stdout,started[0].stderr)))


if __name__=='__main__':unittest.main()
