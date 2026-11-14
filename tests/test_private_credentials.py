import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib.private_credentials import check_private_file, _service_acl, _readonly_memory_mount


class PrivateCredentialsTests(unittest.TestCase):
    def test_owner_only_files_are_accepted_and_public_files_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'key'
            path.write_text('synthetic')
            for mode in (0o400, 0o600):
                path.chmod(mode)
                check_private_file(path)
            for mode in (0o440, 0o640, 0o644, 0o666):
                path.chmod(mode)
                with patch.dict(os.environ, {'CREDENTIALS_DIRECTORY': temporary}):
                    with self.assertRaises(ValueError):
                        check_private_file(path)

    def test_symlinks_and_hardlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'key'
            path.write_text('synthetic');path.chmod(0o600)
            link = Path(temporary) / 'link'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                check_private_file(link)
            link.unlink();os.link(path, link)
            with self.assertRaises(ValueError):
                check_private_file(path)

    def test_acl_grants_only_root_and_the_current_service(self):
        uid, undefined = 998, 0xffffffff
        entries = [(1, 4, undefined), (2, 4, uid), (4, 0, undefined), (16, 4, undefined), (32, 0, undefined)]
        def encoded(rows):
            return struct.pack('<I', 2) + b''.join(struct.pack('<HHI', *row) for row in rows)
        self.assertTrue(_service_acl(encoded(entries), uid, 4))
        for changed in (
                [*entries[:2], (4, 4, undefined), *entries[3:]],
                [entries[0], (2, 4, uid + 1), *entries[2:]],
                [*entries[:-1], (32, 4, undefined)],
                [*entries, (2, 4, uid + 1)],
                [entries[0], (2, 6, uid), *entries[2:]]):
            self.assertFalse(_service_acl(encoded(changed), uid, 4))
        self.assertFalse(_service_acl(b'invalid', uid, 4))

    def test_only_exact_readonly_memory_mount_is_accepted(self):
        path = Path('/run/credentials/axiom-consumer-poll.service')
        for filesystem, options, expected in (('tmpfs', 'ro,nosuid', True), ('ramfs', 'ro', True),
                                               ('tmpfs', 'rw', False), ('ext4', 'ro', False)):
            record = f'45 30 0:40 / {path} {options} - {filesystem} none ro\n'
            with patch.object(Path, 'read_text', return_value=record):
                self.assertEqual(_readonly_memory_mount(path), expected)
        with patch.object(Path, 'read_text', return_value='45 30 0:40 / /run ro - tmpfs none ro\n'):
            self.assertFalse(_readonly_memory_mount(path))
