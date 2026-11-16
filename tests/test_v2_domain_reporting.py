"""Original V1 domain output bytes, pinned release policy and guarded private joins."""
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import combined_reporting, domain_reporting
from lib.full_evaluation import evaluate, persist, validate
from lib.portable.contracts import canonical_digest
from lib.portable.runtime import source_digest, file_digest
from lib.v2_application import initialize, revision, run
from test_portable_runtime import OPA

AT = '2026-11-15T12:00:00Z'
SOURCE = revision()
FIXTURE = ROOT / 'tests/fixtures/axiom-v1-parity/domain-reporting-cases.json'


class DomainReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text())
        assert cls.fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
        cls.values = {}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.json'
            for case in cls.fixture['cases']:
                for domain, payload in case['inputs'].items():
                    path.write_text(json.dumps(payload, indent=2) + '\n')
                    cls.values[case['id'], domain] = evaluate(domain, path, opa=OPA, at=AT, source_revision=SOURCE)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'instance'; self.root.mkdir(mode=0o700)
        (self.root / 'state').mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-domain-node', 'source_revision': SOURCE,
                         'runtime_source_digest': source_digest(), 'opa_sha256': file_digest(OPA)}
        self.context = domain_reporting.DomainReports(self.root, self.settings)

    def store(self, label='red', domain='devsecops-release', **changes):
        value = deepcopy(self.values[label, domain]); value.update(changes)
        return persist(value, self.root)['assessment_id']

    def test_all_original_domain_and_combined_files_match_actual_v1_cli_bytes(self):
        for case in self.fixture['cases']:
            ids = {}
            for domain in ['architecture', 'devsecops-release']:
                input_id = ids[domain] = self.store(case['id'], domain)
                report_id, value = self.context.create('domain', {'assessment': input_id}, AT)
                self.assertEqual(self.context.inspect(report_id), value)
                for name, expected in case['outputs'][domain].items():
                    self.assertEqual((self.context.artifacts / report_id / name).read_bytes(), expected.encode())
                self.assertFalse(value['official_acceptance']); self.assertFalse(value['provider_invoked'])
                self.assertEqual(value['evidence_trust'], 'unverified')
            report_id, value = self.context.create('combined', {'architecture': ids['architecture'],
                'devsecops': ids['devsecops-release']}, AT,
                {'architecture': domain_reporting.DEFAULT_ARCHITECTURE_REF, 'devsecops': domain_reporting.DEFAULT_DEVSECOPS_REF})
            self.assertEqual(self.context.inspect(report_id), value)
            for name, expected in case['outputs']['combined'].items():
                self.assertEqual((self.context.artifacts / report_id / name).read_bytes(), expected.encode())
            self.assertEqual(self.context.create('combined', value['inputs'], AT, value['references'])[0], report_id)

    def test_release_gate_status_and_count_are_bound_to_complete_findings(self):
        for case in self.fixture['cases']:
            value = self.values[case['id'], 'devsecops-release']
            expected = json.loads(case['outputs']['devsecops-release']['devsecops-release.json'])
            self.assertEqual(value['report'], expected)
            self.assertEqual(value['execution'], 'complete')
            self.assertEqual(value['mode'], 'report-only')
            self.assertEqual(case['exits']['fail_on_findings'], int(bool(expected['gate']['findings'])))
        value = deepcopy(self.values['red', 'devsecops-release']); value['report']['gate']['status'] = 'pass'
        with self.assertRaisesRegex(ValueError, 'gate_status_mismatch'): validate(value)
        value['report']['gate']['status'] = 'findings'; value['report']['summary']['finding_count'] = 0
        with self.assertRaisesRegex(ValueError, 'summary_mismatch'): validate(value)

    def test_input_identity_change_is_detected_before_rendering(self):
        input_id = self.store(); path = self.root / 'state/assessments' / (input_id + '.json')
        value = json.loads(path.read_text()); value['report']['gate']['findings'] = []
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'input_changed'):
            self.context.create('domain', {'assessment': input_id}, AT)

    def test_product_time_tool_and_execution_mismatch_are_rejected(self):
        for change in [{'source_revision': '0' * 40}, {'assessed_at': '2026-11-14T12:00:00Z'},
                       {'opa_sha256': '0' * 64}, {'execution': 'incomplete'}]:
            with self.subTest(change=change):
                input_id = self.store(**change)
                with self.assertRaisesRegex(ValueError, 'input_context_mismatch'):
                    self.context.create('domain', {'assessment': input_id}, AT)

    def test_combination_rejects_wrong_domain_and_missing_identity(self):
        architecture = self.store(domain='architecture'); release = self.store()
        with self.assertRaisesRegex(ValueError, 'input_context_mismatch'):
            self.context.create('combined', {'architecture': release, 'devsecops': architecture}, AT,
                {'architecture': 'a.md', 'devsecops': 'd.md'})
        value = deepcopy(self.values['red', 'devsecops-release']); value['report']['target'] = {}
        value['report_json'] = json.dumps(value['report'], indent=2) + '\n'
        missing = persist(value, self.root)['assessment_id']
        with self.assertRaisesRegex(ValueError, 'explicit_combined_target_required'):
            self.context.create('combined', {'architecture': architecture, 'devsecops': missing}, AT,
                {'architecture': 'a.md', 'devsecops': 'd.md'})

    def test_all_three_target_fields_must_match(self):
        architecture = self.values['red', 'architecture']['report']
        for key in ['path', 'commit', 'release_id']:
            value = deepcopy(self.values['red', 'devsecops-release']['report']); value['target'][key] += '-other'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'combined_target_mismatch'):
                combined_reporting.build(architecture, value)
        with self.assertRaisesRegex(ValueError, 'explicit_combined_target_required'):
            combined_reporting.build({}, {})

    def test_explicit_target_alone_cannot_make_incomplete_reports_pass(self):
        architecture = deepcopy(self.values['red', 'architecture']['report'])
        release = deepcopy(self.values['red', 'devsecops-release']['report'])
        architecture['gates'] = []
        with self.assertRaisesRegex(ValueError, 'complete_combined_architecture_gates_required'):
            combined_reporting.build(architecture, release)
        architecture = deepcopy(self.values['red', 'architecture']['report']); release['gate']['findings'] = 'not-an-array'
        with self.assertRaisesRegex(ValueError, 'invalid_combined_gate_findings_or_status'):
            combined_reporting.build(architecture, release)

    def test_invalid_request_identity_and_reference_fail_before_interpreting_paths(self):
        for inputs in [{'assessment': '../escape'}, {'assessment': self.store(), 'extra': '0' * 64}]:
            with self.assertRaisesRegex(ValueError, 'invalid_domain_report_contract'):
                self.context.create('domain', inputs, AT)
        for label in ['', 'a\n.md', 'x' * 2049]:
            with self.assertRaisesRegex(ValueError, 'invalid_domain_report_reference'):
                domain_reporting.reference(label)

    def test_immutable_output_record_and_membership_tampering_are_detected(self):
        input_id = self.store(); report_id, value = self.context.create('domain', {'assessment': input_id}, AT)
        directory = self.context.artifacts / report_id; path = directory / 'devsecops-release.md'; raw = path.read_bytes()
        path.write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError, 'output_changed'): self.context.inspect(report_id)
        path.write_bytes(raw); extra = directory / 'extra'; extra.write_bytes(b'new')
        with self.assertRaisesRegex(ValueError, 'membership_changed'): self.context.inspect(report_id)
        extra.unlink(); record = self.context.assessments / (report_id + '.json')
        v = deepcopy(value); v['official_acceptance'] = True; record.write_text(json.dumps(v))
        with self.assertRaisesRegex(ValueError, 'record_changed'): self.context.inspect(report_id)

    def test_symlink_sources_and_outputs_are_rejected(self):
        input_id = self.store(); path = self.root / 'state/assessments' / (input_id + '.json')
        raw = path.read_bytes(); copy = self.root / 'copy.json'; copy.write_bytes(raw); path.unlink(); path.symlink_to(copy)
        with self.assertRaises(ValueError): self.context.create('domain', {'assessment': input_id}, AT)
        path.unlink(); path.write_bytes(raw)
        report_id, _ = self.context.create('domain', {'assessment': input_id}, AT)
        directory = self.context.artifacts / report_id; output = directory / 'devsecops-release.json'
        output.unlink(); output.symlink_to(copy)
        with self.assertRaisesRegex(ValueError, 'unsafe_domain_report_artifacts'): self.context.inspect(report_id)

    def test_cli_report_only_and_explicit_finding_exit_preserve_v1_exit_codes(self):
        instance = self.root / 'cli'; initialize(instance, opa=OPA, development=True)
        for case in self.fixture['cases']:
            path = self.root / (case['id'] + '.json'); path.write_text(json.dumps(case['inputs']['devsecops-release']))
            for flag in [False, True]:
                output = io.StringIO()
                with redirect_stdout(output):
                    code = run('evaluate', ['--domain', 'devsecops-release', '--input', str(path), '--at', AT,
                                          *(['--fail-on-findings'] if flag else [])], instance_path=instance)
                self.assertEqual(code, case['exits']['fail_on_findings' if flag else 'default'])
                input_id = json.loads(output.getvalue())['assessment_id']
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(run('reports', ['domain', '--id', input_id, '--at', AT], instance_path=instance), 0)
            report_id = json.loads(output.getvalue())['report_id']
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(run('reports', ['inspect-domain', '--id', report_id], instance_path=instance), 0)
            result = json.loads(output.getvalue())
            self.assertTrue(result['input_records_and_complete_outputs_reverified'])
            self.assertFalse(result['original_input_bytes_reverified'])
            self.assertFalse(result['native_metadata_rechecked'])

    def test_original_wire_cannot_disagree_with_the_parsed_report(self):
        value = deepcopy(self.values['red', 'devsecops-release']); value['report_json'] = '{}'
        with self.assertRaisesRegex(ValueError, 'report_wire_mismatch'): validate(value)

    def test_empty_or_mistyped_release_input_is_not_a_false_pass(self):
        for value in [{}, {'release_candidate': 'true'}, {'release_candidate': True},
                      {**self.fixture['cases'][0]['inputs']['devsecops-release'], 'dependencies': [False]}]:
            path = self.root / 'invalid.json'; path.write_text(json.dumps(value))
            with self.assertRaises(ValueError): evaluate('devsecops-release', path, opa=OPA, at=AT, source_revision=SOURCE)


if __name__ == '__main__': unittest.main()
