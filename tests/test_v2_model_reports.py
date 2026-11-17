"""Original model report bytes, declared field bindings and empty-report repairs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_model_followup, report_outputs, report_sources
from lib.report_data import ReportData
from lib.functional_parity import git_read


class ModelReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/fixtures/axiom-v1-parity/model-followup-reporting-cases.json'
        cls.fixture = json.loads(path.read_text()); memberpath = path.with_name(cls.fixture['membership_fixture'])
        assert hashlib.sha256(memberpath.read_bytes()).hexdigest() == cls.fixture['membership_fixture_sha256']
        cls.membership_cases = json.loads(memberpath.read_text())['cases']
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.snapshot = Path(cls.temporary.name).resolve() / 'snapshot'
        cls.manifest = report_sources.capture(ROOT, git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), cls.snapshot)
        cls.data = cls.snapshot / 'data'

    def context(self, root=None): return ReportData(root or self.data, self.manifest['membership'])

    def test_all_six_original_output_files_match_both_bound_input_views(self):
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        for case in self.fixture['cases']:
            members = next(c['membership'] for c in self.membership_cases if c['data_revision'] == case['data_revision'])
            self.assertEqual(hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), case['membership_sha256'])
            for name, sha in case['source_files'].items():
                self.assertEqual(hashlib.sha256((self.data / name).read_bytes()).hexdigest(), sha)
            for kind, files in case['expected_outputs'].items():
                with self.subTest(revision=case['data_revision'], kind=kind):
                    self.assertEqual(report_outputs.build(self.data, kind, membership=members),
                                     {name: raw.encode() for name, raw in files.items()})

    def test_original_failures_and_explicit_input_projection_are_not_hidden(self):
        for case in self.fixture['cases']:
            self.assertEqual(case['original_failures'], {'layout_only': 'KeyError', 'unadapted_current_layout': 'ZeroDivisionError'})
            view = case['automation_declared_input_view']
            self.assertEqual(view['layout'], {'controls/': 'model/controls/'})
            self.assertEqual(len(view['projected_controls']), 41)
            self.assertTrue(all(row['control_id'] == row['source_entry_control'] for row in view['projected_controls']))

    def test_missing_fields_copy_only_the_exact_existing_placement_values(self):
        projected = {row['id']: row for row in report_model_followup.automation_controls(self.context())}
        bindings = self.fixture['cases'][-1]['automation_declared_input_view']['projected_controls']
        for binding in bindings:
            for field, source in binding['fields'].items():
                value = projected[binding['control_id']]
                for part in field.split('.'): value = value[part]
                self.assertEqual(value, source['value'])
        self.assertEqual(len(projected), 46)

    def test_provided_control_classification_and_source_bytes_are_preserved(self):
        before = {name: hashlib.sha256((self.data / name).read_bytes()).hexdigest() for name in self.manifest['files']}
        projected = {row['id']: row for row in report_model_followup.automation_controls(self.context())}
        original = yaml.safe_load((self.data / 'model/controls/dscb-gov.yaml').read_text())['requirements']
        for row in original:
            self.assertEqual(projected[row['id']]['automation'], row['automation'])
            self.assertEqual(projected[row['id']]['verification_requirement'], row['verification_requirement'])
        self.assertFalse((self.data / 'controls').exists())
        self.assertEqual(before, {name: hashlib.sha256((self.data / name).read_bytes()).hexdigest() for name in self.manifest['files']})

    def test_absent_ambiguous_level_and_missing_field_bindings_fail_without_defaults(self):
        for case in ['absent', 'duplicate', 'wrong-level', 'missing-field']:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / 'copy'; shutil.copytree(self.data, root)
                path = root / 'pipeline-baseline/control-placement.yaml'; value = yaml.safe_load(path.read_text())
                rows = value['control_placements']; row = next(r for r in rows if r['control'] == 'DSCB-L1-REQ-001')
                if case == 'absent': rows.remove(row)
                elif case == 'duplicate': rows.append(deepcopy(row))
                elif case == 'wrong-level': row['level'] = 'L3'
                else: row.pop('gate_type')
                path.write_text(yaml.safe_dump(value))
                with self.assertRaises(ValueError): report_model_followup.automation_controls(self.context(root))

    def test_duplicate_control_identity_and_wrong_mapping_type_are_rejected(self):
        for case in ['duplicate-control', 'not-mapping']:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / 'copy'; shutil.copytree(self.data, root)
                path = root / 'model/controls/dscb-l1.yaml'; value = yaml.safe_load(path.read_text())
                if case == 'duplicate-control': value['requirements'].append(deepcopy(value['requirements'][0]))
                else: value = []
                path.write_text(yaml.safe_dump(value))
                with self.assertRaises(ValueError): report_model_followup.automation_controls(self.context(root))

    def test_model_reports_require_explicit_committed_membership(self):
        with self.assertRaisesRegex(ValueError, 'explicit_report_membership_required'):
            report_outputs.build(self.data, 'automation')

    def test_csv_bytes_keep_the_original_crlf_and_column_order(self):
        for kind in ['document-controls', 'open-gaps']:
            files = report_outputs.build(self.data, kind, membership=self.manifest['membership'])
            raw = next(v for n, v in files.items() if n.endswith('.csv'))
            self.assertIn(b'\r\n', raw)
            self.assertNotIn(b'\r\r\n', raw)


class EmptyModelReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.control = {'id': 'DSCB-L1-REQ-099', 'domain': 'synthetic', 'title': 'Synthetic requirement',
            'verification': {'method': 'manual'}, 'policy_as_code': {'candidate': False}}
        values = {'model/controls/dscb-l1.yaml': {'level': 'L1', 'requirements': [self.control]},
            'model/documents/governance-documents.yaml': {'documents': [{'id': 'SYNTHETIC', 'type': 'standard',
                'title': 'Synthetic document', 'status': 'approved', 'repository_path': 'docs/synthetic.md'}]},
            'model/traceability/document-to-control.yaml': {'mappings': []},
            'model/platform/platform-capabilities.yaml': {'capabilities': []},
            'model/waivers/waiver-authorities.yaml': {'authorities': {'low': {}}},
            'schemas/waiver.schema.json': {'properties': {'risk_classification': {'enum': ['low']}}},
            'governance/policy-requirements.yaml': {'source_document': 'DevSecOps Policy', 'requirements': []},
            'governance/directive-requirements.yaml': {'source_document': 'DevSecOps Directive', 'requirements': []}}
        for name, value in values.items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(yaml.safe_dump(value))
        self.data = ReportData(self.root, {name: {'mode': '100644'} for name in values})

    def test_zero_gap_and_zero_mapping_outputs_have_original_headers_and_visible_counts(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/model-followup-reporting-cases.json').read_text())
        for kind, function in [('open-gaps', report_model_followup.open_gaps),
                               ('document-controls', report_model_followup.document_controls)]:
            files = function(self.data)
            name = next(n for n in files if n.endswith('.csv'))
            original = fixture['cases'][-1]['expected_outputs'][kind][name].encode()
            self.assertEqual(files[name], original.splitlines(keepends=True)[0])
            markdown = next(v for n, v in files.items() if n.endswith('.md'))
            self.assertIn(b'`0`', markdown)

    def test_complete_legacy_classification_needs_no_placement_or_optional_text(self):
        path = self.root / 'model/controls/dscb-l1.yaml'; value = yaml.safe_load(path.read_text())
        value['requirements'][0]['automation'] = {'type': 'evidence_check', 'maturity': 'immediate', 'check_type': 'presence'}
        path.write_text(yaml.safe_dump(value))
        result = report_model_followup.automation(self.data)['generated/html/automation_report.md']
        self.assertIn(b'Total requirements: 1', result)
        self.assertIn(b'Automation-supported coverage: 100.0%', result)
        self.assertFalse((self.root / 'pipeline-baseline').exists())

    def test_empty_automation_population_is_execution_failure_not_false_coverage(self):
        path = self.root / 'model/controls/dscb-l1.yaml'; path.write_text('level: L1\nrequirements: []\n')
        with self.assertRaisesRegex(ValueError, 'automation_controls_missing'):
            report_model_followup.automation(self.data)


if __name__ == '__main__': unittest.main()
