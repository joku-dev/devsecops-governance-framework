"""Lazy retained private ledger projection and its closed pure reexecution."""
from copy import deepcopy
import hashlib, json, posixpath
from pathlib import PurePosixPath as P

from lib.synthetic_ledger_projection import LedgerProjection, PrivateLedgerEffects
from lib.synthetic_lifecycle_projection_io import ReplayProjection as ReportReplay
from lib.synthetic_lifecycle_projection import PRIVATE_MASK, EMPTY
from lib.synthetic_lifecycle_io import path_spec
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.workbook_import_io import READ_ERRORS
from lib.document_rendering_io import parse_tool_json
from lib.synthetic_ledger_io import observation


def same(left, right):
    return json.dumps(left, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':')) == json.dumps(right, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(',', ':'))


class ProjectionMixin:
    def ledger_tree(self, blob): self.tree = LedgerProjection(blob)

    def start(self):
        if self.started: return
        empty = self.store(b'')
        if empty != EMPTY: raise IntegrityError('synthetic_ledger_private_empty_content_changed')
        self.emit({'kind': 'synthetic-ledger-private-context', 'creation_mask': PRIVATE_MASK,
                   'identity_namespace': 'private-projection', 'native_source_effects': False, 'empty_content': empty})
        self.started = True

    def prepare(self, path, label):
        spec = self.selection(path, label); self.start(); self.operations += 1
        if self.operations > 8192: raise InputAdmissionError('synthetic_ledger_private_preimage_budget')
        frame, values = self.obtain(path, label)
        self.selection(frame['path'], frame['path'])
        self.emit({'kind': 'lifecycle-private-preimages', 'selection': spec, 'anchor': frame, 'snapshots': values})
        for name, value in values.items():
            known = self.io.metadata.get(name)
            if known is None: continue
            if known['kind'] != value['kind']: raise IntegrityError('synthetic_ledger_private_input_kind_changed')
            if known['kind'] != 'missing':
                if any(known[k] != value[k] for k in ('identity', 'mode')):
                    raise IntegrityError('synthetic_ledger_private_input_identity_changed')
                if known['kind'] == 'file':
                    raw = self.tree.blob(value['content'])
                    if len(raw) != known['bytes']: raise IntegrityError('synthetic_ledger_private_input_size_changed')
                    prior = getattr(self.io, 'ledger_reads', {}).get(name)
                    if prior is None and name in getattr(self.io, 'reads', {}): prior = self.io.reads[name][0]
                    if prior is None and name in getattr(getattr(self.io, 'data', None), 'observed', {}): prior = self.io.data.observed[name][0]
                    if prior is not None and prior != raw: raise IntegrityError('synthetic_ledger_private_input_bytes_changed')
        return spec, self.tree.load(frame, values, path)

    def membership(self, path):
        value = self.tree.state(path)
        if value['kind'] != 'directory' or path in self.tree.nodes: return
        if path not in self.io.members: self.io.native_iterdir(path, path)
        info = self.io.metadata[path]
        self.tree.load_one(path, {'kind': 'directory', 'identity': info['identity'], 'mode': info['mode']})
        self.tree.load_membership(path, self.io.members[path])


