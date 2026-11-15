"""Private archives and controller input boundaries; no real host mutations."""
import copy
import contextlib
import io
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import vm_deployment as vm
import deploy_vm


class DeploymentArchives(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.schema = ROOT / 'schemas/governance-workbench-draft.schema.json'
        self.id = 'a' * 32
        self.raw = b'# Policy\nDSCB-L1-REQ-001: Review this declaration.\n'
        self.draft = {
            'schema_version': '1.0.0', 'draft_id': self.id, 'kind': 'source_candidate',
            'created_at': '2026-11-14T00:00:00Z', 'status': 'local_draft',
            'context': {'commit': 'f' * 40, 'register_sha256': 'c' * 64, 'sources': {}},
            'source': {'id': 'TEST-SRC-001', 'status': 'candidate', 'derived_artifact_areas': []},
            'original_filename': 'original.md', 'upload_name': 'source.md', 'sha256': vm.digest(self.raw),
            'warnings': [], 'lines': [], 'requirements': [], 'deltas': [], 'target': None,
            'notes': [{'subject': 'document', 'reviewer': 'Maintainer', 'outcome': 'needs_clarification',
                       'rationale': 'Keep this original note.', 'recorded_at': '2026-11-14', 'authority': 'proposal_only'}],
            'pr': None, 'limits': ['Proposal only.']}
        folder = self.root / 'source' / self.id
        folder.mkdir(parents=True)
        (folder / 'draft.json').write_text(json.dumps(self.draft))
        (folder / 'source.md').write_bytes(self.raw)

    def bundle(self):
        path = self.root / 'transfer.zip'
        vm.bundle_drafts(self.root / 'source', [self.id], path)
        return path

    def test_import_preserves_exact_metadata_uploads_and_permissions(self):
        # Unselected desktop state, credentials and publication worktrees never travel.
        (self.root / 'source' / 'desktop').mkdir()
        (self.root / 'source' / 'desktop' / 'secret').write_text('do not transfer')
        (self.root / 'source' / 'pr-' / 'worktree').mkdir(parents=True)
        bundle = self.bundle()
        self.assertEqual(len(vm.verify_archive(bundle)), 2)
        target = self.root / 'target'
        vm.import_drafts(bundle, target, self.schema)
        for name in ('draft.json', 'source.md'):
            self.assertEqual((target / self.id / name).read_bytes(), (self.root / 'source' / self.id / name).read_bytes())
            self.assertEqual((target / self.id / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual((target / self.id).stat().st_mode & 0o777, 0o700)

    def test_collision_rejects_whole_batch(self):
        bundle = self.bundle()
        target = self.root / 'target'
        (target / self.id).mkdir(parents=True)
        (target / self.id / 'keep').write_text('unchanged')
        with self.assertRaisesRegex(ValueError, 'collision'):
            vm.import_drafts(bundle, target, self.schema)
        self.assertEqual(list((target / self.id).iterdir()), [target / self.id / 'keep'])

    def test_tampered_upload_and_symlink_source_are_rejected(self):
        folder = self.root / 'source' / self.id
        (folder / 'source.md').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.bundle()
        (folder / 'source.md').unlink()
        (folder / 'source.md').symlink_to(self.root / 'secret')
        with self.assertRaises(ValueError):
            self.bundle()

    def test_schema_invalid_draft_is_not_installed(self):
        invalid = copy.deepcopy(self.draft)
        invalid['notes'][0]['authority'] = 'approved'
        bundle = self.root / 'invalid.zip'
        vm.write_archive(bundle, {f'drafts/{self.id}/draft.json': json.dumps(invalid).encode(),
                                 f'drafts/{self.id}/source.md': self.raw})
        with self.assertRaises(Exception):
            vm.import_drafts(bundle, self.root / 'target', self.schema)
        self.assertFalse((self.root / 'target' / self.id).exists())

    def test_unsafe_paths_and_duplicate_entries_are_rejected(self):
        for name in ('../escape', '/etc/axiom/key', 'state/../../escape', 'state\\escape'):
            path = self.root / 'unsafe.zip'
            path.unlink(missing_ok=True)
            with self.assertRaises(ValueError):
                vm.write_archive(path, {name: b'not extracted'})
            self.assertFalse((self.root / 'escape').exists())
        path = self.root / 'duplicate.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('manifest.json', '{}')
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                archive.writestr('manifest.json', '{}')
        with self.assertRaises(ValueError):
            vm.verify_archive(path)

    def test_backup_recovery_is_private_and_never_overwrites(self):
        state = self.root / 'source'
        environment = self.root / 'workbench.env'
        environment.write_text('AXIOM_WORKBENCH_KEY=private-test-value')
        archive = self.root / 'backup.zip'
        vm.backup(state, environment, self.root/'missing-receipt', self.root/'missing-unit', archive)
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            vm.backup(state, environment, self.root/'missing', self.root/'missing', archive)
        recovery = self.root / 'recovery'
        vm.restore_backup(archive, recovery)
        self.assertEqual((recovery/'config/workbench.env').read_bytes(), environment.read_bytes())
        self.assertEqual((recovery/'state'/self.id/'draft.json').read_bytes(), (state/self.id/'draft.json').read_bytes())
        with self.assertRaises(ValueError):
            vm.restore_backup(archive, recovery)

    def test_corrupt_archive_manifest_fails_verification(self):
        archive = self.root / 'corrupt.zip'
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('state/file', b'changed')
            stream.writestr('manifest.json', json.dumps({'state/file': {'sha256': '0'*64, 'size': 7}}))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            vm.verify_archive(archive)

    def test_oversized_private_file_is_rejected_before_reading(self):
        path = self.root/'oversized'
        with path.open('wb') as stream:
            stream.truncate(vm.MAX_ARCHIVE + 1)
        with self.assertRaisesRegex(ValueError, 'limit'):
            vm.regular_bytes(path)

    def test_partial_import_write_failure_removes_only_new_drafts(self):
        bundle = self.bundle()
        target = self.root / 'target'
        with patch.object(vm.os, 'rename', side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):
                vm.import_drafts(bundle, target, self.schema)
        self.assertEqual(list(target.iterdir()), [])


class ControllerBoundaries(unittest.TestCase):
    def test_unchanged_health_probe_preserves_existing_maintainer_session(self):
        import serve_governance_workbench as workbench
        key = 'private-smoke-test-key-long-enough'
        server = workbench.make_server(SimpleNamespace(state=lambda: {'healthy': True}), key, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
        host = '127.0.0.1:' + str(server.server_port)
        try:
            connection.request('POST', '/api/login', json.dumps({'key': key}),
                               {'Origin': 'http://'+host, 'Content-Type': 'application/json'})
            response = connection.getresponse()
            cookie = response.getheader('Set-Cookie').split(';')[0]
            response.read()
            with tempfile.TemporaryDirectory() as temporary:
                environment = Path(temporary)/'workbench.env'
                environment.write_text('AXIOM_WORKBENCH_KEY='+key+'\n')
                vm.smoke(server.server_port, environment)
                connection.request('GET', '/api/state', headers={'Cookie': cookie})
                response = connection.getresponse()
                response.read()
                self.assertEqual(response.status, 200)
                vm.smoke(server.server_port, environment, logout=True)
                connection.request('GET', '/api/state', headers={'Cookie': cookie})
                response = connection.getresponse()
                response.read()
                self.assertEqual(response.status, 401)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_preflight_rejects_low_disk_and_foreign_listener(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(Path, 'read_text', return_value='ID=ubuntu\nVERSION_ID="24.04"\n'), \
                patch.object(vm.shutil, 'disk_usage', return_value=SimpleNamespace(free=0)):
            with self.assertRaisesRegex(ValueError, 'Insufficient'):
                vm.preflight(8766, 8*1024**3, temporary)
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(Path, 'read_text', return_value='ID=ubuntu\nVERSION_ID="24.04"\n'), \
                patch.object(vm.shutil, 'disk_usage', return_value=SimpleNamespace(free=100*1024**3)), \
                patch.object(vm.subprocess, 'run', return_value=SimpleNamespace(returncode=3)), \
                patch.object(vm.socket, 'socket') as probe:
            probe.return_value.__enter__.return_value.connect_ex.return_value = 0
            with self.assertRaisesRegex(ValueError, 'occupied'):
                vm.preflight(8766, 8*1024**3, temporary)

    def test_revisions_and_import_selections_are_required_before_execution(self):
        for args in (['install'], ['update', '--revision', 'main'], ['rollback', '--revision', 'f'*40], ['import-drafts']):
            with self.subTest(args=args), patch.object(deploy_vm.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    deploy_vm.main(args + ['--config', '/nonexistent/private.json'])
                run.assert_not_called()

    def test_private_config_rejects_public_permissions_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'config.json'
            config.write_text(json.dumps({'host': '192.0.2.1', 'user': 'operator'}))
            config.chmod(0o644)
            with self.assertRaises(ValueError):
                deploy_vm.configuration(config)
            config.chmod(0o600)
            self.assertEqual(deploy_vm.configuration(config)['ssh_port'], 22)
            config.write_text(json.dumps({'host': '192.0.2.1', 'user': 'operator', 'password': 'do not accept'}))
            with self.assertRaises(ValueError):
                deploy_vm.configuration(config)

    def test_private_directories_cannot_redirect_to_other_storage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'real').mkdir()
            (root/'redirect').symlink_to(root/'real')
            with self.assertRaises(ValueError):
                vm.private_directory(root/'redirect')


if __name__ == '__main__':
    unittest.main()
