"""Held descriptor reads confined to one private retained-data directory."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat

from lib.providers.validation_worktree import directory, file_bytes, signature
from lib.validation_files import relative


class RepositoryDataIO:
    def __init__(self, root):
        root = Path(root)
        if root.is_symlink():
            raise ValueError('private_repository_data_directory_required')
        self.root = root.resolve(strict=True)
        value = self.root.stat()
        if not stat.S_ISDIR(value.st_mode) or value.st_mode & 0o077:
            raise ValueError('private_repository_data_directory_required')
        self.identity = (value.st_dev, value.st_ino, value.st_mode)

    @contextmanager
    def opened(self):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        before = os.fstat(fd)
        try:
            if (before.st_dev, before.st_ino, before.st_mode) != self.identity:
                raise ValueError('repository_data_root_identity_changed')
            yield fd
            if signature(before) != signature(os.fstat(fd)) or signature(before) != signature(os.stat(self.root, follow_symlinks=False)):
                raise ValueError('repository_data_root_changed_during_read')
        finally:
            os.close(fd)

    @contextmanager
    def nested(self, fd, parts):
        if not parts:
            yield fd
            return
        if len(parts) > 100:
            raise ValueError('repository_data_depth_budget')
        value = os.stat(parts[0], dir_fd=fd, follow_symlinks=False)
        if stat.S_ISLNK(value.st_mode):
            raise ValueError('repository_data_link_not_admitted')
        if not stat.S_ISDIR(value.st_mode):
            raise NotADirectoryError(errno.ENOTDIR, 'Not a directory', parts[0])
        with directory(fd, parts[0]) as child:
            if child is None:
                raise FileNotFoundError(errno.ENOENT, 'No such file or directory', parts[0])
            with self.nested(child, parts[1:]) as result:
                yield result

    def parts(self, name):
        if name == '':
            return ()
        relative(name)
        parts = Path(name).parts
        if len(parts) > 100:
            raise ValueError('repository_data_depth_budget')
        return parts

    @staticmethod
    def describe(value):
        kind = ('directory' if stat.S_ISDIR(value.st_mode) else 'file' if stat.S_ISREG(value.st_mode)
                else 'symlink' if stat.S_ISLNK(value.st_mode) else 'other')
        return {'kind': kind, 'bytes': value.st_size, 'mode': value.st_mode}

    def stat(self, name):
        parts = self.parts(name)
        with self.opened() as fd:
            try:
                with self.nested(fd, parts[:-1]) as parent:
                    value = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False) if parts else os.fstat(parent)
                    return self.describe(value)
            except (FileNotFoundError, NotADirectoryError):
                return None

    def read(self, name):
        parts = self.parts(name)
        if not parts:
            raise IsADirectoryError(errno.EISDIR, 'Is a directory', str(self.root))
        with self.opened() as fd:
            with self.nested(fd, parts[:-1]) as parent:
                value = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
                if stat.S_ISDIR(value.st_mode):
                    raise IsADirectoryError(errno.EISDIR, 'Is a directory', name)
                if stat.S_ISLNK(value.st_mode):
                    raise ValueError('repository_data_link_not_admitted')
                return file_bytes(parent, parts[-1])

    def entries(self, name):
        with self.opened() as fd:
            with self.nested(fd, self.parts(name)) as parent:
                names = os.listdir(parent)
                if len(names) > 10000:
                    raise ValueError('repository_data_membership_budget')
                rows = [{'name': name, **self.describe(os.stat(name, dir_fd=parent, follow_symlinks=False))} for name in names]
                if names != os.listdir(parent):
                    raise ValueError('repository_data_directory_membership_changed')
                return rows
