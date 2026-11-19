"""Closed local candidate-data acquisition; source programs and providers never run."""
from pathlib import Path, PurePosixPath
import hashlib
import re

from lib.functional_parity import git_read, metadata_bytes
from lib import attestation_files
from lib.review_receipt_files import optional_read
import os
import stat
import secrets

PREFIX = 'status/portable/v2/candidates'
ANCESTORS = ('status', 'status/portable', 'status/portable/v2', PREFIX)
MAX_FILES = 50000
MAX_BYTES = 128 * 1024**2
MAX_FILE = 65536
MAX_TREE = 32 * 1024**2
PROFILE = 'legacy-portable-candidate-index-v1'
MAX_OUTPUT = 512 * 1024**2


def capture(root, revision=None):
    return working(root) if revision is None else committed(root, revision)


def output_destination(path, source_root, *, excluded):
    path = attestation_files.destination(path, excluded)
    source_root = Path(source_root).resolve()
    if path.is_relative_to(source_root) and path != source_root/'generated/portable-intake/index.json':
        raise ValueError('candidate_index_only_generated_output_inside_source')
    return path


def observe_output(path):
    parent = attestation_files.parent(path)
    if parent is None: return None, None
    try:
        raw = optional_read(parent, path.name, MAX_OUTPUT)
        if raw is None: return None, None
        row = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if (not stat.S_ISREG(row.st_mode) or row.st_nlink != 1 or row.st_uid != os.geteuid()
                or row.st_mode & 0o022):
            raise ValueError('candidate_index_owned_regular_output_required')
        metadata = {key: getattr(row, key) for key in
                    ('st_dev', 'st_ino', 'st_size', 'st_mode', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')}
        if optional_read(parent, path.name, MAX_OUTPUT) != raw:
            raise ValueError('candidate_index_output_changed_during_observation')
        return raw, metadata
    finally: os.close(parent)


def replace_output(path, raw, before, metadata):
    """Original atomic replacement; caller durably retains before bytes and intent."""
    if len(raw) > MAX_OUTPUT: raise ValueError('candidate_index_output_budget')
    parent = attestation_files.parent(path, create=True)
    temporary = '.candidate-index-' + secrets.token_hex(16)
    try:
        observed = optional_read(parent, path.name, MAX_OUTPUT)
        if observed != before: raise ValueError('candidate_index_external_output_changed')
        if metadata is not None:
            row = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if any(getattr(row, key) != value for key, value in metadata.items()):
                raise ValueError('candidate_index_external_output_changed')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        if optional_read(parent, path.name, MAX_OUTPUT) != before:
            raise ValueError('candidate_index_external_output_changed')
        os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
        if optional_read(parent, path.name, MAX_OUTPUT) != raw:
            raise ValueError('candidate_index_external_output_changed_after_write')
    finally:
        try: os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError: pass
        os.close(parent)


def _budget(count, size, total, limit, byte_limit):
    if count > limit or size > MAX_FILE or total > byte_limit:
        raise ValueError('candidate_index_budget_exceeded')


def working(root, *, limit=MAX_FILES, byte_limit=MAX_BYTES):
    """Keep the original traversal/quota rules; additionally hold regular files."""
    root = Path(root).resolve()
    source = root/PREFIX
    if (any((root/name).is_symlink() for name in ANCESTORS)
            or not source.resolve().is_relative_to(root)):
        raise ValueError('candidate_source_symlink')
    files = {}
    total = 0
    directories = []
    for visited, path in enumerate(source.rglob('*') if source.exists() else [], 1):
        if visited > 3*limit+4:
            raise ValueError('candidate_index_budget_exceeded')
        if path.is_symlink():
            raise ValueError('candidate_member_symlink')
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(relative)
            continue
        size = path.stat().st_size
        _budget(len(files)+1, size, total+size, limit, byte_limit)
        if path.suffix != '.json':
            raise ValueError('unexpected_candidate_member')
        raw = metadata_bytes(path.parent, path.name, min(MAX_FILE, byte_limit-total))
        _budget(len(files)+1, len(raw), total+len(raw), limit, byte_limit)
        files[relative] = raw
        total += len(raw)
    return {'mode': 'working', 'root': str(root), 'revision': None,
            'directories': directories}, files


def committed(root, revision, *, limit=MAX_FILES, byte_limit=MAX_BYTES):
    """Read exact named product Git objects, including sparse unmaterialized data."""
    root = Path(root).resolve()
    if not isinstance(revision, str) or not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', revision):
        raise ValueError('candidate_source_revision_required')
    if git_read(root, 'rev-parse', '--verify', revision+'^{commit}').decode().strip() != revision:
        raise ValueError('candidate_source_revision_required')
    raw_tree = git_read(root, 'ls-tree', '-r', '-t', '-l', '-z', revision)
    if len(raw_tree) > MAX_TREE:
        raise ValueError('candidate_source_tree_budget')
    files = {}
    directories = []
    total = 0
    visited = 0
    for entry in filter(None, raw_tree.split(b'\0')):
        meta, raw_name = entry.split(b'\t', 1)
        mode, kind, blob, size = meta.decode().split()
        name = raw_name.decode()
        if name in ANCESTORS and mode in ('120000', '160000'):
            raise ValueError('candidate_source_symlink_or_submodule')
        if not name.startswith(PREFIX+'/'):
            continue
        visited += 1
        if visited > 3*limit+4:
            raise ValueError('candidate_index_budget_exceeded')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('candidate_source_path')
        if kind == 'tree':
            directories.append(name)
            continue
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise ValueError('candidate_member_symlink_or_submodule')
        size = int(size)
        _budget(len(files)+1, size, total+size, limit, byte_limit)
        if path.suffix != '.json':
            raise ValueError('unexpected_candidate_member')
        raw = git_read(root, 'cat-file', 'blob', blob)
        algorithm = hashlib.sha1 if len(blob) == 40 else hashlib.sha256
        identity = algorithm(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if len(raw) != size or identity != blob:
            raise ValueError('candidate_source_blob_changed')
        files[name] = raw
        total += size
    return {'mode': 'committed', 'root': str(root), 'revision': revision,
            'directories': directories}, files
