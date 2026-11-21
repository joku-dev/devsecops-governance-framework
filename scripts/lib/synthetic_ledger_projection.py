"""Private POSIX-store model, with explicit effects and no native descriptors.

This models a single candidate sequence. Its lock/fsync events are logical
steps, never claims about native concurrency, durability, ACLs or disk space.
Native capture and replay admission belong to separate adapters.
"""
import errno
from pathlib import PurePosixPath

from lib.synthetic_lifecycle_projection import Projection, PRIVATE_MASK, EMPTY
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import snapshot
from lib.synthetic_ledger_budget import DEFAULT, admitted


class LedgerProjection(Projection):
    """Shared logical inode content, unlink tombstones and directory membership."""

    def __init__(self, blob, *, budget=DEFAULT, ledger=None):
        self.budget = admitted(budget)
        self.ledger = ledger
        super().__init__(blob, max_file=self.budget.file, max_total=self.budget.total)
        self.memberships = {}

    def bounded_scope(self, path, value):
        # Validate bytes and metadata before consulting fields of a retained
        # snapshot. A malformed or dishonest reference is never a scope grant.
        snapshot(value, self.blob, max_file=self.budget.file)
        if (value['kind'] == 'file' and len(self.blob(value['content'])) > DEFAULT.file
                and (self.ledger is None or PurePosixPath(path).parent != PurePosixPath(self.ledger) / 'transactions')):
            raise IntegrityError('synthetic_ledger_wide_file_scope_changed')

    def load_one(self, path, value):
        self.bounded_scope(path, value)
        return super().load_one(path, value)

    def put(self, path, value):
        self.bounded_scope(path, value)
        return super().put(path, value)

    def load_membership(self, path, names):
        if (self.state(path)['kind'] != 'directory' or type(names) is not list
                or len(names) > 10000 or any(type(n) is not str or not n
                    or n in ('.', '..') or '/' in n or '\\' in n or '\0' in n for n in names)
                or len(names) != len(set(names))):
            raise IntegrityError('synthetic_ledger_private_membership_invalid')
        if path in self.memberships and self.memberships[path] != names:
            raise IntegrityError('synthetic_ledger_private_membership_changed')
        self.memberships[path] = list(names)

    def state(self, path):
        try:
            return super().state(path)
        except IntegrityError as error:
            parent = str(PurePosixPath(path).parent)
            if str(error) != 'lifecycle_projection_unobserved_path' or parent == path:
                raise
            parent_value = self.state(parent)
            if parent_value['kind'] in ('missing', 'unreachable'):
                return parent_value
            if parent_value['kind'] == 'file':
                return {'kind': 'unreachable', 'cause': 'NotADirectoryError'}
            if (parent in self.memberships
                    and PurePosixPath(path).name not in self.memberships[parent]):
                return {'kind': 'missing'}
            raise

    def aliases(self, identity):
        return sorted(name for name in self.base.keys() | self.nodes.keys()
                      if self.state(name).get('identity') == identity)

    def entries(self, path, label, base=None):
        if base is None and path not in self.nodes:
            if path not in self.memberships:
                raise IntegrityError('synthetic_ledger_private_membership_missing')
            base = self.memberships[path]
        names = super().entries(path, label, base)
        # Listing a known source name does not observe its object kind. Leave
        # that lazy read/probe to the original caller; only our own explicit
        # tombstones remove names from the retained base membership.
        return [name for name in names
                if self.nodes.get(str(PurePosixPath(path) / name), {}).get('kind') != 'missing']

    def replace_inode(self, identity, value):
        for name in self.aliases(identity):
            self.put(name, value)


