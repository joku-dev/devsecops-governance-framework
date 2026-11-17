"""Private, transactional data generations for V2 candidate authoring.

Payloads may retain historical authority vocabulary. Every generation remains
an unpublished candidate; this store grants no governance authority.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import canonical_digest
from lib.portable.runtime import read_json, source_digest


def private_directory(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('unsafe_candidate_directory')
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    if not path.is_dir() or path.stat().st_mode & 0o077:
        raise ValueError('private_candidate_directory_required')
    return path


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError('private_candidate_directory_required')
    records = {}
    total = 0
    for path in sorted(Path(root).rglob('*')):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError('unsafe_candidate_file')
        if mode & 0o077:
            raise ValueError('private_candidate_file_required')
        if not stat.S_ISREG(mode):
            continue
        size = path.stat().st_size
        total += size
        if size > 16 * 1024**2 or total > 128 * 1024**2 or len(records) >= 10000:
            raise ValueError('candidate_workspace_limit_exceeded')
        records[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def seed(root, source):
    """Copy only committed data blobs; never execute or copy source programs."""
    entries = git_read(source, 'ls-tree', '-r', '-z', 'HEAD', '--', 'docs', 'model')
    for entry in entries.split(b'\0'):
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        relative = Path(raw_path.decode())
        if (mode not in ('100644', '100755') or kind != 'blob'
                or relative.is_absolute() or '..' in relative.parts):
            raise ValueError('unsupported_candidate_seed')
        target = root / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # mkdir(parents=True) uses the process umask for intermediate parents.
        for parent in target.parents:
            if parent == root:
                break
            parent.chmod(0o700)
        target.write_bytes(git_read(source, 'cat-file', 'blob', blob))
        target.chmod(0o600)
    inventory(root)


class CandidateWorkspace:
    def __init__(self, instance, name, *, node_id):
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', name):
            raise ValueError('invalid_candidate_workspace_name')
        self.node_id = node_id
        state = Path(instance) / 'state'
        if state.is_symlink() or not state.is_dir() or state.stat().st_mode & 0o077:
            raise ValueError('private_candidate_state_required')
        base = private_directory(state / 'workspaces')
        self.root = private_directory(base / name)
        self.generations = private_directory(self.root / 'generations')

    @contextmanager
    def lock(self):
        path = self.root / 'lock'
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode) or os.fstat(descriptor).st_mode & 0o077:
                raise ValueError('private_candidate_lock_required')
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('candidate_workspace_busy') from None
            yield
        finally:
            os.close(descriptor)

    def current(self):
        marker = self.root / 'current.json'
        if marker.is_symlink() or not marker.is_file() or marker.stat().st_mode & 0o077:
            raise ValueError('candidate_workspace_not_initialized')
        value = read_json(marker)
        if (set(value) != {'schema_version', 'node_id', 'runtime_source_digest', 'generation',
                           'authority_scope', 'official_acceptance'}
                or value['schema_version'] != 1 or value['node_id'] != self.node_id
                or value['runtime_source_digest'] != source_digest()
                or value['authority_scope'] != 'candidate_only' or value['official_acceptance'] is not False
                or not re.fullmatch(r'[0-9a-f]{64}', value['generation'])):
            raise ValueError('candidate_workspace_binding_mismatch')
        root = self.generations / value['generation']
        if root.is_symlink() or not root.is_dir() or canonical_digest(inventory(root)) != value['generation']:
            raise ValueError('candidate_generation_changed')
        return root, value

    def commit(self, staged):
        # Domain writers keep their V1 serialization. New files stay behind the
        # private staging root and are made private before a generation is exposed.
        for path in [staged, *staged.rglob('*')]:
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                path.chmod(0o700)
            elif stat.S_ISREG(mode):
                path.chmod(0o600)
            else:
                raise ValueError('unsafe_candidate_file')
        identity = canonical_digest(inventory(staged))
        destination = self.generations / identity
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or canonical_digest(inventory(destination)) != identity:
                raise ValueError('candidate_generation_conflict')
        else:
            os.rename(staged, destination)
        value = {'schema_version': 1, 'node_id': self.node_id, 'runtime_source_digest': source_digest(),
                 'generation': identity, 'authority_scope': 'candidate_only', 'official_acceptance': False}
        if (self.root / 'current.json').is_symlink():
            raise ValueError('unsafe_candidate_pointer')
        atomic_json(self.root / 'current.json', value)
        return value

    def initialize(self, source):
        with self.lock():
            if (self.root / 'current.json').exists() or (self.root / 'current.json').is_symlink():
                raise ValueError('fresh_candidate_workspace_required')
            with tempfile.TemporaryDirectory(prefix='staged-', dir=self.root) as temporary:
                staged = Path(temporary) / 'data'
                staged.mkdir(mode=0o700)
                seed(staged, source)
                return self.commit(staged)

    def execute(self, operation, *, write):
        with self.lock():
            current, value = self.current()
            if not write:
                result = operation(current)
                if canonical_digest(inventory(current)) != value['generation']:
                    raise ValueError('candidate_read_changed_generation')
                return value, result
            with tempfile.TemporaryDirectory(prefix='staged-', dir=self.root) as temporary:
                staged = Path(temporary) / 'data'
                shutil.copytree(current, staged)
                result = operation(staged)
                return self.commit(staged), result
