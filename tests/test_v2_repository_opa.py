"""Actual pinned OPA, durable per-process observations and failure cleanup."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.providers.repository_opa import RepositoryOPA
from lib.providers import process_groups
from lib.portable.runtime import approved_opa_hashes


@unittest.skipUnless(shutil.which('opa'), 'pinned OPA not present')
class RepositoryOPATests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workarea = Path(self.temporary.name).resolve()
        self.workarea.chmod(0o700)
        self.rows = []
        self.file = self.workarea / 'native.jsonl'
        self.tool = shutil.which('opa')
        self.hashes = frozenset(approved_opa_hashes('1.18.2'))

    def journal(self, stage):
        def append(row):
            event = {'stage': stage, 'observation': row}
            fd = os.open(self.file, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write((json.dumps(event, sort_keys=True) + '\n').encode())
                stream.flush(); os.fsync(stream.fileno())
            self.rows.append(copy.deepcopy(event))
        return append

    def port(self, **overrides):
        options = {'approved_hashes': self.hashes, 'workarea': self.workarea,
                   'on_intent': self.journal('intent'), 'on_start': self.journal('started'),
                   'on_finish': self.journal('finished')}
        options.update(overrides)
        return RepositoryOPA(self.tool, **options)

    def test_actual_pinned_version_and_original_repository_policy_check_are_journaled(self):
        port = self.port()
        files = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in (ROOT / 'policies/opa').rglob('*') if p.is_file()}
        result = port.check(files, directory_present=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
        self.assertEqual([row['stage'] for row in self.rows], ['intent', 'started', 'finished'] * 2)
        self.assertEqual([json.loads(line) for line in self.file.read_text().splitlines()], self.rows)
        self.assertEqual([row['request']['operation'] for row in port.observations], ['version', 'check'])
        for row in port.observations:
            self.assertTrue(row['process_started'])
            self.assertIsNone(row['error_type'])
            self.assertTrue(process_groups.consistent(row))
            self.assertEqual(row['tool_sha256'], hashlib.sha256(Path(self.tool).resolve().read_bytes()).hexdigest())
        self.assertEqual({p.name for p in self.workarea.iterdir()}, {'native.jsonl'})

    def test_real_syntax_error_is_preserved_as_findings_with_complete_raw_native_streams(self):
        port = self.port()
        result = port.check({'policies/opa/broken.rego': b'package test\ninvalid @\n'}, directory_present=True)
        self.assertNotEqual(result.returncode, 0)
        row = port.observations[-1]
        self.assertEqual(base64.b64decode(row['stdout_base64']).decode(), result.stdout)
        self.assertEqual(base64.b64decode(row['stderr_base64']).decode(), result.stderr)
        self.assertIn('rego_parse_error', result.stdout + result.stderr)
        self.assertIsNone(row['error_type'])
        self.assertEqual(row['request']['files']['policies/opa/broken.rego']['sha256'], hashlib.sha256(b'package test\ninvalid @\n').hexdigest())
        self.assertEqual({p.name for p in self.workarea.iterdir()}, {'native.jsonl'})

    def test_empty_existing_and_missing_directory_keep_native_exit_distinction(self):
        port = self.port()
        self.assertEqual(port.check({}, directory_present=True).returncode, 0)
        missing = port.check({}, directory_present=False)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('no such file or directory', missing.stdout + missing.stderr)

    def test_outside_inventory_and_nonbyte_inputs_fail_before_native_start(self):
        port = self.port(); before = len(self.rows)
        for files in ({'../outside.rego': b''}, {'model/outside.rego': b''}, {'policies/opa/x.rego': 'text'}):
            with self.assertRaises(ValueError): port.check(files, directory_present=True)
        with self.assertRaises(ValueError): port.check({'policies/opa/x.rego': b''}, directory_present=False)
        self.assertEqual(len(self.rows), before)

    def test_wrong_checksum_and_missing_journal_callbacks_never_start_a_process(self):
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(ValueError, 'checksum'): self.port(approved_hashes=frozenset({'0' * 64}))
            with self.assertRaisesRegex(ValueError, 'callbacks'): self.port(on_start=None)
        self.assertEqual(self.rows, [])

    def test_failed_intent_prevents_process_creation(self):
        def fail(_): raise OSError('controlled durable intent failure')
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(OSError, 'controlled durable intent'): self.port(on_intent=fail)
        self.assertEqual(self.rows, [])

    def test_start_journal_failure_closes_started_process_and_both_streams(self):
        import subprocess
        processes = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs); processes.append(process); return process
        def fail(_): raise OSError('controlled started journal failure')
        with patch('subprocess.Popen', side_effect=capture):
            with self.assertRaisesRegex(OSError, 'controlled started journal'): self.port(on_start=fail)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed and processes[0].stderr.closed)
        self.assertEqual(self.rows[-1]['stage'], 'finished')
        self.assertEqual(self.rows[-1]['observation']['error_type'], 'OSError')
        self.assertTrue(process_groups.consistent(self.rows[-1]['observation']))

    def test_start_failure_is_retained_without_claiming_a_started_process(self):
        with patch('subprocess.Popen', side_effect=OSError('controlled spawn failure')):
            with self.assertRaisesRegex(OSError, 'controlled spawn'): self.port()
        self.assertEqual([row['stage'] for row in self.rows], ['intent', 'finished'])
        row = self.rows[-1]['observation']
        self.assertFalse(row['process_started'])
        self.assertEqual(row['error_type'], 'OSError')
        self.assertTrue(process_groups.consistent(row))

    def test_arbitrary_program_and_check_paths_are_not_native_operations(self):
        port = self.port(); before = len(self.rows)
        for argv, request in [(['/bin/sh'], {'operation': 'shell'}),
                              ([port.tool[0], 'eval', 'http.send({})'], {'operation': 'version', 'version': '1.18.2'}),
                              ([port.tool[0], 'check', '/etc'], {'operation': 'check', 'directory_present': True, 'file_order': [], 'files': {}})]:
            with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
                with self.assertRaises(ValueError): port.observe(argv, request)
        self.assertEqual(len(self.rows), before)

    def test_timeout_is_retained_and_started_process_and_streams_are_closed(self):
        import subprocess
        processes = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs); processes.append(process); return process
        with patch('subprocess.Popen', side_effect=capture):
            with self.assertRaisesRegex(TimeoutError, 'repository_opa_timeout'): self.port(timeout=1e-12)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed and processes[0].stderr.closed)
        self.assertTrue(self.rows[-1]['observation']['timed_out'])
        self.assertEqual(self.rows[-1]['observation']['error_type'], 'TimeoutError')

    def test_finish_journal_failure_cannot_turn_into_a_successful_return(self):
        import subprocess
        processes = []
        original = subprocess.Popen
        def capture(*args, **kwargs):
            process = original(*args, **kwargs); processes.append(process); return process
        def fail(_): raise OSError('controlled finished journal failure')
        with patch('subprocess.Popen', side_effect=capture):
            with self.assertRaisesRegex(OSError, 'controlled finished journal'): self.port(on_finish=fail)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed and processes[0].stderr.closed)

    def test_replaced_workarea_is_rejected_before_staging_or_native_start(self):
        port = self.port(); before = len(self.rows)
        old = self.workarea.with_name(self.workarea.name + '-owned-moved')
        self.workarea.rename(old)
        self.addCleanup(shutil.rmtree, old)
        self.workarea.mkdir(mode=0o700)
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(ValueError, 'identity_changed'): port.check({}, directory_present=True)
        self.assertEqual(len(self.rows), before)
        self.assertEqual(list(self.workarea.iterdir()), [])

    def test_unowned_path_inside_workarea_is_not_an_admitted_check(self):
        port = self.port(); before = len(self.rows)
        path = self.workarea / 'repository-opa-unowned/policies/opa'
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(ValueError, 'not_owned'):
                port.observe([port.tool[0], 'check', str(path)],
                             {'operation': 'check', 'directory_present': False, 'file_order': [], 'files': {}})
        self.assertEqual(len(self.rows), before)

    def test_tool_identity_change_is_rejected_before_a_later_native_start(self):
        port = self.port(); before = len(self.rows)
        with patch('lib.providers.repository_opa.executable', return_value=(port.tool[0], '0' * 64)):
            with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
                with self.assertRaisesRegex(ValueError, 'tool_changed'): port.check({}, directory_present=True)
        self.assertEqual(len(self.rows), before)
        self.assertEqual({p.name for p in self.workarea.iterdir()}, {'native.jsonl'})


if __name__ == '__main__':
    unittest.main()
