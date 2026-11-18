"""Bounded inert validation inputs with a stable original display context."""
import errno
from fnmatch import fnmatchcase
import io
import os
from pathlib import PurePosixPath

MAX_FILES = 10000
MAX_FILE = 16 * 1024**2
MAX_TOTAL = 128 * 1024**2
WORKING_PROFILE = 'working-tree-offline-v1'


def relative(name):
    value = PurePosixPath(name)
    if (not isinstance(name, str) or value.is_absolute() or '..' in value.parts
            or str(value) != name or '\\' in name or ':' in name
            or any(ord(c) < 32 for c in name)):
        raise ValueError('unsafe_validation_input_name')
    return name


class ValidationFiles:
    def __init__(self, files, membership=None, *, label='/validation-source', native_profile='product'):
        if native_profile not in ('product', WORKING_PROFILE):
            raise ValueError('invalid_validation_native_profile')
        self.native_profile = native_profile
        if (not isinstance(label, str) or not label.startswith('/') or '\\' in label
                or '..' in PurePosixPath(label).parts or len(label) > 8192 or any(ord(c) < 32 for c in label)):
            raise ValueError('invalid_validation_display_root')
        self.label = label.rstrip('/')
        self.files = dict(files)
        self.membership = set(self.files if membership is None else membership)
        if not set(self.files) <= self.membership or len(self.membership) > MAX_FILES:
            raise ValueError('validation_input_membership_budget')
        for name in self.membership:
            relative(name)
        if (any(not isinstance(raw, bytes) or len(raw) > MAX_FILE for raw in self.files.values())
                or sum(map(len, self.files.values())) > MAX_TOTAL):
            raise ValueError('validation_input_byte_budget')
        self.root = ValidationPath(self, '')

    def directories(self):
        return {str(parent) if parent != PurePosixPath('.') else ''
                for name in self.membership for parent in PurePosixPath(name).parents}

    def write(self, name, raw):
        relative(name)
        previous = self.files.get(name, b'')
        if (not isinstance(raw, bytes) or len(raw) > MAX_FILE
                or sum(map(len, self.files.values())) - len(previous) + len(raw) > MAX_TOTAL
                or name not in self.membership and len(self.membership) >= MAX_FILES):
            raise ValueError('validation_output_budget')
        self.files[name] = raw
        self.membership.add(name)


class ValidationPath:
    def __init__(self, files, name):
        self.files = files
        self.relative = relative(name) if name else ''

    def __truediv__(self, name):
        name = os.fspath(name)
        relative(name)
        return ValidationPath(self.files, '/'.join(filter(None, (self.relative, name))))

    def __str__(self):
        return self.files.label + ('/' + self.relative if self.relative else '')

    def __fspath__(self):
        return str(self)

    def __lt__(self, other):
        return self.relative < other.relative

    @property
    def name(self):
        return PurePosixPath(self.relative).name

    @property
    def suffix(self):
        return PurePosixPath(self.relative).suffix

    @property
    def parent(self):
        parent = PurePosixPath(self.relative).parent
        return ValidationPath(self.files, '' if parent == PurePosixPath('.') else str(parent))

    def relative_to(self, other):
        if not isinstance(other, ValidationPath) or other.files is not self.files:
            raise ValueError('validation_display_root_mismatch')
        return PurePosixPath(self.relative).relative_to(PurePosixPath(other.relative))

    def resolve(self):
        return self

    def exists(self):
        return not self.relative or self.relative in self.files.membership or self.relative in self.files.directories()

    def is_file(self):
        return self.relative in self.files.membership

    def is_dir(self):
        return not self.relative or self.relative in self.files.directories()

    def read_bytes(self):
        if self.relative not in self.files.files:
            if self.relative in self.files.membership:
                raise PermissionError('validation_member_is_inert_membership_only')
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', str(self))
        return self.files.files[self.relative]

    def open(self, mode='r', encoding=None, errors=None):
        if mode not in ('r', 'rt', 'rb'):
            raise ValueError('validation_inputs_are_read_only')
        stream = io.BytesIO(self.read_bytes())
        stream.name = str(self)
        return stream if mode == 'rb' else io.TextIOWrapper(stream, encoding=encoding or 'utf-8', errors=errors)

    def read_text(self, encoding=None, errors=None):
        with self.open(encoding=encoding, errors=errors) as stream:
            return stream.read()

    def glob(self, pattern):
        if '/' in pattern or pattern in ('', '.', '..'):
            raise ValueError('unsupported_validation_glob')
        for name in sorted(self.files.membership):
            path = PurePosixPath(name)
            parent = '' if path.parent == PurePosixPath('.') else str(path.parent)
            if parent == self.relative and fnmatchcase(path.name, pattern):
                yield ValidationPath(self.files, name)

    def rglob(self, pattern):
        if '/' in pattern or pattern in ('', '.', '..'):
            raise ValueError('unsupported_validation_glob')
        prefix = self.relative + '/' if self.relative else ''
        for name in sorted(self.files.membership):
            if name.startswith(prefix) and fnmatchcase(PurePosixPath(name).name, pattern):
                yield ValidationPath(self.files, name)
