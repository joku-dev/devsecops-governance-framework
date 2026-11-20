"""Closed retained ledger file observations, including one exact alias pair."""
from pathlib import PurePosixPath
from lib.requirement_review_output import snapshot
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_io import metadata


def retained_error(wire, failed):
    """Reconstruct original OS diagnostics, including both link filenames."""
    from lib.workbook_import_io import READ_ERRORS
    keys = {'type', 'message', 'errno', 'strerror', 'filename', 'filename2'}
    if (type(wire) is not dict or set(wire) != keys or wire['type'] not in READ_ERRORS
            or type(wire['errno']) is not int or type(wire['strerror']) is not str
            or any(wire[key] is not None and type(wire[key]) is not str for key in ('filename', 'filename2'))):
        raise IntegrityError('synthetic_ledger_error_wire_changed')
    cls = READ_ERRORS[wire['type']]
    error = (cls(wire['errno'], wire['strerror'], wire['filename'], None, wire['filename2'])
             if wire['filename2'] is not None else cls(wire['errno'], wire['strerror'], wire['filename']))
    if (type(error).__name__ != wire['type'] or str(error) != wire['message']
            or failed['exception'] != wire['type'] or failed['message'] != wire['message']):
        raise IntegrityError('synthetic_ledger_error_diagnostic_changed')
    return error


def observation(value, blob, *, path, ledger, transaction_name):
    if type(value) is not dict or set(value) != {'snapshot', 'metadata', 'aliases'}:
        raise IntegrityError('synthetic_ledger_file_observation_changed')
    state, info, aliases = value['snapshot'], value['metadata'], value['aliases']
    snapshot(state, blob)
    if type(aliases) is not list:
        raise IntegrityError('synthetic_ledger_alias_list_changed')
    if state['kind'] in ('missing', 'unreachable'):
        if info is not None or aliases:
            raise IntegrityError('synthetic_ledger_missing_metadata_changed')
        return None
    if (type(info) is not dict or type(info.get('nlink')) is not int
            or state['kind'] == 'file' and not 1 <= info['nlink'] <= 2):
        raise IntegrityError('synthetic_ledger_link_count_changed')
    metadata({**info, 'nlink': 1} if state['kind'] == 'file' else info)
    if info['kind'] != state['kind'] or info['identity'] != state['identity'] or info['mode'] != state['mode']:
        raise IntegrityError('synthetic_ledger_file_identity_changed')
    if state['kind'] == 'directory':
        if aliases: raise IntegrityError('synthetic_ledger_directory_alias_changed')
        return info
    raw = blob(state['content'])
    if len(raw) != info['bytes']:
        raise IntegrityError('synthetic_ledger_file_byte_count_changed')
    if info['nlink'] == 1:
        if aliases: raise IntegrityError('synthetic_ledger_unshared_alias_claim_changed')
        return info
    if (len(aliases) != 2 or any(type(n) is not str for n in aliases)
            or aliases != sorted(set(aliases)) or path not in aliases
            or any(str(PurePosixPath(n).parent) != str(PurePosixPath(ledger) / 'transactions')
                   or str(PurePosixPath(n)) != n or '..' in PurePosixPath(n).parts for n in aliases)):
        raise IntegrityError('synthetic_ledger_scoped_alias_pair_changed')
    pending = [n for n in aliases if PurePosixPath(n).name.startswith('.pending-')]
    accepted = [n for n in aliases if not PurePosixPath(n).name.startswith('.pending-')]
    if len(pending) != 1 or len(accepted) != 1:
        raise IntegrityError('synthetic_ledger_pending_canonical_pair_changed')
    try: expected = transaction_name(raw)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise IntegrityError('synthetic_ledger_alias_transaction_changed') from error
    if type(expected) is not str or PurePosixPath(expected).name != expected or PurePosixPath(accepted[0]).name != expected:
        raise IntegrityError('synthetic_ledger_alias_identity_unbound')
    return info


from lib.synthetic_lifecycle_io import ReplayIO as LifecycleReplay, path_spec, PROBES


class ReplayIO(LifecycleReplay):
    def __init__(self, *args, ledger, transaction_name, **kwargs):
        super().__init__(*args, **kwargs)
        self.ledger, self.transaction_name = ledger, transaction_name
        self.ledger_reads = {}
        if self.mode == 'private-candidate':
            from lib.synthetic_ledger_private import ReplayProjection
            self.projection = self.output = ReplayProjection(self)

    def ledger_path(self, path): return PurePosixPath(path).parent == PurePosixPath(self.ledger) / 'transactions'

    def mkdir(self, *args):
        prior = set(self.touched)
        try: return super().mkdir(*args)
        finally:
            created = {name: value for name, value in self.touched.items()
                       if name not in prior and value['kind'] == 'directory'}
            if created and hasattr(self, 'effect_state'): self.effect_state.mkdir(created)

    def remember_ledger(self, path, value):
        info = observation(value, self.blob, path=path, ledger=self.ledger, transaction_name=self.transaction_name)
        info = info or {'kind': 'missing'}
        if path in self.metadata and self.metadata[path] != info:
            raise IntegrityError('synthetic_ledger_repeated_metadata_changed')
        self.metadata[path] = info

    def ledger_outcome(self, action, path, label, probe=None):
        spec = path_spec(path, label, self.cwd)
        arguments = {'selection': spec}
        if probe is not None: arguments['probe'] = probe
        ok, value = self.outcome('synthetic-ledger-' + action, arguments, 'bytes' if action == 'read' else 'json')
        after = self.row()
        expected = {'kind', 'selection', 'observation', 'failure'} | ({'probe'} if probe is not None else set())
        if (set(after) != expected or after['kind'] != 'synthetic-ledger-' + action + '-after'
                or after['selection'] != spec or probe is not None and after['probe'] != probe):
            raise IntegrityError('synthetic_ledger_input_after_changed')
        if not ok:
            if after['observation'] is not None:
                raise IntegrityError('synthetic_ledger_failed_input_observation_changed')
            raise retained_error(after['failure'], value)
        if after['failure'] is not None:
            raise IntegrityError('synthetic_ledger_success_failure_claim_changed')
        self.remember_ledger(path, after['observation'])
        state = after['observation']['snapshot']
        if action == 'read':
            if state['kind'] != 'file' or value != self.blob(state['content']):
                raise IntegrityError('synthetic_ledger_retained_read_bytes_changed')
            self.ledger_reads[path] = value
        else:
            kind = state['kind']
            expected_value = kind in ('file', 'directory') if probe == 'exists' else kind == 'file' if probe == 'is_file' else kind == 'directory' if probe == 'is_dir' else False
            if type(value) is not bool or value != expected_value:
                raise IntegrityError('synthetic_ledger_retained_probe_result_changed')
        return value

    def read(self, path, label):
        if self.projection is not None and self.projection.tree.affected(path): return self.projection.read(path, label)
        if not self.ledger_path(path): return super().read(path, label)
        return self.ledger_outcome('read', path, label)

    def probe(self, path, kind, label):
        if self.projection is not None and self.projection.tree.affected(path): return self.projection.probe(path, kind, label)
        if not self.ledger_path(path): return super().probe(path, kind, label)
        if kind not in PROBES: raise IntegrityError('synthetic_ledger_probe_changed')
        return self.ledger_outcome('probe', path, label, kind)
