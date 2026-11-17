"""Bounded private copies of CI bundle bytes; never executes inspected content."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

from lib.portable.contracts import canonical_digest
from lib.safe_archive import safe_extract_zip

MAX_MEMBERS = 4096
MAX_MEMBER = 256 * 1024**2
MAX_MATERIAL = 1024**3
MAX_ARCHIVE = 2 * 1024**3
DEFAULT_BUDGET = 2 * 1024**3
MAX_BUDGET = 32 * 1024**3
RESERVE = 8 * 1024**3
CHUNK = 1024**2


def normalized_name(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '..' in path.parts or str(path) != value
            or '\\' in value or ':' in value or any(ord(c) < 32 for c in value)):
        raise ValueError('unsafe_ci_bundle_path')
    return path


def names_are_portable(names):
    """Include implied parents, which ZIP entries need not declare explicitly."""
    spellings = {}
    for name in names:
        path = normalized_name(name)
        for index in range(1, len(path.parts) + 1):
            prefix = '/'.join(path.parts[:index]); key = prefix.casefold()
            if key in spellings and spellings[key] != prefix:
                raise ValueError('ambiguous_ci_bundle_path_case')
            spellings[key] = prefix


def hash_file(path, limit):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError('invalid_ci_bundle_file')
        digest = hashlib.sha256(); size = 0
        while block := stream.read(CHUNK):
            size += len(block)
            if size > limit: raise ValueError('ci_bundle_file_limit')
            digest.update(block)
        if size != metadata.st_size: raise ValueError('ci_bundle_source_changed')
    return {'sha256': digest.hexdigest(), 'bytes': size}


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir(): raise ValueError('unsafe_ci_bundle_directory')
    files = {}; names = []; total = 0; count = 0
    for directory, folders, filenames in os.walk(root, followlinks=False):
        for name in [*folders, *filenames]:
            path = Path(directory) / name
            if path.is_symlink(): raise ValueError('unsafe_ci_bundle_symlink')
            relative = path.relative_to(root).as_posix(); normalized_name(relative)
            names.append(relative); count += 1
            if count > MAX_MEMBERS: raise ValueError('ci_bundle_member_limit')
        for name in filenames:
            path = Path(directory) / name
            item = hash_file(path, MAX_MEMBER); total += item['bytes']
            if total > MAX_MATERIAL: raise ValueError('ci_bundle_material_limit')
            files[path.relative_to(root).as_posix()] = item
    names_are_portable(names)
    return dict(sorted(files.items()))


def describe(source):
    source = Path(source)
    if source.is_symlink(): raise ValueError('unsafe_ci_bundle_source')
    if source.is_dir():
        files = inventory(source)
        return {'kind': 'directory', 'input_sha256': canonical_digest(files), 'files': files,
                'raw_bytes': 0, 'material_bytes': sum(item['bytes'] for item in files.values())}
    if source.suffix.lower() != '.zip': raise ValueError('ci_bundle_zip_or_directory_required')
    item = hash_file(source, MAX_ARCHIVE)
    return {'kind': 'zip', 'input_sha256': item['sha256'], 'raw_bytes': item['bytes']}


def reserve(path, pending=0):
    if shutil.disk_usage(path).free - pending < RESERVE:
        raise ValueError('ci_bundle_free_space_reserve')


def copy_file(source, destination, *, limit, expected, budget):
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    digest = hashlib.sha256(); size = 0
    with os.fdopen(descriptor, 'rb') as incoming:
        if not stat.S_ISREG(os.fstat(incoming.fileno()).st_mode): raise ValueError('unsafe_ci_bundle_file')
        with destination.open('xb') as outgoing:
            destination.chmod(0o600)
            while block := incoming.read(CHUNK):
                size += len(block)
                if size > limit or size > budget: raise ValueError('ci_bundle_storage_budget_exhausted')
                reserve(destination.parent, len(block)); outgoing.write(block); digest.update(block)
    actual = {'sha256': digest.hexdigest(), 'bytes': size}
    if actual != expected: raise ValueError('ci_bundle_source_changed')
    return size


def private_parents(root, relative):
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink(): raise ValueError('unsafe_ci_bundle_target')
        current.mkdir(mode=0o700, exist_ok=True)


def extract_archive(archive, material, *, raw_bytes, budget):
    """Recompute material from retained ZIP bytes with the same initial bounds."""
    archive = Path(archive); material = Path(material)
    with zipfile.ZipFile(archive) as zipped:
        infos = zipped.infolist()
        if len(infos) > MAX_MEMBERS: raise ValueError('ci_bundle_member_limit')
        names_are_portable(PurePosixPath(info.filename.replace('\\', '/')).as_posix().rstrip('/')
                           for info in infos)
        size = sum(info.file_size for info in infos)
    if raw_bytes + size > budget: raise ValueError('ci_bundle_storage_budget_exhausted')
    reserve(material.parent, size)
    safe_extract_zip(archive, material, max_members=MAX_MEMBERS, max_member_bytes=MAX_MEMBER,
                     max_total_bytes=MAX_MATERIAL)
    for path in material.rglob('*'):
        path.chmod(0o700 if path.is_dir() else 0o600)
    return inventory(material)


def copy_bundle(source, expected_sha256, destination, *, budget=DEFAULT_BUDGET):
    if type(budget) is not int or not 0 < budget <= MAX_BUDGET:
        raise ValueError('invalid_ci_bundle_storage_budget')
    source = Path(source); destination = Path(destination)
    if (destination.exists() or destination.is_symlink()
            or any(p.is_symlink() for p in destination.absolute().parents)):
        raise ValueError('fresh_private_ci_bundle_required')
    initial = describe(source)
    if initial['input_sha256'] != expected_sha256: raise ValueError('ci_bundle_digest_mismatch')
    destination.mkdir(mode=0o700)
    material = destination / 'material'; material.mkdir(mode=0o700)
    if initial['kind'] == 'directory':
        if initial['material_bytes'] > budget: raise ValueError('ci_bundle_storage_budget_exhausted')
        reserve(destination, initial['material_bytes']); copied = 0
        for name, expected in initial['files'].items():
            relative = normalized_name(name); private_parents(material, relative)
            copied += copy_file(source / name, material / name, limit=MAX_MEMBER, expected=expected, budget=budget - copied)
    else:
        if initial['raw_bytes'] > budget: raise ValueError('ci_bundle_storage_budget_exhausted')
        archive = destination / 'source.zip'
        copy_file(source, archive, limit=MAX_ARCHIVE,
            expected={'sha256': expected_sha256, 'bytes': initial['raw_bytes']}, budget=budget)
        extract_archive(archive, material, raw_bytes=initial['raw_bytes'], budget=budget)
    files = inventory(material)
    if initial['kind'] == 'directory' and files != initial['files']:
        raise ValueError('ci_bundle_source_changed')
    reserve(destination)
    return {**initial, 'files': files, 'material_bytes': sum(item['bytes'] for item in files.values())}


def verify_directory(material, expected):
    """Directory-origin input has exactly one retained, immutable file copy."""
    files = inventory(material)
    if files != expected['files'] or canonical_digest(files) != expected['input_sha256']:
        raise ValueError('ci_bundle_retained_bytes_changed')
    return files
