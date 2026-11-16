"""Original decision-aid wires, committed dependencies and explicit authority limits."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_sources, report_outputs, report_blocking_readiness as ready, report_blocking_alignment as alignment
from lib.functional_parity import git_read
from lib.report_application import ReportContext
from lib.report_data import ReportData

AT = '2026-11-15T12:00:00Z'


class BlockingWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/fixtures/axiom-v1-parity/blocking-reporting-cases.json'
        cls.fixture = json.loads(path.read_text()); memberpath = path.with_name(cls.fixture['membership_fixture'])
        assert hashlib.sha256(memberpath.read_bytes()).hexdigest() == cls.fixture['membership_fixture_sha256']
        cls.members = json.loads(memberpath.read_text())['cases']
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.snapshot = Path(cls.temporary.name).resolve() / 'snapshot'
        cls.manifest = report_sources.capture(ROOT, git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), cls.snapshot)
        cls.data = cls.snapshot / 'data'

    def test_both_original_json_writers_match_two_bound_370_file_contexts(self):
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        self.assertEqual(len(self.manifest['files']), 370)
        for case in self.fixture['cases']:
            members = next(c['membership'] for c in self.members if c['data_revision'] == case['data_revision'])
            self.assertEqual(hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), case['membership_sha256'])
            for name, sha in case['source_files'].items():
                self.assertEqual(hashlib.sha256((self.data / name).read_bytes()).hexdigest(), sha)
            for kind, files in case['expected_outputs'].items():
                self.assertEqual(report_outputs.build(self.data, kind, membership=members, at=AT),
                                 {n: raw.encode() for n, raw in files.items()})

    def test_alignment_uses_committed_readiness_without_invoking_the_fresh_generator(self):
        before = (self.data / 'generated/reports/blocking-readiness.json').read_bytes()
        with patch.object(ready, 'generate', side_effect=AssertionError('fresh readiness forbidden')):
            actual = report_outputs.build(self.data, 'blocking-alignment', membership=self.manifest['membership'], at=AT)
        expected = self.fixture['cases'][-1]['expected_outputs']['blocking-alignment']
        self.assertEqual(actual, {n: raw.encode() for n, raw in expected.items()})
        self.assertEqual((self.data / 'generated/reports/blocking-readiness.json').read_bytes(), before)

    def test_conflict_presence_is_committed_recursive_json_membership_not_ambient_files(self):
        context = ReportData(self.data, self.manifest['membership'])
        baseline = ready.generate(context, AT)
        repository = baseline['repositories'][0]['repository_id']; encoded = repository.replace('/', '__')
        members = deepcopy(self.manifest['membership'])
        members[f'status/intake-conflicts/nested/{encoded}-a.json'] = {'mode': '100644'}
        members[f'status/intake-conflicts/{encoded}-directory.json/member.txt'] = {'mode': '100644'}
        members[f'status/intake-conflicts/{encoded}-ignored.txt'] = {'mode': '100644'}
        members['status/intake-conflicts/unrelated.json'] = {'mode': '100644'}
        changed = ready.generate(ReportData(self.data, members), AT)
        original = next(r for r in baseline['repositories'] if r['repository_id'] == repository)
        row = next(r for r in changed['repositories'] if r['repository_id'] == repository)
        criterion = lambda r: next(c for c in r['criteria'] if c['id'] == 'no_intake_conflicts')
        self.assertEqual(criterion(row)['observed'], criterion(original)['observed'] + 2)
        self.assertEqual(criterion(row)['status'], 'fail')

    def test_private_reports_preserve_inputs_and_outer_authority_and_detect_output_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            node = Path(temporary).resolve() / 'node'; node.mkdir(mode=0o700); (node / 'state').mkdir(mode=0o700)
            context = ReportContext(node, {'node_id': 'synthetic-blocking-node'})
            data, manifest = context.source_data()
            before = {name: hashlib.sha256((data / name).read_bytes()).hexdigest() for name in manifest['files']}
            for kind in ('blocking-readiness', 'blocking-alignment'):
                identifier, value = context.create(kind, AT)
                self.assertEqual(context.inspect(identifier), value); self.assertEqual(len(value['files']), 1)
                for flag in ('published', 'official_acceptance', 'production_approval', 'risk_acceptance',
                             'authority_transferred', 'operating_acceptance_inherited', 'provider_invoked'):
                    self.assertIs(value[flag], False)
                self.assertEqual(value['mode'], 'report-only'); self.assertIsNone(value['source_configuration_profile'])
                path = context.artifacts / identifier / next(iter(value['files'])); raw = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'derived_report_output_changed'): context.inspect(identifier)
                path.write_bytes(raw); self.assertEqual(context.inspect(identifier), value)
            self.assertEqual(before, {name: hashlib.sha256((data / name).read_bytes()).hexdigest() for name in manifest['files']})

    def test_membership_time_and_original_clock_representation_are_explicit(self):
        for kind in ('blocking-readiness', 'blocking-alignment'):
            with self.assertRaisesRegex(ValueError, 'explicit_report_membership_and_time_required'):
                report_outputs.build(self.data, kind, at=AT)
            with self.assertRaisesRegex(ValueError, 'intake_health_window_not_applicable'):
                report_outputs.build(self.data, kind, membership=self.manifest['membership'], at=AT, window_days=1)
        at = '2026-11-15T14:00:00.123456+02:00'
        files = report_outputs.build(self.data, 'blocking-alignment', membership=self.manifest['membership'], at=at)
        self.assertEqual(json.loads(next(iter(files.values())))['generated_at'], at)
        members = deepcopy(self.manifest['membership']); members.pop('generated/reports/blocking-readiness.json')
        with self.assertRaisesRegex(ValueError, 'uncommitted_report_input'):
            report_outputs.build(self.data, 'blocking-alignment', membership=members, at=AT)


class AlignmentDecisionTests(unittest.TestCase):
    def setUp(self):
        self.integrations = {'integrations': [{'repository': 'synthetic/repo', 'governance_mode': 'block-on-error'}]}
        self.readiness = {'repositories': [{'repository_id': 'synthetic/repo', 'technical_ready': False,
            'manual_approval': 'pending', 'criteria': [{'id': 'gap', 'required': True, 'status': 'fail'}]}]}
        self.record = {'repository_id': 'synthetic/repo', 'current_mode': 'block-on-error',
            'enforcement_change_authorized': False, 'disposition': 'preserve_without_new_approval',
            'mode_observed_at': '2026-10-01T00:00:00Z', 'review_due': '2026-12-12T23:59:59+01:00',
            'required_gap_ids': ['gap']}
        self.model = {'model_introduced_at': '2026-10-02T00:00:00Z', 'legacy_risk_records': [self.record]}

    def assess(self, at=AT):
        return alignment.assess(integrations=self.integrations, readiness=self.readiness, alignment_model=self.model, as_of=at)

    def test_active_legacy_record_does_not_authorize_blocking_activation_or_mutate_inputs(self):
        before = deepcopy((self.integrations, self.readiness, self.model)); report = self.assess()
        self.assertEqual(report['repositories'][0]['alignment'], 'legacy_risk_active')
        self.assertFalse(report['repositories'][0]['blocking_activation_valid'])
        self.assertFalse(report['enforcement_change_authorized']); self.assertEqual(report['enforcement'], 'report_only')
        self.assertEqual(before, (self.integrations, self.readiness, self.model))

    def test_expiry_is_strict_and_pre_model_or_naive_time_is_invalid(self):
        self.assertEqual(self.assess(self.record['review_due'])['repositories'][0]['alignment'], 'legacy_risk_active')
        self.assertEqual(self.assess('2026-12-12T23:00:00Z')['repositories'][0]['alignment'], 'legacy_risk_expired')
        for at in ('2026-10-01T00:00:00Z', '2026-11-15T12:00:00'):
            with self.assertRaises(ValueError): self.assess(at)

    def test_missing_and_incomplete_risk_records_remain_unsafe(self):
        original = deepcopy(self.record)
        for key, value in [('required_gap_ids', []), ('current_mode', 'report-only'), ('enforcement_change_authorized', True),
                           ('disposition', 'approve'), ('mode_observed_at', self.model['model_introduced_at'])]:
            self.record.clear(); self.record.update(deepcopy(original)); self.record[key] = value
            report = self.assess(); self.assertEqual(report['repositories'][0]['alignment'], 'legacy_risk_incomplete')
            self.assertEqual(report['alignment_status'], 'review_required')
        self.model['legacy_risk_records'] = []
        self.assertEqual(self.assess()['repositories'][0]['alignment'], 'unapproved_blocking')

    def test_orphaned_record_requires_review_even_with_nonblocking_consumer(self):
        self.integrations['integrations'][0]['governance_mode'] = 'report-only'
        self.record['repository_id'] = 'synthetic/orphan'
        report = self.assess(); self.assertEqual(report['orphaned_legacy_records'], ['synthetic/orphan'])
        self.assertEqual(report['alignment_status'], 'review_required')
        self.assertEqual(report['repositories'][0]['alignment'], 'nonblocking')

    def test_technical_readiness_still_requires_recorded_manual_approval(self):
        row = self.readiness['repositories'][0]; row['technical_ready'] = True; row['criteria'] = []
        self.model['legacy_risk_records'] = []
        self.assertEqual(self.assess()['repositories'][0]['alignment'], 'unapproved_blocking')
        row['manual_approval'] = 'approved'; report = self.assess()
        self.assertEqual(report['repositories'][0]['alignment'], 'aligned_blocking')
        self.assertTrue(report['repositories'][0]['blocking_activation_valid'])
        self.assertFalse(report['enforcement_change_authorized'])


class ReadinessDecisionTests(unittest.TestCase):
    def test_technical_ready_is_separate_from_approval_and_conflict_and_open_attempts(self):
        latest = {'status': 'pass', 'governance_baseline_ref': 'l1-baseline-v1.1.3', 'commit_id': 'same',
                  'trust': {'effective_level': 'provenance_verified', 'check_summary': {'fail': 0}, 'replay': 'pass'}}
        kwargs = dict(integrations={'integrations': [{'repository': 'synthetic/repo', 'governance_mode': 'report-only'}]},
            devsecops={'repositories': [{'repository_id': 'synthetic/repo', 'latest_result': latest,
                'history': [{'pipeline_event': 'push', 'branch': 'main', 'status': 'pass'}]}]}, architecture={},
            typed={'repositories': [{'repository_id': 'synthetic/repo', 'latest_result': {'commit_id': 'same',
                'collector_status': 'collected', 'freshness': 'pass', 'content_integrity': 'pass', 'replay': 'pass'}}]},
            health={'dimensions': [{'dimension': 'repository_id', 'value': 'synthetic/repo',
                'metrics': {'total': 1, 'success_rate_pct': 100}}]},
            model={'thresholds': {'minimum_mainline_successes': 1, 'minimum_trust_level': 'integrity_verified',
                'minimum_intake_events': 1, 'minimum_intake_success_rate_pct': 100}}, conflict_files=[])
        row = ready.assess(**kwargs)['repositories'][0]
        self.assertTrue(row['technical_ready']); self.assertEqual(row['manual_approval'], 'pending')
        self.assertEqual(row['decision'], 'ready_for_approval')
        kwargs['conflict_files'] = ['status/intake-conflicts/synthetic__repo.json']
        self.assertFalse(ready.assess(**kwargs)['repositories'][0]['technical_ready'])
        kwargs['conflict_files'] = []; kwargs['health']['summary'] = {'collection_attempts': {'open': 1}}
        self.assertFalse(ready.assess(**kwargs)['repositories'][0]['technical_ready'])


if __name__ == '__main__': unittest.main()
