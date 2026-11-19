"""Stdlib admission/lease/capture tests; controlled pins are not official tool proof."""
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.validation_suite import Observation,run
from lib.providers.validation_suite_native import NativeSuite
from lib.providers.validation_suite_storage import SuiteJournal,SuiteSink,raw_new,inspect,verify_component_observations
from lib.v2_source import active_fingerprints

class StorageAndAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.root.chmod(0o700)
    def journal(self):
        target=self.root/'env';request={'profile':'legacy-local-validation-v1','arguments':['--check-tools'],
            'environment':str(target),'expected_opa_version':'1.18.2','check_tools':True,'instance':None}
        value=SuiteJournal(self.root,request,{'source_root':str(ROOT),'active_fingerprints':active_fingerprints(ROOT)})
        raw_new(value.root/'requirements-validation.txt',(ROOT/'requirements-validation.txt').read_bytes())
        raw_new(value.root/'validation-toolchain.env',(ROOT/'scripts/validation-toolchain.env').read_bytes())
        return value
    def finished(self):
        journal=self.journal();sink=SuiteSink()
        class Missing:
            def perform(self,action):return Observation(1,b'',b'explicit missing fixture\n')
        code=run(['--check-tools'],Missing(),journal,sink,environment_label=str(self.root/'env'),expected_opa_version='1.18.2')
        journal.finish({'profile':'legacy-local-validation-v1','state':'complete','original_exit_code':code,'full_default_requested':False},sink.bytes())
        return journal
    def test_known_missing_tool_result_replays_without_touching_a_live_environment(self):
        journal=self.finished();result=inspect(journal.root)
        self.assertTrue(result['retained_declared_replay_consistent']);self.assertEqual(result['original_exit_code'],1)
        self.assertFalse(result['current_environment_rechecked']);self.assertFalse(result['native_execution_authenticated'])
    def test_pending_intent_cannot_be_reported_as_a_completed_replay(self):
        journal=self.journal();journal.before('require_tools')
        value=inspect(journal.root);self.assertIsNone(value['declared_result']);self.assertFalse(value['retained_declared_replay_consistent'])
    def test_changed_raw_phase_stream_is_rejected(self):
        journal=self.finished();path=next(journal.root.glob('phase-*-stderr.bin'));path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'stream_changed'):inspect(journal.root)
    def test_changed_request_cannot_relabel_an_existing_result(self):
        journal=self.finished();path=journal.root/'request.json';data=json.loads(path.read_bytes());data['arguments']=[];data['check_tools']=False;path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'header_binding_changed|scope_changed'):inspect(journal.root)
    def test_changed_captured_pins_are_rejected(self):
        journal=self.finished();path=journal.root/'requirements-validation.txt';path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'captured_input_changed'):inspect(journal.root)
    def test_resealed_result_cannot_forge_full_scope_or_authority(self):
        for change in ({'full_default_requested':True},{'official_acceptance':True}):
            with self.subTest(change=change):
                journal=self.finished();path=journal.root/'result.json';value=json.loads(path.read_bytes());value.update(change);raw=(json.dumps(value)+'\n').encode();path.write_bytes(raw)
                terminal=sorted(journal.root.glob('event-*.json'))[-1];row=json.loads(terminal.read_bytes());row['result_sha256']=hashlib.sha256(raw).hexdigest();terminal.write_text(json.dumps(row))
                with self.assertRaisesRegex(ValueError,'scope_changed|authority_changed'):inspect(journal.root)
    def test_returned_version_phase_without_actual_captures_is_rejected(self):
        journal=self.journal();sink=SuiteSink()
        class Ports:
            def perform(self,action):return Observation(0,b'1.18.2\n' if action=='opa_version' else b'')
        code=run(['--check-tools'],Ports(),journal,sink,environment_label='/env',expected_opa_version='1.18.2')
        journal.finish({'profile':'legacy-local-validation-v1','state':'complete','original_exit_code':code,'full_default_requested':False},sink.bytes())
        with self.assertRaisesRegex(ValueError,'native_membership_changed'):inspect(journal.root)
    def test_unsafe_root_mode_symlink_and_changed_directory_identity_are_rejected(self):
        journal=self.journal();journal.root.chmod(0o755)
        with self.assertRaises(ValueError):journal.before('require_tools')
        journal.root.chmod(0o700);old=journal.root.with_name(journal.root.name+'-retained');journal.root.rename(old);journal.root.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'root_replaced'):journal.before('require_tools')
    def test_stdlib_help_and_full_argument_guard_run_before_dependency_import(self):
        program=ROOT/'scripts/run_axiom_v2_validation_suite.py'
        for args,expected in ((['--help'],0),(['--environment',str(self.root/'env')],2)):
            result=subprocess.run([sys.executable,'-I','-S','-B',str(program),*args],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,expected,result.stderr)
    def test_source_and_state_environment_paths_cannot_overlap_or_replace_product(self):
        defaults={'environment':self.root/'env','state_directory':self.root/'records','check_tools':True,'development':True,'output':'json'}
        for changed in ({'environment':ROOT.parent},{'state_directory':self.root/'env'},{'environment':ROOT/'something'}):
            with self.subTest(changed=changed),self.assertRaises(ValueError),redirect_stderr(StringIO()):NativeSuite({**defaults,**changed})
    def test_shell_signal_status_retains_original_bash_convention(self):
        from lib.providers.validation_suite_native import status
        self.assertEqual(status(-15),143);self.assertEqual(status(-2),130);self.assertEqual(status(29),29)

    def unit_capture(self):
        native=self.root/'work/native';native.mkdir(mode=0o700,parents=True)
        streams={'stdout':b'actual controlled output\n','stderr':b'\nRan 3 tests in 0.125s\n\nOK (skipped=1)\n'}
        outputs={name:raw_new(native/('unit-tests-'+name+'.bin'),raw) for name,raw in streams.items()}
        stats={'tests_run':3,'seconds':0.125,'skipped':1}
        row={'native_root':str(native),'native_outcome':{'command':[sys.executable,'-B','-m','unittest','discover','-s','tests'],'returncode':0,'outputs':outputs},'statistics':stats}
        observed=[{'action':'unit_tests','observation':Observation(0,**streams).wire()}]
        result={'full_unit_discovery_observed':True,'unit_statistics':stats}
        return observed,row,result
    def test_complete_unit_phase_requires_held_streams_and_matching_summary_and_statistics(self):
        rows,row,result=self.unit_capture()
        verify_component_observations(self.root,rows,{},[],[row],result)
        changed={**result,'unit_statistics':{**row['statistics'],'tests_run':4}}
        with self.assertRaisesRegex(ValueError,'statistics_changed'):
            verify_component_observations(self.root,rows,{},[],[row],changed)
        path=self.root/'work/native/unit-tests-stderr.bin';path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'stream_changed'):
            verify_component_observations(self.root,rows,{},[],[row],result)
    def test_returned_unit_phase_without_capture_or_without_full_discovery_claim_is_rejected(self):
        rows,row,result=self.unit_capture()
        with self.assertRaisesRegex(ValueError,'membership_changed'):
            verify_component_observations(self.root,rows,{},[],[],result)
        with self.assertRaisesRegex(ValueError,'unit_claim_changed'):
            verify_component_observations(self.root,rows,{},[],[row],{**result,'full_unit_discovery_observed':False})
    def test_declared_success_cannot_hide_a_failed_or_truncated_captured_unit_summary(self):
        rows,row,result=self.unit_capture()
        from copy import deepcopy
        for stderr in (b'partial dots ...',b'Ran 3 tests in 0.125s\n\nFAILED (failures=1)\n'):
            with self.subTest(stderr=stderr):
                current=deepcopy(row);path=self.root/'work/native/unit-tests-stderr.bin';path.write_bytes(stderr)
                current['native_outcome']['outputs']['stderr']={'path':path.name,'bytes':len(stderr),'sha256':hashlib.sha256(stderr).hexdigest()}
                observations=[{'action':'unit_tests','observation':Observation(0,b'actual controlled output\n',stderr).wire()}]
                with self.assertRaisesRegex(ValueError,'whole_unit_summary'):
                    verify_component_observations(self.root,observations,{},[],[current],result)
    def test_provenance_replay_requires_exact_raw_inputs_and_matches_the_returned_phase(self):
        directory=self.root/'provenance-inputs';directory.mkdir(mode=0o700)
        descriptor=raw_new(directory/'00000.bin',b'{}')
        manifest={'files':{'schemas/evidence-agent-provenance.schema.json':descriptor},'membership':['schemas/evidence-agent-provenance.schema.json'],'label':'/controlled-source'}
        rows=[{'action':'provenance_validation','observation':Observation(0,b'Evidence agent provenance validation passed\n').wire()}]
        verify_component_observations(self.root,rows,{},[manifest],[],{})
        changed=[{'action':'provenance_validation','observation':Observation(0,b'forged output\n').wire()}]
        with self.assertRaisesRegex(ValueError,'component_outcome_changed'):
            verify_component_observations(self.root,changed,{},[manifest],[],{})
    def test_selected_unit_subset_cannot_be_relabelled_as_whole_discovery(self):
        rows,row,result=self.unit_capture()
        row['native_outcome']['command']+=[ '-p','test_selected.py' ]
        with self.assertRaisesRegex(ValueError,'whole_unit_command_required'):
            verify_component_observations(self.root,rows,{},[],[row],result)
    def test_admission_failure_keeps_a_durable_incomplete_cause_without_native_success(self):
        from lib.validation_suite_application import execute
        options={'environment':self.root/'env','state_directory':self.root/'records',
            'check_tools':True,'development':True,'output':'json'}
        with patch.object(NativeSuite,'handoff_if_needed',side_effect=ValueError('validation_suite_deliberate_admission_refusal')),redirect_stderr(StringIO()):
            report,streams,code=execute(options)
        self.assertEqual(code,2);self.assertEqual(report['state'],'incomplete')
        self.assertEqual(report['diagnostics'],['validation_suite_deliberate_admission_refusal'])
        self.assertEqual(streams,{'stdout':b'','stderr':b''})
        record=Path(report['record_root']);held=json.loads((record/'result.json').read_bytes())
        self.assertEqual(held['exception_type'],'ValueError')
        self.assertFalse(inspect(record)['retained_declared_replay_consistent'])

if __name__=='__main__':unittest.main()
