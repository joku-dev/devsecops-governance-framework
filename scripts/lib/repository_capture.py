"""Closed inert repository inputs, independent of a live checkout or provider.

The two profiles distinguish committed Git bytes from actual working files.
Captures never supply executable programs, personal consent or node authority.
"""
import hashlib
import json
from pathlib import PurePosixPath
import re

from lib.ci_bundle_storage import names_are_portable
from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL, relative

COMMITTED = 'committed-product-repository-v1'
WORKING = 'working-tree-product-repository-v1'
PROFILES = (COMMITTED, WORKING)
MAX_MANIFEST = 4 * 1024**2
DATA_ROOTS = frozenset(('.agents', '.codex', '.github', 'adoption-package', 'apps',
    'architecture', 'config', 'demo', 'doc-as-code', 'docs', 'examples', 'generated',
    'governance', 'infra', 'model', 'pipeline-baseline', 'policies', 'releases',
    'schemas', 'scripts', 'status', 'templates', 'tests'))
PRIVATE_PARTS = frozenset(('.git', '.aws', '.azure', '.ssh', '.gnupg', '.kube',
    '.local', '.cache', '.secrets', '__pycache__', 'node_modules', '.ds_store',
    '.idea', '.vscode', '.pytest_cache', '.ruff_cache'))


def path_name(name):
    if type(name) is not str or not name:
        raise ValueError('repository_capture_path_required')
    relative(name)
    if len(name.encode('utf-8')) > 4096 or len(PurePosixPath(name).parts) > 100:
        raise ValueError('repository_capture_path_budget')
    return name


def private_name(name):
    parts = PurePosixPath(name).parts
    leaf = parts[-1].casefold()
    return (any(part.casefold() in PRIVATE_PARTS or part.casefold().startswith('.venv')
                or part.casefold() == 'venv' for part in parts)
            or (leaf == '.env' or leaf.startswith('.env.')) and leaf not in ('.env.example', '.env.sample', '.env.template')
            or leaf in ('id_ed25519', 'id_rsa', 'id_ecdsa', 'credentials', '.netrc')
            or PurePosixPath(leaf).suffix in ('.pem', '.key', '.p12', '.pfx'))


def admitted(name, inventory):
    path_name(name)
    return not private_name(name) and (name in inventory or PurePosixPath(name).parts[0] in DATA_ROOTS)


def object_id(value, algorithm):
    length = {'sha1': 40, 'sha256': 64}.get(algorithm)
    if length is None or type(value) is not str or re.fullmatch('[a-f0-9]{' + str(length) + '}', value) is None:
        raise ValueError('repository_capture_git_identity_required')
    return value


def object_digest(kind, raw, algorithm):
    if type(raw) is not bytes or kind not in ('blob', 'tree', 'commit') or algorithm not in ('sha1', 'sha256'):
        raise ValueError('repository_capture_git_object_required')
    value = kind.encode('ascii') + b' ' + str(len(raw)).encode('ascii') + b'\0' + raw
    return hashlib.new(algorithm, value, usedforsecurity=False).hexdigest()


def git_order(name, inventory, parent):
    path = '/'.join(filter(None, (parent, name)))
    return name.encode('utf-8') + (b'/' if inventory[path]['kind'] == 'tree' else b'')


def tree_directories(inventory):
    result = {'': []}
    for name, row in inventory.items():
        if row['kind'] == 'tree':
            result[name] = []
    for name in inventory:
        path = PurePosixPath(name)
        parent = '' if str(path.parent) == '.' else str(path.parent)
        if parent not in result:
            raise ValueError('repository_capture_git_parent_missing')
        result[parent].append(path.name)
    for name, children in result.items():
        children.sort(key=lambda child: git_order(child, inventory, name))
    return result


def check_inventory(inventory, *, tree, algorithm):
    object_id(tree, algorithm)
    if type(inventory) is not dict or not inventory or len(inventory) > MAX_FILES:
        raise ValueError('repository_capture_inventory_budget')
    total = 0
    for name, row in inventory.items():
        path_name(name)
        if private_name(name):
            raise ValueError('private_tracked_file_prevents_repository_capture')
        if (type(row) is not dict or set(row) != {'kind', 'mode', 'git_object', 'bytes'}
                or row['kind'] not in ('tree', 'blob')):
            raise ValueError('invalid_repository_capture_git_entry')
        object_id(row['git_object'], algorithm)
        if row['kind'] == 'tree':
            if row['mode'] != '040000' or row['bytes'] is not None:
                raise ValueError('invalid_repository_capture_git_directory')
        else:
            if row['mode'] not in ('100644', '100755') or type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_FILE:
                raise ValueError('repository_capture_file_budget')
            total += row['bytes']
    if total > MAX_TOTAL:
        raise ValueError('repository_capture_total_budget')
    names_are_portable(inventory)
    directories = tree_directories(inventory)
    for parent in sorted(directories, key=lambda value: len(PurePosixPath(value).parts), reverse=True):
        raw = bytearray()
        for child in directories[parent]:
            name = '/'.join(filter(None, (parent, child)))
            row = inventory[name]
            mode = '40000' if row['kind'] == 'tree' else row['mode']
            raw.extend(mode.encode('ascii') + b' ' + child.encode('utf-8') + b'\0' + bytes.fromhex(row['git_object']))
        expected = tree if not parent else inventory[parent]['git_object']
        if object_digest('tree', bytes(raw), algorithm) != expected:
            raise ValueError('repository_capture_git_tree_differs')
    return directories


