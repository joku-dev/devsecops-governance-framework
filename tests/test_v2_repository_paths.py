"""Actual held descriptor reads and path semantics within retained data only."""
from pathlib import Path
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_paths import RepositoryPaths
from lib.providers.repository_data_io import RepositoryDataIO
from lib.v2_boundary import violations


class RepositoryPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        self.root.mkdir(mode=0o700)
        for name in ('a.json', 'nested/z.json', 'nested/deep/a.json', 'b.json', 'nested/b.txt'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'name': name}) + '\n')
        self.port = RepositoryDataIO(self.root)
        self.namespace = RepositoryPaths(str(self.root), self.port)
        self.current = self.namespace.root

    def outcome(self, callback):
        try:
            return {'value': callback()}
        except Exception as error:
            return {'type': type(error).__name__, 'message': str(error)}

    def test_actual_files_bytes_text_open_and_path_parts_match_native(self):
        for old in self.root.rglob('*'):
            new = self.namespace.path(old)
            self.assertEqual(str(new), str(old))
            self.assertEqual(new.name, old.name)
            self.assertEqual(new.parts, old.parts)
            self.assertEqual(new.suffix, old.suffix)
            self.assertEqual(new.is_file(), old.is_file())
            self.assertEqual(new.is_dir(), old.is_dir())
            if old.is_file():
                self.assertEqual(new.read_bytes(), old.read_bytes())
                self.assertEqual(new.read_text(), old.read_text())
                with new.open() as stream:
                    self.assertEqual(stream.name, str(old))
                    self.assertEqual(json.load(stream), json.loads(old.read_bytes()))

    def test_native_glob_and_rglob_order_are_retained(self):
        for pattern in ('*', '*.json', '*.txt'):
            self.assertEqual([str(p) for p in self.current.glob(pattern)], [str(p) for p in self.root.glob(pattern)])
            self.assertEqual([str(p) for p in self.current.rglob(pattern)], [str(p) for p in self.root.rglob(pattern)])
        self.assertEqual([str(p) for p in self.current.glob('**/*.json')], [str(p) for p in self.root.glob('**/*.json')])

    def test_structural_relative_paths_do_not_observe_an_ambient_cwd(self):
        value = self.namespace.path('nested/../a.json')
        self.assertFalse(value.is_absolute())
        self.assertEqual(value.parts, Path('nested/../a.json').parts)
        self.assertEqual(value.resolve().read_bytes(), (self.root / 'a.json').read_bytes())
        self.assertEqual((self.current / 'nested/a.json').relative_to(self.current).as_posix(), 'nested/a.json')
        for old in (self.root / 'nested/a.json', self.root.parent / 'outside'):
            self.assertEqual(self.namespace.path(old).is_relative_to(self.current), old.is_relative_to(self.root))

    def test_missing_files_and_parent_files_keep_native_errors(self):
        for name in ('missing.json', 'missing/a.json', 'a.json/child.json', 'nested'):
            self.assertEqual(self.outcome(lambda: (self.current / name).read_bytes()),
                             self.outcome(lambda: (self.root / name).read_bytes()))
        self.assertFalse((self.current / 'a.json/child.json').exists())

    def test_paths_cannot_be_implicitly_coerced_to_unguarded_native_io(self):
        with self.assertRaises(TypeError):
            os.fspath(self.current / 'a.json')
        with self.assertRaises(TypeError):
            Path(self.current / 'a.json')

    def test_absolute_and_parent_escapes_never_call_the_data_port(self):
        outside = self.root.parent / 'outside.json'
        outside.write_text('private controlled external input')
        with patch.object(self.port, 'read', side_effect=AssertionError('outside I/O forbidden')):
            for path in (str(outside), '../outside.json'):
                with self.assertRaisesRegex(ValueError, 'outside_repository_data_namespace'):
                    self.namespace.path(path).read_bytes()

    def test_file_and_parent_symlinks_are_not_followed(self):
        outside = self.root.parent / 'outside'
        outside.mkdir()
        (outside / 'private.json').write_text('private controlled external input')
        (self.root / 'link.json').symlink_to(outside / 'private.json')
        (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        self.assertTrue((self.current / 'link.json').is_symlink())
        for path in ('link.json', 'linked/private.json'):
            with self.assertRaises(ValueError):
                (self.current / path).read_bytes()

    def test_root_replacement_is_detected_before_reading_new_bytes(self):
        previous = self.root.with_name('old-data')
        self.root.rename(previous)
        self.root.mkdir(mode=0o700)
        (self.root / 'a.json').write_text('replacement')
        with self.assertRaisesRegex(ValueError, 'root_identity_changed'):
            (self.current / 'a.json').read_bytes()

    def test_private_root_and_hardlink_guards(self):
        os.link(self.root / 'a.json', self.root / 'hardlink.json')
        with self.assertRaises(ValueError):
            (self.current / 'hardlink.json').read_bytes()
        self.root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private_repository_data_directory_required'):
            RepositoryDataIO(self.root)

    def test_read_failures_release_every_owned_descriptor(self):
        opened, closed = [], []
        real_open, real_close = os.open, os.close
        def track_open(*args, **kwargs):
            result = real_open(*args, **kwargs)
            opened.append(result)
            return result
        def track_close(fd):
            closed.append(fd)
            return real_close(fd)
        with patch('os.open', side_effect=track_open), patch('os.close', side_effect=track_close):
            with self.assertRaises(FileNotFoundError):
                (self.current / 'nested/missing.json').read_bytes()
        self.assertCountEqual(opened, closed)

    def test_namespace_cannot_write_and_has_no_provider_dependency(self):
        with self.assertRaisesRegex(ValueError, 'read_only'):
            (self.current / 'a.json').open('wb')
        path = ROOT / 'scripts/lib/repository_paths.py'
        self.assertEqual(violations(path.relative_to(ROOT).as_posix(), path.read_text()), [])


if __name__ == '__main__':
    unittest.main()
