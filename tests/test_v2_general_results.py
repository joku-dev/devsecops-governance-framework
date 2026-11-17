"""Frozen complete V1 CI/manual mappings and result index semantics."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import ci_bundle_results as bundle
from lib import results_projection as projection


class GeneralResultDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/general-result-cases.json').read_text())
        assert cls.fixture['synthetic']
        assert cls.fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def materialize(self, files):
        for name, payload in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload))

    def test_all_bundle_snapshots_and_validation_equal_frozen_v1(self):
        for case in self.fixture['bundle_cases']:
            with self.subTest(case=case['id']):
                self.materialize(case['files'])
                errors = []
                getattr(bundle, 'validate_' + case['domain'])(self.root, errors, schema_root=ROOT)
                self.assertEqual(errors, case['expected_validation_errors'])
                actual = getattr(bundle, case['domain'] + '_snapshot')(self.root,
                    SimpleNamespace(**case['metadata']), governance_repository=case['governance_repository'],
                    at='2026-11-15T12:00:00Z')
                self.assertEqual(actual, case['expected_snapshot'])

    def test_all_manual_snapshots_equal_frozen_v1(self):
        for case in self.fixture['manual_cases']:
            with self.subTest(case=case['id']):
                actual = bundle.manual_snapshot(SimpleNamespace(**case['metadata']),
                    governance_repository=case['governance_repository'], at='2026-11-15T12:00:00Z',
                    control_summary=case['control_summary'])
                self.assertEqual(actual, case['expected_snapshot'])
                self.assertNotIn('trust', actual)

    def test_complete_all_three_indices_equal_frozen_v1(self):
        for domain, records in self.fixture['index_records'].items():
            with self.subTest(domain=domain):
                for row in records: self.materialize({row['path']: row['payload']})
                expected = self.fixture['expected_indices'][domain]
                actual = getattr(projection, domain + '_index')(self.root, expected['generated_at'],
                    **self.fixture['event_policy'])
                self.assertEqual(actual, expected)
                self.assertFalse((self.root / 'status/repository-results-index.json').exists())
                self.assertFalse((self.root / 'status/architecture-results-index.json').exists())
                self.assertFalse((self.root / 'status/typed-evidence-results-index.json').exists())

    def test_later_branch_or_manual_cannot_replace_mainline_representative(self):
        for row in self.fixture['index_records']['devsecops']: self.materialize({row['path']: row['payload']})
        actual = projection.devsecops_index(self.root, '2026-11-15T12:00:00Z', **self.fixture['event_policy'])
        selected = next(row for row in actual['repositories'] if row['repository_id'] == 'synthetic/results')
        self.assertEqual(selected['latest_result']['pipeline_run_id'], '8001')
        self.assertEqual(actual['summary']['manual_results'], 1)
        branches = next(row for row in actual['repositories'] if row['repository_id'] == 'synthetic/branches')
        self.assertEqual(branches['latest_result']['pipeline_run_id'], '8005')
        self.assertEqual(branches['latest_result']['status'], 'fail')
        # Trust selection is independent of pass/fail, never a best-outcome filter.
        self.assertEqual(selected['history'][1]['trust']['effective_level'], 'integrity_verified')
        self.assertEqual(selected['history'][1]['status'], 'fail')

    def test_typed_selection_is_per_type_and_retains_failed_freshness_and_replay(self):
        for row in self.fixture['index_records']['typed']: self.materialize({row['path']: row['payload']})
        actual = projection.typed_index(self.root, '2026-11-15T12:00:00Z', **self.fixture['event_policy'])
        selected = actual['repositories'][0]
        self.assertEqual({row['evidence_type'] for row in selected['latest_results']}, {'vulnerability_scan', 'sbom'})
        self.assertEqual(selected['latest_result']['pipeline_run_id'], '9005')
        self.assertEqual(selected['latest_result']['freshness'], 'fail')
        self.assertEqual(selected['latest_result']['replay'], 'fail')
        self.assertEqual(actual['summary']['freshness_failures'], 1)
        self.assertEqual(actual['summary']['replay_failures'], 1)
        self.assertEqual(next(row for row in selected['latest_results'] if row['evidence_type'] == 'sbom')['pipeline_run_id'], '9002')

    def test_classification_profile_is_explicit_and_not_bound_to_a_native_event_name(self):
        records = deepcopy(self.fixture['index_records']['devsecops'])
        for row in records:
            item = row['payload']
            if item['repository']['branch'] == 'main': item['repository']['branch'] = 'trunk'
            if item['pipeline']['event'] == 'workflow_dispatch': item['pipeline']['event'] = 'manual'
            self.materialize({row['path']: item})
        policy = {**self.fixture['event_policy'], 'main_branch': 'trunk', 'manual_events': ['manual']}
        actual = projection.devsecops_index(self.root, '2026-11-15T12:00:00Z', **policy)
        selected = next(row for row in actual['repositories'] if row['repository_id'] == 'synthetic/results')
        self.assertEqual(selected['latest_result']['pipeline_run_id'], '8001')
        self.assertEqual(actual['summary']['manual_results'], 1)

    def test_missing_ambiguous_and_malformed_bundle_inputs_fail_closed(self):
        errors = []; bundle.validate_devsecops(self.root, errors, schema_root=ROOT)
        self.assertEqual(len(errors), 2)
        case = self.fixture['bundle_cases'][0]; self.materialize(case['files'])
        self.materialize({'nested/pipeline-evidence.json': case['files']['pipeline-evidence.json']})
        with self.assertRaisesRegex(ValueError, 'ambiguous_ci_bundle_member'):
            bundle.validate_devsecops(self.root, [], schema_root=ROOT)
        (self.root / 'nested/pipeline-evidence.json').unlink()
        (self.root / 'pipeline-evidence.json').write_text('{"pipeline":{},"pipeline":{}}')
        errors = []; bundle.validate_devsecops(self.root, errors, schema_root=ROOT)
        self.assertTrue(any('duplicate_json_key' in row for row in errors))


if __name__ == '__main__': unittest.main()
