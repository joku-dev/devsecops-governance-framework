"""Private durable ordered operation records, including exact content frames.

The chain proves retained-byte consistency. It is declared evidence and never
independent execution authentication, human consent or operating authority.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from lib.ci_bundle_storage import reserve
from lib.result_bytes import strict_json

MAX_EVENT = 24 * 1024**2
MAX_JOURNAL = 512 * 1024**2
MAX_EVENTS = 65536
NAME = 'events.jsonl'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def identity(value):
    return value.st_dev, value.st_ino, value.st_mode


def root_fd(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError('private_repository_journal_root_required')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    metadata = os.fstat(fd)
    if metadata.st_mode & 0o077:
        os.close(fd)
        raise ValueError('private_repository_journal_root_required')
    return root, fd, identity(metadata)


class RepositoryJournal:
    def __init__(self, root, header):
        if type(header) is not dict:
            raise ValueError('repository_journal_binding_required')
        self.root, self.directory, self.root_identity = root_fd(root)
        self.fd = None
        self.failed, self.sequence, self.previous, self.size = False, 0, None, 0
        try:
            self.fd = os.open(NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=self.directory)
            self.file_identity = identity(os.fstat(self.fd))
            os.fsync(self.directory)
            self.append({'kind': 'operation-start', 'binding': header})
        except BaseException:
            self.close()
            raise

    def __enter__(self): return self

    def __exit__(self, *args): self.close()

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.directory is not None:
            os.close(self.directory)
            self.directory = None

    def check(self):
        if self.failed or self.fd is None or self.directory is None:
            raise ValueError('repository_journal_not_appendable')
        if (identity(os.fstat(self.directory)) != self.root_identity
                or identity(os.stat(self.root, follow_symlinks=False)) != self.root_identity):
            raise ValueError('repository_journal_root_identity_changed')
        value = os.fstat(self.fd)
        named = os.stat(NAME, dir_fd=self.directory, follow_symlinks=False)
        if (identity(value) != self.file_identity or identity(named) != self.file_identity
                or value.st_nlink != 1 or value.st_size != self.size):
            raise ValueError('repository_journal_file_identity_changed')

    def append(self, payload):
        self.check()
        if type(payload) is not dict or self.sequence >= MAX_EVENTS:
            raise ValueError('repository_journal_event_budget')
        packet = {'sequence': self.sequence + 1, 'previous': self.previous, 'payload': payload}
        digest = hashlib.sha256(encoded(packet)).hexdigest()
        raw = encoded({**packet, 'sha256': digest}) + b'\n'
        if len(raw) > MAX_EVENT or self.size + len(raw) > MAX_JOURNAL:
            raise ValueError('repository_journal_byte_budget')
        reserve(self.root, len(raw))
        try:
            remaining = memoryview(raw)
            while remaining:
                count = os.write(self.fd, remaining)
                if count <= 0:
                    raise OSError('repository_journal_short_write')
                remaining = remaining[count:]
            os.fsync(self.fd)
            self.size += len(raw)
            self.sequence += 1
            self.previous = digest
            self.check()
        except BaseException:
            self.failed = True
            raise
        return digest


def read_journal(root, *, expected_header=None):
    root, directory, root_identity = root_fd(root)
    fd = None
    try:
        fd = os.open(NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_mode & 0o077 or before.st_nlink != 1
                or before.st_size > MAX_JOURNAL):
            raise ValueError('private_regular_repository_journal_required')
        rows, previous = [], None
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            while raw := stream.readline(MAX_EVENT + 1):
                if len(raw) > MAX_EVENT or not raw.endswith(b'\n') or len(rows) >= MAX_EVENTS:
                    raise ValueError('repository_journal_truncated_or_oversize')
                row = strict_json(raw)
                if (type(row) is not dict or set(row) != {'sequence', 'previous', 'payload', 'sha256'}
                        or type(row['sequence']) is not int or row['sequence'] != len(rows) + 1
                        or row['previous'] != previous or type(row['payload']) is not dict):
                    raise ValueError('repository_journal_chain_changed')
                packet = {key: row[key] for key in ('sequence', 'previous', 'payload')}
                if row['sha256'] != hashlib.sha256(encoded(packet)).hexdigest() or raw != encoded(row) + b'\n':
                    raise ValueError('repository_journal_bytes_changed')
                rows.append(row)
                previous = row['sha256']
        after = os.fstat(fd)
        named = os.stat(NAME, dir_fd=directory, follow_symlinks=False)
        if (identity(after) != identity(before) or identity(named) != identity(before)
                or before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
                or identity(os.stat(root, follow_symlinks=False)) != root_identity):
            raise ValueError('repository_journal_changed_during_read')
        if not rows or rows[0]['payload'].get('kind') != 'operation-start':
            raise ValueError('repository_journal_operation_header_required')
        if expected_header is not None and rows[0]['payload'] != {'kind': 'operation-start', 'binding': expected_header}:
            raise ValueError('repository_journal_operation_binding_changed')
        return rows
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)
