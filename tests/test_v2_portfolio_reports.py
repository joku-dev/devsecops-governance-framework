"""Original portfolio bytes, previous timestamps and bounded bulk reporting."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_sources, report_outputs, report_portfolio, report_application
from lib.functional_parity import git_read
from lib.report_application import ReportContext, file_descriptors

AT = '2026-11-15T12:00:00Z'
NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


class PortfolioGoldenTests(unittest.TestCase):
    def test_both_complete_original_writer_files_match_two_bound_previous_input_contexts(self):
        path = ROOT / 'tests/fixtures/axiom-v1-parity/portfolio-reporting-cases.json'
        fixture = json.loads(path.read_text()); memberpath = path.with_name(fixture['membership_fixture'])
        self.assertEqual(fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        self.assertEqual(hashlib.sha256(memberpath.read_bytes()).hexdigest(), fixture['membership_fixture_sha256'])
        members = json.loads(memberpath.read_text())['cases']
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary).resolve() / 'snapshot'
            manifest = report_sources.capture(ROOT, git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), snapshot)
            for case in fixture['cases']:
                membership = next(c['membership'] for c in members if c['data_revision'] == case['data_revision'])
                self.assertEqual(hashlib.sha256(json.dumps(membership, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), case['membership_sha256'])
                for name, sha in case['source_files'].items():
                    self.assertEqual(hashlib.sha256((snapshot / 'data' / name).read_bytes()).hexdigest(), sha)
                expected = case['expected_outputs']['portfolio']
                self.assertEqual(report_outputs.build(snapshot / 'data', 'portfolio', membership=membership, at=AT),
                                 {name: raw.encode() for name, raw in expected.items()})
            self.assertEqual(len(manifest['files']), 369)

    def test_private_generation_preserves_committed_previous_input_and_grants_no_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            node = Path(temporary).resolve() / 'node'; node.mkdir(mode=0o700); (node / 'state').mkdir(mode=0o700)
            context = ReportContext(node, {'node_id': 'synthetic-portfolio-node'})
            data, _ = context.source_data(); previous = data / 'generated/reports/portfolio-onboarding-status.json'
            old = previous.read_bytes()
            report_id, value = context.create('portfolio', AT)
            self.assertEqual(context.inspect(report_id), value)
            self.assertEqual(previous.read_bytes(), old)
            self.assertEqual(len(value['files']), 2)
            self.assertFalse(value['published']); self.assertFalse(value['official_acceptance'])
            self.assertFalse(value['authority_transferred']); self.assertFalse(value['operating_acceptance_inherited'])
            self.assertIn(b'informational', (context.artifacts / report_id / 'generated/reports/portfolio-onboarding-status.md').read_bytes())


class PortfolioClockTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'integrations': [{'repository': 'synthetic/repo', 'owner': 'Synthetic Owner', 'governance_mode': 'report-only'}]}
        self.dev = {'repositories': [{'repository_id': 'synthetic/repo', 'latest_result': {
            'status': 'pass', 'generated_at': AT, 'pipeline_run_id': '42'}}]}
        self.arch = {'repositories': []}

    def build(self, now=NOW, previous=None):
        return report_portfolio.build_payload(self.registry, self.dev, self.arch, now, previous)

    def test_unchanged_rows_preserve_the_previous_generation_timestamp(self):
        previous = self.build(); current = self.build(NOW + timedelta(hours=1), previous)
        self.assertEqual(current, previous)
        self.assertEqual(current['generated_at'], AT)

    def test_changed_status_or_staleness_advances_timestamp_without_mutating_previous(self):
        previous = self.build(); original = deepcopy(previous)
        self.dev['repositories'][0]['latest_result']['status'] = 'fail'
        changed = self.build(NOW + timedelta(hours=1), previous)
        self.assertNotEqual(changed['generated_at'], AT); self.assertEqual(previous, original)
        stale = self.build(NOW + timedelta(days=31), changed)
        self.assertTrue(stale['repositories'][0]['stale_or_missing'])
        self.assertNotEqual(stale['generated_at'], changed['generated_at'])

    def test_freshness_keeps_original_boundary_missing_and_future_declaration_semantics(self):
        self.assertEqual(report_portfolio.freshness(AT, NOW + timedelta(days=30))['status'], 'current')
        self.assertEqual(report_portfolio.freshness(AT, NOW + timedelta(days=30, seconds=1))['status'], 'stale')
        self.assertEqual(report_portfolio.freshness('', NOW), {'status': 'missing', 'stale_after': None})
        self.assertEqual(report_portfolio.freshness('2026-11-16T12:00:00Z', NOW)['status'], 'current')

    def test_registry_adoption_labels_are_data_and_inputs_remain_unchanged(self):
        self.registry['integrations'].append({'repository': 'synthetic/other', 'governance_mode': 'legacy-blocking'})
        before = deepcopy((self.registry, self.dev, self.arch)); report = self.build()
        self.assertEqual([row['adoption_state'] for row in report['repositories']], ['pilot', 'active'])
        self.assertEqual((self.registry, self.dev, self.arch), before)
        self.assertIn('does not approve waivers or change enforcement modes', report_portfolio.render_markdown(report))

    def test_empty_registry_remains_visible_and_has_no_adoption_claims(self):
        report = report_portfolio.build_payload({'integrations': []}, {}, {}, NOW)
        self.assertEqual(report['summary'], {'repository_count': 0, 'stale_or_missing_count': 0,
                                            'report_only_count': 0, 'active_count': 0})
        self.assertEqual(report['repositories'], [])
        with self.assertRaisesRegex(ValueError, 'explicit_report_membership_and_time_required'):
            report_outputs.build(ROOT, 'portfolio', at=AT)


class FiniteReportCapacityTests(unittest.TestCase):
    def test_64_small_files_fit_but_65_are_rejected(self):
        files = {f'synthetic/report-{i}.txt': b'small' for i in range(64)}
        self.assertEqual(len(file_descriptors(files)), 64)
        files['synthetic/overflow.txt'] = b'small'
        with self.assertRaisesRegex(ValueError, 'output_budget_exhausted'): file_descriptors(files)

    def test_greater_file_count_does_not_bypass_aggregate_byte_limit(self):
        files = {f'synthetic/report-{i}.txt': b'small' for i in range(64)}
        with patch.object(report_application, 'MAX_TOTAL', 100), self.assertRaisesRegex(ValueError, 'output_budget_exhausted'):
            file_descriptors(files)


if __name__ == '__main__': unittest.main()
