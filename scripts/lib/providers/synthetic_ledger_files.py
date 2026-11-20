"""Stable owned ledger observations, including the store's exact hardlink pair.

A failed final unlink can leave the pending and canonical transaction names on
one inode. Only that bounded same-directory pair is admitted. A link elsewhere
or any extra alias remains a technical admission failure, not a V1 verdict.
"""
import os
from pathlib import Path
import stat

from lib.providers.operations_files import held_root
from lib.providers.validation_worktree import signature
from lib.providers.workbook_import_io import ordinary_ancestors
from lib.providers.synthetic_lifecycle_io import metadata
from lib.requirement_validation_budget import InputAdmissionError
from lib.validation_files import MAX_FILE, MAX_TOTAL


class LedgerFiles:
    def __init__(self, owner, ledger, *, transaction_name):
        self.io, self.ledger, self.transaction_name = owner, Path(ledger), transaction_name
        if not self.ledger.is_absolute():
            raise InputAdmissionError('synthetic_ledger_absolute_root_required')
        self.total = 0

    @staticmethod
    def admit(value):
        # Linux does not apply the process umask to symlink mode bits; reject
        # the object kind before platform-dependent permission diagnostics.
        if not stat.S_ISREG(value.st_mode):
            raise InputAdmissionError('synthetic_ledger_regular_bounded_file_required')
        if value.st_uid != os.geteuid() or value.st_mode & 0o7022:
            raise InputAdmissionError('synthetic_ledger_owned_unshared_file_required')
        if not 1 <= value.st_nlink <= 2 or value.st_size > MAX_FILE:
            raise InputAdmissionError('synthetic_ledger_regular_bounded_file_required')

    def members(self, parent):
        names, size = [], 0
        with os.scandir(parent) as entries:
            for entry in entries:
                if ('\\' in entry.name or any(ord(c) < 32 or 0xd800 <= ord(c) <= 0xdfff for c in entry.name)):
                    raise InputAdmissionError('synthetic_ledger_membership_name_not_admitted')
                names.append(entry.name)
                size += len(entry.name.encode('utf-8'))
                if len(names) > 10000 or size > 2 * 1024**2:
                    raise InputAdmissionError('synthetic_ledger_alias_membership_budget')
        return sorted(names)

    def directory(self, path):
        self.io.check(path, path)
        ordinary_ancestors(Path(path))
        with held_root(path) as descriptor:
            before = os.fstat(descriptor)
            if (not stat.S_ISDIR(before.st_mode) or before.st_uid != os.geteuid() or before.st_mode & 0o7022):
                raise InputAdmissionError('synthetic_ledger_owned_directory_observation_required')
            names = self.members(descriptor)
            after = os.fstat(descriptor)
            if signature(before) != signature(after):
                raise InputAdmissionError('synthetic_ledger_directory_changed_during_observation')
            return {'snapshot': {'kind': 'directory', 'mode': stat.S_IMODE(before.st_mode),
                    'identity': [before.st_dev, before.st_ino]}, 'metadata': metadata(before),
                    'aliases': [], 'members': names}

    def pair(self, parent, selected, value, raw):
        if value.st_nlink == 1:
            return []
        if selected.parent != self.ledger / 'transactions':
            raise InputAdmissionError('synthetic_ledger_alias_outside_transaction_directory')
        # Read a complete bounded parent membership while its descriptor is
        # held. Its metadata and both links are checked again after the read.
        before = os.fstat(parent)
        names = self.members(parent)
        aliases = []
        for name in names:
            candidate = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (candidate.st_dev, candidate.st_ino) != (value.st_dev, value.st_ino):
                continue
            self.admit(candidate)
            if signature(candidate) != signature(value):
                raise InputAdmissionError('synthetic_ledger_alias_metadata_changed')
            aliases.append(name)
        if len(aliases) != 2 or selected.name not in aliases:
            raise InputAdmissionError('synthetic_ledger_unknown_or_external_alias')
        pending = [name for name in aliases if name.startswith('.pending-')]
        accepted = [name for name in aliases if not name.startswith('.pending-')]
        if len(pending) != 1 or len(accepted) != 1:
            raise InputAdmissionError('synthetic_ledger_only_pending_canonical_pair_admitted')
        try:
            expected = self.transaction_name(raw)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise InputAdmissionError('synthetic_ledger_alias_transaction_identity_invalid') from error
        if type(expected) is not str or Path(expected).name != expected or accepted != [expected]:
            raise InputAdmissionError('synthetic_ledger_alias_canonical_name_unbound')
        for name in aliases:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if signature(current) != signature(value):
                raise InputAdmissionError('synthetic_ledger_alias_replaced_during_observation')
        final_names = self.members(parent)
        if signature(before) != signature(os.fstat(parent)) or names != final_names:
            raise InputAdmissionError('synthetic_ledger_alias_directory_changed')
        return [str(selected.parent / name) for name in aliases]

    def read(self, path, label):
        self.io.check(path, label)
        selected = Path(path)
        ordinary_ancestors(selected.parent)
        with held_root(selected.parent) as parent:
            parent_value = os.fstat(parent)
            if (not stat.S_ISDIR(parent_value.st_mode) or parent_value.st_uid != os.geteuid()
                    or parent_value.st_mode & 0o7022):
                raise InputAdmissionError('synthetic_ledger_owned_unshared_parent_required')
            entry = os.stat(selected.name, dir_fd=parent, follow_symlinks=False)
            self.admit(entry)
            descriptor = os.open(selected.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                before = os.fstat(descriptor)
                if signature(before) != signature(entry):
                    raise InputAdmissionError('synthetic_ledger_file_replaced_before_read')
                chunks, size = [], 0
                while block := os.read(descriptor, min(65536, MAX_FILE + 1 - size)):
                    chunks.append(block)
                    size += len(block)
                    if size > MAX_FILE:
                        raise InputAdmissionError('synthetic_ledger_file_byte_budget')
                raw = b''.join(chunks)
                aliases = self.pair(parent, selected, before, raw)
                current = os.stat(selected.name, dir_fd=parent, follow_symlinks=False)
                if signature(before) != signature(os.fstat(descriptor)) or signature(before) != signature(current):
                    raise InputAdmissionError('synthetic_ledger_file_changed_during_read')
                self.total += len(raw)
                if self.total > MAX_TOTAL:
                    raise InputAdmissionError('synthetic_ledger_read_total_budget')
                return raw, {'snapshot': {'kind': 'file', 'mode': stat.S_IMODE(before.st_mode),
                    'identity': [before.st_dev, before.st_ino], 'content': self.io.blob(raw)},
                    'metadata': metadata(before), 'aliases': aliases}
            finally:
                os.close(descriptor)
