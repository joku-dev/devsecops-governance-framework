"""Finite product orchestration, actual validator output and journal ordering."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_execution import RepositoryExecution, PROGRAMS
from lib.repository_provenance_validation import RepositoryProvenanceValidation
from lib.repository_snapshot_validation import RepositorySnapshotValidation
from lib.v2_boundary import violations

PROGRAM = 'scripts/validate_evidence_agent_provenance.py'


class RepositoryExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        self.root.mkdir(mode=0o700)
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        self.rows = []
        self.calls = []
        self.validator = RepositoryProvenanceValidation(self.root, validator_class=Draft202012Validator)

    def environment(self, **overrides):
        def unrequested(_): raise AssertionError('this test must not invoke an unrelated product function')
        def provenance(arguments):
            self.calls.append(('provenance', arguments))
            return self.validator.run()
        def release(root, policy): raise AssertionError('this test has no retained release reference scope')
        programs = {name: unrequested for name in PROGRAMS}
        programs[PROGRAM] = provenance
        options = {'validator_class': Draft202012Validator, 'programs': programs,
                   'snapshots': RepositorySnapshotValidation(self.root, validator_class=Draft202012Validator),
                   'verify_release_integrity': release, 'opa_check': None,
                   'append_event': lambda row: self.rows.append(copy.deepcopy(row))}
        options.update(overrides)
        return RepositoryExecution(self.root, **options)

    def command(self, program=PROGRAM, *arguments): return ['python', str(self.root / program), *arguments]

    def test_actual_provenance_validator_whole_outcome_is_journaled_as_product_function(self):
        expected = self.validator.run()
        environment = self.environment()
        with patch('subprocess.Popen', side_effect=AssertionError('source programs must never execute')):
            result = environment.run(self.command())
        self.assertEqual(vars(result), expected)
        self.assertEqual(self.calls, [('provenance', ())])
        self.assertEqual([row['phase'] for row in self.rows], ['intent', 'completed'])
        self.assertEqual(self.rows[-1]['outcome'], expected)
        self.assertEqual(self.rows[0]['request']['kind'], 'product-function')

    def test_real_invalid_input_keeps_complete_validator_stderr_and_exit_one(self):
        directory = self.root / 'status/evidence-agent-provenance'
        directory.mkdir(parents=True)
        (directory / 'bad.json').write_text('{')
        expected = self.validator.run()
        self.assertEqual(expected['returncode'], 1)
        actual = self.environment().run(self.command())
        self.assertEqual(vars(actual), expected)
        self.assertEqual(self.rows[-1]['outcome'], expected)

    def test_unknown_caller_program_and_shell_requests_never_invoke_a_callback(self):
        environment = self.environment()
        for command in (['sh', '-c', 'touch outside'], ['python', '-c', 'print(1)'],
                        self.command('scripts/caller.py'), ['python', '/etc/passwd'],
                        ['python', str(self.root) + '/../caller.py'],
                        ['python', str(self.root) + '//scripts/validate_evidence_agent_provenance.py']):
            with self.subTest(command=command):
                with self.assertRaises(ValueError): environment.run(command)
        self.assertEqual((self.rows, self.calls), ([], []))

    def test_unexpected_options_or_default_program_arguments_are_not_ignored(self):
        environment = self.environment()
        for options in ({'cwd': self.root.parent}, {'capture_output': False}, {'text': False},
                        {'check': True}, {'text': 1}):
            with self.assertRaises(ValueError): environment.run(self.command(), **options)
        with self.assertRaises(ValueError): environment.run(self.command(PROGRAM, '--arbitrary'))
        self.assertEqual((self.rows, self.calls), ([], []))

    def test_attestation_arguments_are_exactly_the_original_fixed_command(self):
        environment = self.environment()
        valid = self.command('scripts/verify_evidence_attestation.py',
            str(self.root / 'docs/examples/evidence-attestation.example.json'), '--output',
            str(self.root / 'generated/reports/evidence-attestation-pilot.json'), '--evaluated-at', '2026-07-17T10:01:00Z')
        # The intentionally unprovided test-only callback must be reached only
        # for that registered command, never for changed input or output paths.
        changed = list(valid); changed[2] = '/etc/passwd'
        with self.assertRaises(ValueError): environment.run(changed)
        self.assertEqual(self.rows, [])
        with self.assertRaises(AssertionError): environment.run(valid)
        self.assertEqual([row['phase'] for row in self.rows], ['intent', 'incomplete'])

    def test_failed_intent_prevents_any_product_effect(self):
        def fail(_): raise OSError('controlled intent failure')
        environment = self.environment(append_event=fail)
        with self.assertRaisesRegex(OSError, 'controlled intent'): environment.run(self.command())
        self.assertEqual(self.calls, [])

    def test_missing_port_cannot_be_replaced_by_synthetic_success(self):
        with self.assertRaises(ValueError): self.environment(programs={})
        with self.assertRaises(ValueError): self.environment(snapshots=object())
        with self.assertRaises(ValueError): self.environment(verify_release_integrity=None)
        with self.assertRaises(ValueError): self.environment(append_event=None)

    def test_malformed_callback_result_stays_incomplete(self):
        environment = self.environment()
        for outcome in ({'returncode': True, 'stdout': '', 'stderr': ''},
                        {'returncode': 0, 'stdout': ''},
                        {'returncode': 0, 'stdout': '', 'stderr': '', 'approved': True}):
            environment.programs[PROGRAM] = lambda arguments, value=outcome: value
            with self.assertRaises(ValueError): environment.run(self.command())
            self.assertEqual(self.rows[-1]['phase'], 'incomplete')
            self.assertNotIn('outcome', self.rows[-1])

    def test_nested_functions_keep_start_completion_order_and_individual_identity(self):
        environment = self.environment()
        parent = 'scripts/generate_governance_change_impact_report.py'
        def invoke(_):
            self.assertEqual(self.rows[-1]['phase'], 'intent')
            return vars(environment.run(self.command()))
        environment.programs[parent] = invoke
        result = environment.run(self.command(parent))
        self.assertEqual(vars(result), self.validator.run())
        self.assertEqual([(row['sequence'], row['phase']) for row in self.rows],
                         [(1, 'intent'), (2, 'intent'), (2, 'completed'), (1, 'completed')])

    def test_unavailable_opa_remains_missing_and_arbitrary_native_operations_fail(self):
        environment = self.environment()
        self.assertIsNone(environment.which('opa'))
        with self.assertRaises(ValueError): environment.which('sh')
        with self.assertRaises(ValueError): environment.run(['opa', 'check', str(self.root / 'policies/opa')])
        with self.assertRaises(ValueError): environment.run(['opa', 'eval', 'true'])
        self.assertEqual(self.rows, [])

    def test_release_scope_cannot_be_redirected_to_another_repository_or_policy(self):
        environment = self.environment()
        with self.assertRaises(ValueError): environment.verify_release_integrity(self.root.parent, self.root / 'model/governance/release-signing-policy.yaml')
        with self.assertRaises(ValueError): environment.verify_release_integrity(self.root, self.root / 'other.yaml')
        self.assertEqual(self.rows, [])

    def test_output_stays_in_retained_streams_even_with_explicit_none(self):
        environment = self.environment(); ambient = io.StringIO()
        with redirect_stdout(ambient):
            environment.print('retained', file=None)
            environment.print('diagnostic', file=environment.stderr)
        self.assertEqual(ambient.getvalue(), '')
        self.assertEqual(environment.stdout.getvalue(), 'retained\n')
        self.assertEqual(environment.stderr.getvalue(), 'diagnostic\n')
        with self.assertRaises(ValueError): environment.print('outside', file=io.StringIO())
        with self.assertRaises(ValueError): environment.print('x' * (1024 * 1024 + 1))

    def test_new_execution_is_neutral_and_does_not_import_native_or_legacy_engine(self):
        name = 'scripts/lib/repository_execution.py'
        self.assertEqual(violations(name, (ROOT / name).read_text()), [])


if __name__ == '__main__':
    unittest.main()
