"""Whole original main/wire/file-effect comparisons with declared native fixtures.

These are deterministic decision tests, not an executed product-suite claim.
The original main is unchanged; only environment observations/clock are supplied.
"""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
import hashlib
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.compliance_result import ComplianceResult, EXPECTED_ARTIFACTS
from lib.compliance_replay import record_generation, inspect_generation, raise_failure
from lib.functional_parity import git_read, V1_REFERENCE
from control_evaluation import POLICY_QUERIES, render_control_evaluation_markdown

AT = '2026-11-15T12:00:00Z'


class Clock:
    @staticmethod
    def now(zone):
        assert zone == timezone.utc
        return datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


class ObservationEnvironment:
    def __init__(self, root, cwd, case, control):
        self.root, self.cwd, self.case, self.control = root, cwd, case, control
        self.commands = []
        self.writes = []

    def timestamp(self):
        return AT

    def resolve(self, path):
        return path.resolve()

    def print(self, value):
        print(value)

    def exists(self, path):
        return path.exists()

    def write(self, path, text):
        self.writes.append((path, text))
        path.write_text(text, encoding='utf-8')

    def control_report(self, path):
        if self.case == 'control-error':
            raise ValueError('declared_control_observation_error')
        return deepcopy(self.control)

    def control_markdown(self, report):
        return render_control_evaluation_markdown(report)

    def run(self, command, cwd=None):
        self.commands.append(command)
        code, out, err = 0, '', ''
        if len(command) > 1 and command[1].endswith('check_repo_governance_integration.py'):
            out = json.dumps({'checks': [{'id': 'complete-controlled-observation',
                'status': 'fail' if self.case == 'integration-findings' else 'pass'}]})
            if self.case == 'integration-empty-error':
                code, out, err = 9, '', 'declared integration acquisition failure'
            if self.case == 'integration-malformed':
                out = '{'
        elif len(command) > 1 and command[1].endswith('validate_governance_repo.py'):
            code = int(self.case == 'validator-failure')
        elif command[:3] == ['python3', '-m', 'unittest']:
            code = int(self.case == 'unit-failure')
            out = 'actual execution is not claimed by this decision fixture'
        elif command[:2] == ['opa', 'check']:
            code = int(self.case == 'opa-check-failure')
        elif command[:2] == ['opa', 'eval']:
            self.assert_query(command[-1])
            code = int(self.case == 'policy-native-failure' and command[-1] == next(iter(POLICY_QUERIES.values())))
            denies = ['declared finding'] if self.case == 'policy-findings' else []
            out = json.dumps({'result': [{'expressions': [{'value': denies}]}]})
            if self.case == 'policy-malformed':
                out = '{}'
        else:
            raise AssertionError('Unexpected command: ' + repr(command))
        return SimpleNamespace(returncode=code, stdout=out, stderr=err)

    @staticmethod
    def assert_query(query):
        if query not in POLICY_QUERIES.values():
            raise AssertionError('Unlisted policy query')


class CompleteComplianceDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = git_read(ROOT, 'show', V1_REFERENCE + ':scripts/generate_governance_compliance_result.py')
        matrix = json.loads((ROOT / 'config/axiom-v2-functional-parity.json').read_bytes())
        row = next(r for r in matrix['entrypoints'] if r['v1_path'] == 'scripts/generate_governance_compliance_result.py')
        if hashlib.sha256(raw).hexdigest() != row['v1_sha256']:
            raise AssertionError('Immutable original wrapper mismatch')
        cls.original = ModuleType('unchanged_original_compliance_main')
        cls.original.__file__ = str(ROOT / 'scripts/generate_governance_compliance_result.py')
        exec(compile(raw, cls.original.__file__, 'exec'), cls.original.__dict__)
        cls.controls = {}
        fixtures = ROOT / 'tests/fixtures/axiom-v1-parity'
        manifest = json.loads((fixtures / 'manifest.json').read_bytes())
        for key in ('green', 'red'):
            row = next(r for r in manifest['cases'] if r['id'] == 'controls-' + key)
            raw = (fixtures / row['report']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['report_sha256']:
                raise AssertionError('Complete original control result fixture mismatch')
            cls.controls[key] = json.loads(raw)

    def compare(self, case='pass', *, skip=False, output_name='result.json', default_target=False,
                overwrite=False, explicit_input=False, relative_output=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / 'product'
            source.mkdir()
            output = root / output_name
            if case != 'missing-output-parent':
                output.parent.mkdir(parents=True, exist_ok=True)
            # Only one retained artifact is physically present; missing inventory
            # slots must not become an invented original overall-pass predicate.
            artifact = source / EXPECTED_ARTIFACTS['status_viewer']
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b'controlled static artifact')
            control = self.controls['red' if case == 'control-findings' else 'green']
            observed = []
            for original in (True, False, 'recorded'):
                for path in (output, output.with_name('control-evaluation-report.json'),
                             output.with_name('control-evaluation-report.md')):
                    if path.is_file():
                        path.unlink()
                    if overwrite and path.parent.exists():
                        path.write_bytes(b'earlier result overwritten by explicit rerun')
                environment = ObservationEnvironment(source, root, case, control)
                stdout, stderr = io.StringIO(), io.StringIO()
                requested_output = output_name if relative_output else output
                arguments = ['original', '--output-file', str(requested_output)]
                inputs = root / 'explicit-original-control-input.json' if explicit_input else None
                if inputs is not None:
                    arguments += ['--input-file', str(inputs)]
                target = None if default_target else root / 'inspected-working-data'
                if target is not None:
                    arguments += ['--target-repo', str(target)]
                if skip:
                    arguments.append('--skip-unit-tests')
                error, result = None, None
                with redirect_stdout(stdout), redirect_stderr(stderr), patch.object(Path, 'cwd', return_value=root):
                    try:
                        if original is True:
                            with patch.multiple(self.original, ROOT=source, run=environment.run,
                                    datetime=Clock, generate_control_evaluation_report=environment.control_report), \
                                    patch.object(sys, 'argv', arguments):
                                result = self.original.main()
                        elif original is False:
                            result, _ = ComplianceResult(environment).generate(output_file=requested_output,
                                target_repo=target, input_file=inputs, skip_unit_tests=skip)
                        else:
                            record = record_generation(environment, output_file=requested_output,
                                target_repo=target, input_file=inputs, skip_unit_tests=skip)
                            inspect_generation(record)
                            if record['outcome']['kind'] == 'raised':
                                raise_failure(record['outcome']['exception'])
                            result = record['outcome']['original_exit_code']
                    except Exception as failure:
                        error = (type(failure).__name__, str(failure))
                outputs = {path.name: path.read_bytes() for path in output.parent.iterdir() if path.is_file()} if output.parent.exists() else {}
                observed.append((result, error, stdout.getvalue(), stderr.getvalue(), outputs, environment.commands))
            self.assertEqual(observed[0], observed[1])
            self.assertEqual(observed[0], observed[2])
            return observed[1]

    def test_default_runs_complete_original_command_and_every_ordered_query(self):
        result = self.compare(default_target=True)
        self.assertEqual(result[0], 0)
        self.assertEqual(len(result[5]), 14)
        self.assertEqual(result[5][2], ['python3', '-m', 'unittest', 'discover', '-s', 'tests'])
        self.assertEqual([c[-1] for c in result[5] if c[:2] == ['opa', 'eval']], list(POLICY_QUERIES.values()))
        report = json.loads(result[4]['result.json'])
        self.assertEqual(len(report['artifacts']), 8)
        self.assertTrue(any(r['status'] == 'missing' for r in report['artifacts']))
        self.assertEqual(report['control_evaluations'], self.controls['green'])

    def test_explicit_skip_preserves_legacy_wire_without_starting_a_unit_command(self):
        result = self.compare(skip=True)
        self.assertEqual(result[0], 0)
        self.assertFalse(any(c[:3] == ['python3', '-m', 'unittest'] for c in result[5]))
        self.assertEqual(json.loads(result[4]['result.json'])['execution']['unit_tests'],
            {'status': 'pass', 'command': 'skipped in nested/test context'})

    def test_native_findings_and_control_failures_match_whole_original_outputs(self):
        for case in ('integration-findings', 'validator-failure', 'unit-failure',
                     'opa-check-failure', 'policy-native-failure', 'policy-findings', 'control-findings'):
            with self.subTest(case=case):
                self.assertEqual(self.compare(case)[0], 1)

    def test_malformed_native_outputs_and_control_errors_preserve_partial_effects(self):
        for case in ('integration-malformed', 'policy-malformed', 'control-error'):
            with self.subTest(case=case):
                result = self.compare(case)
                self.assertIsNone(result[0])
                self.assertIsNotNone(result[1])
                self.assertNotIn('result.json', result[4])

    def test_original_empty_integration_failure_is_retained_as_a_known_wire_limitation(self):
        result = self.compare('integration-empty-error')
        self.assertEqual(result[0], 0)
        self.assertEqual(json.loads(result[4]['result.json'])['checks'], [])

    def test_explicit_rerun_output_alias_and_missing_parent_effects_match_original(self):
        self.assertEqual(self.compare(overwrite=True)[0], 0)
        self.assertEqual(self.compare(output_name='control-evaluation-report.json')[0], 0)
        self.assertEqual(self.compare(output_name='control-evaluation-report.md')[0], 0)
        result = self.compare('missing-output-parent', output_name='absent-parent/result.json')
        self.assertEqual(result[1][0], 'FileNotFoundError')

    def test_explicit_input_and_relative_output_retain_original_path_semantics(self):
        result = self.compare(explicit_input=True, relative_output=True, output_name='nested/result.json')
        self.assertEqual(result[0], 0)
        queries = [c for c in result[5] if c[:2] == ['opa', 'eval']]
        self.assertEqual(len(queries), 10)
        self.assertTrue(all(c[-2].endswith('/explicit-original-control-input.json') for c in queries))
