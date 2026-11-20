"""Read complete private operation trees through held bounded descriptors."""
import os
from pathlib import Path
import stat

from lib.retained_security_tree import RetainedTree, MAX_BYTES, MAX_FILE, MAX_FILES
from lib.validation_files import relative
from lib.providers.operations_files import held_root
from lib.providers.validation_worktree import directory, signature


def capture(path):
    path = Path(path).absolute()
    data = {}
    directories = ['']
    count = total = 0

    def walk(fd, prefix, depth):
        nonlocal count, total
        meta = os.fstat(fd)
        if meta.st_uid != os.geteuid() or meta.st_mode & 0o077 or depth > 100:
            raise ValueError('private_retained_security_directory_required')
        before = signature(meta)
        names = []
        with os.scandir(fd) as iterator:
            for entry in iterator:
                count += 1
                if count > MAX_FILES:
                    raise ValueError('retained_security_membership_budget')
                names.append(entry.name)
        for name in sorted(names):
            label = prefix + '/' + name if prefix else name
            relative(label)
            meta = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(meta.st_mode):
                directories.append(label)
                with directory(fd, name) as child:
                    if child is None:
                        raise ValueError('retained_security_directory_changed')
                    walk(child, label, depth + 1)
                continue
            if (not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_uid != os.geteuid()
                    or meta.st_mode & 0o077 or meta.st_size > MAX_FILE):
                raise ValueError('private_retained_security_file_required')
            opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                before_file = os.fstat(opened)
                if signature(before_file) != signature(meta):
                    raise ValueError('retained_security_file_replaced')
                blocks = []
                size = 0
                while part := os.read(opened, min(65536, MAX_FILE + 1 - size)):
                    size += len(part)
                    total += len(part)
                    if size > MAX_FILE or total > MAX_BYTES:
                        raise ValueError('retained_security_byte_budget')
                    blocks.append(part)
                if (signature(before_file) != signature(os.fstat(opened))
                        or signature(before_file) != signature(os.stat(name, dir_fd=fd, follow_symlinks=False))):
                    raise ValueError('retained_security_file_changed')
                data[label] = b''.join(blocks)
            finally:
                os.close(opened)
        if before != signature(os.fstat(fd)):
            raise ValueError('retained_security_directory_changed')

    with held_root(path) as fd:
        walk(fd, '', 0)
    return RetainedTree(str(path), data, sorted(directories))
