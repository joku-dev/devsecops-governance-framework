"""Explicit bounded legacy local-file inputs; no implicit authority or code execution."""
import hashlib
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import secrets
import stat
import unicodedata

from lib import review_dispatch as logic
from lib.review_git import directory

PROFILES = ('legacy-local-dispatch-files-v1',)
OBSERVATION_KEYS = {'path', 'observed', 'present', 'sha256', 'bytes', 'mode'}


def profile(name):
    if name not in PROFILES: raise ValueError('unsupported_dispatch_file_profile')
    return {'kind': 'legacy-local-dispatch-files-v1', 'profile': name,
            'local_files_only': True, 'provider_invoked': False}


def canonical(path):
    value = Path(os.path.abspath(str(path)))
    logic.text(str(value))
    return value


def resolve(root, label):
    logic.text(label); path = Path(label)
    return canonical(path if path.is_absolute() else root / path)


def legacy_label(repository, label):
    """Preserve V1's lexical repo_relative label, including explicit '..'."""
    root = canonical(repository); logic.text(label); path = Path(label)
    if not path.is_absolute(): path = root / path
    try: return path.relative_to(root).as_posix()
    except ValueError: return path.as_posix()


def guard(path, forbidden_roots, *, writing=False):
    path = canonical(path)
    if path == Path(path.anchor): raise ValueError('dispatch_native_file_required')
    if any(part.casefold() == '.git' for part in path.parts): raise ValueError('dispatch_git_metadata_file_forbidden')
    if writing and any(path.is_relative_to(canonical(root)) for root in forbidden_roots):
        raise ValueError('dispatch_protected_file_target')
    return path


def observation(path, raw=None, mode=None, *, observed=True):
    return {'path': str(path), 'observed': observed, 'present': raw is not None if observed else None,
            'sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None,
            'bytes': len(raw) if raw is not None else None, 'mode': mode}


