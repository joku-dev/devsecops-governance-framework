"""Independent frozen typed wire reports, archive integrity and private ledger."""
import base64
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.consumer_intake_store import atomic_json
from lib.providers.typed_capture import verify
from lib.providers.typed_capture import capture, download, copy_bundle
from lib.providers.transports import Reader
from lib.typed_evidence_application import run as typed_run
from lib.typed_result_ledger import TypedLedger


class TypedIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/typed-container-cases.json').read_text())
        self.bundle = self.base / 'bundle'
        self.bundle.mkdir(mode=0o700)
        (self.bundle / 'archives').mkdir(mode=0o700)
        self.manifest = deepcopy(self.fixture['manifest'])
        for name, raw in self.fixture['archive_bytes_base64'].items():
            (self.bundle / 'archives' / (name + '.zip')).write_bytes(base64.b64decode(raw, validate=True))
        self.seal()
        self.at = self.fixture['at']

    def seal(self):
        atomic_json(self.bundle / 'capture.json', self.manifest)
        self.sha = hashlib.sha256((self.bundle / 'capture.json').read_bytes()).hexdigest()

    def verified(self):
        return verify(self.bundle, self.sha, self.at)

    def ledger(self, name='ledger'):
        ledger = TypedLedger(self.base / name)
        self.addCleanup(ledger.close)
        return ledger

    def test_full_independently_executed_frozen_v1_reports_match(self):
        self.assertTrue(self.fixture['synthetic'])
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        result = self.verified()
        self.assertEqual(result['snapshots'], self.fixture['expected_initial_snapshots'])
        self.assertEqual(result['measured_containers'], self.fixture['expected_measured_containers'])
        self.assertEqual(result['verified_archive_bytes'], sum(row['bytes'] for row in self.manifest['archives'].values()))
        self.assertGreater(result['verified_material_bytes'], 5 * 10240)

    def test_explicit_budget_covers_combined_legal_v1_archive_limits(self):
        # The combined upper bounds exceed 16 GiB. This exercises admission with
        # the complete small fixture; it neither allocates nor reserves 32 GiB.
        result = verify(self.bundle, self.sha, self.at, budget=32 * 1024**3)
        self.assertEqual(result['snapshots'], self.fixture['expected_initial_snapshots'])
        copied = self.base / 'higher-budget-copy'
        copy_bundle(self.bundle, self.sha, copied, budget=32 * 1024**3)
        self.assertEqual(verify(copied, self.sha, self.at, budget=32 * 1024**3), result)
        with self.assertRaises(ValueError): verify(self.bundle, self.sha, self.at, budget=32 * 1024**3 + 1)

    def test_complete_v1_replay_reports_preserved_but_operator_effective_trust_unverified(self):
        result = self.verified()
        ledger = self.ledger()
        receipt = ledger.admit(result['repository'], result['snapshots'], origin='operator_bundle',
            assessment_id='1' * 64, at=self.at)
        self.assertFalse(receipt['official_acceptance'])
        self.assertTrue(all(row['effective_trust'] == 'unverified' for row in receipt['results'].values()))
        for row in ledger.projection()['records']:
            self.assertEqual(row['payload'], self.fixture['expected_replay_snapshots'][row['evidence_type']])
            self.assertEqual(row['effective_trust'], 'unverified')

    def test_idempotent_retry_keeps_first_time_trust_and_receipt(self):
        result = self.verified()
        ledger = self.ledger()
        first = ledger.admit(result['repository'], result['snapshots'], origin='native_reader',
            assessment_id='1' * 64, at=self.at)
        before = ledger.projection()
        later = deepcopy(result['snapshots'])
        for row in later.values():
            row['trust']['verified_at'] = '2026-09-17T10:07:00Z'
        second = ledger.admit(result['repository'], later, origin='native_reader',
            assessment_id='2' * 64, at='2026-09-17T10:07:00Z')
        self.assertTrue(all(row['status'] == 'recorded' for row in first['results'].values()))
        self.assertTrue(all(row['status'] == 'idempotent' for row in second['results'].values()))
        self.assertEqual(before, ledger.projection())

    def test_operator_bundle_cannot_preempt_native_history(self):
        result = self.verified()
        ledger = self.ledger()
        for origin in ('operator_bundle', 'native_reader'):
            receipt = ledger.admit(result['repository'], result['snapshots'], origin=origin,
                assessment_id='1' * 64, at=self.at)
            self.assertTrue(all(row['status'] == 'recorded' for row in receipt['results'].values()))
        projection = ledger.projection()
        self.assertEqual(projection['record_count'], 4)
        self.assertEqual({row['origin'] for row in projection['latest']}, {'operator_bundle', 'native_reader'})
        self.assertTrue(all(row['effective_trust'] == 'provenance_verified' for row in projection['records']
                            if row['origin'] == 'native_reader'))

    def test_resealed_same_identity_content_change_is_quarantined(self):
        result = self.verified()
        ledger = self.ledger()
        ledger.admit(result['repository'], result['snapshots'], origin='operator_bundle', assessment_id='1' * 64, at=self.at)
        before = ledger.projection()['records']
        changed = deepcopy(result['snapshots'])
        changed['sbom']['trust']['capture']['subjects'][0]['digest'] = 'a' * 64
        receipt = ledger.admit(result['repository'], changed, origin='operator_bundle', assessment_id='2' * 64, at=self.at)
        self.assertEqual(receipt['results']['sbom']['status'], 'conflict')
        self.assertEqual(receipt['results']['vulnerability_scan']['status'], 'idempotent')
        self.assertEqual(ledger.projection()['conflict_count'], 1)
        self.assertEqual(before, ledger.projection()['records'])

    def test_failed_batch_rolls_back_all_records(self):
        result = self.verified()
        ledger = self.ledger()
        with patch('lib.typed_result_ledger.promote_effective_level', side_effect=['integrity_verified', ValueError('injected')]):
            with self.assertRaisesRegex(ValueError, 'injected'):
                ledger.admit(result['repository'], result['snapshots'], origin='operator_bundle',
                    assessment_id='1' * 64, at=self.at)
        self.assertEqual(ledger.projection()['record_count'], 0)
        self.assertEqual(ledger.db.execute('SELECT count(*) FROM repositories').fetchone()[0], 0)

    def test_native_identity_and_realm_boundaries_do_not_collapse_display_paths(self):
        result = self.verified()
        ledger = self.ledger()
        ledger.admit(result['repository'], result['snapshots'], origin='native_reader', assessment_id='1' * 64, at=self.at)
        another = {**result['repository'], 'native_id': '10'}
        receipt = ledger.admit(another, result['snapshots'], origin='native_reader', assessment_id='2' * 64, at=self.at)
        self.assertTrue(all(row['status'] == 'recorded' and row['effective_trust'] == 'integrity_verified'
                            for row in receipt['results'].values()))
        isolated = {**another, 'instance': 'https://isolated.example.test'}
        third = ledger.admit(isolated, result['snapshots'], origin='native_reader', assessment_id='3' * 64, at=self.at)
        self.assertTrue(all(row['effective_trust'] == 'provenance_verified' for row in third['results'].values()))
        self.assertEqual(ledger.projection()['record_count'], 6)
        self.assertEqual(len({row['repository_key'] for row in ledger.projection()['records']}), 3)

    def test_archive_bytes_wrong_run_and_duplicate_json_fail_closed(self):
        archive = self.bundle / 'archives/coverage.zip'
        original = archive.read_bytes()
        archive.write_bytes(original + b'x')
        with self.assertRaisesRegex(ValueError, 'bytes_changed'):
            self.verified()
        archive.write_bytes(original)
        self.manifest['run']['head_branch'] = 'feature'
        self.seal()
        with self.assertRaisesRegex(ValueError, 'successful main'):
            self.verified()
        self.manifest['run']['head_branch'] = 'main'
        self.seal()
        path = self.bundle / 'capture.json'
        raw = path.read_text()
        path.write_text('{"schema_version":2,' + raw[1:])
        self.sha = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'duplicate_measured_json_key'):
            self.verified()

    def test_storage_budgets_and_unsafe_archive_source_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'storage_budget_exhausted'):
            verify(self.bundle, self.sha, self.at, budget=1)
        with patch('lib.providers.typed_capture.shutil.disk_usage') as usage:
            usage.return_value.free = 8 * 1024**3
            with self.assertRaisesRegex(ValueError, 'reserve_exhausted'):
                self.verified()
        path = self.bundle / 'archives/coverage.zip'
        real = self.base / 'coverage.zip'
        path.rename(real)
        path.symlink_to(real)
        with self.assertRaisesRegex(ValueError, 'unsafe_bundle_member'):
            self.verified()

    def test_existing_foreign_database_and_tampered_payload_are_rejected(self):
        path = self.base / 'foreign'
        path.mkdir(mode=0o700)
        database = sqlite3.connect(path / 'typed.sqlite3')
        database.execute('CREATE TABLE foreign_state (value TEXT)')
        database.commit();database.close()
        with self.assertRaisesRegex(ValueError, 'incompatible_typed_ledger_schema'):
            TypedLedger(path)
        result = self.verified()
        ledger = self.ledger()
        ledger.admit(result['repository'], result['snapshots'], origin='operator_bundle', assessment_id='1' * 64, at=self.at)
        ledger.db.execute("UPDATE records SET payload='{}'")
        ledger.db.commit()
        with self.assertRaisesRegex(ValueError, 'payload_changed'):
            ledger.projection()

    def test_native_capture_rechecks_metadata_and_uses_system_verification_clock(self):
        case = self
        artifacts = [row['artifact'] for row in self.manifest['archives'].values()]
        class NativeReader:
            calls = 0
            budget = 100
            def get(self, route):
                self.calls += 1
                if '/artifacts?' in route:
                    return {'total_count': len(artifacts), 'artifacts': deepcopy(artifacts)}
                return deepcopy(case.manifest['run'])
        def acquired(reader, repository, artifact, destination, **limits):
            row = next(value for value in self.manifest['archives'].values() if value['artifact']['id'] == artifact['id'])
            destination.write_bytes((self.bundle / row['path']).read_bytes())
            return {key: row[key] for key in ('sha256', 'bytes')}
        destination = self.base / 'native'
        with patch('lib.providers.typed_capture.credential_reader', return_value=NativeReader()), \
             patch('lib.providers.typed_capture.download', side_effect=acquired), \
             patch('lib.providers.typed_capture.verification_clock', return_value=self.at):
            result, sha, proof = capture('joku-dev/ha-CPsWMS', '123', self.base / 'unused.json', destination)
        self.assertEqual(result['snapshots'], self.fixture['expected_initial_snapshots'])
        self.assertEqual(proof['verified_at'], self.at)
        self.assertTrue(proof['native_metadata_rechecked'])
        self.assertEqual(proof['requests'], 3)
        self.assertEqual(verify(destination, sha, self.at), result)

    def test_failed_native_run_is_rejected_before_artifact_reads_or_directory_creation(self):
        run = deepcopy(self.manifest['run'])
        run.update(head_branch='diagnostic', conclusion='failure')
        class NativeReader:
            def get(self, route):
                if '/artifacts?' in route:
                    raise AssertionError('Failed run must not acquire artifacts')
                return run
        destination = self.base / 'failed-native'
        with patch('lib.providers.typed_capture.credential_reader', return_value=NativeReader()), \
             patch('lib.providers.typed_capture.download') as acquired:
            with self.assertRaisesRegex(ValueError, 'successful main'):
                capture('joku-dev/ha-CPsWMS', '123', self.base / 'unused.json', destination)
            acquired.assert_not_called()
        self.assertFalse(destination.exists())

    def test_whole_archive_download_strips_native_authorization(self):
        requests = []
        raw = b'synthetic downloaded archive bytes'
        class Response:
            status = 200
            headers = {'Content-Length': str(len(raw))}
            def __init__(self):
                self.data = io.BytesIO(raw)
            def __enter__(self):return self
            def __exit__(self, *args):pass
            def read(self, size):return self.data.read(size)
        class Opener:
            def open(self, request, **options):
                requests.append(request)
                if len(requests) == 1:
                    raise HTTPError(request.full_url, 302, 'redirect',
                        {'Location': 'https://synthetic.blob.core.windows.net/zip?sig=synthetic'}, None)
                return Response()
        reader = Reader('https://api.github.com', 'synthetic-only', budget=10)
        with patch('lib.providers.typed_capture.build_opener', return_value=Opener()):
            receipt = download(reader, 'joku-dev/ha-CPsWMS', {'id': 1, 'size_in_bytes': len(raw)},
                self.base / 'download.zip', reserve=8 * 1024**3)
        self.assertEqual(receipt['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(requests[0].has_header('Authorization'))
        self.assertFalse(requests[1].has_header('Authorization'))
        self.assertEqual(reader.calls, 2)


class TypedApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/typed-container-cases.json').read_text())
        self.bundle = self.base / 'bundle'
        self.bundle.mkdir(mode=0o700)
        (self.bundle / 'archives').mkdir(mode=0o700)
        for name, raw in self.fixture['archive_bytes_base64'].items():
            (self.bundle / 'archives' / (name + '.zip')).write_bytes(base64.b64decode(raw))
        atomic_json(self.bundle / 'capture.json', self.fixture['manifest'])
        self.sha = hashlib.sha256((self.bundle / 'capture.json').read_bytes()).hexdigest()
        self.node = self.base / 'node'
        self.node.mkdir(mode=0o700)
        for name in ('state', 'credentials'):
            (self.node / name).mkdir(mode=0o700)
        self.settings = {'node_id': '1' * 32}

    def call(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(typed_run(list(arguments), self.node, self.settings), 0)
        return json.loads(output.getvalue())

    def local(self):
        return self.call('verify-local', '--provider', 'github-actions', '--bundle', str(self.bundle),
                         '--sha256', self.sha, '--at', self.fixture['at'])

    def test_explicit_higher_quota_is_schema_bound_and_replayable(self):
        receipt = self.call('verify-local', '--provider', 'github-actions', '--bundle', str(self.bundle),
            '--sha256', self.sha, '--at', self.fixture['at'], '--storage-budget-bytes', str(32 * 1024**3))
        assessment = self.call('inspect', '--id', receipt['assessment_id'])['assessment']
        self.assertEqual(assessment['storage_budget_bytes'], 32 * 1024**3)
        self.assertEqual(assessment['verification']['snapshots'], self.fixture['expected_initial_snapshots'])
        self.assertFalse(assessment['official_acceptance'])

    def test_full_local_flow_uses_private_snapshot_and_explicit_intake(self):
        receipt = self.local()
        self.assertFalse(receipt['official_acceptance'])
        import shutil
        shutil.rmtree(self.bundle)
        inspected = self.call('inspect', '--id', receipt['assessment_id'])
        self.assertFalse(inspected['native_metadata_rechecked_now'])
        self.assertTrue(inspected['bytes_reverified_now'])
        value = inspected['assessment']
        self.assertEqual(value['verification']['snapshots'], self.fixture['expected_initial_snapshots'])
        self.assertEqual(value['evidence_trust'], 'unverified')
        self.assertEqual(self.call('index')['record_count'], 0)
        admitted = self.call('intake', '--id', receipt['assessment_id'])
        self.assertTrue(all(row['effective_trust'] == 'unverified' for row in admitted['results'].values()))
        first = self.call('index', '--limit', '1')
        second = self.call('index', '--limit', '1', '--offset', '1')
        self.assertEqual(first['record_count'], 2)
        self.assertNotEqual(first['records'][0]['identity'], second['records'][0]['identity'])
        self.assertTrue(all(row['status'] == 'idempotent' for row in
            self.call('intake', '--id', receipt['assessment_id'])['results'].values()))

    def test_native_receipt_does_not_promote_its_operator_replay(self):
        def native(provider, repository, run_id, credential, destination, *, requests, budget):
            self.assertEqual(credential, self.node / 'credentials/reader.json')
            copy_bundle(self.bundle, self.sha, destination, budget=budget)
            return verify(destination, self.sha, self.fixture['at'], budget=budget), self.sha, {
                'native_metadata_rechecked': True, 'requests': 3, 'whole_archives_downloaded': True,
                'baseline_lookup': 'same_run_reference', 'verified_at': self.fixture['at']}
        with patch('lib.typed_evidence_application.typed_capture_live', side_effect=native):
            receipt = self.call('capture', '--provider', 'github-actions', '--repository', 'joku-dev/ha-CPsWMS',
                '--run-id', '123', '--credential', 'reader.json')
        admitted = self.call('intake', '--id', receipt['assessment_id'])
        self.assertTrue(all(row['effective_trust'] == 'provenance_verified' for row in admitted['results'].values()))
        local = self.local()
        replay = self.call('intake', '--id', local['assessment_id'])
        self.assertTrue(all(row['effective_trust'] == 'unverified' for row in replay['results'].values()))
        self.assertEqual(self.call('index')['record_count'], 4)

    def test_resealed_report_raw_tamper_and_foreign_node_are_rejected(self):
        receipt = self.local()
        root = self.node / 'state/typed'
        path = root / 'assessments' / (receipt['assessment_id'] + '.json')
        value = json.loads(path.read_text())
        self.settings = {'node_id': '2' * 32}
        with self.assertRaisesRegex(ValueError, 'node_runtime_or_source_changed'):
            self.call('inspect', '--id', receipt['assessment_id'])
        self.settings = {'node_id': '1' * 32}
        value['verification']['snapshots']['sbom']['trust']['effective_level'] = 'attested'
        from lib.portable.contracts import canonical_digest
        forged = canonical_digest(value)
        atomic_json(root / 'assessments' / (forged + '.json'), value)
        with self.assertRaisesRegex(ValueError, 'differs_from_exact_sources'):
            self.call('intake', '--id', forged)
        archive = root / 'raw' / self.sha / 'archives/coverage.zip'
        archive.write_bytes(archive.read_bytes() + b'x')
        with self.assertRaisesRegex(ValueError, 'bytes_changed'):
            self.call('inspect', '--id', receipt['assessment_id'])

    def test_credential_path_and_approval_forgery_fail_closed(self):
        with patch('lib.typed_evidence_application.typed_capture_live') as native:
            with self.assertRaisesRegex(ValueError, 'credential_name'):
                self.call('capture', '--provider', 'github-actions', '--repository', 'joku-dev/ha-CPsWMS',
                    '--run-id', '123', '--credential', '../outside.json')
            native.assert_not_called()
        receipt = self.local()
        root = self.node / 'state/typed'
        value = json.loads((root / 'assessments' / (receipt['assessment_id'] + '.json')).read_text())
        value['official_acceptance'] = True
        from lib.portable.contracts import canonical_digest
        forged = canonical_digest(value)
        atomic_json(root / 'assessments' / (forged + '.json'), value)
        with self.assertRaisesRegex(ValueError, 'invalid_typed_assessment_wrapper'):
            self.call('inspect', '--id', forged)


if __name__ == '__main__':
    unittest.main()
