"""Held working files or immutable Git blobs for whole repository validation."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat

from lib import repository_capture as contract
from lib.providers.validation_worktree import directory, file_bytes, signature
from lib.validation_files import MAX_FILES, MAX_TOTAL


class RepositorySource:
    def __init__(self, git, revision, *, profile):
        if profile not in contract.PROFILES:
            raise ValueError('explicit_repository_capture_profile_required')
        if type(revision) is not str or re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', revision) is None:
            raise ValueError('exact_repository_capture_revision_required')
        self.git, self.revision, self.profile = git, revision, profile
        self.source = git.source

    def binding(self):
        self.git.check_source()
        actual_root = Path(self.git.read('rev-parse', '--show-toplevel').decode('utf-8').rstrip('\n')).resolve()
        algorithm = self.git.read('rev-parse', '--show-object-format').decode('ascii').strip()
        revision = self.git.read('rev-parse', '--verify', 'HEAD^{commit}').decode('ascii').strip()
        tree = self.git.read('rev-parse', '--verify', 'HEAD^{tree}').decode('ascii').strip()
        contract.object_id(revision, algorithm)
        contract.object_id(tree, algorithm)
        if actual_root != self.source or revision != self.revision:
            raise ValueError('repository_capture_product_revision_mismatch')
        return {'algorithm': algorithm, 'revision': revision, 'tree': tree}

    @contextmanager
    def opened(self):
        self.git.check_source()
        fd = os.open(self.source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        before = os.fstat(fd)
        try:
            if (before.st_dev, before.st_ino, before.st_mode) != self.git.identity:
                raise ValueError('repository_capture_root_identity_changed')
            yield fd
            if (signature(before) != signature(os.fstat(fd))
                    or signature(before) != signature(os.stat(self.source, follow_symlinks=False))):
                raise ValueError('repository_capture_root_changed')
        finally:
            os.close(fd)

    def working(self, fd, inventory):
        files, modes, directories, identities = {}, {}, {}, {}
        total, count = 0, 0

        def walk(parent, prefix):
            nonlocal total, count
            before = os.fstat(parent)
            names = os.listdir(parent)
            children = []
            directories[prefix] = children
            identities[prefix] = signature(before)
            for name in names:
                count += 1
                if count > MAX_FILES:
                    raise ValueError('repository_capture_membership_budget')
                path = '/'.join(filter(None, (prefix, name)))
                if not contract.admitted(path, inventory):
                    continue
                metadata = os.stat(name, dir_fd=parent, follow_symlinks=False)
                children.append(name)
                if stat.S_ISDIR(metadata.st_mode):
                    with directory(parent, name) as child:
                        if child is None:
                            raise ValueError('repository_capture_directory_changed')
                        walk(child, path)
                elif stat.S_ISREG(metadata.st_mode):
                    if total + metadata.st_size > MAX_TOTAL:
                        raise ValueError('repository_capture_total_budget')
                    raw = file_bytes(parent, name)
                    if signature(metadata) != signature(os.stat(name, dir_fd=parent, follow_symlinks=False)):
                        raise ValueError('repository_capture_file_changed')
                    total += len(raw)
                    if total > MAX_TOTAL:
                        raise ValueError('repository_capture_total_budget')
                    files[path] = raw
                    modes[path] = '100755' if metadata.st_mode & 0o111 else '100644'
                    identities[path] = signature(metadata)
                else:
                    raise ValueError('repository_capture_selected_link_or_special_file')
            if names != os.listdir(parent) or signature(before) != signature(os.fstat(parent)):
                raise ValueError('repository_capture_directory_changed')
        walk(fd, '')
        return files, modes, directories, identities

    def capture(self):
        before = self.binding()
        algorithm, tree = before['algorithm'], before['tree']
        commit = self.git.read('cat-file', 'commit', self.revision)
        contract.check_commit(commit, revision=self.revision, tree=tree, algorithm=algorithm)
        raw = self.git.read('ls-tree', '-r', '-t', '-l', '-z', '--full-tree', self.revision)
        inventory = contract.parse_tree(raw, tree=tree, algorithm=algorithm)
        if self.profile == contract.COMMITTED:
            files, modes, blobs = {}, {}, {}
            directories = contract.tree_directories(inventory)
            for name, row in inventory.items():
                if row['kind'] != 'blob':
                    continue
                oid = row['git_object']
                if oid not in blobs:
                    blobs[oid] = self.git.read('cat-file', 'blob', oid)
                payload = blobs[oid]
                if len(payload) != row['bytes'] or contract.object_digest('blob', payload, algorithm) != oid:
                    raise ValueError('repository_capture_git_blob_changed')
                files[name], modes[name] = payload, row['mode']
            if self.binding() != before:
                raise ValueError('repository_capture_source_binding_changed')
        else:
            with self.opened() as fd:
                first = self.working(fd, inventory)
                if self.binding() != before:
                    raise ValueError('repository_capture_source_binding_changed')
                second = self.working(fd, inventory)
                if first != second:
                    raise ValueError('repository_capture_working_files_changed')
                if self.binding() != before:
                    raise ValueError('repository_capture_source_binding_changed')
                files, modes, directories, _ = first
        manifest = contract.make_manifest(profile=self.profile, source_root=str(self.source),
            revision=self.revision, tree=tree, algorithm=algorithm, inventory=inventory,
            files=files, modes=modes, directories=directories, commit=commit)
        return manifest, files, commit
