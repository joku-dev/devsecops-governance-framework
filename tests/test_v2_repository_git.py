"""Native Git failure observations, durable-start guards and resource cleanup."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.providers.repository_git import RepositoryGit
from lib.providers import process_groups


@unittest.skipUnless(shutil.which('git'), 'local Git not present')
class RepositoryGitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.root.chmod(0o700)
        self.rows = []
        self.tool = shutil.which('git')
        subprocess.run([self.tool, '-c', 'core.hooksPath=/dev/null', 'init', '-b', 'fixture'],
                       cwd=self.root, check=True, capture_output=True, timeout=10)

    def port(self, **overrides):
        def record(stage): return lambda row: self.rows.append({'stage': stage, 'observation': copy.deepcopy(row)})
        options = {'on_intent': record('intent'), 'on_start': record('started'), 'on_finish': record('finished')}
        options.update(overrides)
        return RepositoryGit(self.root, self.tool, **options)

    def test_arbitrary_command_transport_checkout_and_shell_are_rejected_before_start(self):
        port = self.port(); before = len(self.rows)
        for args in (('fetch', 'https://example.invalid/repo'), ('checkout', 'main'), ('-c', 'alias.x=!sh', 'x'),
                     ('cat-file', 'blob', '../outside'), ('ls-tree', 'HEAD'), ('sh', '-c', 'touch outside')):
            with self.assertRaises(ValueError): port.read(*args)
        self.assertEqual(len(self.rows), before)

    def test_actual_missing_object_retains_nonzero_exit_stderr_and_cleanup(self):
        port = self.port()
        with self.assertRaisesRegex(ValueError, 'read_failed'): port.read('cat-file', 'blob', '0' * 40)
        row = port.observations[-1]
        self.assertTrue(row['process_started'])
        self.assertNotEqual(row['returncode'], 0)
        self.assertTrue(row['stderr_base64'])
        self.assertEqual(row['error_type'], 'ValueError')
        self.assertTrue(process_groups.consistent(row))

    def test_intent_failure_prevents_any_process_from_starting(self):
        def fail(_): raise OSError('controlled intent failure')
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(OSError, 'controlled intent'): self.port(on_intent=fail)
        self.assertEqual(self.rows, [])

    def test_start_failure_retains_an_unstarted_native_observation(self):
        with patch('subprocess.Popen', side_effect=OSError('controlled spawn failure')):
            with self.assertRaisesRegex(OSError, 'controlled spawn'): self.port()
        self.assertEqual([r['stage'] for r in self.rows], ['intent', 'finished'])
        row = self.rows[-1]['observation']
        self.assertFalse(row['process_started'])
        self.assertEqual(row['error_type'], 'OSError')
        self.assertTrue(process_groups.consistent(row))

    def test_started_journal_failure_closes_child_and_all_streams(self):
        original = subprocess.Popen; processes = []
        def started(*args, **options):
            process = original(*args, **options); processes.append(process); return process
        def fail(_): raise OSError('controlled start journal failure')
        with patch('subprocess.Popen', side_effect=started):
            with self.assertRaisesRegex(OSError, 'controlled start journal'): self.port(on_start=fail)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed and processes[0].stderr.closed)
        self.assertEqual(self.rows[-1]['observation']['error_type'], 'OSError')

    def test_timeout_cannot_return_a_successful_git_fact(self):
        with self.assertRaisesRegex(TimeoutError, 'repository_git_timeout'): self.port(timeout=1e-12)
        self.assertTrue(self.rows[-1]['observation']['timed_out'])
        self.assertEqual(self.rows[-1]['observation']['error_type'], 'TimeoutError')
        self.assertTrue(process_groups.consistent(self.rows[-1]['observation']))

    def test_finish_journal_failure_propagates_after_process_cleanup(self):
        original = subprocess.Popen; processes = []
        def started(*args, **options):
            process = original(*args, **options); processes.append(process); return process
        def fail(_): raise OSError('controlled finish journal failure')
        with patch('subprocess.Popen', side_effect=started):
            with self.assertRaisesRegex(OSError, 'controlled finish journal'): self.port(on_finish=fail)
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed and processes[0].stderr.closed)

    def test_changed_tool_and_replaced_checkout_are_rejected_before_a_later_start(self):
        port = self.port(); before = len(self.rows)
        with patch('lib.providers.repository_git.executable', return_value=(port.tool[0], '0' * 64)):
            with self.assertRaisesRegex(ValueError, 'tool_changed'): port.read('--version')
        old = self.root.with_name(self.root.name + '-owned-old')
        self.root.rename(old); self.addCleanup(shutil.rmtree, old); self.root.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'identity_changed'): port.read('--version')
        self.assertEqual(len(self.rows), before)

    def test_raw_native_output_limit_is_enforced_before_unbounded_accumulation(self):
        port = self.port()
        original_open = subprocess.Popen; original_read = os.read; outputs = set(); processes = []
        def started(*args, **options):
            process = original_open(*args, **options)
            if args[0][0] == port.tool[0]:
                processes.append(process); outputs.add(process.stdout.fileno())
            return process
        def read(fd, maximum):
            if fd in outputs: return b'x' * 8193
            return original_read(fd, maximum)
        with patch('subprocess.Popen', side_effect=started), patch('os.read', side_effect=read):
            with self.assertRaisesRegex(ValueError, 'stream_budget'): port.read('--version')
        row = port.observations[-1]
        self.assertTrue(row['output_truncated'])
        self.assertIsNotNone(processes[0].poll())
        self.assertTrue(processes[0].stdout.closed and processes[0].stderr.closed)

    def test_a_git_program_from_the_inspected_repository_cannot_be_selected_as_a_tool(self):
        fake = self.root / 'git'
        fake.write_text('#!/bin/sh\necho git version fake\n'); fake.chmod(0o700)
        with patch('subprocess.Popen', side_effect=AssertionError('inspected program must not execute')):
            with self.assertRaisesRegex(ValueError, 'inside_inspected_source'):
                RepositoryGit(self.root, fake, on_intent=lambda row:None, on_start=lambda row:None, on_finish=lambda row:None)

    def test_journal_callbacks_are_mandatory(self):
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(ValueError, 'callbacks_required'): self.port(on_intent=None)


if __name__ == '__main__': unittest.main()
