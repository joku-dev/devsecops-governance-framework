"""Native startup admission/leases and pre-exec records without serving a UI."""
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.environment_bootstrap import BootstrapFailure
from lib.providers.environment_bootstrap_native import NativeEnvironmentSession
from lib.providers.workbench_startup_native import NativeStartup,StartupJournal
from lib.workbench_startup_application import execute

class StartupAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.root.chmod(0o700)
        self.options={'environment':self.root/'environment','instance':self.root/'instance',
            'state_directory':self.root/'starts','python':sys.executable,'port':18975,'development':True}
        self.output=StringIO();self.quiet=redirect_stderr(self.output);self.quiet.__enter__()
        self.addCleanup(self.quiet.__exit__,None,None,None)
    def session(self,**options):return NativeStartup({**self.options,**options})
    def test_shared_server_leases_block_bootstrap_updates_until_every_reader_closes(self):
        with self.session() as first,self.session() as second:
            first._lease();second._lease()
            opts={**self.options,'state_directory':self.root/'bootstrap-records'}
            with self.assertRaises(BlockingIOError):NativeEnvironmentSession('source-intake-environment-v1',opts)
            first.close()
            with self.assertRaises(BlockingIOError):NativeEnvironmentSession('source-intake-environment-v1',opts)
        # No reader remains. The actual writer now obtains the same inode lease.
        with NativeEnvironmentSession('source-intake-environment-v1',opts) as writer:
            self.assertIsNotNone(writer.lock_fd)
    def test_incomplete_prior_bootstrap_stays_blocked_after_writer_process_releases_lock(self):
        opts={**self.options,'state_directory':self.root/'bootstrap-records'}
        with NativeEnvironmentSession('source-intake-environment-v1',opts) as writer:
            owner=writer.lock_path.read_bytes()
        with self.session() as startup:
            with self.assertRaisesRegex(BootstrapFailure,'reconciliation_required'):startup._lease()
            self.assertIsNone(startup.lease)
        self.assertEqual(writer.lock_path.read_bytes(),owner)
    def test_known_failed_bootstrap_is_not_silently_promoted_by_an_existing_interpreter(self):
        opts={**self.options,'state_directory':self.root/'bootstrap-records'}
        with NativeEnvironmentSession('source-intake-environment-v1',opts) as writer:
            token=writer.journal.before('preflight');writer.journal.failed(token,'explicit_test_failure')
            writer.finish({'state':'failed'},code='explicit_test_failure')
        with self.session() as startup:
            with self.assertRaisesRegex(BootstrapFailure,'reconciliation_required'):startup._lease()
    def test_private_lock_permissions_and_owner_metadata_are_required_before_reader_admission(self):
        for case in ('permissions','shape','foreign-target'):
            with self.subTest(case=case),self.session() as startup:
                path=self.root/('.axiom-bootstrap-'+hashlib.sha256(str(startup.target).encode()).hexdigest()[:24]+'.lock')
                path.write_text(json.dumps({'schema_version':1,'target':'foreign','record_root':'/invalid'}) if case=='foreign-target' else '{}')
                path.chmod(0o644 if case=='permissions' else 0o600)
                with self.assertRaises(BootstrapFailure):startup._lease()
                path.unlink()
    def test_exec_receives_durable_handoff_intent_and_inherits_environment_lease(self):
        class Replaced(BaseException):pass
        with self.session() as startup:
            startup._lease();token=startup.journal.before('handoff_workbench')
            def replace(binary,command,environment):
                rows=[json.loads(p.read_bytes()) for p in sorted(startup.journal.root.glob('event-*.json'))]
                self.assertEqual(rows[-1],{'kind':'phase-intent','phase':token,'action':'handoff_workbench'})
                self.assertTrue(os.get_inheritable(startup.lease))
                self.assertEqual(binary,startup.python)
                self.assertNotIn('AXIOM_WORKBENCH_KEY',environment)
                self.assertNotIn('PYTHONPATH',environment)
                self.assertEqual(command[1:3],['-I','-B'])
                raise Replaced()
            with patch('os.execve',side_effect=replace),self.assertRaises(Replaced):startup.handoff_workbench()
            self.assertEqual(startup.journal.phase,token)
    def test_rejected_exec_leaves_pending_intent_and_closes_lease_without_claiming_ready(self):
        with self.session() as startup:
            startup._lease();token=startup.journal.before('handoff_workbench');fd=startup.lease
            with patch('os.execve',side_effect=OSError('explicit exec failure')),self.assertRaises(OSError):startup.handoff_workbench()
            self.assertEqual(startup.journal.phase,token)
        with self.assertRaises(OSError):os.fstat(fd)
        rows=[json.loads(p.read_bytes()) for p in sorted(startup.journal.root.glob('event-*.json'))]
        self.assertEqual(rows[-1]['kind'],'phase-intent')
    def test_environment_and_instance_cannot_overlap_source_or_each_other(self):
        for options in ({'instance':self.root/'environment/node'}, {'environment':ROOT/'generated'},
                        {'state_directory':self.root/'instance'}, {'environment':ROOT.parent}):
            with self.subTest(options=options),self.assertRaises(BootstrapFailure):self.session(**options)
    def test_symlink_aliases_and_unrelated_environment_content_are_rejected_without_replacement(self):
        target=self.options['environment'];target.mkdir();(target/'keep').write_text('unrelated')
        alias=self.root/'alias';alias.symlink_to(target,target_is_directory=True)
        with self.assertRaisesRegex(BootstrapFailure,'symlink'):self.session(environment=alias)
        with self.session() as startup:
            with self.assertRaisesRegex(BootstrapFailure,'unrecognized'):startup.preflight()
        self.assertEqual((target/'keep').read_text(),'unrelated')
    def test_development_or_missing_explicit_profile_never_enables_publishing(self):
        for options in ({'enable_pr':True}, {'enable_pr':True,'publication_profile':self.root/'profile'},
                        {'enable_pr':True,'development':False}):
            with self.subTest(options=options),self.assertRaisesRegex(BootstrapFailure,'publication_profile'):self.session(**options)
        self.assertFalse(self.options['instance'].exists())
    def test_stdlib_firststart_help_never_imports_installed_validation_dependencies(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/start_axiom_v2_workbench.py'),'--help'],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn(b'--instance',result.stdout)
    def test_source_change_stops_before_native_execution(self):
        with self.session() as startup:
            startup.fingerprints={}
            with patch.object(startup,'preflight',side_effect=AssertionError('must not run')):
                with self.assertRaisesRegex(BootstrapFailure,'source_changed'):startup.perform('preflight')
    def test_journal_unsafe_mode_and_phase_reentry_rejected(self):
        unsafe=self.root/'unsafe';unsafe.mkdir();unsafe.chmod(0o755)
        with self.assertRaises(ValueError):self.session(state_directory=unsafe)
        with self.session() as startup:
            token=startup.journal.before('preflight')
            with self.assertRaisesRegex(ValueError,'already_open'):startup.journal.before('preflight')
            with self.assertRaisesRegex(ValueError,'mismatch'):startup.journal.after(token+1,None)
    def test_known_failure_and_unknown_capture_failure_keep_distinct_exit_and_record_states(self):
        for failure,expected in ((BootstrapFailure('explicit_test_failure'),1),(OSError('explicit native failure'),2)):
            with self.subTest(failure=failure),patch.object(NativeStartup,'preflight',side_effect=failure):
                self.assertEqual(execute(self.options),expected)
        self.assertFalse(self.options['instance'].exists())

if __name__=='__main__':unittest.main()
