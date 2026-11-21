"""Shared closed transition checks for native capture and inert POSIX replay."""
from copy import deepcopy
from pathlib import PurePosixPath as P

from lib.synthetic_ledger_io import observation
from lib.synthetic_lifecycle_io import path_spec
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_ledger_budget import DEFAULT, admitted


def require(value, reason):
    if not value: raise IntegrityError('synthetic_ledger_' + reason)


def observed(value, blob, path, ledger, name_of, *, max_file=DEFAULT.file):
    require(type(value) is dict, 'effect_observation_changed')
    state = value.get('snapshot', {})
    if state.get('kind') == 'directory':
        require(set(value) == {'snapshot', 'metadata', 'aliases', 'members'}, 'directory_observation_changed')
        basic = {key: value[key] for key in ('snapshot', 'metadata', 'aliases')}
        info = observation(basic, blob, path=path, ledger=ledger, transaction_name=name_of, max_file=max_file)
        names = value['members']
        require(type(names) is list and len(names) <= 10000
                and all(type(n) is str and n and n not in ('.', '..') and '/' not in n
                        and '\\' not in n and all(32 <= ord(c) < 0xd800 or 0xdfff < ord(c) for c in n) for n in names)
                and names == sorted(set(names))
                and sum(len(n.encode('utf-8')) for n in names) <= 2 * 1024**2,
                'directory_members_changed')
        return info
    return observation(value, blob, path=path, ledger=ledger, transaction_name=name_of, max_file=max_file)


