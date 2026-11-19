"""Actual complete pinned OPA execution against frozen original green/red inputs."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from control_evaluation import POLICY_QUERIES
from lib.functional_parity import git_read
from lib.providers.compliance_opa import ComplianceOPA


class CompleteComplianceOPA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = shutil.which('opa')
        if cls.tool is None:
            raise AssertionError('The pinned validation OPA must be available')
        cls.revision = git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()
        fixtures = ROOT / 'tests/fixtures/axiom-v1-parity'
        manifest = json.loads((fixtures / 'manifest.json').read_bytes())
        cls.fixtures = {}
        for key in ('green', 'red'):
            row = next(r for r in manifest['cases'] if r['id'] == 'controls-' + key)
            raw, report = (ROOT / row['input']).read_bytes(), (fixtures / row['report']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['input_sha256'] or hashlib.sha256(report).hexdigest() != row['report_sha256']:
                raise AssertionError('Pinned full original comparison changed')
            cls.fixtures[key] = raw, json.loads(report)['policy_results']

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.events = []
        self.label = self.root / 'operator-supplied-input.json'
        self.product = self.root / 'own-product-label'

    def create(self, key='green', **options):
        values = dict(tool=self.tool, source_revision=self.revision, display_root=self.product,
            input_label=self.label, input_bytes=self.fixtures[key][0], workarea=self.root / 'opa',
            on_event=lambda row: self.events.append(deepcopy(row)))
        values.update(options)
        return ComplianceOPA(**values)

    def query(self, query):
        return ['opa', 'eval', '-f', 'json', '-d', str(self.product / 'policies/opa'),
                '-i', str(self.label), query]

    def test_actual_all_policy_check_and_every_query_match_complete_original_denies(self):
        for key in ('green', 'red'):
            with self.subTest(key=key):
                opa = self.create(key, workarea=self.root / key)
                checked = opa.run(['opa', 'check', str(self.product / 'policies/opa')])
                self.assertEqual(checked.returncode, 0)
                for identifier, query in POLICY_QUERIES.items():
                    result = opa.run(self.query(query))
                    self.assertEqual(result.returncode, 0)
                    findings = json.loads(result.stdout)['result'][0]['expressions'][0]['value']
                    self.assertEqual(findings, self.fixtures[key][1][identifier]['deny_messages'])
                self.assertEqual(len(opa.observations), 12)  # version/check/ten full queries
                self.assertTrue(all(row['native_outcome']['exit_code'] == 0 for row in opa.observations))
                for row in opa.observations:
                    area = opa.root / ('native-' + str(row['sequence']))
                    for stream in row['native_outcome']['streams'].values():
                        raw = (area / stream['path']).read_bytes()
                        self.assertEqual(len(raw), stream['bytes'])
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), stream['sha256'])

    def test_retained_input_does_not_depend_on_the_caller_path_after_capture(self):
        self.label.write_bytes(self.fixtures['green'][0])
        opa = self.create(input_bytes=self.label.read_bytes())
        self.label.write_bytes(self.fixtures['red'][0]); self.label.unlink()
        result = opa.run(self.query(POLICY_QUERIES['branch_protection']))
        self.assertEqual(json.loads(result.stdout)['result'][0]['expressions'][0]['value'], [])

    def test_unlisted_query_policy_or_input_cannot_start_a_native_command(self):
        opa = self.create()
        commands = [self.query('data.operator_selected.deny'),
            ['opa', 'check', '/caller-selected/policies'], self.query(POLICY_QUERIES['sbom'])]
        commands[-1][-2] = '/another/operator-input.json'
        with patch('lib.providers.compliance_opa.supervise') as execute:
            for command in commands:
                with self.subTest(command=command), self.assertRaisesRegex(ValueError, 'unsupported_complete_compliance'):
                    opa.run(command)
        execute.assert_not_called()
        self.assertEqual(len(opa.observations), 1)

    def test_frozen_policy_mutation_or_unknown_symlink_rejects_before_execution(self):
        opa = self.create()
        name = next(n for n in opa.files if n.endswith('.rego'))
        path = opa.frozen / name; raw = path.read_bytes(); path.write_bytes(b'package unexpected\n')
        with patch('lib.providers.compliance_opa.supervise') as execute:
            with self.assertRaisesRegex(ValueError, 'frozen_bytes_changed'):
                opa.run(self.query(POLICY_QUERIES['sbom']))
        execute.assert_not_called()
        path.write_bytes(raw)
        (opa.frozen / 'unknown-directory').symlink_to(self.root, target_is_directory=True)
        with patch('lib.providers.compliance_opa.supervise') as execute:
            with self.assertRaisesRegex(ValueError, 'frozen_symlink'):
                opa.run(self.query(POLICY_QUERIES['sbom']))
        execute.assert_not_called()

    def test_wrong_product_or_unapproved_tool_is_rejected_before_area_creation(self):
        for options in ({'source_revision': '0'*40}, {'tool': '/usr/bin/true'}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.create(**options)
            self.assertFalse((self.root / 'opa').exists())

    def test_native_observations_are_preceded_by_intent_and_followed_by_whole_outcome(self):
        opa = self.create()
        opa.run(self.query(POLICY_QUERIES['sbom']))
        self.assertEqual([r['phase'] for r in self.events], ['intent', 'finished', 'intent', 'finished'])
        self.assertNotIn('native_outcome', self.events[-2]['observation'])
        self.assertEqual(self.events[-1]['observation']['native_outcome']['exit_code'], 0)
        self.assertEqual(opa.observations[1]['declared_command'], self.query(POLICY_QUERIES['sbom']))

    def test_observed_missing_input_preserves_whole_check_then_every_native_query_failure(self):
        opa = self.create(input_bytes=None)
        checked = opa.run(['opa', 'check', str(self.product / 'policies/opa')])
        self.assertEqual(checked.returncode, 0)
        for query in POLICY_QUERIES.values():
            result = opa.run(self.query(query))
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr or result.stdout)
        self.assertEqual(len(opa.observations), 12)
        self.assertTrue(all(row['input_sha256'] is None and not row['input_present'] for row in opa.observations))
