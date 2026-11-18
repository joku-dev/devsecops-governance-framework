"""Structural paths whose filesystem operations stay in an explicit data port."""
import errno
from fnmatch import fnmatchcase
import io
from pathlib import PurePosixPath
import posixpath


class RepositoryPaths:
    def __init__(self, root, io_port):
        root = PurePosixPath(root)
        if not root.is_absolute() or '..' in root.parts:
            raise ValueError('absolute_repository_data_namespace_required')
        self.label = root
        self.io = io_port
        self.root = RepositoryPath(self, root)

    def path(self, value):
        if isinstance(value, RepositoryPath):
            if value.namespace is not self:
                raise ValueError('foreign_repository_data_namespace')
            return value
        if not isinstance(value, (str, PurePosixPath)):
            # pathlib.Path is a PurePosixPath on both supported host profiles.
            raise TypeError('repository_path_string_required')
        return RepositoryPath(self, PurePosixPath(value))

    def absolute(self, value):
        value = value if value.is_absolute() else self.label / value
        return PurePosixPath(posixpath.normpath(value.as_posix()))

    def relative(self, value):
        absolute = self.absolute(value)
        try:
            name = absolute.relative_to(self.label).as_posix()
        except ValueError:
            raise ValueError('outside_repository_data_namespace') from None
        return '' if name == '.' else name


class RepositoryPath:
    def __init__(self, namespace, value):
        self.namespace = namespace
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return 'PosixPath(' + repr(str(self)) + ')'

    def __truediv__(self, value):
        return RepositoryPath(self.namespace, self.value / self.namespace.path(value).value)

    def __lt__(self, other):
        return self.value < self.namespace.path(other).value

    def __eq__(self, other):
        return isinstance(other, RepositoryPath) and self.namespace is other.namespace and self.value == other.value

    def __hash__(self):
        return hash((id(self.namespace), self.value))

    @property
    def name(self): return self.value.name

    @property
    def suffix(self): return self.value.suffix

    @property
    def stem(self): return self.value.stem

    @property
    def parts(self): return self.value.parts

    @property
    def parent(self): return RepositoryPath(self.namespace, self.value.parent)

    @property
    def parents(self): return tuple(RepositoryPath(self.namespace, p) for p in self.value.parents)

    def as_posix(self): return self.value.as_posix()

    def is_absolute(self): return self.value.is_absolute()

    def relative_to(self, other):
        return self.value.relative_to(self.namespace.path(other).value)

    def is_relative_to(self, other):
        return self.value.is_relative_to(self.namespace.path(other).value)

    def resolve(self, strict=False):
        value = RepositoryPath(self.namespace, self.namespace.absolute(self.value))
        if strict and not value.exists():
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', str(value))
        return value

    def stat(self):
        return self.namespace.io.stat(self.namespace.relative(self.value))

    def exists(self): return self.stat() is not None

    def is_file(self):
        value = self.stat()
        return value is not None and value['kind'] == 'file'

    def is_dir(self):
        value = self.stat()
        return value is not None and value['kind'] == 'directory'

    def is_symlink(self):
        value = self.stat()
        return value is not None and value['kind'] == 'symlink'

    def read_bytes(self):
        try:
            return self.namespace.io.read(self.namespace.relative(self.value))
        except OSError as error:
            raise type(error)(error.errno, error.strerror, str(self)) from None

    def open(self, mode='r', encoding=None, errors=None):
        if mode not in ('r', 'rt', 'rb'):
            raise ValueError('repository_data_paths_are_read_only')
        buffer = io.BytesIO(self.read_bytes())
        buffer.name = str(self)
        return buffer if mode == 'rb' else io.TextIOWrapper(buffer, encoding=encoding or 'utf-8', errors=errors)

    def read_text(self, encoding=None, errors=None):
        with self.open(encoding=encoding, errors=errors) as stream:
            return stream.read()

    def iterdir(self):
        try:
            rows = self.namespace.io.entries(self.namespace.relative(self.value))
        except OSError as error:
            raise type(error)(error.errno, error.strerror, str(self)) from None
        return iter(self / row['name'] for row in rows)

    def glob(self, pattern):
        if not isinstance(pattern, str) or not pattern or pattern.startswith('/') or '..' in PurePosixPath(pattern).parts:
            raise ValueError('unsupported_repository_data_glob')
        parts = pattern.split('/')
        if parts[0] == '**' and len(parts) == 2:
            yield from self.rglob(parts[1])
            return
        if len(parts) != 1:
            raise ValueError('unsupported_repository_data_glob')
        if not self.is_dir():
            return
        for path in self.iterdir():
            if fnmatchcase(path.name, pattern):
                yield path

    def rglob(self, pattern):
        if not isinstance(pattern, str) or not pattern or '/' in pattern or pattern in ('.', '..'):
            raise ValueError('unsupported_repository_data_glob')
        count = 0
        def visit(directory, depth):
            nonlocal count
            if depth > 100:
                raise ValueError('repository_data_depth_budget')
            if not directory.is_dir():
                return
            children = list(directory.iterdir())
            count += len(children)
            if count > 10000:
                raise ValueError('repository_data_membership_budget')
            for path in children:
                if fnmatchcase(path.name, pattern):
                    yield path
            for path in children:
                if path.is_dir():
                    yield from visit(path, depth + 1)
        yield from visit(self, 0)
