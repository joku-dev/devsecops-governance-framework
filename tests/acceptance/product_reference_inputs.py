"""Supply fixed original comparison data to a private parentless test checkout.

No archived entrypoint is started. Existing tests may explicitly load their
known original functions. No source, baseline, consent or authority is promoted.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import stat
import zlib

from lib.runtime_package import admit, git
from lib.result_bytes import safe_bytes, strict_json
from acceptance.freeze_product_reference_inputs import REFERENCES, AUTHORITY

MAX_ARCHIVE = 16 * 1024**2
MAX_OBJECT = 16 * 1024**2
MAX_OBJECTS = 12000
MAX_TOTAL = 128 * 1024**2


def private_directory(path):
    row = path.lstat()
    if not stat.S_ISDIR(row.st_mode) or row.st_uid != os.geteuid() or row.st_mode & 0o077:
        raise ValueError('private_product_test_directory_required')


def contract(root):
    root = Path(root).resolve(strict=True)
    value = strict_json(safe_bytes(root / 'manifest.json', limit=65536))
    if (type(value) is not dict or set(value) != {'schema_version', 'purpose', 'snapshots', *AUTHORITY}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['purpose'] != 'immutable-original-test-reference-data'
            or any(value[k] is not False for k in AUTHORITY)
            or type(value['snapshots']) is not list or len(value['snapshots']) != len(REFERENCES)):
        raise ValueError('invalid_product_test_reference_contract')
    rows = value['snapshots']
    if [r.get('id') for r in rows if type(r) is dict] != list(REFERENCES):
        raise ValueError('closed_product_test_reference_set_required')
    for row in rows:
        if (set(row) != {'id', 'path', 'source_revision', 'source_tree', 'source_files', 'sha256', 'bytes'}
                or row['path'] != row['id'] + '.zip' or row['source_revision'] != REFERENCES[row['id']]
                or type(row['source_tree']) is not str or not re.fullmatch('[a-f0-9]{40}', row['source_tree'])
                or type(row['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}', row['sha256'])
                or type(row['source_files']) is not int or not 1 <= row['source_files'] <= 10000
                or type(row['bytes']) is not int or not 0 < row['bytes'] <= MAX_ARCHIVE):
            raise ValueError('invalid_product_test_reference_descriptor')
        raw = safe_bytes(root / row['path'], limit=MAX_ARCHIVE)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('product_test_reference_checksum_mismatch')
    return value


def object_bytes(path, oid):
    row = path.lstat()
    if not stat.S_ISREG(row.st_mode) or row.st_nlink != 1:
        raise ValueError('ordinary_product_test_git_object_required')
    compressed = safe_bytes(path, limit=MAX_OBJECT)
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, MAX_OBJECT + 1)
    except zlib.error:
        raise ValueError('invalid_product_test_git_object') from None
    if len(raw) > MAX_OBJECT or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
        raise ValueError('product_test_git_object_budget')
    if hashlib.sha1(raw, usedforsecurity=False).hexdigest() != oid:
        raise ValueError('product_test_git_object_identity_mismatch')
    header, body = raw.split(b'\0', 1)
    kind, size = header.split(b' ', 1)
    if kind not in (b'blob', b'tree', b'commit') or size != str(len(body)).encode():
        raise ValueError('invalid_product_test_git_object')
    return compressed, raw


def prepare(source, expected_revision, input_root, workarea):
    """Only a fresh private shallow clone is eligible; no ordinary worktree edits."""
    source = Path(source).resolve(strict=True)
    private_directory(source)
    git_root = source / '.git'
    if git_root.is_symlink() or not git_root.is_dir():
        raise ValueError('owned_product_test_git_directory_required')
    if Path(git(source, 'rev-parse', '--absolute-git-dir').decode().strip()) != git_root:
        raise ValueError('owned_product_test_git_directory_required')
    if (not re.fullmatch('[a-f0-9]{40}', expected_revision)
            or git(source, 'rev-parse', 'HEAD').decode().strip() != expected_revision
            or git(source, 'status', '--porcelain', '--untracked-files=all')):
        raise ValueError('clean_bound_product_test_checkout_required')
    shallow = git_root / 'shallow'
    if not shallow.is_file() or shallow.is_symlink() or shallow.read_text() != expected_revision + '\n':
        raise ValueError('single_parentless_product_test_snapshot_required')
    value = contract(input_root)  # Verify every archive before any Git effects.
    workarea = Path(workarea).resolve()
    inputs = Path(input_root).resolve(strict=True)
    if (workarea.exists() or workarea.is_symlink() or workarea.is_relative_to(source)
            or source.is_relative_to(workarea) or workarea.is_relative_to(inputs)
            or inputs.is_relative_to(workarea)):
        raise ValueError('fresh_separate_product_test_reference_workarea_required')
    workarea.mkdir(mode=0o700)
    intent = {'schema_version': 1, 'source_revision': expected_revision,
        'source_tree': git(source, 'rev-parse', 'HEAD^{tree}').decode().strip(),
        'state': 'pending', 'snapshots': value['snapshots'], **AUTHORITY}
    (workarea / 'intent.json').write_text(json.dumps(intent, indent=2) + '\n')
    admitted = []
    for row in value['snapshots']:
        target = workarea / row['id']
        manifest = admit(Path(input_root) / row['path'], row['sha256'], target)
        if (manifest['source_commit'] != row['source_revision'] or manifest['source_tree'] != row['source_tree']
                or sum(r['path'].startswith('source/') for r in manifest['files']) != row['source_files']
                or manifest['prepared_dependencies'] or manifest['opa'] is not None):
            raise ValueError('product_test_reference_source_binding_mismatch')
        admitted.append((row, target / 'source/.git/objects'))
    # Admission has reconstructed and checked every complete original tree.
    # Only immutable object data enters this private test Git directory.
    objects = {}; total = 0
    for _, root in admitted:
        for directory in root.iterdir():
            if directory.name in ('info', 'pack'):
                if directory.is_symlink() or not directory.is_dir() or any(directory.iterdir()):
                    raise ValueError('closed_product_test_git_objects_required')
                continue
            if directory.is_symlink() or not directory.is_dir() or not re.fullmatch('[a-f0-9]{2}', directory.name):
                raise ValueError('closed_product_test_git_objects_required')
            for path in directory.iterdir():
                if not re.fullmatch('[a-f0-9]{38}', path.name):
                    raise ValueError('closed_product_test_git_objects_required')
                oid = directory.name + path.name
                compressed, raw = object_bytes(path, oid)
                if oid in objects and objects[oid][1] != raw:
                    raise ValueError('conflicting_product_test_git_objects')
                if oid not in objects:
                    total += len(raw)
                objects[oid] = compressed, raw
                if len(objects) > MAX_OBJECTS or total > MAX_TOTAL:
                    raise ValueError('product_test_reference_object_budget')
    roots = [row['source_revision'] for row in value['snapshots']]
    if {oid for oid, (_, raw) in objects.items() if raw.startswith(b'commit ')} != set(roots):
        raise ValueError('closed_product_test_reference_roots_required')
    for oid, (compressed, raw) in objects.items():
        directory = git_root / 'objects' / oid[:2]
        if directory.is_symlink():
            raise ValueError('ordinary_product_test_git_object_directory_required')
        directory.mkdir(mode=0o700, exist_ok=True)
        target = directory / oid[2:]
        if target.exists() or target.is_symlink():
            if object_bytes(target, oid)[1] != raw:
                raise ValueError('conflicting_product_test_git_objects')
        else:
            with target.open('xb') as stream:
                stream.write(compressed)
            target.chmod(0o400)
    shallow.write_text('\n'.join(sorted({expected_revision, *roots})) + '\n')
    for row in value['snapshots']:
        git(source, 'update-ref', 'refs/axiom-test-inputs/' + row['id'], row['source_revision'])
        if git(source, 'rev-parse', row['source_revision'] + '^{tree}').decode().strip() != row['source_tree']:
            raise ValueError('product_test_reference_tree_changed')
        commit = git(source, 'cat-file', 'commit', row['source_revision'])
        for line in commit.split(b'\n'):
            if line.startswith(b'parent '):
                # Parent objects are not present in these closed snapshots.
                if line[7:].decode() in objects:
                    raise ValueError('unexpected_product_test_parent_history')
    if (git(source, 'rev-parse', 'HEAD').decode().strip() != expected_revision
            or git(source, 'rev-parse', 'HEAD^{tree}').decode().strip() != intent['source_tree']
            or git(source, 'status', '--porcelain', '--untracked-files=all')):
        raise ValueError('product_test_source_changed_by_reference_preparation')
    result = {**intent, 'state': 'complete', 'reference_objects': len(objects),
        'parent_history_downloaded': False, 'archived_entrypoints_started': False,
        'working_source_files_changed': False}
    (workarea / 'prepared.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
