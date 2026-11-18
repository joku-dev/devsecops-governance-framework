"""Whole original generator mains, nested effects and explicit clock inputs.

The test harness alone executes frozen V1 reference functions. Its nested
Python calls are controlled dispatches to those hash-bound functions, not
execution of source programs supplied by a caller. Crypto is explicitly a
synthetic observation here; actual native verification is a separate test.
"""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import io
import json
import shutil
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_report_operations import RepositoryReportOperations, SOURCE_GENERATORS
from lib.provider_ports import configuration_source_profile
from lib import evidence_attestation

FIXTURES = ROOT / 'tests/fixtures/v2-repository-validation'
CONTRACT = json.loads((FIXTURES / 'contract.json').read_bytes())['generators']
FIXED = datetime(2026, 11, 15, 12, 0, 0, 123456, tzinfo=timezone.utc)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED.astimezone(tz) if tz is not None else FIXED.replace(tzinfo=None)


class OriginalGeneratorEffectsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        shutil.copytree(ROOT, self.root,
            ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv*', '.DS_Store'))
        self.original = {}
        self.calls = []
        self.dynamic_clock = False
        self.clock_values = []
        for program, metadata in CONTRACT.items():
            raw = (FIXTURES / (Path(program).name + '.txt')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata['sha256'])
            module = ModuleType('controlled_original_' + Path(program).stem)
            module.__file__ = str(self.root / program)
            exec(compile(raw, str(FIXTURES / (Path(program).name + '.txt')), 'exec'), module.__dict__)
            if hasattr(module, 'datetime'):
                module.datetime = FixedDatetime
            module.subprocess = SimpleNamespace(run=self.original_subprocess)
            self.original[program] = module
        self.crypto = patch.object(evidence_attestation, '_verify_ed25519',
            return_value=(True, 'Ed25519 signature is valid.'))
        self.crypto.start()
        self.addCleanup(self.crypto.stop)

    def original_subprocess(self, command, **options):
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(options, {'cwd': self.root, 'capture_output': True, 'text': True, 'check': False})
        name = Path(command[1]).relative_to(self.root).as_posix()
        return SimpleNamespace(**self.old(name, command[2:]))

    def old(self, program, arguments=()):
        self.calls.append((program, tuple(arguments)))
        for value in vars(self.original[program]).values():
            if callable(getattr(value, 'cache_clear', None)):
                value.cache_clear()
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', [str(self.root / program), *map(str, arguments)]), redirect_stdout(output), redirect_stderr(errors):
            result = self.original[program].main()
        return {'returncode': result, 'stdout': output.getvalue(), 'stderr': errors.getvalue()}

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def restore(self, before):
        after = self.snapshot()
        for name in after.keys() - before.keys():
            (self.root / name).unlink()
        for name, raw in before.items():
            if after.get(name) != raw:
                (self.root / name).parent.mkdir(parents=True, exist_ok=True)
                (self.root / name).write_bytes(raw)

    @contextmanager
    def effects(self):
        rows = []
        write_text, write_bytes, mkdir = Path.write_text, Path.write_bytes, Path.mkdir
        root = self.root
        def name(path):
            return path.relative_to(root).as_posix()
        def text(path, raw, encoding=None, errors=None, newline=None):
            rows.append(('write', name(path), raw.encode(encoding or 'utf-8', errors or 'strict')))
            return write_text(path, raw, encoding=encoding, errors=errors, newline=newline)
        def binary(path, raw):
            rows.append(('write', name(path), bytes(raw)))
            return write_bytes(path, raw)
        def directory(path, mode=0o777, parents=False, exist_ok=False):
            rows.append(('mkdir', name(path), parents, exist_ok))
            return mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        with patch.object(Path, 'write_text', text), patch.object(Path, 'write_bytes', binary), patch.object(Path, 'mkdir', directory):
            yield rows

    def operations(self):
        membership = {name: {'mode': '100644'} for name in self.snapshot()}
        def mkdir(name):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        def write(name, raw):
            (self.root / name).write_bytes(raw)
            membership[name] = {'mode': '100644'}
        def invoke(program, arguments=()):
            self.calls.append((program, tuple(arguments)))
            return operation.run(program, arguments)
        operation = RepositoryReportOperations(self.root, membership, mkdir=mkdir, write=write,
            clock=self.clock,
            source_configuration_profile=configuration_source_profile('github-actions'),
            verify_attestation=lambda key, statement, signature: (True, 'Ed25519 signature is valid.'),
            invoke=invoke)
        return operation, invoke

    def clock(self):
        value = FIXED + timedelta(seconds=len(self.clock_values), microseconds=713 * len(self.clock_values)) if self.dynamic_clock else FIXED
        text = value.isoformat().replace('+00:00', 'Z')
        if self.dynamic_clock:
            self.clock_values.append(text)
        return text

    def assert_files(self, actual, expected):
        self.assertEqual(set(actual), set(expected))
        for name in expected:
            self.assertTrue(actual[name] == expected[name],
                'Whole original file bytes differ: ' + name + ' old=' + hashlib.sha256(expected[name]).hexdigest()
                + ' new=' + hashlib.sha256(actual[name]).hexdigest())

    def arguments(self, program):
        if program != 'scripts/verify_evidence_attestation.py':
            return ()
        return (str(self.root / 'docs/examples/evidence-attestation.example.json'), '--output',
                str(self.root / 'generated/reports/evidence-attestation-pilot.json'), '--evaluated-at',
                '2026-07-17T10:01:00Z')

    def compare(self, programs):
        before = self.snapshot()
        self.calls = []
        self.clock_values = []
        with self.effects() as expected_effects:
            expected = [self.old(name, self.arguments(name)) for name in programs]
        expected_files = self.snapshot()
        expected_calls = self.calls[:]
        expected_clocks = self.clock_values[:]
        self.restore(before)
        self.calls = []
        self.clock_values = []
        _, invoke = self.operations()
        with self.effects() as actual_effects:
            actual = [invoke(name, self.arguments(name)) for name in programs]
        self.assertEqual(actual, expected)
        self.assertEqual(self.calls, expected_calls)
        self.assertEqual(actual_effects, expected_effects)
        self.assert_files(self.snapshot(), expected_files)
        if self.dynamic_clock:
            self.assertEqual(self.clock_values, expected_clocks)
        return actual

    def compare_exception(self, program):
        def outcome(function, *args):
            try:
                return {'returned': function(*args)}
            except Exception as error:
                return {'error_type': type(error).__name__, 'message': str(error)}
        before = self.snapshot()
        self.calls = []
        with self.effects() as expected_effects:
            expected = outcome(self.old, program, self.arguments(program))
        expected_files = self.snapshot()
        expected_calls = self.calls[:]
        self.restore(before)
        self.calls = []
        _, invoke = self.operations()
        with self.effects() as actual_effects:
            actual = outcome(invoke, program, self.arguments(program))
        self.assertEqual(actual, expected)
        self.assertIn('error_type', expected)
        self.assertEqual(self.calls, expected_calls)
        self.assertEqual(actual_effects, expected_effects)
        self.assert_files(self.snapshot(), expected_files)

    def test_all_13_original_generator_mains_outputs_nested_calls_and_files(self):
        self.assertEqual(len(CONTRACT), 13)
        for program in CONTRACT:
            with self.subTest(program=program):
                self.compare([program])

    def test_complete_ordered_generator_pipeline_preserves_every_original_effect(self):
        self.compare(['scripts/generate_governance_graph.py', 'scripts/generate_multi_consumer_readiness.py',
            'scripts/verify_evidence_attestation.py', 'scripts/generate_blocking_readiness.py',
            'scripts/generate_blocking_mode_alignment.py', 'scripts/generate_replay_triage_report.py',
            *SOURCE_GENERATORS])

    def test_intake_original_placeholders_and_missing_generated_outputs_are_preserved(self):
        for stem in ('source-document-intake-status', 'source-document-intake-review-briefs', 'source-document-requirement-delta'):
            for suffix in ('.json', '.md'):
                (self.root / ('generated/reports/' + stem + suffix)).unlink()
        self.compare(['scripts/generate_source_document_intake_review_briefs.py'])

    def test_nested_generators_keep_each_separately_observed_original_clock(self):
        self.dynamic_clock = True
        owner = self
        class ObservedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime.fromisoformat(owner.clock().replace('Z', '+00:00'))
                return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
        for module in self.original.values():
            if hasattr(module, 'datetime'):
                module.datetime = ObservedDatetime
        self.compare(['scripts/generate_source_document_intake_review_briefs.py',
                      'scripts/generate_source_document_requirement_delta.py',
                      'scripts/generate_source_document_process_status.py',
                      'scripts/generate_blocking_mode_alignment.py'])
        self.assertGreater(len(self.clock_values), 4)

    def test_nonzero_nested_original_keeps_partial_outputs_and_exact_caught_error(self):
        report = json.loads((self.root / 'generated/reports/source-lineage-report.json').read_bytes())
        # Select an explicitly required path. A removed policy selected only
        # by glob() intentionally disappears from V1's inventory instead.
        name = next(artifact['artifact_path'] for row in report['lineage'] for artifact in row['derived_artifacts']
                    if artifact['artifact_type'] == 'release_package' and (self.root / artifact['artifact_path']).is_file())
        (self.root / name).unlink()
        results = self.compare(['scripts/generate_source_lineage_report.py', 'scripts/generate_governance_change_impact_report.py'])
        self.assertEqual([row['returncode'] for row in results], [1, 1])
        self.assertIn('source lineage generation failed:', results[1]['stderr'])

    def test_uncaught_markdown_failure_preserves_the_already_written_json(self):
        from lib import report_lineage
        program = 'scripts/generate_source_lineage_report.py'
        with patch.object(self.original[program], 'render_markdown', side_effect=ValueError('controlled rendering failure')), \
                patch.object(report_lineage, 'render_markdown', side_effect=ValueError('controlled rendering failure')):
            self.compare_exception(program)

    def test_missing_mandatory_json_keeps_original_exception_and_no_new_file(self):
        (self.root / 'generated/reports/portfolio-onboarding-status.json').unlink()
        self.compare_exception('scripts/generate_multi_consumer_readiness.py')

    def test_empty_mandatory_yaml_keeps_original_exception(self):
        (self.root / 'status/application-repository-integrations.yaml').write_text('')
        self.compare_exception('scripts/generate_blocking_readiness.py')

    def test_duplicate_json_members_retain_the_original_parser_decision(self):
        path = self.root / 'status/repository-results-index.json'
        raw = path.read_text()
        value = json.loads(raw)
        path.write_text(raw.rstrip()[:-1] + ',"generated_at":' + json.dumps(value['generated_at']) + '}\n')
        self.assertEqual(json.loads(path.read_text()), value)
        self.compare(['scripts/generate_governance_graph.py', 'scripts/generate_multi_consumer_readiness.py',
                      'scripts/generate_replay_triage_report.py'])


if __name__ == '__main__':
    unittest.main()
