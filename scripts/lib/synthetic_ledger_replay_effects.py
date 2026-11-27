"""Original POSIX store reexecution from retained facts; no native effects."""
from pathlib import PurePosixPath as P
import posixpath

from lib.synthetic_ledger_effect_state import EffectState, require
from lib.synthetic_ledger_budget import DEFAULT, admitted
from lib.synthetic_ledger_io import retained_error
from lib.synthetic_lifecycle_io import path_spec
from lib.synthetic_ledger_projection import PrivateLedgerEffects


class ReplayLedgerEffects:
    O_RDONLY, O_CREAT, O_RDWR, O_NOFOLLOW, O_DIRECTORY = (PrivateLedgerEffects.O_RDONLY,
        PrivateLedgerEffects.O_CREAT, PrivateLedgerEffects.O_RDWR, PrivateLedgerEffects.O_NOFOLLOW,
        PrivateLedgerEffects.O_DIRECTORY)
    LOCK_EX, LOCK_UN = PrivateLedgerEffects.LOCK_EX, PrivateLedgerEffects.LOCK_UN

    def __init__(self, owner, ledger, *, transaction_name):
        self.io, self.ledger = owner, P(ledger)
        require(owner.mode == 'selected-files', 'replay_native_mode_changed')
        self.state = EffectState(owner.blob, str(self.ledger), owner.cwd, transaction_name,
            budget=admitted(getattr(owner, "ledger_budget", DEFAULT)))
        owner.effect_state = self.state

    @property
    def descriptors(self): return self.state.descriptors

    def descriptor(self, token, role=None):
        require(type(token) is int and token in self.descriptors, 'replay_descriptor_changed')
        row = self.descriptors[token]
        require(role is None or row['role'] == role, 'replay_descriptor_role_changed')
        return row

    def path(self, path):
        label = str(path); value = P(label)
        if not value.is_absolute(): value = P(self.io.cwd) / value
        name = posixpath.normpath(str(value))
        path_spec(name, label, self.io.cwd)
        require(len(P(name).parts) <= 100, 'replay_path_depth_budget')
        return name, label

    def scope(self, paths):
        names = list(paths) + [row['path'] for row in self.descriptors.values()]
        for path in list(names):
            for parent in P(path).parents:
                if not parent.is_relative_to(self.ledger): break
                names.append(str(parent))
        return list(dict.fromkeys(names))

    def call(self, action, args, paths):
        before = self.io.row()
        values = self.state.before(before, action, self.scope(paths), self.io.metadata)
        ok, value = self.io.outcome('synthetic-ledger-' + action, args, 'json')
        after = self.io.row()
        failure = None if ok else retained_error(after.get('failure'), value)
        self.state.finish(values, after, action, args, ok, value)
        self.io.output.invalidate(list(after['files']), parents=True)
        if failure is not None: raise failure
        return value

    def open(self, path, flags, mode=0o777):
        name, label = self.path(path)
        require(type(flags) is int and type(mode) is int and 0 <= mode <= 0o777,
                'replay_open_options_changed')
        require(name == str(self.ledger / '.append.lock') and flags == 7
                or name == str(self.ledger / 'transactions') and flags == 8,
                'replay_open_selection_changed')
        return self.call('open', {'path': name, 'label': label, 'flags': flags, 'mode': mode}, [name])

    def mkstemp(self, *, prefix, dir):
        directory, label = self.path(dir)
        require(directory == str(self.ledger / 'transactions') and prefix == '.pending-', 'replay_temporary_selection_changed')
        value = self.call('mkstemp', {'directory': directory, 'label': label, 'prefix': prefix}, [directory])
        return value['descriptor'], value['temporary']

    def fdopen(self, descriptor, mode):
        row = self.descriptor(descriptor, 'temporary')
        require(mode == 'wb' and not row['stream'], 'replay_stream_mode_changed')
        self.call('fdopen', {'descriptor': descriptor, 'mode': mode}, [row['path']])
        return ReplayLedgerStream(self, descriptor)

    def fsync(self, descriptor):
        row = self.descriptor(descriptor)
        return self.call('fsync', {'descriptor': descriptor}, [row['path']])

    def close(self, descriptor):
        row = self.descriptor(descriptor)
        require(not row['stream'], 'replay_close_ownership_changed')
        return self.call('close', {'descriptor': descriptor}, [row['path']])

    def flock(self, descriptor, operation):
        row = self.descriptor(descriptor, 'lock')
        require(type(operation) is int and operation in (1, 2), 'replay_lock_operation_changed')
        return self.call('flock', {'descriptor': descriptor, 'operation': operation}, [row['path']])

    def link(self, source, target):
        source, source_label = self.path(source); target, target_label = self.path(target)
        return self.call('link', {'source': source, 'source_label': source_label,
            'target': target, 'target_label': target_label}, [source, target])

    def unlink(self, path):
        name, label = self.path(path)
        require(name in self.state.observed, 'replay_cleanup_preimage_missing')
        aliases = self.state.observed[name]['aliases']
        return self.call('unlink', {'path': name, 'label': label}, [name] + [n for n in aliases if n != name])


class ReplayLedgerStream:
    def __init__(self, owner, descriptor): self.owner, self.token = owner, descriptor
    def row(self): return self.owner.descriptor(self.token, 'temporary')
    def __enter__(self):
        self.owner.call('stream-enter', {'descriptor': self.token}, [self.row()['path']])
        return self
    def __exit__(self, kind, error, traceback):
        return self.owner.call('stream-exit', {'descriptor': self.token,
            'exception_type': None if kind is None else kind.__name__,
            'exception_message': None if error is None else str(error)}, [self.row()['path']])
    def write(self, raw):
        import hashlib
        require(type(raw) is bytes, 'replay_stream_payload_type_changed')
        ref = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        require(self.owner.io.blob(ref) == raw, 'replay_stream_payload_changed')
        return self.owner.call('stream-write', {'descriptor': self.token, 'payload': ref}, [self.row()['path']])
    def flush(self): return self.owner.call('stream-flush', {'descriptor': self.token}, [self.row()['path']])
    def fileno(self):
        self.row()
        return self.token
