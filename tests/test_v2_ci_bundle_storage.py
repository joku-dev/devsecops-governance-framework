"""Private byte snapshots, portable ZIP paths and resource boundaries."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.ci_bundle_storage import copy_bundle, describe, inventory, verify_directory, RESERVE


class CiBundleStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'; self.source.mkdir(mode=0o700)
        (self.source / 'evidence').mkdir()
        (self.source / 'evidence/pipeline-evidence.json').write_text('{"synthetic":true}\n')

    def archive(self, members=None, name='bundle.zip'):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as archive:
            if members is None: archive.write(self.source / 'evidence/pipeline-evidence.json', 'evidence/pipeline-evidence.json')
            else:
                for key, value in members.items(): archive.writestr(key, value)
        return path

    def test_directory_copy_is_sealed_private_and_independent_of_original(self):
        initial = describe(self.source)
        destination = self.root / 'copied'
        receipt = copy_bundle(self.source, initial['input_sha256'], destination)
        self.assertEqual(receipt, initial)
        shutil.rmtree(self.source)
        self.assertEqual(verify_directory(destination / 'material', receipt), receipt['files'])
        for path in (destination, *(destination.rglob('*'))): self.assertEqual(path.stat().st_mode & 0o077, 0)
        file = destination / 'material/evidence/pipeline-evidence.json'; file.write_text('Changed\n')
        with self.assertRaisesRegex(ValueError, 'retained_bytes_changed'): verify_directory(destination / 'material', receipt)

    def test_zip_copy_preserves_original_bytes_and_material_inventory(self):
        archive = self.archive(); receipt = describe(archive); destination = self.root / 'zip-copy'
        copied = copy_bundle(archive, receipt['input_sha256'], destination)
        self.assertEqual(hashlib.sha256((destination / 'source.zip').read_bytes()).hexdigest(), receipt['input_sha256'])
        self.assertEqual(copied['files'], inventory(self.source))
        self.assertEqual(copied['material_bytes'], sum(v['bytes'] for v in copied['files'].values()))

    def test_windows_zip_separators_keep_v1_extraction_semantics(self):
        archive = self.archive({'evidence\\pipeline-evidence.json': b'{}'})
        value = copy_bundle(archive, describe(archive)['input_sha256'], self.root / 'windows-copy')
        self.assertEqual(set(value['files']), {'evidence/pipeline-evidence.json'})

    def test_implicit_parent_case_aliases_are_rejected_consistently(self):
        archive = self.archive({'Evidence/a.json': b'{}', 'evidence/b.json': b'{}'})
        with self.assertRaisesRegex(ValueError, 'path_case'):
            copy_bundle(archive, describe(archive)['input_sha256'], self.root / 'case-copy')

    def test_symlink_and_non_regular_files_are_not_followed(self):
        outside = self.root / 'outside.json'; outside.write_text('private outside')
        (self.source / 'leak.json').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'): describe(self.source)
        (self.source / 'leak.json').unlink()
        os.mkfifo(self.source / 'fifo')
        with self.assertRaisesRegex(ValueError, 'invalid_ci_bundle_file'): describe(self.source)

    def test_traversal_zip_is_rejected_and_does_not_escape(self):
        archive = self.archive({'../outside.json': b'{}'})
        with self.assertRaises(ValueError): copy_bundle(archive, describe(archive)['input_sha256'], self.root / 'escape-copy')
        self.assertFalse((self.root / 'outside.json').exists())

    def test_wrong_digest_existing_destination_budget_and_reserve_fail_closed(self):
        value = describe(self.source)
        with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
            copy_bundle(self.source, '0' * 64, self.root / 'bad-digest')
        with self.assertRaisesRegex(ValueError, 'budget_exhausted'):
            copy_bundle(self.source, value['input_sha256'], self.root / 'low-budget', budget=1)
        destination = self.root / 'existing'; destination.mkdir()
        with self.assertRaisesRegex(ValueError, 'fresh_private'):
            copy_bundle(self.source, value['input_sha256'], destination)
        free = shutil.disk_usage(self.root)
        with patch('lib.ci_bundle_storage.shutil.disk_usage', return_value=type(free)(free.total, free.used, RESERVE)):
            with self.assertRaisesRegex(ValueError, 'free_space_reserve'):
                copy_bundle(self.source, value['input_sha256'], self.root / 'no-reserve')

    def test_source_change_during_copy_is_not_committed_as_original_input(self):
        original = describe(self.source)
        (self.source / 'evidence/pipeline-evidence.json').write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError, 'digest_mismatch'):
            copy_bundle(self.source, original['input_sha256'], self.root / 'changed')


if __name__ == '__main__': unittest.main()
