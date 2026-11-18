"""Read-only byte namespace for an explicitly supplied embedded capture.

Materialized captures contain ordinary files and derived directories only. No
caller path, source code, network request or operating authority is imported.
"""
import errno
from pathlib import PurePosixPath
from types import MappingProxyType


class RepositoryMemoryIO:
    def __init__(self, files, *, maximum_bytes=25 * 1024 * 1024, maximum_members=10000):
        if type(files) is not dict or not files or len(files) > maximum_members:
            raise ValueError('embedded_capture_membership_budget')
        retained = {}
        children = {'': {}}
        total = 0
        for name, data in files.items():
            if type(name) is not str or type(data) is not bytes:
                raise TypeError('embedded_capture_bytes_required')
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or str(path) != name or not path.parts:
                raise ValueError('unsafe_embedded_capture_member')
            if len(path.parts) > 100:
                raise ValueError('embedded_capture_depth_budget')
            total += len(data)
            if total > maximum_bytes:
                raise ValueError('embedded_capture_size_budget')
            parent = ''
            for part in path.parts[:-1]:
                child = '/'.join(filter(None, (parent, part)))
                if child in retained:
                    raise FileExistsError(errno.EEXIST, 'File exists', child)
                children[parent].setdefault(part, 'directory')
                children.setdefault(child, {})
                parent = child
            if name in children:
                raise IsADirectoryError(errno.EISDIR, 'Is a directory', name)
            children[parent][path.name] = 'file'
            retained[name] = data
        if len(children) + len(retained) > maximum_members:
            raise ValueError('embedded_capture_membership_budget')
        self.files = MappingProxyType(retained)
        self.directories = MappingProxyType({key: tuple(value.items()) for key, value in children.items()})

    def stat(self, name):
        if name in self.files:
            return {'kind': 'file', 'bytes': len(self.files[name]), 'mode': 0o100600}
        if name in self.directories:
            return {'kind': 'directory', 'bytes': 0, 'mode': 0o40700}
        return None

    def read(self, name):
        if name in self.directories:
            raise IsADirectoryError(errno.EISDIR, 'Is a directory', name)
        try:
            return self.files[name]
        except KeyError:
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', name) from None

    def entries(self, name):
        if name in self.files:
            raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', name)
        try:
            entries = self.directories[name]
        except KeyError:
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', name) from None
        return [{'name': child, **self.stat('/'.join(filter(None, (name, child))))} for child, _ in entries]
