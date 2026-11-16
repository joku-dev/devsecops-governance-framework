"""Exact original source-intake reports and candidate/provenance boundaries."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_outputs, report_sources
from lib.report_data import ReportData
from lib.report_requirement_delta import extract_requirements
from lib.source_document_text import SourceDocumentExtractionError
from lib.functional_parity import git_read


class OriginalSourceReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/fixtures/axiom-v1-parity/source-intake-reporting-cases.json'
        cls.fixture = json.loads(path.read_text())
        memberpath = path.with_name(cls.fixture['membership_fixture'])
        assert hashlib.sha256(memberpath.read_bytes()).hexdigest() == cls.fixture['membership_fixture_sha256']
        cls.membership_cases = json.loads(memberpath.read_text())['cases']
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.snapshot = Path(cls.temporary.name).resolve() / 'snapshot'
        cls.manifest = report_sources.capture(ROOT, git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), cls.snapshot)
        cls.data = cls.snapshot / 'data'

    def outputs(self, kind, root=None):
        return report_outputs.build(root or self.data, kind, membership=self.manifest['membership'], at=self.fixture['at'])

    def report(self, kind):
        return json.loads(next(raw for name, raw in self.outputs(kind).items() if name.endswith('.json')))

    def test_all_ten_original_file_bytes_match_both_exact_v1_input_contexts(self):
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        for case in self.fixture['cases']:
            membership = next(row['membership'] for row in self.membership_cases if row['data_revision'] == case['data_revision'])
            self.assertEqual(hashlib.sha256(json.dumps(membership, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), case['membership_sha256'])
            for name, sha in case['source_files'].items():
                self.assertEqual(hashlib.sha256((self.data / name).read_bytes()).hexdigest(), sha)
            for kind, files in case['expected_outputs'].items():
                with self.subTest(revision=case['data_revision'], kind=kind):
                    self.assertEqual(report_outputs.build(self.data, kind, membership=membership, at=self.fixture['at']),
                                     {name: raw.encode() for name, raw in files.items()})

    def test_candidate_decisions_and_source_status_are_not_promoted(self):
        intake = self.report('source-intake'); briefs = self.report('source-review-briefs')
        self.assertEqual(intake['summary']['status_counts'], {'approved': 9, 'candidate': 6})
        self.assertEqual(briefs['summary']['human_decision_required'], 6)
        self.assertFalse(briefs['decision']['autonomous_decisions_enabled'])
        self.assertFalse(intake['decision']['runtime_governance_changed'])
        self.assertEqual(self.report('source-replacement')['decision']['current_state'], 'assessment_only')

    def test_withheld_source_and_unverified_identifiers_retain_their_original_boundaries(self):
        report = self.report('requirement-delta'); inventory = report['requirement_intake_inventory']
        self.assertFalse(report['decision']['candidate_promoted'])
        self.assertEqual(inventory['summary']['inferred_candidate_count'], 0)
        self.assertEqual(inventory['summary']['extraction_row_id_count'], 0)
        self.assertEqual(inventory['summary']['author_identified_count'], 0)
        self.assertEqual(inventory['summary']['explicit_identifier_count'], 46)
        self.assertEqual([row['source_id'] for row in inventory['skipped_sources']], ['CISO-REQ-SRC-001'])

    def test_process_report_preserves_blockers_historical_counts_and_utf8_writer(self):
        files = self.outputs('source-process'); report = self.report('source-process')
        self.assertEqual(report['authorized_source_baseline']['status'], 'blocked')
        self.assertEqual(report['authorized_source_baseline']['final_source_baseline_approval'], 'not_recorded')
        self.assertEqual(report['summary']['lifecycle']['proposals'], 867)
        self.assertEqual(report['summary']['lifecycle']['undecided'], 783)
        raw = next(raw for name, raw in files.items() if name.endswith('.json'))
        self.assertIn('prüfen'.encode(), raw)
        self.assertNotIn(b'pr\\u00fcfen', raw)

    def test_fresh_dependencies_do_not_trust_old_generated_payloads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / 'copy'; shutil.copytree(self.data, root)
            for name in ['source-lineage-report', 'architecture-source-replacement-assessment',
                         'source-document-intake-status', 'governance-change-impact']:
                p = root / ('generated/reports/' + name + '.json'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{invalid')
            for kind in ['source-intake', 'source-review-briefs', 'requirement-delta']:
                with self.subTest(kind=kind): self.assertEqual(self.outputs(kind, root), self.outputs(kind))

    def test_process_profile_reads_its_original_committed_input_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / 'copy'; shutil.copytree(self.data, root)
            (root / 'generated/reports/source-document-requirement-delta.json').write_text('{invalid')
            with self.assertRaises(ValueError): self.outputs('source-process', root)


class SourceExtractionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(); self.path = self.root / 'source.md'
        self.data = ReportData(self.root, {'source.md': {'mode': '100644'}})

    def test_unlabelled_prose_and_reference_mentions_do_not_create_requirements(self):
        self.path.write_text('Systems MUST retain evidence.\nSee DSCB-L1-REQ-001 for requirements.\n')
        self.assertEqual(extract_requirements(self.data, 'SYNTHETIC', self.path), [])

    def test_identifier_provenance_is_separate_from_declared_identifier_presence(self):
        self.path.write_text('| ID | Requirement |\n| --- | --- |\n| DSCB-L1-REQ-099 | Systems MUST retain evidence. |\n')
        ordinary = extract_requirements(self.data, 'SYNTHETIC', self.path)[0]
        declared_author = extract_requirements(self.data, 'SYNTHETIC', self.path, 'author_provided')[0]
        self.assertEqual(ordinary['intake_priority'], 'unassigned')
        self.assertEqual(declared_author['intake_priority'], 'p1')
        self.assertEqual(ordinary['source_requirement_id'], declared_author['source_requirement_id'])

    def test_missing_and_linked_sources_fail_before_extraction(self):
        with self.assertRaisesRegex(SourceDocumentExtractionError, 'does not exist'):
            self.data.extract(self.root / 'absent.md')
        outside = self.root / 'outside.md'; outside.write_text('Synthetic outside marker')
        self.path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'unsafe_v2_boundary_source'): self.data.extract(self.path)

    def test_source_size_limit_precedes_format_extraction(self):
        self.path.write_bytes(b'x' * (16 * 1024**2 + 1))
        with self.assertRaises(ValueError): self.data.extract(self.path)


if __name__ == '__main__': unittest.main()