class ReplayProjection(ProjectionMixin, ReportReplay):
    def __init__(self, owner):
        super().__init__(owner)
        self.ledger_tree(owner.blob)

    def emit(self, value):
        if not same(self.io.row(), value): raise IntegrityError('synthetic_ledger_private_observation_changed')

    def obtain(self, path, label):
        aliases = {}
        while (self.io.position < self.io.limit and type(self.io.events[self.io.position]) is dict
               and self.io.events[self.io.position].get('kind') == 'synthetic-ledger-private-alias-preimage'):
            row = self.io.row()
            if set(row) != {'kind', 'path', 'observation'} or row['path'] in aliases:
                raise IntegrityError('synthetic_ledger_private_alias_preimage_changed')
            path_spec(row['path'], row['path'], self.io.cwd)
            info = observation(row['observation'], self.io.blob, path=row['path'], ledger=str(self.io.ledger), transaction_name=self.io.transaction_name)
            if info is None or info['kind'] != 'file' or info['nlink'] != 2:
                raise IntegrityError('synthetic_ledger_private_alias_pair_required')
            aliases[row['path']] = row['observation']
        frame, values = super().obtain(path, label)
        if any(name not in values or not same(value['snapshot'], values[name]) for name, value in aliases.items()):
            raise IntegrityError('synthetic_ledger_private_alias_snapshot_binding_changed')
        return frame, values

    def perform(self, action, args, effect, *, encoding='json'):
        # The original private store emits domain steps inside the operation.
        # Consume the intent first, then recompute and validate those steps.
        token = self.io.position
        if not same(self.io.row(), {'kind': 'intent', 'operation': token, 'action': action, 'arguments': args}):
            raise IntegrityError('synthetic_ledger_private_intent_changed')
        expected = error = None
        try: expected = effect()
        except (OSError, UnicodeError) as failure: error = failure
        row = self.io.row()
        if error is not None:
            if (set(row) != {'kind', 'operation', 'exception', 'message'} or row['kind'] != 'failed'
                    or row['operation'] != token or row['exception'] != type(error).__name__ or row['message'] != str(error)):
                raise IntegrityError('synthetic_ledger_private_failure_changed')
            raise error
        if (set(row) != {'kind', 'operation', 'encoding', 'value'} or row['kind'] != 'returned'
                or row['operation'] != token or row['encoding'] != encoding):
            raise IntegrityError('synthetic_ledger_private_return_changed')
        raw = self.io.blob(row['value']); value = raw if encoding == 'bytes' else parse_tool_json(raw)
        if type(expected) is not type(value) or expected != value:
            raise IntegrityError('synthetic_ledger_private_result_changed')
        return value


