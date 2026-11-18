"""Immutable operation records, interrupted writes and deleted-source reads."""
import hashlib
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import repository_operation as contract
from lib.providers.repository_operations import RepositoryOperation, load_operation
from lib.providers.repository_journal import RepositoryJournal
from lib.v2_boundary import violations
import test_v2_repository_capture as fixture


@unittest.skipUnless(shutil.which('git'), 'local Git not present')
class RepositoryOperationTests(unittest.TestCase):
    # Share the actual Git fixture setup without inheriting its nineteen tests.
    command = fixture.RepositoryCaptureTests.command
    commit = fixture.RepositoryCaptureTests.commit
    journal = fixture.RepositoryCaptureTests.journal
    port = fixture.RepositoryCaptureTests.port
    capture = fixture.RepositoryCaptureTests.capture

    def setUp(self):
        fixture.RepositoryCaptureTests.setUp(self)
        self.manifest, self.files, self.commit_raw = self.capture()
        self.operation = self.base / 'operation'; self.operation.mkdir(mode=0o700)
        self.header = {'schema_version': 1, 'kind': 'product-repository-validation',
            'operation_id': 'a' * 64, 'node_id': 'b' * 32, 'runtime_source_digest': 'c' * 64,
            'source_revision': self.revision, 'source_tree': self.manifest['tree'],
            'source_root': str(self.source), 'profile': self.manifest['profile'],
            'engine_profile': 'legacy-repository-validator-v1',
            'assessed_at': '2026-11-15T12:00:00Z', **contract.AUTHORITY}
        self.result = {'execution': 'complete', 'exception_type': None, 'exit_code': 0,
            'stdout': 'Validation passed\n', 'stderr': ''}
        self.outputs = {**self.files, 'generated/reports/new.txt': b'complete raw bytes\r\n\x00\xff'}

    def completed(self, **overrides):
        with RepositoryOperation(self.operation, self.header) as operation:
            operation.append({'kind': 'source-git', 'phase': 'intent', 'request': 'explicit captured request'})
            operation.retain_inputs(self.manifest, self.files, self.commit_raw)
            operation.append({'kind': 'engine', 'phase': 'completed'})
            operation.finish(overrides.get('result', self.result), self.outputs, {'explicit_scope': 'storage-test'})
        return load_operation(self.operation, self.header)

    def test_exact_private_bytes_survive_source_deletion_without_native_execution(self):
        value = self.completed(); shutil.rmtree(self.source)
        with patch('subprocess.Popen', side_effect=AssertionError('retained loading is offline')):
            reloaded = load_operation(self.operation, self.header)
        self.assertEqual(value, reloaded)
        self.assertEqual(reloaded['inputs'], self.files)
        self.assertEqual(reloaded['outputs'], self.outputs)
        self.assertEqual(reloaded['state'], 'recorded_complete_replay_unverified')
        self.assertFalse(reloaded['binding']['official_acceptance'])
        self.assertTrue(all(not path.stat().st_mode & 0o077 for path in self.operation.rglob('*')))

    def test_pending_record_exists_before_any_acquisition_and_is_never_resumed(self):
        with RepositoryOperation(self.operation, self.header):
            value = load_operation(self.operation, self.header)
            self.assertEqual(value['state'], 'pending_incomplete')
            self.assertNotIn('inputs', value)
        before = (self.operation / 'events.jsonl').read_bytes()
        with self.assertRaises(FileExistsError):RepositoryOperation(self.operation, self.header)
        self.assertEqual((self.operation / 'events.jsonl').read_bytes(), before)

    def test_changed_node_runtime_source_time_or_authority_rejects_an_existing_operation(self):
        self.completed()
        for name, changed in {'node_id': 'd' * 32, 'runtime_source_digest': 'd' * 64,
                'source_revision': 'd' * len(self.revision), 'source_tree': 'd' * len(self.revision),
                'source_root': '/different', 'assessed_at': '2026-11-16T12:00:00Z',
                'official_acceptance': True, 'mode': 'blocking'}.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                load_operation(self.operation, self.header | {name: changed})

    def test_boolean_versions_codes_and_false_authority_integer_are_not_interchangeable(self):
        for changed in ({'schema_version': True}, {'published': 0}, {'node_id': 'anything'},
                        {'source_root': '/a/../b'}, {'profile': 'implicit'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):contract.binding(self.header | changed)
        for changed in ({'exit_code': True}, {'execution': 'complete', 'exit_code': 2},
                        {'exception_type': 'ValueError'}, {'execution': 'incomplete'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):contract.outcome(self.result | changed)

    def test_incomplete_execution_remains_incomplete_and_never_claims_replay(self):
        value = self.completed(result=self.result | {'execution': 'incomplete', 'exit_code': 2,
                                                     'exception_type': 'FileNotFoundError'})
        self.assertEqual(value['state'], 'recorded_incomplete_replay_unverified')
        self.assertEqual(value['outcome']['exit_code'], 2)

    def test_source_and_non_generated_output_cannot_be_modified_by_an_operation(self):
        with RepositoryOperation(self.operation, self.header) as operation:
            operation.retain_inputs(self.manifest, self.files, self.commit_raw)
            for output in ({**self.outputs, 'model/catalog.json': b'changed'},
                           {**self.outputs, 'new.py': b'executable'},
                           {k: v for k, v in self.outputs.items() if k != 'README.md'}):
                with self.assertRaises(ValueError):operation.finish(self.result, output, {})
            self.assertFalse((self.operation / 'replay.json').exists())
            self.assertEqual(load_operation(self.operation, self.header)['state'], 'pending_incomplete')

    def test_every_input_and_terminal_record_is_durable_before_the_event_is_visible(self):
        actual = os.fsync; calls = []
        def sync(fd):calls.append(fd); return actual(fd)
        with patch('os.fsync', side_effect=sync):
            self.completed()
        # Each distinct blob plus capture/replay: data and containing directory.
        distinct = len({hashlib.sha256(raw).hexdigest() for raw in self.outputs.values()})
        self.assertGreaterEqual(len(calls), 2 * distinct + 2 * 2 + 6)

    def test_input_write_failure_poisoning_retains_pending_and_cannot_continue(self):
        with RepositoryOperation(self.operation, self.header) as operation:
            with patch('os.write', side_effect=OSError('controlled disk failure')):
                with self.assertRaises(OSError):operation.retain_inputs(self.manifest, self.files, self.commit_raw)
            self.assertEqual(load_operation(self.operation, self.header)['state'], 'pending_incomplete')
            with self.assertRaisesRegex(ValueError, 'not_appendable'):operation.append({'kind': 'anything'})

    def test_terminal_journal_failure_never_creates_a_completed_operation(self):
        with RepositoryOperation(self.operation, self.header) as operation:
            operation.retain_inputs(self.manifest, self.files, self.commit_raw)
            actual = operation.journal.append
            def append(row):
                if row['kind'] == 'operation-finished':raise OSError('controlled journal failure')
                return actual(row)
            with patch.object(operation.journal, 'append', side_effect=append):
                with self.assertRaises(OSError):operation.finish(self.result, self.outputs, {})
            self.assertEqual(load_operation(self.operation, self.header)['state'], 'pending_incomplete')
            with self.assertRaisesRegex(ValueError, 'not_appendable'):operation.finish(self.result, self.outputs, {})

    def test_completed_record_is_single_use_and_cannot_be_extended_or_overwritten(self):
        with RepositoryOperation(self.operation, self.header) as operation:
            operation.retain_inputs(self.manifest, self.files, self.commit_raw)
            operation.finish(self.result, self.outputs, {})
            before = (self.operation / 'events.jsonl').read_bytes()
            with self.assertRaises(ValueError):operation.append({'kind': 'after-terminal'})
            with self.assertRaises(ValueError):operation.finish(self.result, self.outputs, {})
            self.assertEqual((self.operation / 'events.jsonl').read_bytes(), before)

    def test_tampered_raw_content_and_capture_or_replay_metadata_are_rejected(self):
        self.completed()
        for path in [self.operation / 'capture.json', self.operation / 'replay.json',
                     next((self.operation / 'content').iterdir())]:
            original = path.read_bytes(); path.write_bytes(original + b'\n')
            with self.subTest(path=path.name), self.assertRaises(ValueError):load_operation(self.operation, self.header)
            path.write_bytes(original)

    def test_links_shared_files_and_unexpected_members_are_rejected(self):
        self.completed(); leaf = next((self.operation / 'content').iterdir())
        leaf.chmod(0o644)
        with self.assertRaises(ValueError):load_operation(self.operation, self.header)
        leaf.chmod(0o600); extra = self.operation / 'content' / ('e' * 64)
        extra.write_bytes(b'extra'); extra.chmod(0o600)
        with self.assertRaises(ValueError):load_operation(self.operation, self.header)
        extra.unlink(); outside = self.base / 'extra-link'; os.link(leaf, outside)
        with self.assertRaises(ValueError):load_operation(self.operation, self.header)
        outside.unlink(); raw = leaf.read_bytes(); leaf.unlink(); leaf.symlink_to(self.base / 'nonexistent')
        with self.assertRaises((ValueError, OSError)):load_operation(self.operation, self.header)
        leaf.unlink(); leaf.write_bytes(raw); leaf.chmod(0o600)
        extra = self.operation / 'unrecognized'; extra.write_bytes(b'extra')
        with self.assertRaises(ValueError):load_operation(self.operation, self.header)

    def test_rebound_content_directory_cannot_redirect_writes(self):
        with RepositoryOperation(self.operation, self.header) as operation:
            operation.retain_inputs(self.manifest, self.files, self.commit_raw)
            (self.operation / 'content').rename(self.operation / 'previous')
            (self.operation / 'content').mkdir(mode=0o700)
            with self.assertRaisesRegex(ValueError, 'directory_changed'):
                operation.finish(self.result, self.outputs, {})
            self.assertEqual(list((self.operation / 'content').iterdir()), [])

    def test_reserved_events_cannot_fake_a_completion_or_replace_the_binding(self):
        with RepositoryOperation(self.operation, self.header) as operation:
            for name in ('operation-start', 'inputs-retained', 'operation-finished'):
                with self.assertRaisesRegex(ValueError, 'reserved_event'):operation.append({'kind': name})
            self.assertEqual(load_operation(self.operation, self.header)['state'], 'pending_incomplete')

    def test_extra_events_after_completion_are_rejected_even_with_rebuilt_hash_chain(self):
        value = self.completed(); payloads = [row['payload'] for row in value['journal']]
        (self.operation / 'events.jsonl').unlink()
        with RepositoryJournal(self.operation, self.header) as journal:
            for payload in payloads[1:]:journal.append(payload)
            journal.append({'kind': 'late-event'})
        with self.assertRaisesRegex(ValueError, 'terminal_order_changed'):load_operation(self.operation, self.header)

    def test_core_contract_contains_no_native_or_provider_imports(self):
        name = 'scripts/lib/repository_operation.py'
        self.assertEqual(violations(name, (ROOT / name).read_text()), [])


if __name__ == '__main__':unittest.main()
