"""Execute the unchanged frozen V1 CLI; compare complete outputs and effects."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.runtime_validation import RuntimeValidation
from lib.validation_files import ValidationFiles
from lib.validation_operations import RuntimeValidationEnvironment
from lib.providers.validation_tools import ValidationOPA
from lib.providers import validation_tools
from lib.validation_application import ValidationContext
from lib.validation_application import execute
from lib.validation_replay import ReplayOPA, encoded
from lib.validation_queries import request
from lib.portable import runtime as portable_runtime
from test_portable_runtime import OPA

spec = importlib.util.spec_from_file_location('original_runtime_validation',
    ROOT / 'tests/acceptance/v1_runtime_validation_oracle.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
DIRECTORY = ROOT / 'tests/fixtures/v2-runtime-validation'


class OriginalRuntimeValidation(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.original = oracle.Original(DIRECTORY, Path(temporary.name).resolve())
        self.data = deepcopy(self.original.contract['data'])

    def edit_yaml(self, name, change):
        value = yaml.safe_load(self.data[name])
        change(value)
        self.data[name] = yaml.safe_dump(value, sort_keys=False).encode()

    def compare(self, *, opa=OPA):
        self.original.write_data(self.data)
        # Membership is only an existence fact. The source programs are never
        # read or executed by the product implementation.
        membership = (set(self.original.contract['membership']) -
            set(self.original.contract['data'])) | set(self.data)
        files = ValidationFiles(self.data, membership, label=str(self.original.root))
        port = ValidationOPA(opa, product_root=self.original.root)
        environment = RuntimeValidationEnvironment(files, port)
        code = RuntimeValidation(environment).main()
        old_code, old_stdout, old_stderr, old_files = self.original.run(opa=opa)
        self.assertEqual((code, environment.stdout.getvalue().encode(), environment.stderr.getvalue().encode()),
                         (old_code, old_stdout, old_stderr))
        self.assertEqual(files.files, old_files)
        self.assertTrue(all(not item['process_started'] for item in environment.commands))
        self.assertTrue(all(item['process_started'] for item in port.observations))
        return code, environment, port

    def test_success_whole_cli_streams_all_generated_files_and_eight_real_queries(self):
        code, environment, port = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(len(port.observations), 8)
        self.assertEqual(len(environment.commands), 3)
        self.assertIn('- expected markers: 41\n', environment.stdout.getvalue())
        self.assertIn('- architecture requirements: 14\n', environment.stdout.getvalue())

    def test_duplicate_missing_and_unknown_marker_ids(self):
        def change(value):
            value['markers'][0]['id'] = value['markers'][1]['id']
            value['markers'][-1]['id'] = 'UNKNOWN'
        self.edit_yaml('architecture/quality-markers.yaml', change)
        code, environment, _ = self.compare()
        self.assertEqual(code, 1)
        self.assertIn('Duplicate architecture marker IDs:', environment.stdout.getvalue())
        self.assertIn('Missing architecture marker IDs:', environment.stdout.getvalue())
        self.assertIn('Unknown architecture marker IDs:', environment.stdout.getvalue())

    def test_unknown_level_references_and_wrong_requirement_count(self):
        def change(value):
            value['requirements'].pop()
            value['requirements'][0].update(source_markers=['UNKNOWN'],
                source_guardrails=['UNKNOWN'], source_review_gates=['UNKNOWN'])
        self.edit_yaml('architecture/arch-l1.yaml', change)
        code, environment, _ = self.compare()
        self.assertEqual(code, 1)
        for text in ('unknown markers:', 'unknown guardrails:', 'unknown review gates:',
                     'Unexpected ARCH-L1 architecture requirement count:'):
            self.assertIn(text, environment.stdout.getvalue())

    def test_missing_optional_demo_input_still_reports_its_schema_failure(self):
        del self.data['generated/demo/ha-cpswms-architecture-release-input.json']
        code, environment, port = self.compare()
        self.assertEqual(code, 1)
        self.assertEqual(len(port.observations), 4)
        self.assertEqual(len(environment.commands), 2)

    def test_missing_optional_devsecops_report_skips_combination(self):
        del self.data['generated/demo/ha-cpswms-devsecops-governance-report.json']
        code, environment, _ = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(len(environment.commands), 2)

    def test_malformed_exception_schema_json(self):
        self.data['schemas/architecture-exception.schema.json'] = b'{invalid'
        code, environment, _ = self.compare()
        self.assertEqual(code, 1)
        self.assertIn('is not valid JSON:', environment.stdout.getvalue())

    def test_empty_remediations(self):
        self.edit_yaml('architecture/remediation-actions.yaml', lambda v: v.update(remediations=[]))
        code, environment, _ = self.compare()
        self.assertEqual(code, 1)
        self.assertIn('contains no remediations', environment.stdout.getvalue())

    def test_absent_opa_keeps_original_failures_and_other_generator_effects(self):
        code, environment, port = self.compare(opa=None)
        self.assertEqual(code, 1)
        self.assertEqual(port.observations, [])
        self.assertEqual(len(environment.commands), 3)
        self.assertIn('OPA executable not found', environment.stdout.getvalue())

    def test_additional_policy_findings_alone_do_not_fail_original_validator(self):
        # Trusted synthetic policy in the isolated product fixture, not a
        # caller-provided executable accepted by the installed application.
        self.data['policies/opa/architecture_readiness.rego'] = (
            b'package architecture.readiness\nimport rego.v1\ndeny contains "synthetic finding" if { true }\n')
        code, environment, port = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(len(port.observations), 8)
        report = json.loads(environment.files.files['generated/demo/ha-cpswms-architecture-governance-report.json'])
        self.assertGreater(report['summary']['finding_count'], 0)

    def test_primary_policy_findings_fail_but_remaining_example_queries_still_run(self):
        self.data['policies/opa/architecture_release_readiness.rego'] = (
            b'package architecture.release_readiness\nimport rego.v1\ndeny contains "synthetic finding" if { true }\n')
        code, environment, port = self.compare()
        self.assertEqual(code, 1)
        self.assertEqual(len(port.observations), 8)
        self.assertIn('Example architecture release candidate failed policy:', environment.stdout.getvalue())

    def test_actual_native_responses_replay_all_outputs_without_starting_a_process(self):
        _, environment, port = self.compare()
        retained = encoded(port.observations)
        replay = ReplayOPA(retained, available=True, tool_sha256=port.tool_sha256)
        files = ValidationFiles(self.data, self.original.contract['membership'], label=str(self.original.root))
        other = RuntimeValidationEnvironment(files, replay)
        with patch('subprocess.Popen', side_effect=AssertionError('offline replay started a process')):
            self.assertEqual(RuntimeValidation(other).main(), 0)
            replay.finish()
        self.assertEqual(files.files, environment.files.files)
        self.assertEqual(other.stdout.getvalue(), environment.stdout.getvalue())
        self.assertEqual(other.commands, environment.commands)

    def test_reordered_mutated_missing_and_incomplete_native_observations_are_rejected(self):
        _, _, port = self.compare()
        original = encoded(port.observations)
        def response_edit(rows):
            rows[0]['request']['input_sha256'] = '0' * 64
        def cleanup_edit(rows):
            rows[0]['cleanup_absence_check'] = 'unproven'
        def exit_edit(rows):
            rows[0]['returncode'] = True
        def error_edit(rows):
            rows[0]['error_type'] = 'TimeoutError'
        for change in (lambda r: r.reverse(), lambda r: r.clear(), response_edit,
                       cleanup_edit, exit_edit, error_edit):
            rows = deepcopy(original)
            change(rows)
            replay = ReplayOPA(rows, available=True, tool_sha256=port.tool_sha256)
            files = ValidationFiles(self.data, self.original.contract['membership'], label=str(self.original.root))
            with self.subTest(change=change.__name__), self.assertRaises(ValueError):
                replay.run(['opa', 'eval', '--format=json', '--data', str(files.root / original[0]['request']['policy']),
                    '--input', str(files.root / original[0]['request']['input']), original[0]['request']['query']], files)

    def test_query_and_current_product_policy_are_explicit_native_boundaries(self):
        self.original.write_data(self.data)
        files = ValidationFiles(self.data, label=str(self.original.root))
        command = ['opa', 'eval', '--data', str(files.root / 'policies/opa/architecture_readiness.rego'),
            '--input', str(files.root / 'policies/example-input.architecture-release-candidate.json'),
            'data.architecture.readiness.deny']
        self.assertEqual(request(command, files)['query'], command[-1])
        for changed in ([*command[:-1], 'data.unrelated'], ['sh', *command[1:]],
                        [*command[:2], '--bundle', *command[3:]], [*command, '--extra']):
            with self.subTest(command=changed), self.assertRaises(ValueError):
                request(changed, files)
        port = ValidationOPA(OPA, product_root=self.original.root)
        files.files['policies/opa/architecture_readiness.rego'] += b'\n# caller substitution\n'
        with self.assertRaisesRegex(ValueError, 'not_current_product_code'):
            port.run(command, files)
        self.assertEqual(port.observations, [])

    def test_real_native_output_budget_and_timeout_preserve_incomplete_observations(self):
        self.original.write_data(self.data)
        files = ValidationFiles(self.data, label=str(self.original.root))
        command = ['opa', 'eval', '--data', str(files.root / 'policies/opa/architecture_readiness.rego'),
            '--input', str(files.root / 'policies/example-input.architecture-release-candidate.json'),
            'data.architecture.readiness.deny']
        port = ValidationOPA(OPA, product_root=self.original.root)
        with patch.object(validation_tools, 'MAX_STREAM', 1), self.assertRaisesRegex(ValueError, 'output_budget'):
            port.run(command, files)
        self.assertTrue(port.observations[0]['process_started'])
        self.assertEqual(port.observations[0]['error_type'], 'ValueError')
        self.assertTrue(port.observations[0]['output_truncated'])
        self.assertLessEqual(len(port.observations[0]['stdout']), 1)
        port = ValidationOPA(OPA, product_root=self.original.root, timeout=0.0000001)
        with self.assertRaises(TimeoutError):
            port.run(command, files)
        self.assertEqual(port.observations[0]['error_type'], 'TimeoutError')

    def test_unhandled_original_yaml_failure_is_explicit_incomplete_not_a_fabricated_traceback(self):
        self.data['architecture/quality-markers.yaml'] = b'markers: [unclosed'
        self.original.write_data(self.data)
        files = ValidationFiles(self.data, self.original.contract['membership'], label=str(self.original.root))
        port = ValidationOPA(OPA, product_root=self.original.root)
        outcome, _ = execute(files, port)
        old_code, _, old_stderr, _ = self.original.run(opa=OPA)
        self.assertEqual(old_code, 1)
        self.assertIn(b'ParserError:', old_stderr)
        self.assertEqual((outcome['execution'], outcome['exit_code'], outcome['exception_type']),
                         ('incomplete', 2, 'ParserError'))
        self.assertEqual(port.observations, [])

    def test_unapproved_or_changed_native_binary_is_rejected_before_execution(self):
        fake = self.original.root / 'fake-opa'
        fake.write_bytes(b'unapproved fixture, never executable')
        with self.assertRaisesRegex(ValueError, 'checksum_mismatch'):
            ValidationOPA(fake, product_root=self.original.root)
        self.original.write_data(self.data)
        files = ValidationFiles(self.data, label=str(self.original.root))
        port = ValidationOPA(OPA, product_root=self.original.root)
        port.tool_sha256 = '0' * 64
        with self.assertRaisesRegex(ValueError, 'tool_changed'):
            port.run(['opa', 'eval', '--data', str(files.root / 'policies/opa/architecture_readiness.rego'),
                '--input', str(files.root / 'policies/example-input.architecture-release-candidate.json'),
                'data.architecture.readiness.deny'], files)
        self.assertEqual(port.observations, [])


class RetainedRuntimeValidation(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        product = self.base / 'product'
        product.mkdir(mode=0o700)
        self.original = oracle.Original(DIRECTORY, product)
        self.original.write_data(self.original.contract['data'])
        environment = {'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_AUTHOR_NAME': 'Synthetic fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Synthetic fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
        import os
        for args in (('init', '-q'), ('add', '.'), ('commit', '-qm', 'Trusted immutable V1 fixture')):
            subprocess.run(['git', '-C', str(product), *args], env={**os.environ, **environment}, check=True,
                           capture_output=True)
        instance = self.base / 'instance'
        instance.mkdir(mode=0o700)
        (instance / 'state').mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-validation-node', 'opa': str(OPA)}
        self.context = ValidationContext(instance, self.settings, product_root=product)

    def test_complete_private_run_uses_committed_data_and_replays_without_native_execution(self):
        # Deliberately dirty inspected data cannot reinterpret committed input.
        (self.original.root / 'architecture/arch-l1.yaml').write_text('invalid dirty data')
        operation, value = self.context.create('2026-11-18T10:00:00Z')
        self.assertEqual(value['exit_code'], 0)
        self.assertFalse(value['source_worktree_clean'])
        self.assertFalse(value['working_tree_used'])
        with patch('lib.validation_application.ValidationOPA', side_effect=AssertionError('replay invoked OPA')):
            self.assertEqual(self.context.inspect(operation), value)
        self.assertEqual(self.context.status()[0]['state'], 'retained_declared_replay_consistent')
        self.assertFalse(value['authority_transferred'])
        self.assertFalse(value['independent_execution_attested'])

    def test_changed_inputs_generated_bytes_node_and_authority_fail_closed(self):
        operation, value = self.context.create('2026-11-18T10:00:00Z')
        target = self.context.operations / operation
        for relative in ('inputs/architecture/arch-l1.yaml', 'outputs/generated/csv/architecture_runtime_traceability.csv'):
            path = target / relative
            raw = path.read_bytes()
            path.write_bytes(raw + b'\nchanged')
            with self.subTest(path=relative), self.assertRaises(ValueError):
                self.context.inspect(operation)
            path.write_bytes(raw)
        path = target / 'assessment.json'
        raw = path.read_bytes()
        for field, changed in (('node_id', 'foreign-node'), ('published', True), ('official_acceptance', True)):
            data = json.loads(raw)
            data[field] = changed
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.context.inspect(operation)
        path.write_bytes(raw)
        self.assertEqual(self.context.inspect(operation), value)

    def test_pending_operation_never_resumes_or_invokes_native_tool(self):
        with patch('lib.validation_application.ValidationOPA', side_effect=ValueError('synthetic_initialization_failure')):
            with self.assertRaisesRegex(ValueError, 'initialization_failure'):
                self.context.create('2026-11-18T10:00:00Z')
        operation = next(self.context.operations.iterdir()).name
        with patch('lib.validation_application.ValidationOPA', side_effect=AssertionError('pending resumed')):
            with self.assertRaisesRegex(ValueError, 'pending_requires_review'):
                self.context.inspect(operation)
        self.assertEqual(self.context.status()[0]['state'], 'pending_incomplete_or_invalid')

    def test_closed_metadata_strict_scalars_and_approved_native_identity(self):
        operation, _ = self.context.create('2026-11-18T10:00:00Z')
        target = self.context.operations / operation
        report = target / 'assessment.json'
        pending = target / 'pending.json'
        before, before_pending = report.read_bytes(), pending.read_bytes()
        for case in ('boolean_exit', 'unapproved_tool', 'unknown_metadata', 'boolean_generator', 'boolean_request'):
            value = json.loads(before)
            if case == 'boolean_exit':
                value['exit_code'] = False
            elif case == 'unapproved_tool':
                value['opa_sha256'] = '0' * 64
                for row in value['native_observations']:
                    row['tool_sha256'] = '0' * 64
            elif case == 'unknown_metadata':
                value['unexpected_field'] = 'synthetic metadata'
                intent = json.loads(before_pending)
                intent['unexpected_field'] = 'synthetic metadata'
                pending.write_text(json.dumps(intent))
            elif case == 'boolean_generator':
                value['generator_commands'][0]['process_started'] = 0
            else:
                value['native_observations'][0]['request']['format_json'] = 1
            report.write_text(json.dumps(value))
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.context.inspect(operation)
            report.write_bytes(before)
            pending.write_bytes(before_pending)
        self.assertEqual(self.context.inspect(operation)['exit_code'], 0)


class InertValidationFiles(unittest.TestCase):
    def test_newlines_globs_membership_only_and_read_only_paths(self):
        value = ValidationFiles({'data/a.yaml': b'a\r\nb\rc\n', 'data/nested/b.yaml': b''},
            ['data/a.yaml', 'data/nested/b.yaml', 'scripts/original.py'])
        self.assertEqual((value.root / 'data/a.yaml').read_text(), 'a\nb\nc\n')
        self.assertEqual([p.name for p in (value.root / 'data').glob('*.yaml')], ['a.yaml'])
        self.assertEqual([p.name for p in (value.root / 'data').rglob('*.yaml')], ['a.yaml', 'b.yaml'])
        self.assertTrue((value.root / 'scripts/original.py').exists())
        with self.assertRaises(PermissionError):
            (value.root / 'scripts/original.py').read_bytes()
        with self.assertRaises(ValueError):
            (value.root / 'data/a.yaml').open('w')

    def test_paths_cannot_escape_or_alias_the_snapshot(self):
        for name in ('/absolute', '../escape', 'a/../b', 'a//b', 'a\\b', 'a:b', 'a\nb'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ValidationFiles({name: b''})


class RuntimeFingerprintClosure(unittest.TestCase):
    def test_each_installed_validation_module_byte_change_invalidates_runtime_binding(self):
        root = portable_runtime.ROOT
        registered = json.loads((root / 'config/axiom-v2-distribution.json').read_text())['python_files']
        expected = {name for name in registered if '/validation_' in name
                    or '/compliance_' in name or name.endswith('/runtime_validation.py')}
        expected.add('config/axiom-v2-validation-capabilities.json')
        with patch.object(portable_runtime, 'file_digest', wraps=portable_runtime.file_digest) as measured:
            baseline = portable_runtime.source_digest()
        paths = {call.args[0].relative_to(root).as_posix() for call in measured.call_args_list}
        self.assertTrue(expected <= paths, sorted(expected - paths))
        self.assertGreaterEqual(len(expected), 10)
        with tempfile.TemporaryDirectory() as temporary:
            retained = Path(temporary).resolve()
            for name in paths:
                path = retained / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / name, path)
            with patch.object(portable_runtime, 'ROOT', retained):
                self.assertEqual(portable_runtime.source_digest(), baseline)
                for name in sorted(expected):
                    path = retained / name
                    raw = path.read_bytes()
                    path.write_bytes(raw + b'\n# Synthetic isolated runtime-byte mutation\n')
                    with self.subTest(module=name):
                        self.assertNotEqual(portable_runtime.source_digest(), baseline)
                    path.write_bytes(raw)
                self.assertEqual(portable_runtime.source_digest(), baseline)


if __name__ == '__main__':
    unittest.main()