class PrivateLedgerEffects:
    # Domain constants, deliberately unrelated to platform os/fcntl bit values.
    O_RDONLY, O_CREAT, O_RDWR, O_NOFOLLOW, O_DIRECTORY = 0, 1, 2, 4, 8
    LOCK_EX, LOCK_UN = 1, 2

    def __init__(self, tree, store, *, absolute, emit):
        self.tree, self.store, self.absolute, self.emit = tree, store, absolute, emit
        self.descriptors = {}
        self.serial = self.temporary_serial = self.operations = self.total = 0
        self.locks = {}

    def begin(self, action, arguments):
        self.operations += 1
        if self.operations > 8192:
            raise InputAdmissionError('synthetic_ledger_private_operation_budget')
        # Reserve/retain intent before changing the candidate state.
        self.emit({'kind': 'synthetic-ledger-private-effect', 'sequence': self.operations,
                   'action': action, 'arguments': arguments, 'native_effect': False})

    def path(self, path):
        label = str(path)
        value = self.absolute(PurePosixPath(label))
        if len(PurePosixPath(value).parts) > 100:
            raise InputAdmissionError('synthetic_ledger_private_path_depth_budget')
        from lib.synthetic_lifecycle_io import path_spec
        path_spec(value, label, self.absolute(PurePosixPath('.')))
        return value, label

    @staticmethod
    def fail(number, label=None):
        messages = {errno.ENOENT: 'No such file or directory',
                    errno.ENOTDIR: 'Not a directory', errno.EISDIR: 'Is a directory',
                    errno.EEXIST: 'File exists', errno.EACCES: 'Permission denied',
                    errno.EBADF: 'Bad file descriptor',
                    errno.EWOULDBLOCK: 'Resource temporarily unavailable'}
        if label is None:
            raise OSError(number, messages[number])
        raise OSError(number, messages[number], label)

    def descriptor(self, descriptor, kind=None):
        if type(descriptor) is not int or descriptor not in self.descriptors:
            self.fail(errno.EBADF)
        row = self.descriptors[descriptor]
        if kind is not None and row['kind'] != kind:
            self.fail(errno.EBADF)
        return row

    def allocate(self, path, value, *, writable):
        if len(self.descriptors) >= 128:
            raise InputAdmissionError('synthetic_ledger_private_descriptor_budget')
        self.serial += 1
        self.descriptors[self.serial] = {
            'path': path, 'identity': value['identity'], 'kind': value['kind'],
            'writable': writable, 'stream': False, 'value': value}
        return self.serial

    def open(self, path, flags, mode=0o777):
        name, label = self.path(path)
        lock_flags = self.O_CREAT | self.O_RDWR | self.O_NOFOLLOW
        if type(flags) is not int or flags not in (lock_flags, self.O_DIRECTORY):
            raise InputAdmissionError('synthetic_ledger_private_open_flags')
        if type(mode) is not int or not 0 <= mode <= 0o777:
            raise InputAdmissionError('synthetic_ledger_private_open_mode')
        if len(self.descriptors) >= 128:
            raise InputAdmissionError('synthetic_ledger_private_descriptor_budget')
        self.begin('open', {'path': name, 'label': label, 'flags': flags, 'mode': mode})
        self.tree.parent(name, label)
        value = self.tree.state(name)
        if flags == self.O_DIRECTORY:
            if value['kind'] == 'missing': self.fail(errno.ENOENT, label)
            if value['kind'] != 'directory': self.fail(errno.ENOTDIR, label)
            if not value['mode'] & 0o400: self.fail(errno.EACCES, label)
            return self.allocate(name, value, writable=False)
        if value['kind'] == 'missing':
            self.tree.parent(name, label, write=True)
            value = self.tree.fresh('file', mode & ~PRIVATE_MASK, EMPTY)
            self.tree.put(name, value)
        if value['kind'] == 'directory': self.fail(errno.EISDIR, label)
        if value['kind'] != 'file': self.fail(errno.ENOTDIR, label)
        if value['mode'] & 0o600 != 0o600: self.fail(errno.EACCES, label)
        return self.allocate(name, value, writable=True)

    def mkstemp(self, *, prefix, dir):
        directory, label = self.path(dir)
        if prefix != '.pending-':
            raise InputAdmissionError('synthetic_ledger_private_temp_prefix')
        if len(self.descriptors) >= 128:
            raise InputAdmissionError('synthetic_ledger_private_descriptor_budget')
        self.begin('mkstemp', {'directory': directory, 'label': label, 'prefix': prefix})
        for _ in range(2049):
            self.temporary_serial += 1
            name = prefix + 'private-' + str(self.temporary_serial).zfill(8)
            path = str(PurePosixPath(directory) / name)
            self.tree.parent(path, str(PurePosixPath(label) / name), write=True)
            if self.tree.state(path)['kind'] != 'missing': continue
            value = self.tree.fresh('file', 0o600, EMPTY)
            self.tree.put(path, value)
            # Both pinned Python 3.12/3.13 hosts return absolute mkstemp names.
            return self.allocate(path, value, writable=True), path
        raise InputAdmissionError('synthetic_ledger_private_temp_namespace_budget')

    def fdopen(self, descriptor, mode):
        row = self.descriptor(descriptor, 'file')
        if mode != 'wb' or not row['writable'] or row['stream']:
            raise InputAdmissionError('synthetic_ledger_private_stream_contract')
        self.begin('fdopen', {'descriptor': descriptor, 'mode': mode})
        row['stream'] = True
        return PrivateLedgerStream(self, descriptor)

    def fsync(self, descriptor):
        self.descriptor(descriptor)
        self.begin('fsync', {'descriptor': descriptor})

    def close(self, descriptor):
        row = self.descriptor(descriptor)
        self.begin('close', {'descriptor': descriptor})
        # POSIX releases a file's held flock when its owning descriptor closes.
        key = tuple(row['identity'])
        if self.locks.get(key) == descriptor: self.locks.pop(key)
        self.descriptors.pop(descriptor)

    def flock(self, descriptor, operation):
        row = self.descriptor(descriptor, 'file')
        if operation not in (self.LOCK_EX, self.LOCK_UN) or type(operation) is not int:
            raise InputAdmissionError('synthetic_ledger_private_lock_operation')
        self.begin('flock', {'descriptor': descriptor, 'operation': operation})
        key = tuple(row['identity'])
        if operation == self.LOCK_UN:
            if self.locks.get(key) == descriptor: self.locks.pop(key)
        elif key in self.locks and self.locks[key] != descriptor:
            # A finite private candidate cannot promise a native blocking wait.
            self.fail(errno.EWOULDBLOCK)
        else: self.locks[key] = descriptor

    def link(self, source, target):
        source, source_label = self.path(source)
        target, target_label = self.path(target)
        self.begin('link', {'source': source, 'source_label': source_label,
                            'target': target, 'target_label': target_label})
        try:
            self.tree.parent(source, source_label)
            value = self.tree.state(source)
            if value['kind'] == 'missing': self.fail(errno.ENOENT, source_label)
            if value['kind'] != 'file':
                raise InputAdmissionError('synthetic_ledger_private_link_regular_file_required')
            self.tree.parent(target, target_label, write=True)
            if self.tree.state(target)['kind'] != 'missing': self.fail(errno.EEXIST, target_label)
            self.tree.put(target, value)
        except OSError as error:
            raise type(error)(error.errno, error.strerror, source_label, None, target_label) from None

    def unlink(self, path):
        name, label = self.path(path)
        self.begin('unlink', {'path': name, 'label': label})
        self.tree.parent(name, label, write=True)
        value = self.tree.state(name)
        if value['kind'] == 'missing': self.fail(errno.ENOENT, label)
        if value['kind'] != 'file': self.fail(errno.EISDIR, label)
        self.tree.put(name, {'kind': 'missing'})


