"""Retain exact Git commit/tree/blob proof without executing inspected code."""
import base64
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from lib.ci_bundle_storage import names_are_portable, reserve
from lib.functional_parity import git_read
from lib.result_bytes import safe_bytes
from lib.source_collection import snapshot
from lib.v2_boundary import safe_source

MAX_FILES = 10000
MAX_FILE = 16 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_MANIFEST = 4 * 1024**2
MAX_COMMIT = 64 * 1024
MAX_PATH = 4096


def portable_source_names(names):
    names_are_portable(names)
    spellings = {}
    for name in names:
        parts = Path(name).parts
        if any(unicodedata.normalize('NFC', part.casefold()) == '.git' for part in parts):
            raise ValueError('unsafe_source_metadata_name')
        for index in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:index]); key = unicodedata.normalize('NFC', prefix.casefold())
            if key in spellings and spellings[key] != prefix:
                raise ValueError('ambiguous_source_unicode_name')
            spellings[key] = prefix


def object_sha(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False).hexdigest()


def tree_sha(files):
    root = {}
    for name, row in files.items():
        parts = name.split('/'); node = root
        for part in parts[:-1]:
            if part in node and not isinstance(node[part], dict): raise ValueError('source_path_collision')
            node = node.setdefault(part, {})
        if parts[-1] in node: raise ValueError('source_path_collision')
        node[parts[-1]] = (row['mode'], row['git_blob'])
    # Postorder traversal avoids depending on Python's recursion limit for
    # deeply nested yet bounded Git paths.
    digests = {}; pending = [(root, False)]
    while pending:
        node, visited = pending.pop()
        if not visited:
            pending.append((node, True))
            pending.extend((entry, False) for entry in node.values() if isinstance(entry, dict))
            continue
        body = b''
        for name, entry in sorted(node.items(), key=lambda item: (item[0] + ('/' if isinstance(item[1], dict) else '')).encode()):
            mode, identity = ('40000', digests[id(entry)]) if isinstance(entry, dict) else entry
            body += mode.encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(identity)
        digests[id(node)] = object_sha('tree', body)
    return digests[id(root)]


def verify(data, manifest):
    if Path(data).is_symlink(): raise ValueError('unsafe_source_data')
    data = Path(data).resolve()
    if set(manifest) != {'schema_version', 'commit', 'tree', 'commit_object_base64', 'files'} or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('invalid_source_manifest')
    if any(not isinstance(manifest[k], str) or not re.fullmatch('[a-f0-9]{40}', manifest[k]) for k in ('commit', 'tree')):
        raise ValueError('invalid_source_commit')
    if len((json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()) > MAX_MANIFEST: raise ValueError('source_manifest_budget')
    commit = base64.b64decode(manifest['commit_object_base64'], validate=True)
    if len(commit) > MAX_COMMIT or object_sha('commit', commit) != manifest['commit']:
        raise ValueError('source_commit_changed')
    if commit.split(b'\n', 1)[0] != b'tree ' + manifest['tree'].encode(): raise ValueError('source_commit_tree_changed')
    files = manifest['files']
    if not isinstance(files, dict) or not files or len(files) > MAX_FILES: raise ValueError('source_member_budget')
    if any(len(name.encode()) > MAX_PATH for name in files): raise ValueError('source_path_budget')
    portable_source_names(files)
    if data.is_symlink() or not data.is_dir(): raise ValueError('unsafe_source_data')
    actual = set(); actual_directories = set()
    expected_directories = {p.as_posix() for name in files for p in Path(name).parents if p != Path('.')}
    for path in data.rglob('*'):
        if path.is_symlink(): raise ValueError('unsafe_source_data')
        if path.is_file(): actual.add(path.relative_to(data).as_posix())
        elif path.is_dir(): actual_directories.add(path.relative_to(data).as_posix())
        else: raise ValueError('unsafe_source_data')
        if len(actual) > MAX_FILES: raise ValueError('source_member_budget')
    if actual != set(files) or actual_directories != expected_directories: raise ValueError('source_members_changed')
    size = 0
    for name, row in files.items():
        path = safe_source(data, name)
        if '.git' in Path(name).parts or set(row) != {'mode', 'git_blob', 'bytes', 'sha256'} or row['mode'] not in ('100644', '100755'):
            raise ValueError('unsafe_source_member')
        if type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_FILE: raise ValueError('source_file_budget')
        size += row['bytes']
        if size > MAX_TOTAL: raise ValueError('source_total_budget')
        raw = safe_bytes(path, limit=MAX_FILE)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256'] or object_sha('blob', raw) != row['git_blob']:
            raise ValueError('source_blob_changed')
    if tree_sha(files) != manifest['tree']: raise ValueError('source_tree_changed')
    return manifest


def capture(repository, revision, data):
    repository = Path(repository).resolve()
    if Path(data).is_symlink(): raise ValueError('unsafe_source_data')
    data = Path(data).resolve()
    if Path(git_read(repository, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != repository:
        raise ValueError('source_repository_root_required')
    if not re.fullmatch('[a-f0-9]{40}', revision) or git_read(repository, 'rev-parse', '--verify', revision + '^{commit}').decode().strip() != revision:
        raise ValueError('source_exact_commit_required')
    size = int(git_read(repository, 'cat-file', '-s', revision))
    if not 0 < size <= MAX_COMMIT: raise ValueError('source_commit_budget')
    commit = git_read(repository, 'cat-file', 'commit', revision)
    rows = git_read(repository, 'ls-tree', '-r', '-l', '-z', revision)
    if len(rows) > MAX_MANIFEST: raise ValueError('source_manifest_budget')
    files = {}; total = 0
    for raw in filter(None, rows.split(b'\0')):
        meta, name = raw.split(b'\t', 1); mode, kind, blob, length = meta.decode().split(); name = name.decode()
        safe_source(data, name)
        if kind != 'blob' or mode not in ('100644', '100755') or '.git' in Path(name).parts: raise ValueError('unsafe_source_member')
        length = int(length); total += length
        if not 0 <= length <= MAX_FILE or total > MAX_TOTAL or len(files) >= MAX_FILES: raise ValueError('source_member_budget')
        if name in files: raise ValueError('source_path_collision')
        files[name] = {'mode': mode, 'git_blob': blob, 'bytes': length}
    if any(len(name.encode()) > MAX_PATH for name in files): raise ValueError('source_path_budget')
    portable_source_names(files)
    if object_sha('commit', commit) != revision: raise ValueError('source_commit_changed')
    if commit.split(b'\n', 1)[0] != b'tree ' + tree_sha(files).encode(): raise ValueError('source_tree_changed')
    reserve(data.parent, total + MAX_MANIFEST + MAX_COMMIT)
    binding = snapshot(repository, revision, data)
    for name, row in files.items(): row['sha256'] = binding['files'][name]
    manifest = {'schema_version': 1, 'commit': revision, 'tree': binding['tree'],
                'commit_object_base64': base64.b64encode(commit).decode(), 'files': files}
    return verify(data, manifest)
