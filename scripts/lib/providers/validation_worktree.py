"""Held, bounded current-file acquisition for an explicit product worktree."""
from contextlib import contextmanager
import os
from pathlib import Path
import stat

from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL, relative
from lib.validation_sources import SCOPES, offline_working_schemas, working_manifest, working_refs


def signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


@contextmanager
def directory(parent, name):
    try: fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        yield None
        return
    except OSError:
        raise ValueError('unsafe_validation_worktree_directory') from None
    before = os.fstat(fd)
    try:
        yield fd
        after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if signature(before) != signature(os.fstat(fd)) or signature(before) != signature(after):
            raise ValueError('validation_worktree_directory_changed')
    finally: os.close(fd)


def file_bytes(parent, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_FILE:
            raise ValueError('unsafe_or_oversize_validation_worktree_file')
        blocks = []; size = 0
        while True:
            block = os.read(fd, min(65536, MAX_FILE + 1 - size))
            if not block: break
            blocks.append(block); size += len(block)
            if size > MAX_FILE: raise ValueError('validation_worktree_file_budget')
        if (signature(before) != signature(os.fstat(fd))
                or signature(before) != signature(os.stat(name, dir_fd=parent, follow_symlinks=False))):
            raise ValueError('validation_worktree_file_changed')
        return b''.join(blocks)
    finally: os.close(fd)


class ValidationWorktree:
    def __init__(self, source, revision):
        source = Path(source)
        if source.is_symlink(): raise ValueError('explicit_ordinary_validation_worktree_required')
        self.source = source.resolve(strict=True)
        self.revision = revision
        self.check_source()
        self.tree = self.git('rev-parse', 'HEAD^{tree}').decode().strip()

    def git(self, *arguments):
        # Existing bounded native Git primitive: no hooks, filters, fsmonitor,
        # lazy network fetch, inherited Git overrides or unlimited output.
        from lib.review_git import git
        return git(self.source, *arguments, limit=256 * 1024, timeout=30)

    def clean(self):
        return not bool(self.git('status', '--porcelain', '--untracked-files=all', '--ignore-submodules=all').strip())

    def check_source(self):
        if (Path(self.git('rev-parse', '--show-toplevel').decode().strip()).resolve() != self.source
                or self.git('rev-parse', 'HEAD').decode().strip() != self.revision):
            raise ValueError('validation_worktree_product_revision_mismatch')

    def capture(self):
        self.check_source()
        fd = os.open(self.source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        before = os.fstat(fd); files = {}; total = 0; members = 0

        def walk(parent, prefix, components):
            nonlocal total, members
            if len(Path(prefix).parts) > 100: raise ValueError('validation_worktree_depth_budget')
            if components:
                with directory(parent, components[0]) as child:
                    if child is not None: walk(child, prefix, components[1:])
                return
            names = sorted(os.listdir(parent))
            for name in names:
                members += 1
                if members > MAX_FILES: raise ValueError('validation_worktree_membership_budget')
                path = prefix + '/' + name; relative(path)
                meta = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISDIR(meta.st_mode):
                    with directory(parent, name) as child:
                        if child is None: raise ValueError('validation_worktree_directory_changed')
                        walk(child, path, [])
                elif stat.S_ISREG(meta.st_mode):
                    if total + meta.st_size > MAX_TOTAL: raise ValueError('validation_worktree_total_budget')
                    raw = file_bytes(parent, name); total += len(raw)
                    if total > MAX_TOTAL: raise ValueError('validation_worktree_total_budget')
                    files[path] = raw
                else: raise ValueError('unsafe_validation_worktree_member')
            if names != sorted(os.listdir(parent)): raise ValueError('validation_worktree_membership_changed')

        def exists(parent, parts):
            if len(parts) > 100: raise ValueError('validation_worktree_depth_budget')
            if not parts: return True
            try: meta = os.stat(parts[0], dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError: return False
            if stat.S_ISLNK(meta.st_mode) or not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode)):
                raise ValueError('unsafe_validation_worktree_reference')
            if len(parts) == 1: return True
            if not stat.S_ISDIR(meta.st_mode): return False
            with directory(parent, parts[0]) as child:
                return child is not None and exists(child, parts[1:])

        try:
            for scope in SCOPES: walk(fd, scope, scope.split('/'))
            offline_working_schemas(files)
            membership = set(files)
            for name in working_refs(files):
                if exists(fd, Path(name).parts): membership.add(name)
            if (signature(before) != signature(os.fstat(fd))
                    or signature(before) != signature(os.stat(self.source, follow_symlinks=False))):
                raise ValueError('validation_worktree_root_changed')
            self.check_source()
            return files, working_manifest(files, membership, revision=self.revision,
                tree=self.tree, source=self.source)
        except OSError as error:
            raise ValueError('validation_worktree_acquisition_changed_or_unsafe') from error
        finally: os.close(fd)