def read(path, limit):
    """Open every ancestor through directory descriptors without following links."""
    path = guard(path, ()); parts = path.parts[1:]
    try: parent = directory(Path('/'), '/'.join(parts[:-1]))
    except FileNotFoundError: return observation(path), None, None
    except OSError: raise ValueError('dispatch_native_file_read_failed') from None
    try:
        try: descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError: return observation(path), None, None
        except OSError: raise ValueError('dispatch_native_file_read_failed') from None
    finally: os.close(parent)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit: raise ValueError('dispatch_native_file_budget_or_type')
        raw = stream.read(limit + 1); after = os.fstat(stream.fileno())
        if len(raw) > limit: raise ValueError('dispatch_native_file_budget_or_type')
        if any(getattr(before, key) != getattr(after, key) for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')):
            raise ValueError('dispatch_native_file_changed_during_read')
        return observation(path, raw, stat.S_IMODE(before.st_mode) & 0o777), raw, (before.st_dev, before.st_ino)


def observations(request, before_state):
    action = request['action']; recording = False; label = request['usage_log']
    if action == 'dispatch':
        state = logic.state(before_state); recording = logic.active(state)
        if recording: label = state.get('usage_log', logic.DEFAULT_LOG)
    state_read = action != 'usage-summary'
    log_read = action == 'usage-summary' or (action == 'dispatch' and (recording or request['log_usage'] or request['provider_review'] is not None))
    state_write = action in ('record-window', 'record-continuous') or (action == 'dispatch' and recording)
    log_write = action == 'dispatch' and log_read
    return state_read, log_read, state_write, log_write, label


def validate(snapshot, request, before_state, before_log, forbidden_roots=()):
    logic.checked_request(request)
    if not isinstance(snapshot, dict) or set(snapshot) != {'schema_version', 'profile', 'repository_path', 'requested_usage_log', 'requested_usage_log_label', 'state', 'log'} or type(snapshot['schema_version']) is not int or snapshot['schema_version'] != 1:
        raise ValueError('invalid_dispatch_file_snapshot')
    profile(snapshot['profile']); root = canonical(snapshot['repository_path'])
    if snapshot['repository_path'] != str(root): raise ValueError('invalid_dispatch_file_repository')
    if snapshot['requested_usage_log_label'] != request['usage_log']: raise ValueError('dispatch_file_label_changed')
    requested = resolve(root, request['usage_log'])
    if snapshot['requested_usage_log'] != str(requested): raise ValueError('dispatch_requested_file_changed')
    state_read, log_read, state_write, log_write, label = observations(request, before_state)
    for key, raw, expected_observation, limit, writing in [('state', before_state, state_read, logic.MAX_STATE, state_write),
            ('log', before_log, log_read, logic.MAX_LOG, log_write)]:
        row = snapshot[key]
        if not isinstance(row, dict) or set(row) != OBSERVATION_KEYS or type(row['observed']) is not bool or row['observed'] != expected_observation:
            raise ValueError('invalid_dispatch_file_observation')
        path = guard(row['path'], forbidden_roots, writing=writing) if expected_observation or writing else canonical(row['path'])
        if row['path'] != str(path): raise ValueError('invalid_dispatch_file_path')
        if row['observed'] is False:
            if raw is not None or any(row[name] is not None for name in ('present', 'sha256', 'bytes', 'mode')):
                raise ValueError('dispatch_unobserved_file_has_data')
        elif type(row['present']) is not bool: raise ValueError('invalid_dispatch_file_presence')
        elif not row['present']:
            if raw is not None or any(row[name] is not None for name in ('sha256', 'bytes', 'mode')):
                raise ValueError('dispatch_missing_file_has_data')
        elif (not isinstance(raw, bytes) or len(raw) > limit or type(row['bytes']) is not int or row['bytes'] != len(raw)
                or row['sha256'] != hashlib.sha256(raw).hexdigest() or type(row['mode']) is not int or not 0 <= row['mode'] <= 0o777):
            raise ValueError('dispatch_native_file_bytes_changed')
    selected = resolve(root, label)
    if snapshot['log']['path'] != str(selected): raise ValueError('dispatch_selected_file_changed')
    if log_write and not selected.is_relative_to(root) and selected != requested:
        raise ValueError('dispatch_recording_log_outside_declared_scope')
    if (state_write or log_write) and snapshot['state']['path'].casefold() == snapshot['log']['path'].casefold():
        raise ValueError('dispatch_native_state_log_alias')
    return {'state_write': state_write, 'log_write': log_write}


def capture(repository, usage_state, request, profile_name, *, forbidden_roots=()):
    profile(profile_name); logic.checked_request(request); root = canonical(repository)
    try: root_descriptor = directory(Path('/'), '/'.join(root.parts[1:]))
    except OSError: raise ValueError('dispatch_file_repository_directory_required') from None
    os.close(root_descriptor)
    state_path = resolve(root, usage_state); requested = resolve(root, request['usage_log'])
    before_state = before_log = state_identity = log_identity = None
    if request['action'] != 'usage-summary':
        guard(state_path, forbidden_roots, writing=request['action'] in ('record-window', 'record-continuous'))
        state, before_state, state_identity = read(state_path, logic.MAX_STATE)
    else: state = observation(state_path, observed=False)
    state_read, log_read, state_write, log_write, label = observations(request, before_state)
    if state_read or state_write: guard(state_path, forbidden_roots, writing=state_write)
    selected = resolve(root, label)
    if log_read or log_write: guard(selected, forbidden_roots, writing=log_write)
    if log_write and not selected.is_relative_to(root) and selected != requested:
        raise ValueError('dispatch_recording_log_outside_declared_scope')
    if log_read: log, before_log, log_identity = read(selected, logic.MAX_LOG)
    else: log = observation(selected, observed=False)
    if state_identity is not None and state_identity == log_identity: raise ValueError('dispatch_native_state_log_alias')
    snapshot = {'schema_version': 1, 'profile': profile_name, 'repository_path': str(root),
        'requested_usage_log': str(requested), 'requested_usage_log_label': request['usage_log'], 'state': state, 'log': log}
    validate(snapshot, request, before_state, before_log, forbidden_roots)
    return snapshot, before_state, before_log


@contextmanager
def locks(paths):
    """Stable per-user locks outside inspected repositories, shared by V2 instances."""
    root = Path('/tmp').resolve() / ('axiom-dispatch-file-locks-' + str(os.geteuid()))
    try: root.mkdir(mode=0o700)
    except FileExistsError: pass
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    descriptors = []
    try:
        info = os.fstat(directory_fd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077: raise ValueError('private_dispatch_file_locks_required')
        names = sorted({hashlib.sha256(unicodedata.normalize('NFC', str(canonical(p))).casefold().encode()).hexdigest() for p in paths})
        for name in names:
            fd = os.open(name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory_fd)
            descriptors.append(fd); info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid()
                    or info.st_nlink != 1 or info.st_size != 0): raise ValueError('private_dispatch_file_lock_required')
            try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('dispatch_native_files_busy') from None
        yield
    finally:
        for fd in descriptors: os.close(fd)
        os.close(directory_fd)


def parent_directory(path):
    """Create only explicitly requested output parents without following links."""
    path = canonical(path); fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            try: os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError: pass
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = following
        return fd
    except BaseException:
        os.close(fd); raise


def replace(path, raw, mode):
    """Replace one regular file atomically; never claim a two-file transaction."""
    path = canonical(path); parent = parent_directory(path); temporary = '.axiom-dispatch-' + secrets.token_hex(16)
    try:
        try: original = os.open(path.name, os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError: pass
        else:
            try:
                if not stat.S_ISREG(os.fstat(original).st_mode): raise ValueError('dispatch_native_regular_file_required')
            finally: os.close(original)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), mode); os.fsync(stream.fileno())
        os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        try: os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError: pass
        os.close(parent)


