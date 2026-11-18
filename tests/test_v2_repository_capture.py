"""Actual Git/FD capture, closed deleted-caller validation and source races."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import repository_capture as contract
from lib.providers.repository_git import RepositoryGit
from lib.providers.repository_source import RepositorySource
from lib.providers import process_groups
from lib.v2_boundary import violations


@unittest.skipUnless(shutil.which('git'), 'local Git not present')
class RepositoryCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / 'source'
        self.source.mkdir(mode=0o700)
        self.rows = []
        self.journal_path = self.base / 'native.jsonl'
        self.git_tool = shutil.which('git')
        self.command('init', '-b', 'fixture')
        for name, raw in {'README.md': b'# Controlled data\n', 'model/catalog.json': b'{"version":1}\n',
                'model/nested/record.json': b'{"input":true}\n', 'schemas/local.schema.json': b'{"type":"object"}\n',
                'scripts/caller.py': b'raise AssertionError("inspected code must never run")\n',
                '.github/workflows/fixture.yml': b'name: inert test data\n', '.gitignore': b'.venv*\n'}.items():
            path = self.source / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(raw)
        (self.source / 'scripts/caller.py').chmod(0o700)
        self.commit()

    def command(self, *arguments, input=None):
        environment = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_COUNT': '0'}
        for key in list(environment):
            if key.startswith('GIT_') and key not in ('GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_COUNT'):
                environment.pop(key)
        return subprocess.run([self.git_tool, '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
            '-c', 'user.name=AXIOM test', '-c', 'user.email=axiom-test@example.invalid',
            *arguments], cwd=self.source, input=input, capture_output=True, check=True,
            env=environment, timeout=10).stdout

    def commit(self):
        self.command('add', '.')
        self.command('commit', '--no-gpg-sign', '-m', 'controlled fixture')
        self.revision = self.command('rev-parse', 'HEAD').decode().strip()

    def journal(self, stage):
        def append(row):
            value = {'stage': stage, 'observation': row}
            fd = os.open(self.journal_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write((json.dumps(value, sort_keys=True) + '\n').encode())
                stream.flush(); os.fsync(stream.fileno())
            self.rows.append(copy.deepcopy(value))
        return append

    def port(self, **overrides):
        options = {'on_intent': self.journal('intent'), 'on_start': self.journal('started'),
                   'on_finish': self.journal('finished')}
        options.update(overrides)
        return RepositoryGit(self.source, self.git_tool, **options)

    def capture(self, profile=contract.COMMITTED, **overrides):
        return RepositorySource(self.port(), self.revision, profile=profile).capture()

    def test_committed_complete_blob_graph_hashes_modes_and_individual_process_journal(self):
        manifest, files, commit = self.capture()
        self.assertEqual(files['scripts/caller.py'], (self.source / 'scripts/caller.py').read_bytes())
        self.assertEqual(manifest['files']['scripts/caller.py']['mode'], '100755')
        self.assertEqual(set(files), {name for name, row in manifest['inventory'].items() if row['kind'] == 'blob'})
        self.assertEqual(manifest['directories'], contract.tree_directories(manifest['inventory']))
        self.assertEqual(contract.check_capture(manifest, files, commit, revision=self.revision), manifest)
        self.assertEqual([row['stage'] for row in self.rows], ['intent', 'started', 'finished'] * (len(self.rows) // 3))
        self.assertEqual([json.loads(line) for line in self.journal_path.read_text().splitlines()], self.rows)
        for event in self.rows:
            if event['stage'] == 'finished':
                self.assertTrue(event['observation']['process_started'])
                self.assertTrue(process_groups.consistent(event['observation']))
                self.assertIsNone(event['observation']['error_type'])
        self.assertFalse((self.base / 'caller-executed').exists())

    def test_committed_profile_ignores_changed_missing_and_linked_working_files(self):
        expected = self.capture()
        (self.source / 'README.md').write_bytes(b'working changes')
        (self.source / 'scripts/caller.py').unlink()
        (self.source / 'model/catalog.json').unlink()
        (self.source / 'model/catalog.json').symlink_to('/etc/passwd')
        self.assertEqual(self.capture(), expected)

    def test_committed_profile_restores_all_inert_data_from_a_sparse_checkout(self):
        expected = self.capture()
        self.command('sparse-checkout', 'set', '--no-cone', '--stdin', input=b'/model/\n/README.md\n')
        self.assertFalse((self.source / 'scripts/caller.py').exists())
        self.assertEqual(self.capture(), expected)

    def test_working_profile_preserves_actual_mutations_untracked_data_empty_dirs_and_order(self):
        (self.source / 'README.md').unlink()
        (self.source / 'model/catalog.json').write_bytes(b'{"version":2}\n')
        (self.source / 'model/new.json').write_bytes(b'new bytes')
        (self.source / 'model/empty').mkdir()
        manifest, files, commit = self.capture(contract.WORKING)
        self.assertNotIn('README.md', files)
        self.assertEqual(files['model/catalog.json'], b'{"version":2}\n')
        self.assertEqual(files['model/new.json'], b'new bytes')
        self.assertEqual(manifest['directories']['model/empty'], [])
        self.assertEqual(manifest['directories']['model'], os.listdir(self.source / 'model'))
        contract.check_capture(manifest, files, commit, revision=self.revision)
        committed, baseline, _ = self.capture()
        self.assertNotIn('model/new.json', baseline)
        self.assertIn('README.md', baseline)
        self.assertEqual(committed['profile'], contract.COMMITTED)

    def test_private_local_files_and_unsupported_untracked_roots_are_never_read(self):
        for name in ('.env', '.aws/credentials', '.venv-validation/token', 'docs/token.key', 'unknown/private.json'):
            path = self.source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'must not be retained')
        (self.source / 'model/.DS_Store').write_bytes(b'local metadata')
        (self.source / 'model/.venv-hidden').symlink_to(self.base, target_is_directory=True)
        import lib.providers.repository_source as provider
        original = provider.file_bytes
        def guarded(parent, name):
            self.assertNotIn(name, ('credentials', '.env', 'token', 'token.key', '.DS_Store', 'private.json'))
            return original(parent, name)
        with patch.object(provider, 'file_bytes', side_effect=guarded):
            manifest, files, _ = self.capture(contract.WORKING)
        self.assertFalse(any(contract.private_name(name) for name in files))
        self.assertNotIn('unknown', manifest['directories'][''])
        self.assertTrue((self.source / '.env').exists())

    def test_private_tracked_file_is_rejected_before_any_blob_is_read(self):
        (self.source / 'docs').mkdir(); (self.source / 'docs/token.key').write_bytes(b'private')
        self.commit(); port = self.port()
        with self.assertRaisesRegex(ValueError, 'private_tracked_file'):
            RepositorySource(port, self.revision, profile=contract.COMMITTED).capture()
        self.assertFalse(any(row['arguments'][:2] == ['cat-file', 'blob'] for row in port.observations))

    def test_working_symlink_hardlink_and_fifo_are_rejected_without_source_execution(self):
        path = self.source / 'model/unsafe'
        path.symlink_to('/etc/passwd')
        with self.assertRaises(ValueError): self.capture(contract.WORKING)
        path.unlink(); os.link(self.source / 'README.md', path)
        with self.assertRaises(ValueError): self.capture(contract.WORKING)
        path.unlink(); os.mkfifo(path)
        with self.assertRaises(ValueError): self.capture(contract.WORKING)
        path.unlink()
        self.assertEqual(self.capture()[1]['README.md'], (self.source / 'README.md').read_bytes())

    def test_working_capture_rechecks_every_file_after_the_first_complete_read(self):
        source = RepositorySource(self.port(), self.revision, profile=contract.WORKING)
        original = source.working; count = 0
        def changed(fd, inventory):
            nonlocal count
            result = original(fd, inventory); count += 1
            if count == 1: (self.source / 'model/catalog.json').write_bytes(b'changed after first snapshot')
            return result
        with patch.object(source, 'working', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'working_files_changed'): source.capture()
        self.assertEqual(count, 2)

    def test_change_between_file_stat_and_read_completion_is_rejected(self):
        import lib.providers.repository_source as provider
        original = provider.file_bytes
        def changed(parent, name):
            raw = original(parent, name)
            if name == 'catalog.json': (self.source / 'model/catalog.json').write_bytes(b'changed during read')
            return raw
        with patch.object(provider, 'file_bytes', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'file_changed'): self.capture(contract.WORKING)

    def test_head_change_and_wrong_product_revision_are_never_silently_admitted(self):
        original_revision = self.revision
        (self.source / 'README.md').write_bytes(b'new commit'); self.commit()
        with self.assertRaisesRegex(ValueError, 'revision_mismatch'):
            RepositorySource(self.port(), original_revision, profile=contract.COMMITTED).capture()
        with self.assertRaises(ValueError): RepositorySource(self.port(), 'main', profile=contract.COMMITTED)
        with self.assertRaises(ValueError): RepositorySource(self.port(), self.revision, profile='automatic')

    def test_replaced_root_during_working_capture_closes_all_owned_directory_fds(self):
        import lib.providers.repository_source as provider
        original_read = provider.file_bytes; original_open, original_close = os.open, os.close
        descriptors = set(); changed = False
        def opened(*args, **options):
            fd = original_open(*args, **options)
            if args[1] & os.O_DIRECTORY: descriptors.add(fd)
            return fd
        def closed(fd):
            descriptors.discard(fd); return original_close(fd)
        def replace(parent, name):
            nonlocal changed
            raw = original_read(parent, name)
            if not changed:
                changed = True
                self.source.rename(self.base / 'old-source')
                self.source.mkdir(mode=0o700)
            return raw
        with patch('os.open', side_effect=opened), patch('os.close', side_effect=closed), patch.object(provider, 'file_bytes', side_effect=replace):
            with self.assertRaises((ValueError, FileNotFoundError)): self.capture(contract.WORKING)
        self.assertEqual(descriptors, set())

    def test_closed_capture_verifies_after_the_original_checkout_is_deleted(self):
        manifest, files, commit = self.capture()
        shutil.rmtree(self.source)
        self.assertEqual(contract.check_capture(manifest, files, commit, revision=self.revision), manifest)

    def test_changed_blob_even_with_rehashed_descriptor_cannot_change_committed_tree(self):
        manifest, files, commit = self.capture()
        files['README.md'] = b'forged'
        manifest['files']['README.md'] = contract.file_descriptor(files['README.md'], '100644', 'sha1')
        with self.assertRaisesRegex(ValueError, 'committed_bytes_differ'):
            contract.check_capture(manifest, files, commit, revision=self.revision)

    def test_inventory_tree_commit_extra_missing_and_duplicate_directory_members_are_bound(self):
        manifest, files, commit = self.capture()
        changes = []
        value = copy.deepcopy(manifest); value['inventory']['README.md']['git_object'] = '0' * 40; changes.append(value)
        value = copy.deepcopy(manifest); value['directories'][''].append('README.md'); changes.append(value)
        value = copy.deepcopy(manifest); value['directories'][''].remove('README.md'); changes.append(value)
        value = copy.deepcopy(manifest); value['source_root'] = '/tmp/../outside'; changes.append(value)
        value = copy.deepcopy(manifest); value['unrecognized'] = True; changes.append(value)
        for value in changes:
            with self.assertRaises(ValueError): contract.check_capture(value, files, commit, revision=self.revision)
        with self.assertRaises(ValueError): contract.check_capture(manifest, files, commit + b'changed', revision=self.revision)
        with self.assertRaises(ValueError): contract.check_capture(manifest, files | {'model/extra': b'x'}, commit, revision=self.revision)
        with self.assertRaises(ValueError): contract.check_capture(manifest, {k:v for k,v in files.items() if k != 'README.md'}, commit, revision=self.revision)

    def test_git_hooks_filters_fsmonitor_and_inherited_git_overrides_cannot_execute(self):
        marker = self.base / 'unexpected-execution'
        hook = self.base / 'hook.sh'; hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n'); hook.chmod(0o700)
        self.command('config', 'core.fsmonitor', str(hook))
        self.command('config', 'core.hooksPath', str(self.base))
        self.command('config', 'filter.evil.smudge', str(hook))
        (self.source / '.gitattributes').write_text('* filter=evil\n')
        with patch.dict(os.environ, {'GIT_DIR': '/not-the-repo', 'GIT_WORK_TREE': '/not-the-repo',
                                    'GIT_CONFIG_PARAMETERS': "'alias.rev-parse=malicious'"}):
            manifest, files, commit = self.capture()
        self.assertFalse(marker.exists())
        contract.check_capture(manifest, files, commit, revision=self.revision)

    def test_selected_committed_symlink_and_submodule_entries_are_not_plain_source(self):
        (self.source / 'model/link').symlink_to('catalog.json'); self.commit()
        with self.assertRaises(ValueError): self.capture()

    def test_actual_sha256_git_objects_and_commit_tree_binding_are_supported(self):
        shutil.rmtree(self.source / '.git')
        try: self.command('init', '--object-format=sha256', '-b', 'fixture')
        except subprocess.CalledProcessError: self.skipTest('Git does not support SHA-256 repositories')
        self.commit()
        manifest, files, commit = self.capture()
        self.assertEqual(manifest['object_format'], 'sha256')
        self.assertEqual(len(manifest['revision']), 64)
        contract.check_capture(manifest, files, commit, revision=self.revision)

    def test_source_directory_spaces_are_preserved_in_the_binding_label(self):
        new = self.source.with_name('source with a space ')
        self.source.rename(new); self.source = new
        manifest, _, _ = self.capture()
        self.assertEqual(manifest['source_root'], str(new))

    def test_manifest_core_has_no_native_or_provider_imports(self):
        name = 'scripts/lib/repository_capture.py'
        self.assertEqual(violations(name, (ROOT / name).read_text()), [])


if __name__ == '__main__': unittest.main()