class PrivateLedgerStream:
    def __init__(self, owner, descriptor):
        self.owner, self.descriptor = owner, descriptor
        self.closed = False
        self.buffer = b''

    def require_open(self):
        if self.closed: raise ValueError('I/O operation on closed file.')
        return self.owner.descriptor(self.descriptor, 'file')

    def __enter__(self):
        self.require_open()
        return self

    def __exit__(self, kind, error, traceback):
        self.close()
        return False

    def write(self, raw):
        self.require_open()
        if type(raw) is not bytes:
            raise InputAdmissionError('synthetic_ledger_private_bytes_required')
        if len(self.buffer) + len(raw) > self.owner.tree.budget.file or self.owner.total + len(raw) > self.owner.tree.budget.total:
            raise InputAdmissionError('synthetic_ledger_private_stream_budget')
        self.owner.begin('stream-write', {'descriptor': self.descriptor,
                                          'payload': self.owner.store(raw)})
        self.owner.total += len(raw)
        self.buffer += raw
        return len(raw)

    def flush(self):
        row = self.require_open()
        self.owner.begin('stream-flush', {'descriptor': self.descriptor})
        value = {**row['value'], 'content': self.owner.store(self.buffer)}
        row['value'] = value
        self.owner.tree.replace_inode(row['identity'], value)

    def fileno(self):
        self.require_open()
        return self.descriptor

    def close(self):
        if self.closed: return
        try:
            self.flush()
        finally:
            try: self.owner.close(self.descriptor)
            finally: self.closed = True