def parse_tree(raw, *, tree, algorithm):
    if type(raw) is not bytes or len(raw) > MAX_MANIFEST or not raw.endswith(b'\0'):
        raise ValueError('repository_capture_tree_listing_budget')
    inventory = {}
    for item in raw.split(b'\0')[:-1]:
        try:
            fields, name = item.split(b'\t', 1)
            mode, kind, oid, size = fields.decode('ascii').split()
            name = name.decode('utf-8')
            size = None if size == '-' else int(size)
        except (ValueError, UnicodeError):
            raise ValueError('invalid_repository_capture_tree_listing') from None
        path_name(name)
        if name in inventory or len(inventory) >= MAX_FILES:
            raise ValueError('repository_capture_inventory_budget')
        inventory[name] = {'kind': kind, 'mode': mode, 'git_object': oid, 'bytes': size}
    check_inventory(inventory, tree=tree, algorithm=algorithm)
    return inventory


def check_commit(raw, *, revision, tree, algorithm):
    object_id(revision, algorithm)
    object_id(tree, algorithm)
    if type(raw) is not bytes or len(raw) > MAX_MANIFEST or object_digest('commit', raw, algorithm) != revision:
        raise ValueError('repository_capture_commit_differs')
    header = raw.partition(b'\n\n')[0].splitlines()
    trees = [line[5:] for line in header if line.startswith(b'tree ')]
    if not header or header[0] != b'tree ' + tree.encode('ascii') or trees != [tree.encode('ascii')]:
        raise ValueError('repository_capture_commit_tree_differs')


def file_descriptor(raw, mode, algorithm):
    if type(raw) is not bytes or len(raw) > MAX_FILE or mode not in ('100644', '100755'):
        raise ValueError('repository_capture_file_budget')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': mode,
            'git_blob': object_digest('blob', raw, algorithm)}


def make_manifest(*, profile, source_root, revision, tree, algorithm, inventory, files, modes, directories, commit):
    value = {'schema_version': 1, 'profile': profile, 'source_root': source_root, 'revision': revision,
        'tree': tree, 'object_format': algorithm, 'inventory': inventory,
        'files': {name: file_descriptor(raw, modes[name], algorithm) for name, raw in files.items()},
        'directories': directories, 'commit': {'bytes': len(commit), 'sha256': hashlib.sha256(commit).hexdigest()}}
    check_capture(value, files, commit, revision=revision, tree=tree)
    return value


def check_capture(value, files, commit, *, revision, tree=None):
    if (type(value) is not dict or set(value) != {'schema_version', 'profile', 'source_root', 'revision', 'tree',
            'object_format', 'inventory', 'files', 'directories', 'commit'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['profile'] not in PROFILES or value['revision'] != revision
            or tree is not None and value['tree'] != tree):
        raise ValueError('invalid_repository_capture_manifest')
    root = value['source_root']
    if (type(root) is not str or not root or not PurePosixPath(root).is_absolute()
            or str(PurePosixPath(root)) != root or '..' in PurePosixPath(root).parts
            or len(root.encode('utf-8')) > 8192 or any(ord(c) < 32 for c in root)):
        raise ValueError('invalid_repository_capture_source_label')
    algorithm = value['object_format']
    expected_directories = check_inventory(value['inventory'], tree=value['tree'], algorithm=algorithm)
    check_commit(commit, revision=revision, tree=value['tree'], algorithm=algorithm)
    if value['commit'] != {'bytes': len(commit), 'sha256': hashlib.sha256(commit).hexdigest()}:
        raise ValueError('repository_capture_commit_descriptor_differs')
    if (type(files) is not dict or type(value['files']) is not dict or set(files) != set(value['files'])
            or not files or len(files) > MAX_FILES or any(type(raw) is not bytes for raw in files.values())
            or sum(map(len, files.values())) > MAX_TOTAL):
        raise ValueError('repository_capture_file_set_differs')
    for name, raw in files.items():
        if not admitted(name, value['inventory']):
            raise ValueError('repository_capture_input_scope_differs')
        row = value['files'][name]
        if (type(row) is not dict or type(row.get('bytes')) is not int
                or row != file_descriptor(raw, row.get('mode'), algorithm)):
            raise ValueError('repository_capture_file_descriptor_differs')
    directories = value['directories']
    if type(directories) is not dict or '' not in directories or len(directories) + len(files) > MAX_FILES:
        raise ValueError('repository_capture_directory_budget')
    for parent, children in directories.items():
        if parent:
            if not admitted(parent, value['inventory']) or parent in files:
                raise ValueError('repository_capture_directory_scope_differs')
        if (type(children) is not list or any(type(name) is not str or '/' in name or name in ('', '.', '..') for name in children)
                or len(set(children)) != len(children)):
            raise ValueError('invalid_repository_capture_directory_membership')
    actual_children = {name: set() for name in directories}
    for name in set(files) | (set(directories) - {''}):
        path = PurePosixPath(name)
        parent = '' if str(path.parent) == '.' else str(path.parent)
        if parent not in actual_children:
            raise ValueError('repository_capture_directory_parent_missing')
        actual_children[parent].add(path.name)
    if any(set(directories[name]) != children for name, children in actual_children.items()):
        raise ValueError('repository_capture_directory_membership_differs')
    names_are_portable(set(files) | (set(directories) - {''}))
    if value['profile'] == COMMITTED:
        expected_files = {name: row for name, row in value['inventory'].items() if row['kind'] == 'blob'}
        if set(files) != set(expected_files) or directories != expected_directories:
            raise ValueError('repository_capture_committed_membership_differs')
        for name, row in expected_files.items():
            captured = value['files'][name]
            if (captured['git_blob'], captured['bytes'], captured['mode']) != (row['git_object'], row['bytes'], row['mode']):
                raise ValueError('repository_capture_committed_bytes_differ')
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_MANIFEST:
        raise ValueError('repository_capture_manifest_budget')
    return value
