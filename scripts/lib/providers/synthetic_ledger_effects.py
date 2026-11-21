"""Explicit owned POSIX effects for the complete original synthetic store.

Logical descriptor tokens are retained; producer fd integers stay private to
this adapter. Real buffered stream behavior, errors and partial file states
are observed after every operation. This is never the private projection.
"""
import errno
import fcntl
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
import time
import hashlib

from lib.providers.operations_files import held_root
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.providers.synthetic_lifecycle_io import capture_port
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_ledger_projection import PrivateLedgerEffects
from lib.synthetic_lifecycle_io import path_spec
from lib.synthetic_ledger_budget import DEFAULT, admitted
from lib.synthetic_ledger_effect_state import EffectState
from lib.requirement_validation_replay import IntegrityError


def error_value(error):
    return {'type': type(error).__name__, 'message': str(error),
            'errno': error.errno, 'strerror': error.strerror,
            'filename': error.filename, 'filename2': error.filename2}


class NativeLedgerEffects:
    O_RDONLY = PrivateLedgerEffects.O_RDONLY
    O_CREAT = PrivateLedgerEffects.O_CREAT
    O_RDWR = PrivateLedgerEffects.O_RDWR
    O_NOFOLLOW = PrivateLedgerEffects.O_NOFOLLOW
    O_DIRECTORY = PrivateLedgerEffects.O_DIRECTORY
    LOCK_EX, LOCK_UN = PrivateLedgerEffects.LOCK_EX, PrivateLedgerEffects.LOCK_UN

    def __init__(self, owner, ledger, *, transaction_name, lock_seconds=30):
        if owner.mode != 'selected-files':
            raise InputAdmissionError('synthetic_ledger_native_selected_files_required')
        if type(lock_seconds) not in (int, float) or not 0 < lock_seconds <= 30:
            raise InputAdmissionError('synthetic_ledger_finite_lock_budget_required')
        self.budget = admitted(getattr(owner, "ledger_budget", DEFAULT))
        self.io, self.ledger = owner, Path(ledger)
        self.files = getattr(owner, 'ledger_files', None)
        if self.files is None: self.files = LedgerFiles(owner, ledger, transaction_name=transaction_name, budget=self.budget)
        if self.files.ledger != self.ledger or self.files.budget != self.budget:
            raise InputAdmissionError('synthetic_ledger_file_scope_changed')
        self.transaction_name, self.lock_seconds = transaction_name, lock_seconds
        self.descriptors, self.temporary_names, self.observed = {}, set(), {}
        self.serial = self.operations = self.total = 0
        self.state = EffectState(owner.blob, str(self.ledger), owner.cwd, transaction_name, budget=self.budget)
        # Capturing resolves retained blob references without reading selected
        # source again. The record owns these inert private bytes.
        from lib.providers.sbom_export_storage import read_private
        def retained(ref):
            if type(ref.get('bytes')) is not int or not 0 <= ref['bytes'] <= self.budget.file:
                raise InputAdmissionError('synthetic_ledger_private_blob_budget')
            raw = read_private(owner.record.blobs / ref['sha256'], self.budget.file)
            if len(raw) != ref['bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
                raise InputAdmissionError('synthetic_ledger_private_blob_changed')
            return raw
        self.state.blob = retained
        self.observed = self.state.observed
        owner.effect_state = self.state
        self.attempts = []

    @property
    def record(self): return self.io.record

    def release_resources(self):
        """Release owned host resources after the original kernel has ended.

        This is adapter teardown, outside the retained original execution. It
        needs no journal reservation and never unlinks history or retries an
        original operation. Buffered teardown can flush bytes; its presence
        therefore makes capture incomplete rather than certifying those bytes
        as part of the reconstructed original execution.
        """
        observed = len(self.descriptors)
        streams = sum(row['handle'] is not None for row in self.descriptors.values())
        errors = []
        for token, row in tuple(self.descriptors.items()):
            try:
                value = os.fstat(row['fd'])
                if ([value.st_dev, value.st_ino] != row['identity']
                        or stat.S_IMODE(value.st_mode) != row['mode']
                        or value.st_uid != os.geteuid()):
                    errors.append('descriptor_identity_changed')
                    continue
                if row['handle'] is not None:
                    try: row['handle'].close()
                    except Exception as error: errors.append(type(error).__name__)
                try: value = os.fstat(row['fd'])
                except OSError as error:
                    if error.errno != errno.EBADF: raise
                    self.descriptors.pop(token)
                    continue
                # Closing a buffered object may release its fd. Recheck the
                # binding before touching any still-open integer descriptor.
                if [value.st_dev, value.st_ino] != row['identity']:
                    errors.append('descriptor_identity_changed')
                    continue
                os.close(row['fd'])
                self.descriptors.pop(token)
            except Exception as error:
                errors.append(type(error).__name__)
        return {'required': True, 'observed_descriptors': observed,
                'released_descriptors': observed - len(self.descriptors),
                'remaining_descriptors': len(self.descriptors),
                'buffered_streams': streams, 'errors': errors}

    def path(self, path):
        label = str(path)
        value = PurePosixPath(label)
        if not value.is_absolute(): value = PurePosixPath(self.io.cwd) / value
        import posixpath
        name = posixpath.normpath(str(value))
        path_spec(name, label, self.io.cwd)
        self.io.check(name, label, write=True)
        if len(PurePosixPath(name).parts) > 100:
            raise InputAdmissionError('synthetic_ledger_native_path_depth_budget')
        return name, label

    def snapshot(self, name):
        anchor = self.io.output.anchor(name)
        try:
            with held_root(Path(name).parent) as parent:
                value = os.stat(Path(name).name, dir_fd=parent, follow_symlinks=False)
                regular = stat.S_ISREG(value.st_mode)
        except (FileNotFoundError, NotADirectoryError):
            regular = False
        if regular:
            _, observation = self.files.read(name, name)
            return observation
        state = anchor.snapshot(name)
        if state['kind'] == 'directory':
            observed = self.files.directory(name)
            if observed['snapshot'] != state:
                raise InputAdmissionError('synthetic_ledger_directory_replaced_before_observation')
            return observed
        return {'snapshot': state, 'metadata': None, 'aliases': []}

    def resources(self):
        rows = []
        for token, row in sorted(self.descriptors.items()):
            value = os.fstat(row['fd'])
            if ([value.st_dev, value.st_ino] != row['identity']
                    or stat.S_IMODE(value.st_mode) != row['mode']
                    or value.st_uid != os.geteuid()):
                raise InputAdmissionError('synthetic_ledger_open_descriptor_changed')
            try:
                with held_root(Path(row['path']).parent) as parent:
                    named = os.stat(Path(row['path']).name, dir_fd=parent, follow_symlinks=False)
                if (named.st_dev, named.st_ino, named.st_mode) != (value.st_dev, value.st_ino, value.st_mode):
                    raise InputAdmissionError('synthetic_ledger_open_descriptor_path_replaced')
            except FileNotFoundError:
                if row['role'] != 'temporary' or value.st_nlink != 0:
                    raise InputAdmissionError('synthetic_ledger_open_descriptor_path_removed') from None
            if row['role'] == 'lock' and value.st_nlink != 1 or row['role'] == 'temporary' and value.st_nlink not in (0, 1):
                raise InputAdmissionError('synthetic_ledger_open_descriptor_alias_changed')
            rows.append({'descriptor': token, 'path': row['path'], 'role': row['role'],
                         'identity': row['identity'], 'mode': row['mode'],
                         'stream': row['handle'] is not None, 'nlink': value.st_nlink})
        return rows

    def scope(self, paths):
        names = list(paths) + [row['path'] for row in self.descriptors.values()]
        for path in list(names):
            for parent in Path(path).parents:
                if not parent.is_relative_to(self.ledger): break
                names.append(str(parent))
        return list(dict.fromkeys(names))

    def call(self, action, arguments, paths, effect):
        self.operations += 1
        if self.operations > 8192:
            self.io.record.capture_incomplete = True
            raise InputAdmissionError('synthetic_ledger_native_operation_budget')
        before_paths = self.scope(paths)
        before = {name: self.snapshot(name) for name in before_paths}
        for name, value in before.items():
            if name in self.observed and self.observed[name] != value:
                raise InputAdmissionError('synthetic_ledger_changed_between_effects')
            if name in self.io.metadata:
                actual = value['metadata']
                if actual is None: actual = self.io.entry(name)
                if actual != self.io.metadata[name]:
                    raise InputAdmissionError('synthetic_ledger_input_changed_before_effect')
        frame = {'kind': 'synthetic-ledger-effect-before', 'action': action,
                 'files': before, 'descriptors': self.resources()}
        try: self.state.before(frame, action, before_paths, self.io.metadata)
        except IntegrityError as error:
            raise InputAdmissionError(str(error)) from error
        self.io.append(frame)
        failure, ok, value, technical = None, False, None, False
        try:
            value = self.io.perform('synthetic-ledger-' + action, arguments, effect)
            ok = True
            return value
        except OSError as error:
            failure = error_value(error)
            raise
        except Exception:
            technical = True
            self.io.record.capture_incomplete = True
            raise
        finally:
            try:
                # The effect has now run. Clear its exact causal source cache
                # entries before acquiring after-images; otherwise the shared
                # anchor guard mistakes our own new directory entry for an
                # external change. The before-images were already validated.
                after_paths = self.scope(paths + (self.attempts if action == 'mkstemp' else []))
                self.io.output.invalidate(after_paths, parents=True)
                after = {name: self.snapshot(name) for name in after_paths}
                frame = {'kind': 'synthetic-ledger-effect-after', 'action': action,
                         'files': after, 'descriptors': self.resources(), 'failure': failure,
                         'attempts': list(self.attempts) if action == 'mkstemp' else []}
                self.io.append(frame)
                if not technical:
                    try: self.state.finish(before, frame, action, arguments, ok, value)
                    except IntegrityError as error: raise InputAdmissionError(str(error)) from error
                # Native changes invalidate lazy source caches for exactly the
                # affected names and their directory memberships.
            except Exception:
                self.io.record.capture_incomplete = True
                raise

    def require_capacity(self):
        if len(self.descriptors) >= 128:
            raise InputAdmissionError('synthetic_ledger_native_descriptor_budget')

    def allocate(self, fd, path, role):
        value = os.fstat(fd)
        if (value.st_uid != os.geteuid() or value.st_mode & 0o7022
                or role == 'directory' and not stat.S_ISDIR(value.st_mode)
                or role != 'directory' and (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1)):
            raise InputAdmissionError('synthetic_ledger_new_owned_descriptor_required')
        self.serial += 1
        self.descriptors[self.serial] = {'fd': fd, 'path': path, 'role': role,
            'identity': [value.st_dev, value.st_ino], 'mode': stat.S_IMODE(value.st_mode), 'handle': None}
        return self.serial

    def descriptor(self, token, role=None):
        if type(token) is not int or token not in self.descriptors:
            raise InputAdmissionError('synthetic_ledger_unknown_descriptor_token')
        row = self.descriptors[token]
        if role is not None and row['role'] != role:
            raise InputAdmissionError('synthetic_ledger_descriptor_role_changed')
        return row

    @capture_port
    def open(self, path, flags, mode=0o777):
        self.require_capacity()
        name, label = self.path(path)
        lock_flags = self.O_CREAT | self.O_RDWR | self.O_NOFOLLOW
        if type(flags) is not int or type(mode) is not int or not 0 <= mode <= 0o777:
            raise InputAdmissionError('synthetic_ledger_original_open_contract_required')
        if flags == lock_flags and Path(name) == self.ledger / '.append.lock':
            role, native_flags = 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        elif flags == self.O_DIRECTORY and Path(name) == self.ledger / 'transactions':
            role, native_flags = 'directory', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        else:
            raise InputAdmissionError('synthetic_ledger_original_open_selection_required')
        anchor = self.io.output.anchor(name)
        def effect():
            parts = anchor.parts(name)
            with anchor.root_fd() as root:
                with anchor.parent(root, parts[:-1]) as parent:
                    try: fd = os.open(parts[-1], native_flags, mode, dir_fd=parent)
                    except OSError as error:
                        if error.filename is None: raise
                        raise type(error)(error.errno, error.strerror, label) from None
                    try: return self.allocate(fd, name, role)
                    except BaseException:
                        os.close(fd)
                        raise
        return self.call('open', {'path': name, 'label': label, 'flags': flags, 'mode': mode}, [name], effect)

    @capture_port
    def mkstemp(self, *, prefix, dir):
        self.require_capacity()
        directory, label = self.path(dir)
        if prefix != '.pending-' or Path(directory) != self.ledger / 'transactions':
            raise InputAdmissionError('synthetic_ledger_original_temporary_selection_required')
        paths = [directory]
        self.attempts = []
        anchor = self.io.output.anchor(directory)
        def effect():
            # tempfile's generator is used only for inert random names. The
            # exclusive creation is relative to the held owned parent fd.
            parts = anchor.parts(directory)
            with anchor.root_fd() as root:
                with anchor.parent(root, parts) as parent:
                    for _ in range(128):
                        name = prefix + next(tempfile._get_candidate_names())
                        self.attempts.append(str(Path(directory) / name))
                        self.io.reserve()
                        try: fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                        except FileExistsError: continue
                        except OSError as error:
                            if error.filename is None: raise
                            raise type(error)(error.errno, error.strerror, str(Path(directory) / name)) from None
                        path = str(Path(directory) / name)
                        paths.append(path)
                        self.temporary_names.add(path)
                        try: token = self.allocate(fd, path, 'temporary')
                        except BaseException:
                            os.close(fd)
                            raise
                        return {'descriptor': token, 'temporary': path}
            raise InputAdmissionError('synthetic_ledger_temporary_collision_budget')
        value = self.call('mkstemp', {'directory': directory, 'label': label, 'prefix': prefix}, paths, effect)
        return value['descriptor'], value['temporary']

    @capture_port
    def fdopen(self, descriptor, mode):
        row = self.descriptor(descriptor, 'temporary')
        if mode != 'wb' or row['handle'] is not None:
            raise InputAdmissionError('synthetic_ledger_original_buffered_stream_required')
        def effect(): row['handle'] = os.fdopen(row['fd'], mode)
        self.call('fdopen', {'descriptor': descriptor, 'mode': mode}, [row['path']], effect)
        return NativeLedgerStream(self, descriptor)

    @capture_port
    def fsync(self, descriptor):
        row = self.descriptor(descriptor)
        return self.call('fsync', {'descriptor': descriptor}, [row['path']], lambda: self.sync_descriptor(row['fd']))

    def sync_descriptor(self, descriptor):
        """Selected-store effect only; journal persistence has its own fsync."""
        return os.fsync(descriptor)

    @capture_port
    def close(self, descriptor):
        row = self.descriptor(descriptor)
        if row['handle'] is not None:
            raise InputAdmissionError('synthetic_ledger_stream_owned_close_required')
        def effect():
            try: return os.close(row['fd'])
            finally:
                try: os.fstat(row['fd'])
                except OSError as error:
                    if error.errno == errno.EBADF: self.descriptors.pop(descriptor)
                    else: raise
        return self.call('close', {'descriptor': descriptor}, [row['path']], effect)

    @capture_port
    def flock(self, descriptor, operation):
        row = self.descriptor(descriptor, 'lock')
        if type(operation) is not int or operation not in (self.LOCK_EX, self.LOCK_UN):
            raise InputAdmissionError('synthetic_ledger_original_lock_operation_required')
        def effect():
            if operation == self.LOCK_UN: return fcntl.flock(row['fd'], fcntl.LOCK_UN)
            deadline = time.monotonic() + self.lock_seconds
            while True:
                try: return fcntl.flock(row['fd'], fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise InputAdmissionError('synthetic_ledger_native_lock_capture_timeout')
                    time.sleep(0.02)
        return self.call('flock', {'descriptor': descriptor, 'operation': operation}, [row['path']], effect)

    @capture_port
    def link(self, source, target):
        source, source_label = self.path(source)
        target, target_label = self.path(target)
        if source not in self.temporary_names or Path(target).parent != self.ledger / 'transactions':
            raise InputAdmissionError('synthetic_ledger_original_publication_selection_required')
        raw, _ = self.files.read(source, source_label)
        if Path(target).name != self.transaction_name(raw):
            raise InputAdmissionError('synthetic_ledger_publication_identity_unbound')
        anchor = self.io.output.anchor(source)
        def effect():
            parts = anchor.parts(source)
            with anchor.root_fd() as root:
                with anchor.parent(root, parts[:-1]) as parent:
                    try: return os.link(parts[-1], Path(target).name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                    except OSError as error:
                        if error.filename is None: raise
                        raise type(error)(error.errno, error.strerror, source_label, None, target_label) from None
        return self.call('link', {'source': source, 'source_label': source_label,
            'target': target, 'target_label': target_label}, [source, target], effect)

    @capture_port
    def unlink(self, path):
        name, label = self.path(path)
        if name not in self.temporary_names:
            raise InputAdmissionError('synthetic_ledger_original_temporary_cleanup_required')
        anchor = self.io.output.anchor(name)
        def effect():
            parts = anchor.parts(name)
            with anchor.root_fd() as root:
                with anchor.parent(root, parts[:-1]) as parent:
                    try: return os.unlink(parts[-1], dir_fd=parent)
                    except OSError as error:
                        if error.filename is None: raise
                        raise type(error)(error.errno, error.strerror, label) from None
        # A successful unlink changes the sibling canonical file's nlink and
        # ctime too. Invalidate those retained source observations together.
        observation = self.snapshot(name)
        paths = [name] + [n for n in observation['aliases'] if n != name]
        return self.call('unlink', {'path': name, 'label': label}, paths, effect)


class NativeLedgerStream:
    def __init__(self, owner, descriptor):
        self.owner, self.token = owner, descriptor

    def row(self): return self.owner.descriptor(self.token, 'temporary')

    @capture_port
    def __enter__(self):
        row = self.row()
        self.owner.call('stream-enter', {'descriptor': self.token}, [row['path']],
                        lambda: row['handle'].__enter__() and None)
        return self

    @capture_port
    def __exit__(self, kind, error, traceback):
        row = self.row()
        arguments = {'descriptor': self.token, 'exception_type': None if kind is None else kind.__name__,
                     'exception_message': None if error is None else str(error)}
        def effect():
            try: return row['handle'].__exit__(kind, error, traceback)
            finally:
                if row['handle'].closed: self.owner.descriptors.pop(self.token)
        return self.owner.call('stream-exit', arguments, [row['path']], effect)

    @property
    def io(self): return self.owner.io

    @capture_port
    def write(self, raw):
        row = self.row()
        if type(raw) is not bytes or len(raw) > self.owner.budget.file or self.owner.total + len(raw) > self.owner.budget.total:
            raise InputAdmissionError('synthetic_ledger_original_stream_byte_budget')
        self.owner.total += len(raw)
        return self.owner.call('stream-write', {'descriptor': self.token, 'payload': self.io.blob(raw)},
                               [row['path']], lambda: row['handle'].write(raw))

    @capture_port
    def flush(self):
        row = self.row()
        return self.owner.call('stream-flush', {'descriptor': self.token}, [row['path']], row['handle'].flush)

    def fileno(self):
        self.row()
        return self.token

    @property
    def record(self): return self.io.record
