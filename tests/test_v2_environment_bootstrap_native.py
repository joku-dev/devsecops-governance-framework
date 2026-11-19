"""Admission and persisted ownership must hold before native environment writes."""
from pathlib import Path
import json,os,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.environment_bootstrap import BootstrapFailure
from lib.providers.environment_bootstrap_native import NativeEnvironmentSession
from lib.providers.environment_bootstrap_storage import inspect

class NativeBootstrapAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.root.chmod(0o700)
        self.options={'environment':self.root/'environment','state_directory':self.root/'records',
            'python':sys.executable,'development':True}
    def session(self,**options):
        return NativeEnvironmentSession('source-intake-environment-v1',{**self.options,**options})
    def test_opened_interrupted_operation_blocks_another_attempt_even_after_flock_released(self):
        with self.session() as first:
            record=first.journal.root;lock=first.lock_path
            owner=json.loads(lock.read_bytes());self.assertEqual(owner['record_root'],str(record))
        raw=lock.read_bytes()
        with patch('subprocess.Popen',side_effect=AssertionError('Must not execute')):
            with self.assertRaisesRegex(BootstrapFailure,'previous_operation_incomplete'):self.session()
        self.assertEqual(lock.read_bytes(),raw)
        self.assertIsNone(inspect(record)['declared_result'])
        self.assertFalse(self.options['environment'].exists())
    def test_a_returned_own_native_phase_requires_its_actual_native_capture(self):
        with self.session() as value:
            token=value.journal.before('preflight');value.journal.after(token,None)
            with self.assertRaisesRegex(ValueError,'successful_phase_native_evidence_mismatch'):
                inspect(value.journal.root)

    def test_writer_rechecks_owner_size_after_flock_when_previous_writer_finishes_during_admission(self):
        import fcntl,hashlib
        target=self.options['environment']
        path=self.root/('.axiom-bootstrap-'+hashlib.sha256(str(target).encode()).hexdigest()[:24]+'.lock')
        path.touch(mode=0o600);self.assertEqual(path.stat().st_size,0)
        original=fcntl.flock;interleaved=False;retained=[]
        def reordered(descriptor,operation):
            nonlocal interleaved
            if not interleaved:
                interleaved=True
                with self.session() as first:
                    retained.append((first.journal.root,path.read_bytes()))
                self.assertGreater(path.stat().st_size,0)
            return original(descriptor,operation)
        # A real previous writer creates an unfinished owner between this
        # caller's file open/stat and actual lock acquisition. No mock sizes or
        # invented completed result; only the finite interleaving is controlled.
        with patch('fcntl.flock',side_effect=reordered):
            with self.assertRaisesRegex(BootstrapFailure,'previous_operation_incomplete'):self.session()
        self.assertEqual(len(retained),1)
        self.assertEqual(path.read_bytes(),retained[0][1])
        self.assertIsNone(inspect(retained[0][0])['declared_result'])
        self.assertFalse(target.exists())

    def test_live_lock_blocks_second_coordinator_without_replacing_owner(self):
        with self.session() as first:
            raw=first.lock_path.read_bytes()
            with self.assertRaises(BlockingIOError):self.session()
            self.assertEqual(first.lock_path.read_bytes(),raw)
    def test_actual_recorded_known_failure_allows_new_explicit_attempt(self):
        with self.session() as first:
            token=first.journal.before('preflight');first.journal.failed(token,'bootstrap_interpreter_unavailable')
            first.finish({'state':'failed'},code='bootstrap_interpreter_unavailable');old=first.journal.root
        with self.session() as second:
            self.assertNotEqual(second.journal.root,old)
            self.assertEqual(inspect(old)['declared_result'],'failed')
    def test_corrupt_previous_record_blocks_before_native_execution_and_keeps_original_owner(self):
        with self.session() as first:record=first.journal.root;lock=first.lock_path
        raw=lock.read_bytes();(record/'events.jsonl').write_bytes(b'corrupt')
        with self.assertRaisesRegex(BootstrapFailure,'previous_operation_inspection_required'):self.session()
        self.assertEqual(lock.read_bytes(),raw)
    def test_alias_target_and_unrecognized_nonempty_directory_are_rejected(self):
        actual=self.root/'actual';actual.mkdir();alias=self.root/'alias';alias.symlink_to(actual,target_is_directory=True)
        with self.assertRaisesRegex(BootstrapFailure,'path_symlink'):self.session(environment=alias)
        (actual/'keep').write_text('existing unrelated data')
        with self.assertRaisesRegex(BootstrapFailure,'not_recognized'):self.session(environment=actual)
        self.assertEqual((actual/'keep').read_text(),'existing unrelated data')
    def test_captured_own_source_bytes_are_required_by_retained_inspection(self):
        with self.session() as value:record=value.journal.root
        self.assertIsNone(inspect(record)['declared_result'])
        path=record/'inputs/requirements-source-document-intake.lock';path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError,'captured_input_bytes_changed'):inspect(record)
    def test_unsupported_platform_is_known_failed_exit_one_before_environment_writes(self):
        from lib.environment_bootstrap_application import execute
        with patch('lib.providers.environment_bootstrap_native.select_tool',
                side_effect=ValueError("Unsupported validation platform: ('Explicit-test', 'none')")):
            value=execute('validation-environment-v1',self.options)
        self.assertEqual(value['exit_code'],1)
        self.assertEqual(value['state'],'failed')
        self.assertEqual(value['diagnostics'],['bootstrap_validation_platform_unsupported'])
        self.assertFalse(self.options['environment'].exists())
        retained=inspect(value['record_root'])
        self.assertEqual(retained['declared_result'],'failed')
        self.assertEqual(retained['native_capture_outcomes_consistent'],1)
        self.assertFalse(retained['official_acceptance'])

    def test_mirror_with_credentials_rejected_before_private_record_or_lock_is_created(self):
        with self.assertRaisesRegex(BootstrapFailure,'credential_free_https'):self.session(opa_mirror='https://user:password@example.invalid')
        self.assertEqual(list((self.root/'records').iterdir()),[])
        self.assertFalse(any(self.root.glob('*.lock')))

if __name__=='__main__':unittest.main()
