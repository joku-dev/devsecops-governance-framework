"""Finite result CLI, private projections and source-backed historical membership."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import base64

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import result_application
from lib.ci_bundle_storage import describe
from lib.portable.contracts import canonical_digest
from lib.result_assessments import ResultContext
from lib.result_snapshot_store import ResultLedger, logical_identity


class ResultApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.instance = self.base / 'instance'; self.instance.mkdir(mode=0o700)
        self.settings = {'node_id': '1' * 32}
        self.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/general-result-cases.json').read_text())
        self.at = '2026-11-15T12:00:00Z'
        self.source = self.base / 'bundle'; self.source.mkdir()
        self.metadata = self.base / 'metadata.json'

    def call(self, *args, expected=0):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(result_application.run(list(args), self.instance, self.settings), expected)
        return json.loads(stream.getvalue())

    def inputs(self, case=None, kind='bundle'):
        case = deepcopy(case or self.fixture['bundle_cases'][0])
        for name, value in case.get('files', {}).items():
            (self.source / name).write_text(json.dumps(value))
        repository = {'provider': 'synthetic', 'instance': 'https://scm.example', 'native_id': 'synthetic-1',
                      'path': case['expected_snapshot']['repository_id'], 'url': 'https://scm.example/synthetic/results'}
        metadata = {'schema_version': 1, 'input_kind': kind, 'domain': case.get('domain', 'devsecops'),
            'repository': repository, 'governance_repository': case['governance_repository'], 'parameters': case['metadata']}
        self.metadata.write_text(json.dumps(metadata))
        return case

    def verified(self, case=None):
        self.inputs(case)
        return self.call('verify-bundle', '--bundle', str(self.source), '--sha256', describe(self.source)['input_sha256'],
                         '--metadata', str(self.metadata), '--at', self.at)

    def project(self, domain='devsecops'):
        return self.call('project', '--domain', domain, '--origin', 'operator_bundle', '--scm', 'synthetic',
            '--service', 'https://scm.example', '--main-branch', 'main', '--event-profile', 'legacy-v1', '--at', self.at)

    def test_verify_inspect_explicit_intake_and_complete_private_projection(self):
        receipt = self.verified()
        self.assertFalse(receipt['official_acceptance'])
        inspected = self.call('inspect', '--id', receipt['assessment_id'])
        self.assertTrue(inspected['raw_sources_reverified']); self.assertFalse(inspected['native_metadata_rechecked_now'])
        self.assertEqual(inspected['assessment']['snapshots']['devsecops'], self.fixture['bundle_cases'][0]['expected_snapshot'])
        self.assertEqual(self.call('records', '--origin', 'operator_bundle', '--domain', 'devsecops')['record_count'], 0)
        admitted = self.call('intake', '--id', receipt['assessment_id'])
        self.assertEqual(admitted['results']['devsecops']['status'], 'recorded')
        self.assertEqual(self.call('intake', '--id', receipt['assessment_id'])['results']['devsecops']['status'], 'idempotent')
        projection = self.project()
        self.assertEqual(projection['source_count'], 1); self.assertFalse(projection['published'])
        view = self.call('inspect-project', '--id', projection['projection_id'])['projection']
        self.assertEqual(view['reported_index'], view['effective_index'])
        selected = view['effective_index']['repositories'][0]
        self.assertEqual(selected['latest_result']['status'], 'pass')
        self.assertEqual(selected['latest_result']['trust']['effective_level'], 'unverified')
        root = self.instance / 'state/results/projections' / projection['projection_id']
        for name in view['files']: self.assertTrue((root / name).is_file())
        self.assertFalse((self.instance / 'status').exists())

    def test_manual_and_architecture_routes_preserve_whole_v1_payloads(self):
        case = self.inputs(self.fixture['manual_cases'][0], 'manual')
        summary = self.base / 'summary.json'; summary.write_text(json.dumps(case['control_summary']))
        receipt = self.call('manual', '--metadata', str(self.metadata), '--summary', str(summary), '--at', self.at)
        value = self.call('inspect', '--id', receipt['assessment_id'])['assessment']
        self.assertEqual(value['snapshots']['devsecops'], case['expected_snapshot'])
        arch = self.fixture['bundle_cases'][2]
        receipt = self.verified(arch); self.call('intake', '--id', receipt['assessment_id'])
        projection = self.project('architecture')
        value = self.call('inspect-project', '--id', projection['projection_id'])['projection']
        self.assertEqual(value['reported_index']['summary']['passing_results'], 1)
        self.assertEqual(value['effective_index']['repositories'][0]['latest_result']['architecture_summary'], arch['expected_snapshot']['architecture_summary'])

    def test_validation_only_does_not_create_an_assessment_or_admit_results(self):
        self.inputs(); sha = describe(self.source)['input_sha256']
        self.assertEqual(self.call('describe', '--bundle', str(self.source))['input_sha256'], sha)
        result = self.call('validate-bundle', '--bundle', str(self.source), '--sha256', sha, '--domain', 'devsecops')
        self.assertEqual(result['validation'], 'pass'); self.assertFalse(result['provider_invoked'])
        self.assertFalse(list((self.instance / 'state/results/assessments').glob('*.json')))
        (self.source / 'baseline-gate-result.json').unlink()
        result = self.call('validate-bundle', '--bundle', str(self.source), '--sha256', describe(self.source)['input_sha256'],
                           '--domain', 'devsecops', expected=2)
        self.assertEqual(result['validation'], 'fail')

    def test_project_snapshot_membership_survives_later_records(self):
        receipt = self.verified(); self.call('intake', '--id', receipt['assessment_id'])
        first = self.project(); before = self.call('inspect-project', '--id', first['projection_id'])['projection']
        later = deepcopy(self.fixture['bundle_cases'][0]); later['metadata']['pipeline_run_id'] = '7002'
        later['metadata']['generated_at'] = '2026-11-15T13:00:00Z'
        receipt = self.verified(later); self.call('intake', '--id', receipt['assessment_id'])
        self.assertEqual(self.call('inspect-project', '--id', first['projection_id'])['projection'], before)
        second = self.project(); self.assertNotEqual(second['projection_id'], first['projection_id'])
        self.assertEqual(second['source_count'], 2)

    def test_resealed_database_outcome_is_rejected_against_original_input(self):
        receipt = self.verified(); self.call('intake', '--id', receipt['assessment_id'])
        ledger = ResultLedger(self.instance / 'state/results/ledger')
        value = deepcopy(self.fixture['bundle_cases'][0]['expected_snapshot']); value['overall_status'] = 'fail'
        ledger.db.execute('UPDATE records SET payload=?,digest=?,logical_identity=?',
                          (json.dumps(value), canonical_digest(value), logical_identity(value)))
        ledger.db.commit(); ledger.close()
        with self.assertRaisesRegex(ValueError, 'report_differs_from_source'): self.project()

    def test_missing_foreign_or_changed_projection_sources_are_not_silently_adopted(self):
        receipt = self.verified(); self.call('intake', '--id', receipt['assessment_id'])
        projection = self.project()
        root = self.instance / 'state/results/projections' / projection['projection_id']
        stored = json.loads((root / 'projection.json').read_text())
        member = root / next(iter(stored['files'])); member.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'retained_file_changed'):
            self.call('inspect-project', '--id', projection['projection_id'])
        (self.instance / 'state/results/assessments' / (receipt['assessment_id'] + '.json')).unlink()
        with self.assertRaises(OSError): self.project()

    def test_typed_empty_projection_is_scoped_and_has_no_native_refresh(self):
        result = self.project('typed')
        self.assertEqual(result['source_count'], 0)
        value = self.call('inspect-project', '--id', result['projection_id'])['projection']
        self.assertFalse(value['native_metadata_rechecked_now']); self.assertFalse(value['official_acceptance'])
        self.assertEqual(value['effective_index']['summary']['result_count'], 0)

    def test_typed_reported_trust_is_retained_but_operator_effective_trust_is_unverified(self):
        from lib.consumer_intake_store import atomic_json
        from lib.typed_evidence_application import run as typed_run
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/typed-container-cases.json').read_text())
        bundle = self.base / 'typed-bundle'; bundle.mkdir(mode=0o700)
        (bundle / 'archives').mkdir(mode=0o700)
        for name, raw in fixture['archive_bytes_base64'].items():
            (bundle / 'archives' / (name + '.zip')).write_bytes(base64.b64decode(raw))
        atomic_json(bundle / 'capture.json', fixture['manifest'])
        import hashlib
        sha = hashlib.sha256((bundle / 'capture.json').read_bytes()).hexdigest()
        def typed(*arguments):
            stream = io.StringIO()
            with redirect_stdout(stream): self.assertEqual(typed_run(list(arguments), self.instance, self.settings), 0)
            return json.loads(stream.getvalue())
        receipt = typed('verify-local', '--provider', 'github-actions', '--bundle', str(bundle),
                        '--sha256', sha, '--at', fixture['at'])
        typed('intake', '--id', receipt['assessment_id'])
        proof = typed('inspect', '--id', receipt['assessment_id'])['assessment']
        descriptor = proof['verification']['repository']
        result = self.call('project', '--domain', 'typed', '--origin', 'operator_bundle',
            '--scm', descriptor['provider'], '--service', descriptor['instance'], '--main-branch', 'main',
            '--event-profile', 'legacy-v1', '--at', self.at)
        value = self.call('inspect-project', '--id', result['projection_id'])['projection']
        self.assertEqual(value['reported_index']['summary']['trust_level_counts'], {'provenance_verified': 2})
        self.assertEqual(value['effective_index']['summary']['trust_level_counts'], {'unverified': 2})
        self.assertEqual(value['reported_index']['summary']['result_count'], 2)
        self.assertEqual(value['effective_index']['summary']['result_count'], 2)
        self.assertFalse(value['native_metadata_rechecked_now']); self.assertFalse(value['published'])


if __name__ == '__main__': unittest.main()