class PrivateLedgerPort:
    O_RDONLY, O_CREAT, O_RDWR, O_NOFOLLOW, O_DIRECTORY = (PrivateLedgerEffects.O_RDONLY,
        PrivateLedgerEffects.O_CREAT, PrivateLedgerEffects.O_RDWR, PrivateLedgerEffects.O_NOFOLLOW,
        PrivateLedgerEffects.O_DIRECTORY)
    LOCK_EX, LOCK_UN = PrivateLedgerEffects.LOCK_EX, PrivateLedgerEffects.LOCK_UN

    def __init__(self, owner, ledger):
        if owner.mode != 'private-candidate': raise InputAdmissionError('synthetic_ledger_private_mode_required')
        self.io, self.ledger, self.projection = owner, P(ledger), owner.projection
        self.streams = {}
        self.core = PrivateLedgerEffects(self.projection.tree, self.projection.store,
            absolute=lambda path: posixpath.normpath(str(path if path.is_absolute() else P(owner.cwd) / path)),
            emit=self.projection.emit)

    @property
    def descriptors(self): return self.core.descriptors

    def path(self, path): return self.core.path(path)

    def scope(self, paths):
        names = list(paths) + [row['path'] for row in self.descriptors.values()]
        for path in list(names):
            for parent in P(path).parents:
                if not parent.is_relative_to(self.ledger): break
                names.append(str(parent))
        return list(dict.fromkeys(names))

    def resources(self):
        return {'descriptors': [{'descriptor': key, **deepcopy(value)} for key, value in sorted(self.descriptors.items())],
                'locks': [{'identity': list(key), 'descriptor': value} for key, value in sorted(self.core.locks.items())],
                'buffers': [{'descriptor': key, 'payload': self.projection.store(value.core.buffer)}
                            for key, value in sorted(self.streams.items()) if key in self.descriptors]}

    def states(self, paths):
        tree = self.core.tree
        return {'states': {name: tree.state(name) for name in paths},
                'members': {name: tree.entries(name, name) for name in paths if tree.state(name)['kind'] == 'directory'}}

    def call(self, action, args, paths, effect):
        paths = self.scope(paths)
        for name in paths:
            self.projection.prepare(name, name)
            self.projection.membership(name)
        self.projection.emit({'kind': 'synthetic-ledger-private-before', 'action': action,
                              **self.states(paths), **self.resources(), 'native_effect': False})
        tree = self.core.tree; tree.changed = []
        try: return self.projection.perform('synthetic-ledger-private-' + action, args, effect)
        finally:
            changed = list(tree.changed)
            after = list(dict.fromkeys(paths + changed))
            self.projection.emit({'kind': 'synthetic-ledger-private-after', 'action': action,
                                  **self.states(after), **self.resources(), 'changed': changed, 'native_effect': False})
            self.io.projected_changes.update({name: tree.nodes[name] for name in changed})

    def open(self, path, flags, mode=0o777):
        name, label = self.path(path)
        return self.call('open', {'path': name, 'label': label, 'flags': flags, 'mode': mode}, [name], lambda: self.core.open(path, flags, mode))

    def mkstemp(self, *, prefix, dir):
        name, label = self.path(dir)
        def effect():
            token, temporary = self.core.mkstemp(prefix=prefix, dir=dir)
            return {'descriptor': token, 'temporary': temporary}
        value = self.call('mkstemp', {'directory': name, 'label': label, 'prefix': prefix}, [name], effect)
        return value['descriptor'], value['temporary']

    def fdopen(self, descriptor, mode):
        row = self.core.descriptor(descriptor)
        def effect(): self.streams[descriptor] = PrivateStreamPort(self, descriptor, self.core.fdopen(descriptor, mode))
        self.call('fdopen', {'descriptor': descriptor, 'mode': mode}, [row['path']], effect)
        return self.streams[descriptor]

    def fsync(self, descriptor):
        row = self.core.descriptor(descriptor)
        return self.call('fsync', {'descriptor': descriptor}, [row['path']], lambda: self.core.fsync(descriptor))

    def close(self, descriptor):
        row = self.core.descriptor(descriptor)
        return self.call('close', {'descriptor': descriptor}, [row['path']], lambda: self.core.close(descriptor))

    def flock(self, descriptor, operation):
        row = self.core.descriptor(descriptor)
        return self.call('flock', {'descriptor': descriptor, 'operation': operation}, [row['path']], lambda: self.core.flock(descriptor, operation))

    def link(self, source, target):
        source_name, source_label = self.path(source); target_name, target_label = self.path(target)
        return self.call('link', {'source': source_name, 'source_label': source_label, 'target': target_name, 'target_label': target_label},
                         [source_name, target_name], lambda: self.core.link(source, target))

    def unlink(self, path):
        name, label = self.path(path)
        return self.call('unlink', {'path': name, 'label': label}, [name], lambda: self.core.unlink(path))


class PrivateStreamPort:
    def __init__(self, owner, token, core): self.owner, self.token, self.core = owner, token, core
    def path(self): return self.owner.core.descriptor(self.token)['path']
    def __enter__(self):
        def effect(): self.core.__enter__()
        self.owner.call('stream-enter', {'descriptor': self.token}, [self.path()], effect)
        return self
    def __exit__(self, kind, error, traceback):
        return self.owner.call('stream-exit', {'descriptor': self.token,
            'exception_type': None if kind is None else kind.__name__, 'exception_message': None if error is None else str(error)},
            [self.path()], lambda: self.core.__exit__(kind, error, traceback))
    def write(self, raw):
        return self.owner.call('stream-write', {'descriptor': self.token, 'payload': self.owner.projection.store(raw)},
                               [self.path()], lambda: self.core.write(raw))
    def flush(self):
        return self.owner.call('stream-flush', {'descriptor': self.token}, [self.path()], self.core.flush)
    def fileno(self): return self.core.fileno()
