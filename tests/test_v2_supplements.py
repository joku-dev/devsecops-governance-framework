"""Frozen V1 supplement parity and private replay/authority negatives."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.assurance_projection import build_assurance
from lib.consolidated_projection import build_consolidated
from lib.measured_application import assessment, persist
from lib.portable.contracts import canonical_digest
from lib.provider_ports import measured_supplement_profile
from lib.supplement_application import (run, load, bundle_snapshot, logical_measured_path,
                                      staging_report, validate)
from unittest.mock import patch


class SupplementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.node = self.base / 'node'
        self.node.mkdir(mode=0o700)
        (self.node / 'state').mkdir(mode=0o700)
        (self.node / 'state/measured').mkdir(mode=0o700)
        self.settings = {'node_id': '1' * 32}
        self.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/supplement-cases.json').read_text())
        self.input = self.fixture['input']
        self.measured = self.input['measured']
        self.at = self.input['at']
        value = assessment(self.measured, provider='github-actions', kind='l1', at=self.at,
            origin='operator_bundle', input_sha256='2' * 64,
            capture={'native_metadata_rechecked': False, 'independent_attestation': False})
        self.measured_id = persist(value, self.node / 'state/measured')['assessment_id']
        self.bundle = self.base / self.input['bundle_name']
        self.bundle.mkdir()
        for name, raw in self.input['files'].items():
            (self.bundle / name).write_text(raw)

    def call(self, command, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            result = run([command, '--measured', self.measured_id, '--at', self.at, *arguments],
                         self.node, self.settings)
        self.assertEqual(result, 0)
        return json.loads(output.getvalue())

    def staging(self):
        return self.call('staging', '--bundle', str(self.bundle),
                         '--evidence-repository-commit', self.input['evidence_repository_commit'])

    def reseal_bundle(self):
        files = {p.name: p.read_bytes() for p in self.bundle.iterdir() if p.name != 'SHA256SUMS'}
        (self.bundle / 'SHA256SUMS').write_text(''.join(
            hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())))

    def test_independently_executed_v1_complete_reports_match(self):
        self.assertTrue(self.fixture['synthetic'])
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        profile = measured_supplement_profile('github-actions', self.measured)
        name, files = bundle_snapshot(self.bundle)
        staging = staging_report(name, files, self.measured, profile, self.input['evidence_repository_commit'], self.at)
        self.assertEqual(staging, self.fixture['expected_staging'])
        measured_file = logical_measured_path(self.measured)
        self.assertEqual(build_assurance(self.measured, [], root=ROOT,
            measured_source_file=measured_file, verified_at=self.at), self.fixture['expected_assurance'])
        self.assertEqual(build_consolidated(self.measured, staging, root=ROOT,
            profile=profile['consolidated_profile'], measured_source_file=measured_file,
            staging_source_file=staging['source_file']), self.fixture['expected_consolidated'])

    def test_cli_replays_exact_sources_without_promoting_inner_trust_or_approval(self):
        assurance = self.call('assurance')
        staging = self.staging()
        consolidated = self.call('consolidate', '--staging', staging['supplement_id'])
        for receipt, expected in [(assurance, 'expected_assurance'), (staging, 'expected_staging'),
                                  (consolidated, 'expected_consolidated')]:
            value = load(self.node, receipt['supplement_id'], self.settings)
            self.assertEqual(value['report'], self.fixture[expected])
            self.assertTrue(value['reported_trust_only'])
            self.assertEqual(value['evidence_trust'], 'unverified')
            for key in ('official_acceptance', 'authority_transferred', 'production_approval', 'risk_acceptance'):
                self.assertFalse(value[key])
            path = self.node / 'state/supplements/assessments' / (receipt['supplement_id'] + '.json')
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(self.staging(), staging)

    def test_stale_bundle_and_resealed_different_subject_are_rejected(self):
        self.at = '2026-10-01T11:00:00Z'
        with self.assertRaisesRegex(ValueError, 'seven-day'):
            self.staging()
        self.at = self.input['at']
        receipt_path = self.bundle / 'deployment-receipt.json'
        value = json.loads(receipt_path.read_text())
        value['context']['source_attempt'] = 2
        receipt_path.write_text(json.dumps(value))
        self.reseal_bundle()
        with self.assertRaisesRegex(ValueError, 'exact measured run'):
            self.staging()
        self.assertFalse((self.node / 'state/supplements/assessments').exists())

    def test_approval_target_or_raw_checksum_change_cannot_be_joined(self):
        path = self.bundle / 'deployment-approval.json'
        approval = json.loads(path.read_text())
        approval['target']['address'] = '192.0.2.99'
        path.write_text(json.dumps(approval))
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.staging()
        self.reseal_bundle()
        with self.assertRaisesRegex(ValueError, 'approval does not match'):
            self.staging()

    def test_raw_replay_tamper_and_foreign_node_are_rejected(self):
        receipt = self.staging()
        with self.assertRaisesRegex(ValueError, 'foreign_node'):
            load(self.node, receipt['supplement_id'], {'node_id': '3' * 32})
        raw = next((self.node / 'state/supplements/raw').glob('*/synthetic-staging/checks.txt'))
        raw.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'raw_bundle_changed'):
            load(self.node, receipt['supplement_id'], self.settings)

    def test_changed_report_recomputed_and_rejected_even_after_identity_reseal(self):
        receipt = self.call('assurance')
        value = load(self.node, receipt['supplement_id'], self.settings)
        value['report']['controls'][0]['missing_scope'] = ['forged']
        value['report']['assurance_binding'] = 'a' * 64
        new_id = canonical_digest(value)
        path = self.node / 'state/supplements/assessments' / (new_id + '.json')
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'differs_from_exact_sources'):
            load(self.node, new_id, self.settings)
        value['official_acceptance'] = True
        with self.assertRaisesRegex(ValueError, 'invalid_supplement_wrapper'):
            validate(value)

    def test_wrong_dependency_domain_is_rejected_before_recursing(self):
        receipt = self.call('assurance')
        with self.assertRaisesRegex(ValueError, 'exact_staging_source_required'):
            self.call('consolidate', '--staging', receipt['supplement_id'])

    def test_symlink_nested_member_duplicate_json_and_oversize_are_rejected(self):
        extra = self.bundle / 'linked.log'
        extra.symlink_to(self.bundle / 'checks.txt')
        with self.assertRaisesRegex(ValueError, 'unsafe_supplement_source'):
            self.staging()
        extra.unlink()
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, 'nonregular'):
            self.staging()
        extra.rmdir()
        with extra.open('wb') as handle:
            handle.truncate(16 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, 'oversize'):
            self.staging()
        extra.unlink()
        (self.bundle / 'deployment-approval.json').write_text('{"decision":1,"decision":2}')
        self.reseal_bundle()
        with self.assertRaisesRegex(ValueError, 'duplicate_measured_json_key'):
            self.staging()

    def test_explicit_timezone_and_typed_byte_binding_are_required(self):
        self.at = '2026-09-16T11:00:00'
        with self.assertRaisesRegex(ValueError, 'timezone_required'):
            self.call('assurance')
        self.at = self.input['at']
        typed = self.base / 'typed.json'
        typed.write_text('{"schema_version":1,"snapshots":[]}')
        with self.assertRaisesRegex(ValueError, 'digest_changed'):
            self.call('assurance', '--typed-bundle', str(typed), '--sha256', '0' * 64)
        sha = hashlib.sha256(typed.read_bytes()).hexdigest()
        receipt = self.call('assurance', '--typed-bundle', str(typed), '--sha256', sha)
        value = load(self.node, receipt['supplement_id'], self.settings)
        self.assertEqual(value['inputs']['typed_bundle_sha256'], sha)

    def test_duplicate_typed_sources_do_not_fill_control_gaps(self):
        # A complete source report remains insufficient for missing control scope.
        typed = []
        for path in sorted((ROOT / 'status/typed-evidence-results/joku-dev__ha-CPsWMS').glob('*35241262722*.json')):
            value = json.loads(path.read_text())
            value['pipeline'].update(pipeline_run_id=self.measured['run']['id'], run_attempt=self.measured['run']['attempt'])
            value['repository']['commit_id'] = self.measured['run']['commit']
            typed.append({'snapshot': value, 'source_file': path.relative_to(ROOT).as_posix()})
        self.assertEqual(len(typed), 2)
        target = self.base / 'typed.json'
        target.write_text(json.dumps({'schema_version': 1, 'snapshots': typed}))
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        receipt = self.call('assurance', '--typed-bundle', str(target), '--sha256', sha)
        result = load(self.node, receipt['supplement_id'], self.settings)
        controls = {row['control_id']: row for row in result['report']['controls']}
        self.assertEqual(controls['DSCB-L1-REQ-001']['effective_level'], 'unverified')
        self.assertEqual(result['evidence_trust'], 'unverified')
        target.write_text(json.dumps({'schema_version': 1, 'snapshots': [*typed, typed[0]]}))
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Ambiguous typed evidence'):
            self.call('assurance', '--typed-bundle', str(target), '--sha256', sha)

    def test_stored_receipt_must_fit_its_bounded_reader(self):
        receipt = self.call('assurance')
        value = load(self.node, receipt['supplement_id'], self.settings)
        with patch('lib.supplement_application.MAX_FILE', 100):
            with self.assertRaisesRegex(ValueError, 'oversize_supplement_receipt'):
                validate(value)


if __name__ == '__main__':
    unittest.main()