class EffectState:
    def __init__(self, blob, ledger, cwd, transaction_name, *, budget=DEFAULT):
        self.budget = admitted(budget)
        self.blob, self.ledger, self.cwd, self.name_of = blob, ledger, cwd, transaction_name
        self.observed, self.descriptors, self.payloads, self.relaxed_dirs = {}, {}, {}, {}
        self.temporaries, self.uncertain = set(), set()
        self.serial = self.total = self.operations = 0

    def mkdir(self, created):
        """Consume only directories proved created by the shared output port."""
        for name, state in created.items():
            if not P(name).is_relative_to(self.ledger): continue
            self.relaxed_dirs[name] = {'identity': state['identity'], 'mode': state['mode'], 'members': []}
        for name in created:
            parent = str(P(name).parent)
            if parent in self.relaxed_dirs:
                self.relaxed_dirs[parent]['members'].append(P(name).name)
            elif parent in self.observed:
                prior = self.observed[parent]
                require(prior['snapshot']['kind'] == 'directory', 'mkdir_parent_kind_changed')
                self.relaxed_dirs[parent] = {**prior['snapshot'], 'members': list(prior['members']) + [P(name).name]}
        for name, value in self.relaxed_dirs.items():
            value['members'] = sorted(set(value['members']))
            self.observed.pop(name, None)

    def files(self, values):
        require(type(values) is dict and len(values) <= 260, 'effect_file_map_changed')
        for name, value in values.items():
            path_spec(name, name, self.cwd)
            require(P(name).is_relative_to(self.ledger), 'effect_file_scope_changed')
            observed(value, self.blob, name, self.ledger, self.name_of, max_file=self.budget.file)

    def resource_rows(self, rows):
        require(type(rows) is list and len(rows) <= 128, 'resource_rows_changed')
        result = {}
        for row in rows:
            require(type(row) is dict and set(row) == {'descriptor', 'path', 'role', 'identity', 'mode', 'stream', 'nlink'}, 'resource_row_changed')
            token = row['descriptor']
            require(type(token) is int and token > 0 and token not in result
                    and row['role'] in ('temporary', 'directory', 'lock')
                    and type(row['stream']) is bool
                    and type(row['identity']) is list and len(row['identity']) == 2
                    and all(type(n) is int and n >= 0 for n in row['identity'])
                    and type(row['mode']) is int and 0 <= row['mode'] <= 0o777 and not row['mode'] & 0o022
                    and type(row['nlink']) is int and row['nlink'] >= 0,
                    'resource_fields_changed')
            path_spec(row['path'], row['path'], self.cwd)
            require(P(row['path']).is_relative_to(self.ledger), 'resource_scope_changed')
            require(not row['stream'] or row['role'] == 'temporary', 'resource_stream_role_changed')
            require(row['nlink'] == 1 if row['role'] == 'lock' else row['nlink'] in (0, 1) if row['role'] == 'temporary' else row['nlink'] >= 1,
                    'resource_link_count_changed')
            result[token] = row
        require(list(result) == sorted(result), 'resource_order_changed')
        return result

    def bind_resources(self, rows, files):
        for row in rows.values():
            require(row['path'] in files, 'descriptor_path_observation_missing')
            value = files[row['path']]
            if value['snapshot']['kind'] == 'missing':
                require(row['role'] == 'temporary' and row['nlink'] == 0, 'unlinked_descriptor_binding_changed')
            else:
                require(value['snapshot']['kind'] == ('directory' if row['role'] == 'directory' else 'file')
                        and value['snapshot']['identity'] == row['identity']
                        and value['snapshot']['mode'] == row['mode']
                        and value['metadata']['nlink'] == row['nlink'], 'descriptor_path_binding_changed')

    def before(self, frame, action, expected_paths, input_metadata):
        self.operations += 1
        require(self.operations <= 8192, 'effect_operation_budget')
        require(type(frame) is dict and set(frame) == {'kind', 'action', 'files', 'descriptors'}
                and frame['kind'] == 'synthetic-ledger-effect-before' and frame['action'] == action,
                'effect_before_changed')
        self.files(frame['files'])
        require(set(frame['files']) == set(expected_paths), 'effect_before_selection_changed')
        require(self.resource_rows(frame['descriptors']) == self.descriptors, 'descriptor_preimage_changed')
        self.bind_resources(self.descriptors, frame['files'])
        for name, value in frame['files'].items():
            if name in self.observed: require(self.observed[name] == value, 'effect_preimage_changed')
            if name in self.relaxed_dirs:
                expected = self.relaxed_dirs.pop(name)
                require(value['snapshot']['kind'] == 'directory'
                        and all(value['snapshot'][k] == expected[k] for k in ('mode', 'identity'))
                        and value['members'] == expected['members'], 'owned_mkdir_effect_changed')
            if name in input_metadata:
                require((value['metadata'] or {'kind': 'missing'}) == input_metadata[name], 'input_effect_preimage_changed')
        return frame['files']

    def identity(self, a, z, *, links=False):
        require(a['snapshot']['kind'] == z['snapshot']['kind']
                and all(a['snapshot'][k] == z['snapshot'][k] for k in ('identity', 'mode'))
                and a['metadata']['uid'] == z['metadata']['uid']
                and (links or a['metadata']['nlink'] == z['metadata']['nlink']), 'effect_inode_changed')

    def allocate(self, rows, token, path, role, value):
        require(type(token) is int and token == self.serial + 1, 'new_descriptor_token_changed')
        self.serial = token
        state, info = value['snapshot'], value['metadata']
        require(state['kind'] == ('directory' if role == 'directory' else 'file'), 'new_descriptor_kind_changed')
        rows[token] = {'descriptor': token, 'path': path, 'role': role, 'identity': state['identity'],
                       'mode': state['mode'], 'stream': False, 'nlink': info['nlink']}
        if role == 'temporary': self.payloads[token] = b''

    def finish(self, before, after, action, args, ok, value):
        require(type(after) is dict and set(after) == {'kind', 'action', 'files', 'descriptors', 'failure', 'attempts'}
                and after['kind'] == 'synthetic-ledger-effect-after' and after['action'] == action,
                'effect_after_changed')
        self.files(after['files'])
        z = after['files']; rows = deepcopy(self.descriptors)
        actual_rows = self.resource_rows(after['descriptors'])
        require(type(after['attempts']) is list and (action == 'mkstemp' or not after['attempts']), 'temporary_attempts_changed')
        require(after['failure'] is None if ok else after['failure'] is not None, 'effect_failure_claim_changed')
        mutable = set()
        token = args.get('descriptor')
        row = rows.get(token)
        if action == 'open':
            name, flags = args['path'], args['flags']
            role = 'lock' if name == str(P(self.ledger) / '.append.lock') and flags == 7 else 'directory'
            require(role == 'lock' or name == str(P(self.ledger) / 'transactions') and flags == 8, 'open_selection_changed')
            if before[name]['snapshot']['kind'] == 'missing' and z[name]['snapshot']['kind'] == 'file':
                require(role == 'lock' and self.blob(z[name]['snapshot']['content']) == b''
                        and z[name]['metadata']['nlink'] == 1 and not z[name]['snapshot']['mode'] & ~args['mode'], 'new_lock_file_changed')
                mutable.add(name)
            if ok: self.allocate(rows, value, name, role, z[name])
        elif action == 'mkstemp':
            directory = args['directory']; attempts = after['attempts']
            require(args['prefix'] == '.pending-' and directory == str(P(self.ledger) / 'transactions')
                    and 1 <= len(attempts) <= 128
                    and all(type(n) is str and str(P(n).parent) == directory and P(n).name.startswith('.pending-')
                            and str(P(n)) == n for n in attempts), 'temporary_attempt_selection_changed')
            require(set(z) == set(before) | set(attempts), 'temporary_after_paths_changed')
            initial = set(before[directory]['members'])
            require(all(P(n).name in initial for n in attempts[:-1]), 'temporary_collision_claim_changed')
            name = attempts[-1]
            if P(name).name not in initial and z[name]['snapshot']['kind'] != 'missing':
                require(z[name]['snapshot']['kind'] == 'file' and z[name]['snapshot']['mode'] == 0o600
                        and z[name]['metadata']['nlink'] == 1 and self.blob(z[name]['snapshot']['content']) == b'', 'temporary_creation_changed')
                mutable.add(name)
            if ok:
                require(type(value) is dict and set(value) == {'descriptor', 'temporary'} and value['temporary'] == name
                        and name in mutable, 'temporary_return_changed')
                self.allocate(rows, value['descriptor'], name, 'temporary', z[name])
                self.temporaries.add(name)
        elif action in ('fdopen', 'stream-enter', 'stream-write', 'stream-flush', 'stream-exit', 'fsync', 'flock', 'close'):
            require(type(token) is int and row is not None, 'effect_descriptor_changed')
            name = row['path']
            require(name in before and name in z, 'descriptor_file_observation_missing')
            if action == 'fdopen':
                require(row['role'] == 'temporary' and not row['stream'] and args['mode'] == 'wb', 'fdopen_contract_changed')
                if ok: row['stream'] = True
            elif action.startswith('stream-'):
                require(row['role'] == 'temporary' and row['stream'], 'stream_resource_changed')
                if action == 'stream-write':
                    raw = self.blob(args['payload']); self.total += len(raw)
                    require(len(raw) <= self.budget.file and self.total <= self.budget.total, 'stream_payload_budget')
                    if ok: require(type(value) is int and 0 <= value <= len(raw), 'stream_write_return_changed')
                    self.payloads[token] += raw[:value] if ok else raw
                    if not ok: self.uncertain.add(token)
                if action in ('stream-write', 'stream-flush', 'stream-exit'):
                    self.identity(before[name], z[name]); old = self.blob(before[name]['snapshot']['content']); new = self.blob(z[name]['snapshot']['content'])
                    require(new.startswith(old) and self.payloads[token].startswith(new), 'buffered_file_prefix_changed')
                    if ok and action in ('stream-flush', 'stream-exit') and token not in self.uncertain:
                        require(new == self.payloads[token], 'buffered_flush_content_changed')
                    mutable.add(name)
                if action == 'stream-exit' and (ok or token not in actual_rows): rows.pop(token)
            elif action == 'flock':
                require(row['role'] == 'lock' and args['operation'] in (1, 2), 'lock_resource_changed')
            elif action == 'close':
                require(not row['stream'], 'stream_close_ownership_changed')
                if ok or token not in actual_rows: rows.pop(token)
            if ok and action != 'stream-write': require(value is None or action == 'stream-exit' and value is False, 'effect_null_return_changed')
        elif action == 'link':
            source, target = args['source'], args['target']
            require(source in self.temporaries and P(target).parent == P(self.ledger) / 'transactions', 'publication_selection_changed')
            if ok:
                require(before[target]['snapshot']['kind'] == 'missing' and z[source] == z[target]
                        and z[source]['metadata']['nlink'] == 2, 'publication_link_changed')
                self.identity(before[source], z[source], links=True)
                require(before[source]['snapshot']['content'] == z[source]['snapshot']['content'], 'publication_payload_changed')
                mutable.update((source, target))
                require(value is None, 'link_return_changed')
        elif action == 'unlink':
            name = args['path']; require(name in self.temporaries, 'cleanup_selection_changed')
            if ok:
                require(z[name] == {'snapshot': {'kind': 'missing'}, 'metadata': None, 'aliases': []}, 'cleanup_missing_state_changed')
                mutable.add(name)
                for alias in before[name]['aliases']:
                    if alias == name: continue
                    require(alias in z and z[alias]['snapshot'] == before[alias]['snapshot']
                            and z[alias]['metadata']['nlink'] == 1 and not z[alias]['aliases']
                            and all(z[alias]['metadata'][k] == before[alias]['metadata'][k] for k in ('uid', 'mtime_ns')), 'cleanup_alias_changed')
                    mutable.add(alias)
                for key, resource in rows.items():
                    if resource['path'] == name: resource['nlink'] = 0
                require(value is None, 'unlink_return_changed')
        else: require(False, 'unknown_store_effect')
        if action != 'mkstemp': require(set(z) == set(before), 'effect_after_paths_changed')
        # All directory member deltas must be explained by captured child
        # creation/removal. File content writes do not create new names.
        for name, old in before.items():
            new = z[name]
            if old['snapshot']['kind'] == 'directory':
                # APFS can change a directory's link count for ordinary file
                # entries; ext4 typically counts subdirectories. Bind the raw
                # observation to members, without imposing either host model.
                self.identity(old, new, links=True)
                members = set(old['members'])
                for child in mutable:
                    if str(P(child).parent) != name: continue
                    prior_kind = before.get(child, {'snapshot': {'kind': 'missing'}})['snapshot']['kind']
                    if z[child]['snapshot']['kind'] == 'missing': members.discard(P(child).name)
                    elif prior_kind == 'missing': members.add(P(child).name)
                require(set(new['members']) == members, 'namespace_delta_changed')
                if members == set(old['members']): require(new == old, 'unchanged_directory_metadata_changed')
                mutable.add(name)
            if name not in mutable: require(new == old, 'unowned_effect_change')
        require(actual_rows == rows, 'descriptor_transition_changed')
        self.bind_resources(rows, z)
        self.descriptors = rows
        self.observed.update(z)
