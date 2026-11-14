"""Private ordinary files and narrowly validated systemd credential ACLs.

systemd 254+ can expose a root-owned 0440 file with an ACL granting only the
service UID access. Its group mode bits are the ACL mask, not a group grant.
"""
import os
from pathlib import Path
import re
import stat
import struct
import sys


def _service_acl(value, uid, permission):
    if len(value) != 44 or struct.unpack('<I', value[:4])[0] != 2:
        return False
    entries = [struct.unpack('<HHI', value[offset:offset + 8]) for offset in range(4, len(value), 8)]
    undefined = 0xffffffff
    expected = {(1, permission, undefined), (2, permission, uid), (4, 0, undefined),
                (16, permission, undefined), (32, 0, undefined)}
    return len(set(entries)) == 5 and set(entries) == expected


def _readonly_memory_mount(directory):
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        before, after = line.split(' - ', 1)
        fields, filesystem = before.split(), after.split()[0]
        if fields[4] == str(directory):
            return 'ro' in fields[5].split(',') and filesystem in {'tmpfs', 'ramfs'}
    return False


def check_private_file(path):
    """Reject public files; accept ACL credentials only in their real service mount."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Private file must not be a symlink')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid not in {0, os.geteuid()}:
            raise ValueError('Expected an owned private regular file')
        if not info.st_mode & 0o077:
            return
        directory = path.parent
        credential_directory = os.environ.get('CREDENTIALS_DIRECTORY')
        if (sys.platform != 'linux' or stat.S_IMODE(info.st_mode) != 0o440 or info.st_uid != 0
                or not credential_directory or directory != Path(credential_directory)
                or directory.parent != Path('/run/credentials')
                or not re.fullmatch(r'[A-Za-z0-9_.@:-]+\.service', directory.name)
                or directory.resolve() != directory):
            raise ValueError('Private file has unsafe permissions')
        parent = directory.stat()
        if (parent.st_uid != 0 or stat.S_IMODE(parent.st_mode) != 0o550
                or not _readonly_memory_mount(directory)
                or not _service_acl(os.getxattr(fd, 'system.posix_acl_access'), os.geteuid(), 4)
                or not _service_acl(os.getxattr(directory, 'system.posix_acl_access'), os.geteuid(), 5)):
            raise ValueError('Credential is not isolated to this service UID')
    finally:
        os.close(fd)
