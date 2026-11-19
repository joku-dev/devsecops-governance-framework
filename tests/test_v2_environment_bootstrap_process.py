"""Actual own-child outcomes and bounded capture without requiring installed deps."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.environment_bootstrap_storage import BootstrapJournal
from lib.providers import environment_bootstrap_process as native


class EnvironmentBootstrapProcesses(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.root.chmod(0o700)
        self.journal=BootstrapJournal(self.root,{'profile':'validation-environment-v1'},{'source':'explicit_test'})
        self.addCleanup(self.journal.close)
        self.runner=native.BootstrapProcesses(self.journal)
        self.journal.before('preflight')

    def run_own(self,program,**extra):
        return self.runner.run('test_own_program',[sys.executable,'-I','-S','-B','-c',program],
            cwd=self.root,environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},timeout=extra.pop('timeout',10),**extra)

    def events(self):
        return [json.loads(row)['payload'] for row in (self.journal.root/'events.jsonl').read_bytes().splitlines()]

    def test_actual_success_keeps_both_streams_and_intent_before_start_before_finish(self):
        value=self.run_own('import sys;sys.stdout.buffer.write(b"exact stdout\\n");sys.stderr.buffer.write(b"exact stderr\\n")')
        self.assertEqual(value['exit_code'],0)
        for channel,expected in [('stdout',b'exact stdout\n'),('stderr',b'exact stderr\n')]:
            row=value['streams'][channel]
            self.assertEqual((self.journal.root/row['path']).read_bytes(),expected)
            self.assertEqual(row['sha256'],hashlib.sha256(expected).hexdigest())
            self.assertEqual(row['bytes'],len(expected))
        kinds=[e['kind'] for e in self.events()]
        self.assertLess(kinds.index('native-intent'),kinds.index('native-started'))
        self.assertLess(kinds.index('native-started'),kinds.index('native-finished'))
        self.assertFalse(next(e for e in self.events() if e['kind']=='native-intent')['OS_network_or_process_tree_isolation_attested'])

    def test_actual_nonzero_exit_is_retained_without_becoming_process_start_failure(self):
        value=self.run_own('import sys;print("declared child failure");sys.exit(23)')
        self.assertEqual(value['exit_code'],23)
        self.assertTrue(value['terminal_result_observed'])

    def test_wall_timeout_leaves_intent_with_no_invented_completed_outcome(self):
        with self.assertRaisesRegex(TimeoutError,'wall_budget'):
            self.run_own('import time;time.sleep(10)',timeout=.1)
        self.assertIn('native-started',[e['kind'] for e in self.events()])
        self.assertNotIn('native-finished',[e['kind'] for e in self.events()])

    def test_stream_limit_stops_owned_child_and_never_reports_complete(self):
        with self.assertRaisesRegex(ValueError,'stream_budget'):
            self.run_own('import sys;sys.stdout.buffer.write(b"x"*4096)',stream_limit=128)
        self.assertNotIn('native-finished',[e['kind'] for e in self.events()])

    def test_log_write_failure_cannot_gain_successful_native_outcome(self):
        with patch.object(native,'write_all',side_effect=OSError('declared disk failure')):
            with self.assertRaisesRegex(OSError,'declared disk failure'):self.run_own('print("actual output")')
        self.assertNotIn('native-finished',[e['kind'] for e in self.events()])

    def test_invalid_command_or_absent_phase_never_starts_a_process(self):
        self.journal.after(self.journal.phase,None)
        with patch.object(native.subprocess,'Popen',side_effect=AssertionError('Must not start')):
            with self.assertRaisesRegex(ValueError,'durable_phase_intent'):self.run_own('print("forbidden")')
        self.journal.before('environment_python_executable')
        with patch.object(native.subprocess,'Popen',side_effect=AssertionError('Must not start')):
            with self.assertRaisesRegex(ValueError,'fixed_command_required'):
                self.runner.run('bad',['relative-python','-c','pass'],cwd=self.root,environment={},timeout=1)

    def test_failed_intent_fsync_prevents_actual_process_start(self):
        with patch.object(native.os,'fsync',side_effect=OSError('declared fsync failure')):
            with patch.object(native.subprocess,'Popen',side_effect=AssertionError('Must not start')):
                with self.assertRaisesRegex(OSError,'declared fsync failure'):self.run_own('print("forbidden")')

    def test_metadata_environment_never_serializes_environment_values(self):
        result=self.runner.run('test_own_program',[sys.executable,'-I','-S','-B','-c','print("ok")'],
            cwd=self.root,environment={'PATH':'/usr/bin:/bin','DECLARED_PRIVATE_VALUE':'never-log-this-value'},timeout=10)
        self.assertEqual(result['exit_code'],0)
        self.assertNotIn(b'never-log-this-value',(self.journal.root/'events.jsonl').read_bytes())

    def test_actual_partial_file_writes_are_completed_without_truncating_capture(self):
        actual_write=os.write
        def partial(descriptor,raw):
            return actual_write(descriptor,raw[:3])
        with patch.object(native.os,'write',side_effect=partial):
            outcome=self.run_own('print("a complete captured line")')
        row=outcome['streams']['stdout']
        self.assertEqual((self.journal.root/row['path']).read_bytes(),b'a complete captured line\n')
        self.assertEqual(row['bytes'],len(b'a complete captured line\n'))

    def test_inspection_binds_complete_native_capture_bytes_and_rejects_mutation(self):
        from lib.providers.environment_bootstrap_storage import inspect
        outcome=self.run_own('print("retained real native output")')
        value=inspect(self.journal.root)
        self.assertEqual(value['state'],'pending_incomplete')
        self.assertEqual(value['native_capture_outcomes_consistent'],1)
        path=self.journal.root/outcome['streams']['stdout']['path'];path.write_bytes(b'forged')
        with self.assertRaisesRegex(ValueError,'stream_bytes_changed'):inspect(self.journal.root)
