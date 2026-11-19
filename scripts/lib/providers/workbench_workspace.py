"""Private instance-owned draft files and explicit offline backup/restore effects."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from lib import attestation_files, workbench_archive
from lib.candidate_workspace import private_directory
from lib.result_bytes import safe_bytes
from lib.consumer_intake_store import atomic_json


class WorkbenchWorkspace:
    def __init__(self, instance, settings, *, create=True):
        self.instance = Path(instance).absolute()
        if any(p.is_symlink() for p in (self.instance, *self.instance.parents)):
            raise ValueError('private_workbench_instance_required')
        self.instance = self.instance.resolve()
        self.product = Path(settings['source_root']).resolve()
        if self.instance.is_relative_to(self.product) or self.product.is_relative_to(self.instance):
            raise ValueError('workbench_instance_outside_product_required')
        self.state = self.instance/'state'
        for path in (self.instance, self.state): self.checked_directory(path)
        self.root = self.state/'workbench'
        if create: private_directory(self.root)
        elif self.root.exists(): self.checked_directory(self.root)
        self.binding = {name: settings[name] for name in workbench_archive.BINDING_KEYS}
        workbench_archive.binding(self.binding)
        self.schema = json.loads((self.product/'schemas/governance-workbench-draft.schema.json').read_text())

    @staticmethod
    def checked_directory(path):
        row = path.lstat()
        if not stat.S_ISDIR(row.st_mode) or row.st_uid != os.geteuid() or row.st_mode & 0o077:
            raise ValueError('private_workbench_directory_required')

    @contextmanager
    def lease(self):
        """One server OR offline backup/restore owner, for the entire operation."""
        path = self.state/'workbench.lock'
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            row = os.fstat(fd)
            if (not stat.S_ISREG(row.st_mode) or row.st_uid != os.geteuid()
                    or row.st_nlink != 1 or row.st_mode & 0o077):
                raise ValueError('private_workbench_lock_required')
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('workbench_workspace_busy') from None
            yield
        finally: os.close(fd)

    @staticmethod
    def entries(path):
        rows = []
        for row in path.iterdir():
            rows.append(row)
            if len(rows) > workbench_archive.MAX_FILES:
                raise ValueError('workbench_workspace_budget')
        return sorted(rows)

    def capture(self):
        self.checked_directory(self.root)
        files = {}; directories = []; total = 0
        for folder in self.entries(self.root):
            if not re.fullmatch('[a-f0-9]{32}', folder.name):
                raise ValueError('unexpected_workbench_workspace_entry')
            self.checked_directory(folder); directories.append(folder.name)
            for path in self.entries(folder):
                name = path.relative_to(self.root).as_posix(); workbench_archive.member_name(name)
                row = path.lstat()
                if (not stat.S_ISREG(row.st_mode) or row.st_uid != os.geteuid()
                        or row.st_nlink != 1 or row.st_mode & 0o077):
                    raise ValueError('private_workbench_file_required')
                total += row.st_size
                if (row.st_size > workbench_archive.MAX_FILE or total > workbench_archive.MAX_TOTAL
                        or len(files) + len(directories) >= workbench_archive.MAX_FILES):
                    raise ValueError('workbench_workspace_budget')
                files[name] = safe_bytes(path, limit=workbench_archive.MAX_FILE)
                after = path.lstat()
                if any(getattr(row,k) != getattr(after,k) for k in ('st_ino','st_dev','st_size','st_mode','st_nlink','st_mtime_ns','st_ctime_ns')):
                    raise ValueError('workbench_workspace_changed_during_capture')
        workbench_archive.checked_files(files, directories, self.schema)
        return files, directories

    def backup(self, destination):
        destination = attestation_files.destination(destination, (self.instance, self.product))
        with self.lease():
            files, directories = self.capture()
            raw, manifest = workbench_archive.create(files, directories, self.binding, self.schema)
            parent = attestation_files.parent(destination, create=True)
            try:
                fd = os.open(destination.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            finally: os.close(parent)
        return self.receipt(raw, manifest, 'backup')

    def inspect(self, archive, expected_sha256, *, allow_source_change=False):
        from lib.providers.workbench_data import private_bytes
        if not isinstance(expected_sha256, str) or not re.fullmatch('[a-f0-9]{64}', expected_sha256):
            raise ValueError('explicit_workbench_backup_digest_required')
        raw = private_bytes(Path(archive), workbench_archive.MAX_TOTAL + 16 * 1024**2)
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError('workbench_backup_checksum_mismatch')
        manifest, files = workbench_archive.inspect(raw, self.schema, self.binding, allow_source_change=allow_source_change)
        return raw, manifest, files

    def restore(self, archive, expected_sha256, *, allow_source_change=False):
        with self.lease():
            raw, manifest, files = self.inspect(archive, expected_sha256, allow_source_change=allow_source_change)
            if any(self.root.iterdir()): raise ValueError('fresh_workbench_restore_required')
            with tempfile.TemporaryDirectory(prefix='.workbench-restore-', dir=self.state) as temporary:
                staged = Path(temporary)/'drafts'; staged.mkdir(mode=0o700)
                for name in manifest['directories']: (staged/name).mkdir(mode=0o700)
                for name, data in files.items():
                    target = staged/name; target.write_bytes(data); target.chmod(0o600)
                if any(self.root.iterdir()): raise ValueError('workbench_restore_destination_changed')
                os.rename(staged, self.root)
            result = self.receipt(raw, manifest, 'restore')
            # Historical source node is metadata only. No key/session/publisher is copied.
            atomic_json(self.state/'workbench-restore.json', result)
            if self.capture() != (files, manifest['directories']):
                raise ValueError('workbench_restore_bytes_changed')
            return result

    def receipt(self, raw, manifest, operation):
        return {'operation': operation, 'execution': 'complete', 'scope': 'workbench-drafts-and-uploads',
            'sha256': hashlib.sha256(raw).hexdigest(), 'file_count': len(manifest['files']),
            'draft_directory_count': len(manifest['directories']),
            'source_revision': self.binding['source_revision'],
            'backup_source_revision': manifest['source']['source_revision'],
            'historical_source_import': any(manifest['source'][k] != self.binding[k] for k in workbench_archive.BINDING_KEYS - {'node_id'}),
            'original_node_id': manifest['source']['node_id'], 'node_id': self.binding['node_id'],
            **workbench_archive.FLAGS}
