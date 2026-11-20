"""Held, bounded, read-only operational sources and their retained-byte replay."""
from contextlib import contextmanager, ExitStack
import errno
import os
from pathlib import Path, PurePosixPath
import stat

from lib.operations_sources import FILE_ERRORS, record_value, record_values, text, yaml_value
from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL, relative
from lib.providers.validation_worktree import directory, file_bytes, signature
from lib.providers.sbom_export_storage import read_private


RECORD_DIRECTORIES = frozenset(('intake-events', 'collection-attempts', 'results',
                              'architecture-results', 'typed-evidence-results', 'intake-conflicts'))
REGISTRY = 'status/application-repository-integrations.yaml'
SECURITY_MODEL = 'model/controls/governance-repository-security.yaml'


@contextmanager
def held_ancestor(parent, name):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    before = os.fstat(fd)
    try:
        yield fd
        after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        # Ancestors can contain unrelated activity. Bind directory identity,
        # mode and owner without requiring their complete membership to freeze.
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid')
        if any(getattr(before, key) != getattr(value, key)
               for value in (os.fstat(fd), after) for key in fields):
            raise ValueError('operations_source_ancestor_changed')
    finally:
        os.close(fd)


@contextmanager
def held_root(source):
    # Resolve no user-supplied aliases: every ancestor is opened without
    # following symlinks and remains held for the duration of acquisition.
    source = Path(source).expanduser().absolute()
    if '..' in source.parts:
        raise ValueError('operations_source_root_not_normalized')
    with ExitStack() as stack:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, fd)
        for name in source.parts[1:]:
            fd = stack.enter_context(held_ancestor(fd, name))
        yield fd


@contextmanager
def held_parent(root, components, *, absent_ok=False):
    with ExitStack() as stack:
        fd = root
        for name in components:
            fd = stack.enter_context(directory(fd, name))
            if fd is None:
                if not absent_ok:
                    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), '/'.join(components))
                break
        yield fd


def raw_file(root, name):
    relative(name)
    parts = PurePosixPath(name).parts
    with held_parent(root, parts[:-1]) as parent:
        meta = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        if stat.S_ISDIR(meta.st_mode):
            raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), name)
        return file_bytes(parent, parts[-1])


def inventory(parent, prefix):
    """Bounded discovery; path-component sorting agrees with sorted(Path)."""
    found = []
    entries = []
    count = 0

    def walk(fd, path, depth):
        nonlocal count
        if depth > 100:
            raise ValueError('operations_source_depth_budget')
        before = signature(os.fstat(fd))
        with os.scandir(fd) as iterator:
            names = []
            for entry in iterator:
                count += 1
                if count > MAX_FILES:
                    raise ValueError('operations_source_membership_budget')
                names.append(entry.name)
        for name in sorted(names):
            target = path + '/' + name
            relative(target)
            meta = os.stat(name, dir_fd=fd, follow_symlinks=False)
            entries.append((target, signature(meta)))
            if name.endswith('.json'):
                found.append(target)
            if stat.S_ISDIR(meta.st_mode):
                with directory(fd, name) as child:
                    if child is None:
                        raise ValueError('operations_source_membership_changed')
                    walk(child, target, depth + 1)
            elif not stat.S_ISREG(meta.st_mode):
                raise ValueError('operations_source_unsafe_member')
        if before != signature(os.fstat(fd)):
            raise ValueError('operations_source_directory_changed')

    walk(parent, prefix, 0)
    return sorted(found, key=PurePosixPath), entries


class NativeSources:
    """No executable from the supplied source tree is loaded or invoked."""
    def __init__(self, source, record, indexes):
        self.source = Path(source)
        self.record = record
        self.indexes = dict(indexes)
        self.total = 0
        self.allowed_files = {REGISTRY, SECURITY_MODEL}
        for name in self.indexes.values():
            relative(name)
            if '/' in name or not name.endswith('.json'):
                raise ValueError('operations_source_index_profile_invalid')
            self.allowed_files.add('status/' + name)

    def account(self, raw):
        self.total += len(raw)
        if len(raw) > MAX_FILE or self.total > MAX_TOTAL:
            raise ValueError('operations_source_total_budget')
        return raw

    def read_bytes(self, name):
        if name not in self.allowed_files:
            raise ValueError('operations_source_file_not_selected')

        def effect():
            with held_root(self.source) as root:
                return self.account(raw_file(root, name))
        return self.record.perform('operations_source_file', {'name': name}, effect, encoding='bytes')

    def registry(self):
        return yaml_value(self.read_bytes(REGISTRY))

    def index_domains(self):
        return self.indexes

    def index(self, domain):
        import json
        return json.loads(text(self.read_bytes('status/' + self.indexes[domain])))

    def security_model(self):
        return yaml_value(self.read_bytes(SECURITY_MODEL))

    def records(self, selected):
        if selected not in RECORD_DIRECTORIES:
            raise ValueError('operations_source_directory_not_selected')

        def effect():
            value = {'members': [], 'reads': [], 'stopped': None}
            prefix = 'status/' + selected
            with held_root(self.source) as root, held_parent(root, prefix.split('/'), absent_ok=True) as parent:
                if parent is None:
                    return value
                names, before = inventory(parent, prefix)
                value['members'] = names
                for name in names:
                    try:
                        raw = self.account(raw_file(root, name))
                    except (OSError, ValueError) as error:
                        if type(error).__name__ not in FILE_ERRORS:
                            raise
                        value['stopped'] = {'kind': 'read', 'name': name,
                                            'exception': type(error).__name__, 'message': str(error)}
                        break
                    value['reads'].append({'name': name, 'body': self.record.blob(raw)})
                    try:
                        record_value(raw, name)
                    except (ValueError, TypeError) as error:
                        value['stopped'] = {'kind': 'decode', 'name': name,
                                            'exception': type(error).__name__, 'message': str(error)}
                        break
                if (names, before) != inventory(parent, prefix):
                    raise ValueError('operations_source_membership_or_bytes_changed')
            return value

        value = self.record.perform('operations_source_records', {'directory': selected}, effect)
        def retained_blob(ref):
            import hashlib
            raw = read_private(self.record.blobs / ref['sha256'], MAX_FILE)
            if len(raw) != ref['bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise ValueError('operations_source_retained_bytes_changed')
            return raw
        return record_values(value, retained_blob, directory=selected)


class RetainedSources(NativeSources):
    """Use only retained bytes; no current root, files, clock or native process."""
    def __init__(self, calls, indexes):
        # Deliberately no native base initialization/source path.
        self.calls = calls
        self.indexes = dict(indexes)
        self.total = 0
        self.allowed_files = {REGISTRY, SECURITY_MODEL, *('status/' + name for name in self.indexes.values())}

    def read_bytes(self, name):
        if name not in self.allowed_files:
            raise ValueError('operations_source_file_not_selected')
        return self.account(self.calls.call('operations_source_file', {'name': name}, encoding='bytes'))

    def records(self, selected):
        if selected not in RECORD_DIRECTORIES:
            raise ValueError('operations_source_directory_not_selected')
        value = self.calls.call('operations_source_records', {'directory': selected})
        return record_values(value, lambda ref: self.account(self.calls.blob(ref)), directory=selected)
