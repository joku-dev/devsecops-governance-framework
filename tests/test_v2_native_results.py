"""Frozen native wire parity and bounded synthetic native capture/replay."""
import base64
from contextlib import redirect_stdout, closing
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.ci_bundle_storage import hash_file, DEFAULT_BUDGET
from lib.consumer_intake_store import atomic_json
from lib.native_result_assessments import NativeResultContext
from lib.portable.contracts import canonical_digest
from lib.provider_errors import AccessFailure
from lib.providers import general_results as native
from lib.result_application import run
from lib.result_assessments import ResultContext
from lib.result_index_application import persist, inspect, realm_key
from lib.result_snapshot_store import ResultLedger


class NativeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/native-result-cases.json').read_text())
        assert cls.fixture['synthetic']
        assert cls.fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.instance = self.base / 'node'; self.instance.mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-native-result-node'}
        self.case = deepcopy(self.fixture['cases'][0])

    def bundle(self, case=None, path=None):
        case = case or self.case; path = path or self.base / 'capture'
        path.mkdir(mode=0o700)
        archive = path / 'artifact.zip'; archive.write_bytes(base64.b64decode(case['zip_base64'])); archive.chmod(0o600)
        manifest = {'schema_version': 1, 'kind': 'native-general-result-capture', 'provider': native.PROVIDER,
            'repository_id': 'synthetic/native', 'domain': case['domain'], 'parameters': case['parameters'],
            'run': case['run'], 'jobs': case['jobs'], 'artifacts': [case['artifact']],
            'branch_protected': case['branch_protected'], 'branch_protection_lookup': case['branch_protection_lookup'],
            'archives': {'primary': {**hash_file(archive, 1024**3), 'path': 'artifact.zip', 'artifact': case['artifact']}},
            'verified_at': case['at']}
        if 'companion' in case:
            companion = case['companion']; archive = path / 'governance-run-input.zip'
            archive.write_bytes(base64.b64decode(companion['zip_base64'])); archive.chmod(0o600)
            manifest['artifacts'].append(companion['artifact'])
            manifest['archives']['companion'] = {**hash_file(archive, 1024**3),
                'path': 'governance-run-input.zip', 'artifact': companion['artifact']}
        return path, manifest, self.seal(path, manifest)

    def seal(self, path, manifest):
        atomic_json(path / 'capture.json', manifest)
        return hash_file(path / 'capture.json', native.MAX_MANIFEST)['sha256']

    def fake_reader(self, case=None, *, changed=False, protection_error=None, duplicate=False):
        case = deepcopy(case or self.case)
        class FakeReader:
            calls = 0
            budget = 100
            def get(self, path):
                self.calls += 1
                if '/branches/' in path:
                    if protection_error: raise protection_error
                    if case['branch_protected'] is None: raise AccessFailure('http_403')
                    return {'protected': case['branch_protected']}
                value = deepcopy(case['run'])
                if changed and self.calls > 1: value['updated_at'] = '2026-11-15T11:56:00Z'
                return value
            def pages(self, path, field, limit):
                self.calls += 1
                rows = deepcopy(case['jobs'] if field == 'jobs' else [case['artifact']])
                if field == 'artifacts' and 'companion' in case: rows.append(deepcopy(case['companion']['artifact']))
                if duplicate: rows += rows
                yield from rows
        return FakeReader()

    def capture_patches(self, case=None, **options):
        case = case or self.case
        reader = self.fake_reader(case, **options)
        def download(_, repository, artifact, path, **kwargs):
            self.assertEqual(repository, 'synthetic/native')
            source = case['companion'] if 'companion' in case and artifact == case['companion']['artifact'] else case
            self.assertEqual(artifact, source['artifact'])
            path.write_bytes(base64.b64decode(source['zip_base64'])); path.chmod(0o600)
            return hash_file(path, 1024**3)
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(native, 'credential_reader', return_value=reader))
        stack.enter_context(patch.object(native, 'download', side_effect=download))
        stack.enter_context(patch.object(native, 'verification_clock', return_value=case['at']))
        return stack

    def create(self, case=None):
        case = case or self.case
        with self.capture_patches(case):
            return NativeResultContext(self.instance, self.settings).create_native(native.PROVIDER,
                'synthetic/native', str(case['run']['id']), 1, self.base / 'unused-synthetic-credential',
                domain=case['domain'], options=case['parameters'])

    def test_complete_both_domain_reports_and_trust_equal_independent_frozen_v1(self):
        for case in self.fixture['cases']:
            with self.subTest(case=case['id']):
                path, _, sha = self.bundle(case, self.base / case['id'])
                actual = native.verify(path, sha, budget=DEFAULT_BUDGET)
                self.assertEqual(actual['snapshots'][case['domain']], case['expected_snapshot'])
                self.assertEqual(actual['repository']['native_id'], '42')

    def test_physical_digest_mismatch_and_nullable_protection_remain_visible(self):
        case = self.fixture['cases'][1]; path, _, sha = self.bundle(case)
        result = native.verify(path, sha, budget=DEFAULT_BUDGET)['snapshots']['devsecops']
        self.assertFalse(result['evidence']['artifact_digest'])
        self.assertIsNone(result['repository']['branch_protected'])
        self.assertEqual(result['repository']['branch_protection_lookup']['http_status'], 403)
        self.assertEqual(result['overall_status'], 'fail')

    def test_capture_requires_stable_attempt_metadata_and_binds_exact_original_archives(self):
        assessment_id, value = self.create()
        self.assertEqual(value['input_origin'], 'native_reader')
        self.assertEqual(value['snapshots']['devsecops'], self.case['expected_snapshot'])
        self.assertTrue(value['capture']['native_metadata_rechecked'])
        self.assertFalse(value['official_acceptance'])
        self.assertFalse(value['authority_transferred'])
        self.assertEqual(NativeResultContext(self.instance, self.settings).load(assessment_id), value)

    def test_native_capture_preserves_findings_and_companion_source_identity(self):
        for case in self.fixture['cases'][1:]:
            with self.subTest(case=case['id']):
                assessment_id, value = self.create(case)
                self.assertEqual(value['snapshots'][case['domain']], case['expected_snapshot'])
                self.assertEqual(NativeResultContext(self.instance, self.settings).load(assessment_id), value)
                if 'companion' in case:
                    subjects = value['snapshots']['devsecops']['trust']['capture']['subjects']
                    self.assertNotIn('governance_run_input', {row['id'] for row in subjects})
                    self.assertEqual(value['snapshots']['devsecops']['downloaded_artifact']['governance_run_input_artifact']['artifact_id'], '9991')

    def test_quota_is_enforced_before_native_download_and_against_complete_retained_bytes(self):
        with self.capture_patches(), patch.object(native, 'download') as download:
            with self.assertRaisesRegex(ValueError, 'storage_budget_exhausted'):
                native.capture('synthetic/native', '8100', 1, self.base / 'unused', self.base / 'too-small',
                    domain='devsecops', options=self.case['parameters'], storage_budget=1)
            download.assert_not_called()
        path, _, sha = self.bundle()
        with self.assertRaisesRegex(ValueError, 'storage_budget_exhausted'):
            native.verify(path, sha, budget=self.case['artifact']['size_in_bytes'])

    def test_foreign_attempt_job_is_rejected_before_archive_acquisition(self):
        case = deepcopy(self.case); case['jobs'][0]['run_attempt'] = 2
        with self.capture_patches(case), patch.object(native, 'download') as download:
            with self.assertRaisesRegex(ValueError, 'job_binding_mismatch'):
                native.capture('synthetic/native', '8100', 1, self.base / 'unused', self.base / 'foreign-job',
                               domain='devsecops', options=case['parameters'])
            download.assert_not_called()

    def test_run_rerun_or_metadata_change_aborts_without_persisted_proof(self):
        context = NativeResultContext(self.instance, self.settings)
        with self.capture_patches(changed=True), self.assertRaisesRegex(ValueError, 'changed_during_capture'):
            context.create_native(native.PROVIDER, 'synthetic/native', '8100', 1, self.base / 'unused',
                                  domain='devsecops', options=self.case['parameters'])
        self.assertEqual(list(context.assessments.iterdir()), [])
        with self.assertRaisesRegex(ValueError, 'run_binding_mismatch'):
            native.check_run(self.case['run'], 'synthetic/native', '8100', 2)

    def test_foreign_run_repository_native_id_artifact_and_url_are_rejected(self):
        for mutate in ('repo', 'native_id', 'run', 'url', 'branch', 'size'):
            with self.subTest(mutate=mutate):
                artifact = deepcopy(self.case['artifact'])
                if mutate == 'repo': artifact['workflow_run']['head_sha'] = 'b'*40
                elif mutate == 'native_id': artifact['workflow_run']['repository_id'] = 99
                elif mutate == 'run': artifact['workflow_run']['id'] = 99
                elif mutate == 'url': artifact['archive_download_url'] = 'https://hostile.example/stolen'
                elif mutate == 'branch': artifact['workflow_run']['head_branch'] = 'other'
                else: artifact['size_in_bytes'] = 2*1024**3
                with self.assertRaisesRegex(ValueError, 'artifact_binding_mismatch'):
                    native.check_artifact(artifact, self.case['run'], 'synthetic/native')

    def test_duplicate_native_artifact_or_job_ids_are_rejected(self):
        with self.capture_patches(duplicate=True), self.assertRaisesRegex(ValueError, 'list_identity_ambiguous'):
            native.capture('synthetic/native', '8100', 1, self.base / 'unused', self.base / 'captured',
                           domain='devsecops', options=self.case['parameters'])

    def test_nullable_protection_http_failure_is_distinct_from_exhausted_budget(self):
        reader = self.fake_reader(protection_error=AccessFailure('http_403'))
        self.assertEqual(native.protection(reader, 'synthetic/native', 'main'),
                         (None, {'status': 'unavailable', 'http_status': 403}))
        reader = self.fake_reader(protection_error=AccessFailure('request_budget_exhausted'))
        with self.assertRaises(AccessFailure): native.protection(reader, 'synthetic/native', 'main')

    def test_private_credentials_require_exact_explicit_repository_and_endpoint(self):
        path = self.base / 'reader.json'
        value = {'schema_version': 1, 'provider': native.PROVIDER, 'instance': 'https://api.github.com',
                 'repository': 'synthetic/native', 'token': 'synthetic-unused-not-a-real-token'}
        atomic_json(path, value)
        reader = native.credential_reader(path, 'synthetic/native', 100)
        self.assertEqual(reader.budget, 100)
        for field, replacement in [('instance', 'https://hostile.example'), ('repository', 'other/native'),
                                   ('token', 'x\nmalformed')]:
            changed = {**value, field: replacement}; atomic_json(path, changed)
            with self.assertRaises(ValueError): native.credential_reader(path, 'synthetic/native', 100)
        atomic_json(path, value); path.chmod(0o644)
        with self.assertRaises(ValueError): native.credential_reader(path, 'synthetic/native', 100)

    def test_archive_corruption_or_unlisted_material_cannot_be_resealed(self):
        path, manifest, sha = self.bundle()
        (path / 'artifact.zip').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'archive_bytes_changed'):
            native.verify(path, sha, budget=DEFAULT_BUDGET)
        (path / 'artifact.zip').write_bytes(base64.b64decode(self.case['zip_base64']))
        (path / 'unlisted.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'undeclared_native_result_capture_file'):
            native.verify(path, sha, budget=DEFAULT_BUDGET)

    def test_native_raw_metadata_snapshot_and_foreign_node_tampering_fail_closed(self):
        assessment_id, value = self.create(); context = NativeResultContext(self.instance, self.settings)
        changed = deepcopy(value); changed['snapshots']['devsecops']['overall_status'] = 'fail'
        fake_id = canonical_digest(changed); atomic_json(context.assessments / (fake_id + '.json'), changed)
        with self.assertRaisesRegex(ValueError, 'differs_from_exact_sources'): context.load(fake_id)
        with self.assertRaisesRegex(ValueError, 'node_runtime_or_source_changed'):
            NativeResultContext(self.instance, {'node_id': 'foreign'}).load(assessment_id)
        (context.raw / value['input_id'] / 'capture.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'manifest_changed'):
            NativeResultContext(self.instance, self.settings).load(assessment_id)

    def test_record_budget_counts_the_actual_persisted_serialization(self):
        _, value = self.create(); context = NativeResultContext(self.instance, self.settings)
        compact_size = len(json.dumps(value, sort_keys=True).encode())
        with patch('lib.native_result_assessments.MAX_ASSESSMENT', compact_size + 1):
            with self.assertRaisesRegex(ValueError, 'assessment_record_limit'): context.validate(value)

    def test_native_indices_verify_private_proof_and_keep_effective_trust(self):
        assessment_id, value = self.create()
        context = ResultContext(self.instance, self.settings)
        with closing(ResultLedger(context.root / 'ledger')) as ledger:
            ledger.admit(value['repository'], value['snapshots'], origin='native_reader',
                         assessment_id=assessment_id, at=value['assessed_at'])
        projection_id, projection = persist(context, self.settings, domain='devsecops', origin='native_reader',
            realm=realm_key('github', 'https://api.github.com'), at=self.case['at'], profile='legacy-v1', main_branch='main')
        self.assertEqual(projection['reported_index'], projection['effective_index'])
        self.assertEqual(len(projection['reported_index']['repositories']), 1)
        self.assertEqual(inspect(context, self.settings, projection_id), projection)
        self.assertFalse(projection['official_acceptance'])

    def test_cli_capture_inspect_and_intake_are_separate_and_sanitized(self):
        output = io.StringIO()
        with self.capture_patches(), redirect_stdout(output):
            code = run(['capture-native', '--provider', native.PROVIDER, '--repository', 'synthetic/native',
                '--run-id', '8100', '--attempt', '1', '--credential-file', str(self.base / 'unused'),
                '--domain', 'devsecops', '--artifact-name', self.case['parameters']['artifact_name'],
                '--baseline-ref', self.case['parameters']['baseline_ref'], '--governance-repository',
                self.case['parameters']['governance_repository']], self.instance, self.settings)
        self.assertEqual(code, 0); assessment_id = json.loads(output.getvalue())['assessment_id']
        for command in ('inspect-native', 'intake-native'):
            with redirect_stdout(io.StringIO()): self.assertEqual(run([command, '--id', assessment_id], self.instance, self.settings), 0)
        with self.assertRaises(FileNotFoundError): ResultContext(self.instance, self.settings).load(assessment_id)


if __name__ == '__main__': unittest.main()
