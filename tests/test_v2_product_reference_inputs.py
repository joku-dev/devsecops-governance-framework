"""Original comparisons remain strict when own tests have no parent history."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from acceptance.product_reference_inputs import prepare, contract, REFERENCES
from lib.functional_parity import require_frozen_scope
from lib.runtime_package import git, text_json

INPUTS = ROOT / 'tests/fixtures/product-test-reference-inputs'


class ProductReferenceInputs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / 'source'
        self.source.mkdir(mode=0o700)
        git(self.source, 'init', '--template=', '-q')
        (self.source / 'own-data.txt').write_text('Private current-product test fixture\n')
        git(self.source, 'add', 'own-data.txt')
        git(self.source, '-c', 'commit.gpgsign=false', '-c', 'user.name=Test fixture',
            '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'Private current source')
        self.head = git(self.source, 'rev-parse', 'HEAD').decode().strip()
        self.shallow = self.source / '.git/shallow'
        self.shallow.write_text(self.head + '\n')
        self.work = self.base / 'work'

    def unchanged(self):
        self.assertEqual(git(self.source, 'rev-parse', 'HEAD').decode().strip(), self.head)
        self.assertEqual(git(self.source, 'status', '--porcelain', '--untracked-files=all'), b'')
        self.assertEqual((self.source / 'own-data.txt').read_text(), 'Private current-product test fixture\n')

    def copy_inputs(self):
        target = self.base / 'inputs'
        shutil.copytree(INPUTS, target)
        return target

    def test_complete_original_scope_and_historical_bytes_work_without_parent_history(self):
        result = prepare(self.source, self.head, INPUTS, self.work)
        self.assertEqual(result['state'], 'complete')
        self.assertFalse(result['archived_entrypoints_started'])
        self.assertFalse(result['authority_transferred'])
        self.assertFalse(result['operating_acceptance_inherited'])
        self.assertFalse(result['parent_history_downloaded'])
        self.unchanged()
        matrix = json.loads((ROOT / 'config/axiom-v2-functional-parity.json').read_bytes())
        require_frozen_scope(matrix, self.source)  # Every original entrypoint/CI/area stays checked.
        receipt = git(self.source, 'show', REFERENCES['v1'] + ':scripts/record_agent_review.py')
        self.assertEqual(receipt, (ROOT / 'tests/fixtures/v2-review-receipts/record_agent_review.py.txt').read_bytes())
        producer = git(self.source, 'show', REFERENCES['lifecycle-pilot'] + ':.github/workflows/governance-repository-security.yml')
        self.assertIn(b'governance', producer)
        roots = set(git(self.source, 'log', '--all', '--format=%H').decode().splitlines())
        self.assertEqual(roots, {self.head, *REFERENCES.values()})
        for revision in REFERENCES.values():
            for line in git(self.source, 'cat-file', 'commit', revision).splitlines():
                if line.startswith(b'parent '):
                    with self.assertRaises(ValueError):
                        git(self.source, 'cat-file', '-e', line[7:].decode())

    def test_corrupt_archive_is_rejected_before_any_reference_git_effect(self):
        inputs = self.copy_inputs()
        path = inputs / 'v1.zip'
        raw = path.read_bytes()
        path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(ValueError, 'checksum_mismatch'):
            prepare(self.source, self.head, inputs, self.work)
        self.unchanged()
        self.assertFalse(self.work.exists())
        self.assertEqual(self.shallow.read_text(), self.head + '\n')

    def test_self_consistent_new_hashes_cannot_replace_original_tree_bytes(self):
        inputs = self.copy_inputs()
        path = inputs / 'v1.zip'
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            files = {entry.filename: archive.read(entry) for entry in entries}
        manifest = json.loads(files['manifest.json'])
        name = 'source/scripts/record_agent_review.py'
        raw = files[name] + b'\n# Synthetic changed reference\n'
        files[name] = raw
        row = next(r for r in manifest['files'] if r['path'] == name)
        row.update(size=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
            git_blob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False).hexdigest())
        files['manifest.json'] = text_json(manifest).encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as changed:
            for entry in entries:
                changed.writestr(entry, files[entry.filename])
        path.write_bytes(buffer.getvalue())
        metadata = json.loads((inputs / 'manifest.json').read_bytes())
        descriptor = next(r for r in metadata['snapshots'] if r['id'] == 'v1')
        descriptor.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        (inputs / 'manifest.json').write_text(text_json(metadata))
        contract(inputs)  # Coherent outer checksums alone are deliberately insufficient.
        with self.assertRaisesRegex(ValueError, 'package_tree_mismatch'):
            prepare(self.source, self.head, inputs, self.work)
        self.unchanged()
        self.assertEqual(self.shallow.read_text(), self.head + '\n')
        self.assertFalse((self.source / '.git/refs/axiom-test-inputs').exists())
        self.assertFalse((self.work / 'prepared.json').exists())

    def test_unlisted_source_identity_is_not_an_approved_reference(self):
        inputs = self.base / 'inputs'
        inputs.mkdir()
        value = deepcopy(json.loads((INPUTS / 'manifest.json').read_bytes()))
        value['snapshots'][0]['source_revision'] = '0' * 40
        (inputs / 'manifest.json').write_text(text_json(value))
        with self.assertRaisesRegex(ValueError, 'descriptor'):
            prepare(self.source, self.head, inputs, self.work)
        self.assertFalse(self.work.exists())
        self.unchanged()

    def test_shared_or_symlinked_git_directory_is_rejected(self):
        original = self.source / '.git'
        moved = self.base / 'other-git'
        original.rename(moved)
        original.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'owned_product_test_git_directory'):
            prepare(self.source, self.head, INPUTS, self.work)
        self.assertFalse(self.work.exists())

    def test_unmarked_or_previously_extended_checkout_is_not_silently_reused(self):
        for value in (None, self.head + '\n' + REFERENCES['v1'] + '\n'):
            with self.subTest(value=value):
                if value is None:
                    self.shallow.unlink(missing_ok=True)
                else:
                    self.shallow.write_text(value)
                with self.assertRaisesRegex(ValueError, 'single_parentless'):
                    prepare(self.source, self.head, INPUTS, self.work)
                self.assertFalse(self.work.exists())