def prepared_writes(rows, profile_name, forbidden_roots):
    """Check the closed finite write set before acquiring any target lock."""
    profile(profile_name)
    if not isinstance(rows, list) or len(rows) > 2:
        raise ValueError('invalid_dispatch_native_write_set')
    kinds = set(); prepared = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'kind', 'before', 'before_raw', 'after_raw'} or row['kind'] not in ('state', 'log') or row['kind'] in kinds:
            raise ValueError('invalid_dispatch_native_write')
        kinds.add(row['kind']); limit = logic.MAX_STATE if row['kind'] == 'state' else logic.MAX_LOG
        before = row['before']; raw = row['before_raw']; after = row['after_raw']
        if (not isinstance(before, dict) or set(before) != OBSERVATION_KEYS or before['observed'] is not True
                or type(before['present']) is not bool or not isinstance(after, bytes) or len(after) > limit):
            raise ValueError('invalid_dispatch_native_write')
        path = guard(before['path'], forbidden_roots, writing=True)
        if before['path'] != str(path): raise ValueError('invalid_dispatch_native_write_path')
        if before['present']:
            if (not isinstance(raw, bytes) or len(raw) > limit or type(before['bytes']) is not int or before['bytes'] != len(raw)
                    or before['sha256'] != hashlib.sha256(raw).hexdigest() or type(before['mode']) is not int or not 0 <= before['mode'] <= 0o777):
                raise ValueError('dispatch_native_before_bytes_changed')
        elif raw is not None or any(before[key] is not None for key in ('bytes', 'sha256', 'mode')):
            raise ValueError('dispatch_native_missing_write_has_data')
        prepared.append((row, path, limit, before['mode'] if before['present'] else 0o600))
    prepared.sort(key=lambda value: value[0]['kind'] != 'log')
    if len({unicodedata.normalize('NFC', str(path)).casefold() for _, path, _, _ in prepared}) != len(prepared):
        raise ValueError('dispatch_native_state_log_alias')
    return prepared


def write_rows(rows, profile_name, *, forbidden_roots=(), allow_after=False, before_write=None):
    """Apply outputs, or resume only still-matching partial outputs.

    The coordinator persists its recovery record in before_write, under all file
    locks and before the first effect. A new application requires before bytes;
    recovery may also accept bytes that are already exactly the requested after.
    """
    if type(allow_after) is not bool: raise ValueError('invalid_dispatch_native_write_set')
    prepared = prepared_writes(rows, profile_name, forbidden_roots)
    result = {'written': [], 'already_desired': []}
    with locks([path for _, path, _, _ in prepared]):
        decisions = []; identities = set()
        for row, path, limit, mode in prepared:
            current, raw, file_identity = read(path, limit)
            if file_identity is not None:
                if file_identity in identities: raise ValueError('dispatch_native_state_log_alias')
                identities.add(file_identity)
            is_before = current == row['before'] and raw == row['before_raw']
            is_after = current['present'] and raw == row['after_raw'] and current['mode'] == mode
            if allow_after and is_after: decisions.append(False)
            elif is_before: decisions.append(True)
            else: raise ValueError('dispatch_native_file_conflict')
        if before_write is not None: before_write()
        for (row, path, limit, mode), needed in zip(prepared, decisions):
            if needed:
                current, raw, _ = read(path, limit)
                if current != row['before'] or raw != row['before_raw']: raise ValueError('dispatch_native_file_conflict')
                replace(path, row['after_raw'], mode); result['written'].append(row['kind'])
            else: result['already_desired'].append(row['kind'])
        for row, path, limit, mode in prepared:
            current, raw, _ = read(path, limit)
            if not current['present'] or raw != row['after_raw'] or current['mode'] != mode:
                raise ValueError('dispatch_native_output_verification_failed')
    return result


def verify_outputs(rows, profile_name, *, forbidden_roots=()):
    """A completed operation may verify outputs, never reapply rolled-back data."""
    prepared = prepared_writes(rows, profile_name, forbidden_roots)
    with locks([path for _, path, _, _ in prepared]):
        identities = set()
        for row, path, limit, mode in prepared:
            current, raw, file_identity = read(path, limit)
            if file_identity is not None:
                if file_identity in identities: raise ValueError('dispatch_native_state_log_alias')
                identities.add(file_identity)
            if not current['present'] or raw != row['after_raw'] or current['mode'] != mode:
                raise ValueError('dispatch_native_output_verification_failed')
    return {'verified': [row['kind'] for row, _, _, _ in prepared]}
