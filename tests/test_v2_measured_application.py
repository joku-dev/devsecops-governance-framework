"""Full V1 wire/decision parity and private acquisition boundaries; synthetic data."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_measured_l1 as v1_fixture
from lib.providers.measured_capture import export_bundle, import_bundle, capture, credential_reader, RemoteZip, selected_files
from lib.providers.measured_l1 import normalize as native_l1
from lib.providers.measured_security import normalize as native_security
from lib.measured_application import run, validate


class MeasuredApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.fixture = v1_fixture.MeasuredL1Tests()
        self.fixture.setUp()
        f = self.fixture
        self.captured = (f.run, json.dumps(f.report).encode(), f.report_artifact, f.bundles, json.dumps(f.trace).encode())
        self.node = self.base / 'node'
        self.node.mkdir(mode=0o700)
        for name in ('state', 'credentials'):
            (self.node / name).mkdir(mode=0o700)

    def bundle(self, kind='l1'):
        target = self.base / ('bundle-' + kind)
        return target, export_bundle(self.captured, target, kind)

    def call(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run(list(arguments), self.node), 0)
        return json.loads(output.getvalue())

    def test_full_l1_and_container_results_match_original_v1(self):
        expected = self.fixture.normalized()
        self.assertEqual(native_l1(*self.captured), expected)
        root, sha = self.bundle()
        self.assertEqual(import_bundle(root, sha, 'l1'), expected)
        root, sha = self.bundle('containers')
        security = native_security(self.fixture.run, self.fixture.report,
            {s: self.fixture.bundles['image-' + s] for s in self.fixture.images})
        self.assertEqual(import_bundle(root, sha, 'containers'), security)
        self.assertEqual(len(expected['controls']), 16)
        self.assertEqual(expected['summary'], {'measured': 7, 'partial': 4, 'findings': 2, 'gap': 3})

    def test_independent_frozen_v1_raw_groups_and_full_reports_match(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/measured-native-cases.json').read_text())
        self.assertTrue(fixture['synthetic'])
        self.assertEqual(fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        value = fixture['input']
        captured = (value['run'], value['report'].encode(), value['report_artifact'],
                    {name: ({key: raw.encode() for key, raw in item['files'].items()}, item['artifact'])
                     for name, item in value['bundles'].items()}, value['traceability'].encode())
        self.assertEqual(native_l1(*captured), fixture['expected_l1'])
        for kind, expected in [('l1', fixture['expected_l1']), ('containers', fixture['expected_containers'])]:
            root = self.base / ('frozen-' + kind)
            sha = export_bundle(captured, root, kind)
            self.assertEqual(import_bundle(root, sha, kind), expected)

    def test_local_cli_preserves_gaps_without_native_or_human_authority(self):
        root, sha = self.bundle()
        receipt = self.call('verify-local', '--provider', 'github-actions', '--kind', 'l1',
                            '--bundle', str(root), '--sha256', sha, '--at', '2026-11-15T12:00:00Z')
        self.assertFalse(receipt['official_acceptance'])
        path = self.node / 'state/measured/assessments' / (receipt['assessment_id'] + '.json')
        value = json.loads(path.read_text())
        self.assertEqual(value['report'], self.fixture.normalized())
        self.assertEqual(value['input_origin'], 'operator_bundle')
        self.assertEqual(value['capture'], {'native_metadata_rechecked': False, 'independent_attestation': False})
        self.assertEqual(value['evidence_trust'], 'unverified')
        self.assertFalse(value['production_approval'])
        self.assertFalse(value['risk_acceptance'])
        self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(self.call('verify-local', '--provider', 'github-actions', '--kind', 'l1',
                            '--bundle', str(root), '--sha256', sha, '--at', '2026-11-15T12:00:00Z'), receipt)
        forged = deepcopy(value)
        forged['official_acceptance'] = True
        with self.assertRaisesRegex(ValueError, 'wrapper'):
            validate(forged)
        forged = deepcopy(value)
        forged['source_revision'] = 'f' * 40
        with self.assertRaisesRegex(ValueError, 'source_changed'):
            validate(forged)

    def test_tampered_file_wrong_manifest_and_symlink_fail_closed(self):
        root, sha = self.bundle()
        with self.assertRaisesRegex(ValueError, 'manifest_changed'):
            import_bundle(root, '0' * 64, 'l1')
        source = root / 'source/junit.xml'
        before = source.read_bytes()
        source.write_bytes(before + b' ')
        with self.assertRaisesRegex(ValueError, 'bytes_changed'):
            import_bundle(root, sha, 'l1')
        source.unlink()
        external = self.base / 'external.xml'
        external.write_bytes(before)
        source.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'unsafe_measured_bundle_file'):
            import_bundle(root, sha, 'l1')

    def test_resealed_wrong_run_and_image_bindings_are_rejected(self):
        f = self.fixture
        for mutation in ('branch', 'image', 'runtime', 'sbom'):
            candidate = deepcopy(self.captured)
            if mutation == 'branch':
                candidate[0]['head_branch'] = 'diagnostic-branch'
            else:
                bundles = candidate[3]
                group, filename = {'image': ('image-query-api', 'vulnerabilities.json'),
                                   'runtime': ('runtime', 'deployment.json'),
                                   'sbom': ('image-query-api', 'sbom.cyclonedx.json')}[mutation]
                payload = json.loads(bundles[group][0][filename])
                if mutation == 'image':payload['Metadata']['ImageID'] = 'sha256:' + 'f' * 64
                elif mutation == 'runtime':payload['containers'][0]['build_config_digest'] = 'sha256:' + 'f' * 64
                else:payload['metadata']['component']['properties'][0]['value'] = 'sha256:' + 'f' * 64
                raw = bundles[group][0]
                raw[filename] = json.dumps(payload).encode()
                manifest = json.loads(raw['manifest.json'])
                manifest['files'][filename] = {'sha256': hashlib.sha256(raw[filename]).hexdigest(), 'bytes': len(raw[filename])}
                raw['manifest.json'] = json.dumps(manifest).encode()
            root = self.base / ('bad-' + mutation)
            sha = export_bundle(candidate, root, 'l1')
            with self.assertRaises(ValueError, msg=mutation):
                import_bundle(root, sha, 'l1')

    def test_duplicate_json_and_entity_junit_are_not_evidence(self):
        candidate = deepcopy(self.captured)
        candidate = list(candidate)
        candidate[1] = b'{"context":{},"context":{}}'
        with self.assertRaisesRegex(ValueError, 'duplicate_measured_json_key'):
            native_l1(*candidate)
        f = self.fixture
        f.change('source', 'junit.xml', b'<!DOCTYPE xml [<!ENTITY bad "injected">]><testsuite/>')
        with self.assertRaisesRegex(ValueError, 'DTD/entity'):
            native_l1(*self.captured)

    def test_credential_must_match_provider_origin_repository_and_private_file(self):
        path = self.node / 'credentials/reader.json'
        credential = {'schema_version': 1, 'provider': 'github-actions', 'instance': 'https://api.github.com',
                      'repository': 'joku-dev/ha-CPsWMS', 'token': 'synthetic-test-reader'}
        path.write_text(json.dumps(credential));path.chmod(0o600)
        self.assertEqual(credential_reader(path, credential['repository'], 100).base, credential['instance'])
        credential['instance'] = 'https://wrong.example'
        path.write_text(json.dumps(credential))
        with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
            credential_reader(path, credential['repository'], 100)
        path.chmod(0o644)
        with self.assertRaises(ValueError):credential_reader(path, credential['repository'], 100)

    def test_live_capture_has_explicit_reader_and_exact_commit_content(self):
        fixture = self.fixture
        listing = [fixture.report_artifact, *(a for _, a in fixture.bundles.values())]
        trace = self.captured[4]
        blob = b'blob ' + str(len(trace)).encode() + b'\0' + trace
        import base64
        class Reader:
            calls = 0
            def get(self, path):
                self.calls += 1
                if '/contents/' in path:
                    return {'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(trace).decode(),
                            'sha': hashlib.sha1(blob, usedforsecurity=False).hexdigest()}
                if '/artifacts?' in path:return {'total_count': len(listing), 'artifacts': listing}
                return deepcopy(fixture.run)
        def selected(reader, repository, artifact, names, accounting):
            if artifact['name'] == 'l1-control-coverage':return {'l1-coverage.json': self.captured[1]}
            return {name: fixture.bundles[artifact['name'][3:]][0][name] for name in names}
        with patch('lib.providers.measured_capture.credential_reader', return_value=Reader()), \
             patch('lib.providers.measured_capture.selected_files', side_effect=selected):
            result, proof, raw = capture('joku-dev/ha-CPsWMS', 42, self.base / 'not-read.json')
        self.assertEqual(result, fixture.normalized())
        self.assertTrue(proof['native_metadata_rechecked'])
        self.assertFalse(proof['whole_archive_downloaded'])
        self.assertEqual(raw[4], trace)

    def test_live_capture_rejects_failed_branch_before_any_artifact_read(self):
        run = deepcopy(self.fixture.run)
        run.update(head_branch='test/axiom-v2-parity-reference', conclusion='failure')
        class Reader:
            def get(self, path):return run
        with patch('lib.providers.measured_capture.credential_reader', return_value=Reader()), \
             patch('lib.providers.measured_capture.selected_files') as selected:
            with self.assertRaisesRegex(ValueError, 'successful_main_run_required'):
                capture('joku-dev/ha-CPsWMS', 42, self.base / 'not-read.json')
            selected.assert_not_called()

    def test_capture_application_saves_replay_bytes_without_transferring_native_claim(self):
        proof = {'requests': 3, 'selected_transport_bytes': 0,
                 'native_metadata_rechecked': True, 'whole_archive_downloaded': False}
        with patch('lib.measured_application.measured_capture_live',
                   return_value=(self.fixture.normalized(), proof, self.captured)) as native:
            receipt = self.call('capture', '--provider', 'github-actions', '--kind', 'l1',
                '--repository', 'joku-dev/ha-CPsWMS', '--run-id', '42', '--credential', 'reader.json',
                '--at', '2026-11-15T12:00:00Z')
        self.assertEqual(native.call_args.args[3], self.node / 'credentials/reader.json')
        stored = self.node / 'state/measured/assessments' / (receipt['assessment_id'] + '.json')
        value = json.loads(stored.read_text())
        self.assertTrue(value['capture']['native_metadata_rechecked'])
        replay = self.call('verify-local', '--provider', 'github-actions', '--kind', 'l1',
            '--bundle', receipt['raw_bundle'], '--sha256', receipt['input_manifest_sha256'],
            '--at', '2026-11-15T12:00:00Z')
        replay_value = json.loads((self.node / 'state/measured/assessments' / (replay['assessment_id'] + '.json')).read_text())
        self.assertEqual(value['report'], replay_value['report'])
        self.assertFalse(replay_value['capture']['native_metadata_rechecked'])
        self.assertEqual(replay_value['evidence_trust'], 'unverified')

    def test_remote_storage_never_gets_native_authorization(self):
        class Reader:
            calls = 0
            budget = 10
        requests = []
        class Response:
            def __init__(self, request):
                self.request = request
                self.headers = {'Content-Length': '4'} if request.get_method() == 'HEAD' else {'Content-Range': 'bytes 0-3/4'}
                self.status = 200 if request.get_method() == 'HEAD' else 206
            def __enter__(self):return self
            def __exit__(self, *args):pass
            def read(self, size):return b'data'
        class Opener:
            def open(self, request, **options):
                requests.append(request)
                return Response(request)
        with patch('lib.providers.measured_capture.build_opener', return_value=Opener()):
            stream = RemoteZip(Reader(), 'https://synthetic.blob.core.windows.net/artifact?sig=synthetic', 4, {'bytes': 0})
            self.assertEqual(stream.read(4), b'data')
        self.assertTrue(all(not request.has_header('Authorization') for request in requests))
        with self.assertRaisesRegex(ValueError, 'storage_endpoint'):
            RemoteZip(Reader(), 'https://untrusted.example/artifact', 4, {'bytes': 0})

    def test_request_and_range_budgets_are_fail_closed(self):
        class Reader:
            calls = 1
            budget = 1
        with self.assertRaisesRegex(Exception, 'request_budget_exhausted'):
            RemoteZip(Reader(), 'https://synthetic.blob.core.windows.net/artifact', 4, {'bytes': 0})

    def test_authenticated_api_redirect_and_selected_zip_ranges(self):
        import zipfile
        from lib.providers.transports import Reader
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', '{"synthetic":true}')
        raw = stream.getvalue()
        requests = []
        signed = 'https://synthetic.blob.core.windows.net/artifact?sig=synthetic'
        class Response:
            def __init__(self, status, headers, content=b''):
                self.status, self.headers, self.content = status, headers, content
            def __enter__(self):return self
            def __exit__(self, *args):pass
            def read(self, limit):return self.content[:limit]
        class Opener:
            def open(self, request, **options):
                requests.append(request)
                if request.full_url.startswith('https://api.github.com/'):
                    raise HTTPError(request.full_url, 302, 'Found', {'Location': signed}, None)
                if request.get_method() == 'HEAD':
                    return Response(200, {'Content-Length': str(len(raw))})
                start, end = map(int, request.get_header('Range').removeprefix('bytes=').split('-'))
                return Response(206, {'Content-Range': f'bytes {start}-{end}/{len(raw)}'}, raw[start:end + 1])
        reader = Reader('https://api.github.com', 'synthetic-test-reader', budget=50)
        with patch('lib.providers.measured_capture.build_opener', return_value=Opener()):
            result = selected_files(reader, 'joku-dev/ha-CPsWMS', {'id': 42, 'size_in_bytes': len(raw)},
                                    ['manifest.json'], {'bytes': 0})
        self.assertEqual(result, {'manifest.json': b'{"synthetic":true}'})
        self.assertEqual(requests[0].get_header('Authorization'), 'Bearer synthetic-test-reader')
        self.assertTrue(all(not request.has_header('Authorization') for request in requests[1:]))
        self.assertEqual(reader.calls, len(requests))


if __name__ == '__main__':
    unittest.main()
