"""Original candidate/health/replay wires and immutable explicit window semantics."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_sources, report_outputs, report_intake_health, report_replay_triage
from lib.report_application import ReportContext
from lib.report_data import ReportData
from lib.functional_parity import git_read
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import canonical_digest

AT = '2026-11-15T12:00:00Z'


class CandidateHealthGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/fixtures/axiom-v1-parity/candidate-health-replay-cases.json'
        cls.fixture = json.loads(path.read_text()); memberpath = path.with_name(cls.fixture['membership_fixture'])
        assert hashlib.sha256(memberpath.read_bytes()).hexdigest() == cls.fixture['membership_fixture_sha256']
        cls.members = json.loads(memberpath.read_text())['cases']
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.snapshot = Path(cls.temporary.name).resolve() / 'snapshot'
        cls.manifest = report_sources.capture(ROOT, git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), cls.snapshot)
        cls.data = cls.snapshot / 'data'

    def test_all_five_original_writer_outputs_match_both_bound_contexts(self):
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        for case in self.fixture['cases']:
            members = next(c['membership'] for c in self.members if c['data_revision'] == case['data_revision'])
            self.assertEqual(hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), case['membership_sha256'])
            for name, sha in case['source_files'].items():
                self.assertEqual(hashlib.sha256((self.data / name).read_bytes()).hexdigest(), sha)
            for kind, files in case['expected_outputs'].items():
                with self.subTest(revision=case['data_revision'], kind=kind):
                    self.assertEqual(report_outputs.build(self.data, kind, membership=members, at=AT),
                                     {name: raw.encode() for name, raw in files.items()})

    def test_candidate_report_stays_non_normative_and_does_not_rewrite_sources(self):
        before = {name: hashlib.sha256((self.data / name).read_bytes()).hexdigest() for name in self.manifest['files']}
        files = report_outputs.build(self.data, 'candidate-maturity', membership=self.manifest['membership'], at=AT)
        report = json.loads(next(v for n, v in files.items() if n.endswith('.json')))
        self.assertEqual(report['status'], 'candidate'); self.assertFalse(report['normative'])
        self.assertEqual(report['enforcement'], 'none')
        self.assertEqual(report['summary']['human_review_required'], report['summary']['harmonized_requirements'])
        self.assertEqual(before, {name: hashlib.sha256((self.data / name).read_bytes()).hexdigest() for name in self.manifest['files']})

    def test_all_selection_applies_custom_window_only_to_health(self):
        wide = report_outputs.build(self.data, 'all', membership=self.manifest['membership'], at=AT)
        narrow = report_outputs.build(self.data, 'all', membership=self.manifest['membership'], at=AT, window_days=1)
        self.assertEqual(len(wide), 33)
        self.assertEqual({name for name in wide if wide[name] != narrow[name]}, {'status/intake-health.json'})
        self.assertEqual(json.loads(narrow['status/intake-health.json'])['window']['days'], 1)

    def test_membership_time_and_applicable_window_are_explicit(self):
        for kind in ['candidate-maturity', 'intake-health', 'replay-triage']:
            with self.assertRaisesRegex(ValueError, 'explicit_report_membership_and_time_required'):
                report_outputs.build(self.data, kind, at=AT)
        with self.assertRaisesRegex(ValueError, 'intake_health_window_not_applicable'):
            report_outputs.build(self.data, 'candidate-maturity', membership=self.manifest['membership'], at=AT, window_days=1)
        for days in [0, -1, True, '30']:
            with self.assertRaisesRegex(ValueError, 'invalid_intake_health_window'):
                report_outputs.build(self.data, 'intake-health', membership=self.manifest['membership'], at=AT, window_days=days)


class SyntheticHistoricalReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(); self.members = {}
        for name in report_intake_health.INDEX_NAMES.values(): self.write('status/' + name, {'repositories': []})

    def write(self, name, value):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value))
        self.members[name] = {'mode': '100644'}

    def context(self): return ReportData(self.root, self.members)

    def test_window_is_inclusive_and_excludes_future_events(self):
        for i, at in enumerate(['2026-11-15T11:00:00Z', '2026-11-14T12:00:00Z',
                                '2026-11-10T12:00:00Z', '2026-11-16T12:00:00Z']):
            self.write(f'status/intake-events/{i}.json', {'completed_at': at, 'status': 'success', 'duration_ms': 100})
        short = report_intake_health.generate(self.context(), AT, 1)
        longer = report_intake_health.generate(self.context(), AT, 30)
        self.assertEqual(short['summary']['events']['total'], 2)
        self.assertEqual(longer['summary']['events']['total'], 3)
        self.assertEqual(short['window']['days'], 1)
        self.assertEqual(short['generated_at'], AT)

    def test_attempt_lifecycle_keeps_resolved_open_and_permanent_distinct(self):
        for label, retryable in [('resolved', True), ('open', True), ('permanent', False)]:
            source = {'repository_id': 'synthetic/repo', 'run_id': label, 'artifact_name': 'evidence'}
            self.write(f'status/collection-attempts/{label}.json', {'repository_id': 'synthetic/repo',
                'source': source, 'errors': [{'retryable': retryable}]})
            if label == 'resolved':
                self.write('status/results/resolved.json', {'repository_id': 'synthetic/repo',
                    'generated_at': AT, 'trust': {'capture': {'source': source}}})
        report = report_intake_health.generate(self.context(), AT, 1)
        self.assertEqual(report['observation_status'], 'no_data')
        self.assertEqual(report['summary']['collection_attempts'], {'total': 3, 'open': 1, 'resolved': 1, 'permanent': 1})
        self.assertIsNone(report['summary']['events']['duration_ms']['p95'])

    def test_empty_replay_and_health_are_visible_without_acceptance(self):
        health = report_intake_health.generate(self.context(), AT)
        self.assertEqual(health['observation_status'], 'no_data')
        self.assertEqual(health['summary']['events']['total'], 0)
        replay = report_replay_triage.generate(self.context(), AT)
        self.assertEqual(replay['summary']['assessments'], 0)
        self.assertEqual(replay['generated_at'], '1970-01-01T00:00:00Z')
        self.assertTrue(all(value is False for value in replay['decision_boundary'].values()))

    def test_original_malformed_replay_skip_does_not_swallow_strict_duplicate_errors(self):
        self.write('status/results/bad.json', 'not JSON')
        self.assertEqual(report_replay_triage.generate(self.context(), AT)['summary']['assessments'], 0)
        self.write('status/results/bad.json', '{"trust":{},"trust":{}}')
        with self.assertRaisesRegex(ValueError, 'duplicate_result_input_key'):
            report_replay_triage.generate(self.context(), AT)

    def test_window_overflow_and_missing_timezone_are_named_execution_errors(self):
        with self.assertRaisesRegex(ValueError, 'invalid_intake_health_window'):
            report_intake_health.generate(self.context(), AT, 10 ** 20)
        with self.assertRaises(ValueError): report_intake_health.generate(self.context(), '2026-11-15T12:00:00')


class PrivateWindowReportTests(unittest.TestCase):
    def test_window_is_bound_to_identity_and_recomputed_during_inspection(self):
        with tempfile.TemporaryDirectory() as temporary:
            node = Path(temporary).resolve() / 'node'; node.mkdir(mode=0o700); (node / 'state').mkdir(mode=0o700)
            context = ReportContext(node, {'node_id': 'synthetic-window-node'})
            first, value = context.create('intake-health', AT, 30)
            second, narrow = context.create('intake-health', AT, 1)
            self.assertNotEqual(first, second); self.assertEqual(narrow['window_days'], 1)
            self.assertEqual(context.inspect(first), value); self.assertEqual(context.inspect(second), narrow)
            self.assertFalse(value['published']); self.assertFalse(value['official_acceptance'])
            changed = deepcopy(value); changed['window_days'] = 1; fake = canonical_digest(changed)
            atomic_json(context.assessments / (fake + '.json'), changed)
            with self.assertRaisesRegex(ValueError, 'report_differs_from_sources'): context.inspect(fake)
            # The logical status filename belongs to this private artifact root.
            self.assertTrue((context.artifacts / first / 'status/intake-health.json').is_file())


if __name__ == '__main__': unittest.main()
