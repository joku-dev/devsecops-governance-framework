"""Whole decision replay, negative ordering and retained exception semantics.

Native command responses below are declared decision fixtures. They do not
attest an actual product-suite execution or complete compliance acquisition.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_v2_compliance_result as original_cases
from lib.compliance_replay import record_generation, inspect_generation, failure, raise_failure
from lib.portable.contracts import canonical_digest


class ComplianceReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original_cases.CompleteComplianceDecisions.setUpClass()

    def record(self, case='pass', *, skip=False, output_name='result.json'):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / 'own-product'; source.mkdir()
            control = original_cases.CompleteComplianceDecisions.controls['green']
            environment = original_cases.ObservationEnvironment(source, root, case, control)
            with redirect_stdout(io.StringIO()):
                record = record_generation(environment, output_file=root / output_name,
                    target_repo=root / 'consumer-data', skip_unit_tests=skip)
            files = {path.name: path.read_bytes() for path in root.iterdir() if path.is_file()}
        # The entire source/consumer/export tree is now absent. All filesystem
        # resolution/native execution/output effects must come from the trace.
        return record, files

    @staticmethod
    def repin(record):
        record['record_digest'] = canonical_digest({k: v for k, v in record.items() if k != 'record_digest'})
        return record

    def test_complete_default_and_explicit_skip_replay_offline_without_native_or_file_operations(self):
        for skip in (False, True):
            with self.subTest(skip=skip):
                record, files = self.record(skip=skip)
                self.assertEqual(record['outcome']['original_exit_code'], 0)
                commands = [e['arguments'][0] for e in record['events'] if e['port'] == 'run']
                self.assertEqual(len(commands), 13 if skip else 14)
                self.assertEqual(any(c[:3] == ['python3', '-m', 'unittest'] for c in commands), not skip)
                self.assertEqual(len(record['outcome']['report']['artifacts']), 8)
                self.assertEqual(set(files), {'control-evaluation-report.json', 'control-evaluation-report.md', 'result.json'})
                with (patch.object(Path, 'resolve', side_effect=AssertionError('live path resolution')),
                        patch.object(Path, 'write_text', side_effect=AssertionError('live export write')),
                        patch('subprocess.Popen', side_effect=AssertionError('live native execution'))):
                    result = inspect_generation(record)
                self.assertTrue(result['original_decision_outcome_equal'])
                self.assertFalse(result['native_execution_authenticated'])

    def test_every_native_failure_and_original_empty_stdout_limitation_replay(self):
        for case in ('integration-findings', 'validator-failure', 'unit-failure',
                     'opa-check-failure', 'policy-native-failure', 'policy-findings', 'integration-empty-error'):
            with self.subTest(case=case):
                record, _ = self.record(case)
                self.assertEqual(record['outcome']['original_exit_code'], 0 if case == 'integration-empty-error' else 1)
                inspect_generation(record)

    def test_malformed_native_output_and_missing_parent_preserve_errors_without_inventing_output(self):
        for case, name, exception in (('integration-malformed', 'result.json', 'JSONDecodeError'),
                ('policy-malformed', 'result.json', 'KeyError'),
                ('missing-output-parent', 'absent/result.json', 'FileNotFoundError')):
            with self.subTest(case=case):
                record, files = self.record(case, output_name=name)
                self.assertEqual(record['outcome']['kind'], 'raised')
                self.assertEqual(record['outcome']['exception']['type'], exception)
                self.assertNotIn('result.json', files)
                inspect_generation(record)

    def test_output_aliases_replay_all_ordered_writes_instead_of_collapsing_effects(self):
        for name in ('control-evaluation-report.json', 'control-evaluation-report.md'):
            record, files = self.record(output_name=name)
            writes = [e for e in record['events'] if e['port'] == 'write']
            self.assertEqual(len(writes), 3)
            self.assertEqual(writes[-1]['arguments'][0], writes[0 if name.endswith('.json') else 1]['arguments'][0])
            self.assertIn(b'"governance_repo"', files[name])
            inspect_generation(record)

    def test_recomputed_record_checksum_does_not_hide_reordered_command_or_effect(self):
        record, _ = self.record()
        queries = [i for i, e in enumerate(record['events']) if e['port'] == 'run'
                   and e['arguments'][0][:2] == ['opa', 'eval']]
        changed = deepcopy(record)
        a, b = queries[:2]
        changed['events'][a], changed['events'][b] = changed['events'][b], changed['events'][a]
        with self.assertRaises(ValueError):
            inspect_generation(self.repin(changed))
        changed = deepcopy(record)
        next(e for e in changed['events'] if e['port'] == 'write')['arguments'][1] += 'changed bytes'
        with self.assertRaises(ValueError):
            inspect_generation(self.repin(changed))

    def test_changed_outcome_unused_event_or_authority_is_rejected(self):
        record, _ = self.record()
        for change in ('outcome', 'unused', 'authority'):
            changed = deepcopy(record)
            if change == 'outcome':
                changed['outcome']['report']['status'] = 'fail'
            elif change == 'unused':
                changed['events'].append(deepcopy(changed['events'][-1]))
            else:
                changed['official_acceptance'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspect_generation(self.repin(changed))

    def test_sorted_nested_json_is_not_silently_accepted_as_the_original_wire(self):
        record, files = self.record()
        control = next(e['value'] for e in record['events'] if e['port'] == 'control_report')
        self.assertEqual(list(control), list(original_cases.CompleteComplianceDecisions.controls['green']))
        self.assertEqual(files['control-evaluation-report.json'], (json.dumps(control, indent=2)+'\n').encode())
        sorted_record = json.loads(json.dumps(record, sort_keys=True))
        # The semantic checksum ignores mapping order. The complete replay must
        # still reject the changed formatted JSON, without relying on that pin.
        self.assertEqual(sorted_record['record_digest'], record['record_digest'])
        with self.assertRaises(ValueError):
            inspect_generation(sorted_record)

    def test_native_boolean_exit_and_unlisted_event_fields_are_rejected(self):
        record, _ = self.record()
        for mutation in ('boolean_exit', 'unexpected_field'):
            changed = deepcopy(record)
            native = next(e for e in changed['events'] if e['port'] == 'run')
            if mutation == 'boolean_exit':
                native['value']['returncode'] = False
            else:
                native['provider_approval'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                inspect_generation(self.repin(changed))

    def test_closed_exception_codec_preserves_type_arguments_and_filename(self):
        for error in (FileNotFoundError(2, 'No such file or directory', '/absent/output'),
                OSError(5, 'I/O error'), KeyError('missing'), TypeError('wrong type')):
            with self.subTest(error=type(error).__name__):
                encoded = failure(error)
                try:
                    raise_failure(encoded)
                except type(error) as replayed:
                    self.assertEqual(failure(replayed), encoded)
                    self.assertEqual(str(replayed), str(error))
                else:
                    self.fail('Exception was not raised')
