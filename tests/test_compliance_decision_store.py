"""Durable port ordering and interruption boundaries with declared native data."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_v2_compliance_result as original_cases
from lib.providers import compliance_decisions as store
from lib.providers.repository_journal import read_journal


class ComplianceDecisionStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original_cases.CompleteComplianceDecisions.setUpClass()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.operation = self.root / 'operation'; self.operation.mkdir(mode=0o700)
        self.source = self.root / 'own-product'; self.source.mkdir()
        self.header = {'schema_version': 1, 'kind': 'product-compliance-decision-record',
            'engine_profile': 'legacy-extended-compliance-v1', 'operation_id': '1'*64,
            'node_id': '2'*32, 'runtime_source_digest': '3'*64,
            'source_revision': '4'*40, 'source_tree': '5'*40, 'package_sha256': '6'*64,
            'assessed_at': original_cases.AT, **store.AUTHORITY}

    def environment(self, case='pass'):
        return original_cases.ObservationEnvironment(self.source, self.root, case,
            original_cases.CompleteComplianceDecisions.controls['green'])

    def record(self, environment=None, **options):
        with redirect_stdout(io.StringIO()):
            return store.record(self.operation, self.header, environment or self.environment(),
                output_file=self.root / 'result.json', **options)

    def test_every_native_intent_is_flushed_before_the_port_is_called(self):
        environment = self.environment()
        original = environment.run
        observed = []
        def run(command):
            events = read_journal(self.operation, expected_header=self.header)
            last = events[-1]['payload']
            self.assertEqual(last['phase'], 'intent')
            self.assertEqual(last['observation'], {'port': 'run', 'arguments': [command]})
            observed.append(command)
            return original(command)
        environment.run = run
        result = self.record(environment)
        self.assertEqual(len(observed), 14)
        self.assertEqual(result['state'], 'declared_decision_recorded_replay_consistent')
        self.assertFalse(result['native_acquisition_verified'])
        self.assertTrue(result['decision_replay_verified'])
        self.assertEqual(set(p.name for p in self.operation.iterdir()), {'decision.json', 'events.jsonl'})
        self.assertEqual((self.operation / 'decision.json').stat().st_mode & 0o777, 0o600)

    def test_interruption_preserves_pending_intent_without_completion_or_resume(self):
        environment = self.environment()
        original = environment.run
        def interrupt(command):
            if command[:3] == ['python3', '-m', 'unittest']:
                raise KeyboardInterrupt()
            return original(command)
        environment.run = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.record(environment)
        self.assertFalse((self.operation / 'decision.json').exists())
        result = store.load(self.operation, self.header)
        self.assertEqual(result['state'], 'pending_incomplete')
        self.assertFalse(result['decision_replay_verified'])
        self.assertFalse(result['native_acquisition_verified'])
        with self.assertRaises(FileExistsError):
            self.record()

    def test_original_error_can_have_a_complete_decision_record_without_native_success_claim(self):
        result = self.record(self.environment('integration-malformed'))
        self.assertEqual(result['decision']['outcome']['kind'], 'raised')
        self.assertEqual(result['decision']['outcome']['exception']['type'], 'JSONDecodeError')
        self.assertTrue(result['decision_replay_verified'])
        self.assertFalse(result['native_acquisition_verified'])
        self.assertFalse((self.root / 'result.json').exists())

    def test_private_storage_preserves_the_original_nested_json_order_and_exact_exports(self):
        environment = self.environment()
        result = self.record(environment)
        expected = (json.dumps(environment.control, indent=2)+'\n').encode()
        self.assertEqual((self.root / 'control-evaluation-report.json').read_bytes(), expected)
        retained = store.load(self.operation, self.header)['decision']
        observed = next(e['value'] for e in retained['events'] if e['port'] == 'control_report')
        self.assertEqual(list(observed), list(environment.control))
        self.assertEqual(retained, result['decision'])

    def test_retained_byte_tampering_and_unexpected_files_are_rejected(self):
        self.record()
        path = self.operation / 'decision.json'; raw = path.read_bytes()
        path.write_bytes(raw.replace(b'"pass"', b'"fail"', 1))
        with self.assertRaisesRegex(ValueError, 'retained_bytes_changed'):
            store.load(self.operation, self.header)
        path.write_bytes(raw)
        (self.operation / 'unlisted').write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError, 'membership_changed'):
            store.load(self.operation, self.header)

    def test_foreign_node_or_source_binding_does_not_reuse_a_record(self):
        self.record()
        for key, value in (('node_id', '7'*32), ('source_revision', '8'*40), ('package_sha256', '9'*64)):
            header = {**self.header, key: value}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'operation_binding_changed'):
                store.load(self.operation, header)

    def test_incomplete_journal_or_symlinked_final_record_never_becomes_consistent(self):
        self.record()
        path = self.operation / 'decision.json'; raw = path.read_bytes()
        path.unlink(); external = self.root / 'earlier.json'; external.write_bytes(raw); external.chmod(0o600)
        path.symlink_to(external)
        with self.assertRaises(OSError):
            store.load(self.operation, self.header)

    def test_authority_change_and_boolean_schema_are_rejected_before_any_event(self):
        for key in ('official_acceptance', 'schema_version'):
            header = {**self.header, key: True}
            with self.subTest(key=key), self.assertRaises(ValueError):
                store.record(self.operation, header, self.environment(), output_file=self.root / 'result.json')
            self.assertEqual(list(self.operation.iterdir()), [])
