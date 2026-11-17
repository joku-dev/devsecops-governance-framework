"""Bounded local Git and regular-file observations; never execute target programs."""
import hashlib
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
from lib.review_planning import canonical_paths, contracts, PROTOCOL, ROUTING

MAX_FILE = 16 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_FACTS = 8 * 1024**2
OBJECT_ID = r'(?:[a-f0-9]{40}|[a-f0-9]{64})'


def git(root, *arguments, limit=MAX_FACTS, timeout=30):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null', GIT_CONFIG_NOSYSTEM='1',
        GIT_CONFIG_COUNT='0', GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false', GIT_NO_REPLACE_OBJECTS='1',
        GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_OPTIONAL_LOCKS='0', GIT_ATTR_NOSYSTEM='1')
    args = ['git', '--no-optional-locks', '--literal-pathspecs', '-c', 'safe.directory=' + str(root),
        '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c', 'core.attributesFile=/dev/null',
        '-c', 'protocol.allow=never', *arguments]
    with subprocess.Popen(args, cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True) as process:
        output = bytearray(); errors = 0; deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, 'out'); selector.register(process.stderr, selectors.EVENT_READ, 'err')
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0: raise ValueError('review_git_timeout')
                    for key, _ in selector.select(min(remaining, 0.2)):
                        raw = os.read(key.fileobj.fileno(), 65536)
                        if not raw: selector.unregister(key.fileobj); continue
                        if key.data == 'out': output.extend(raw)
                        else: errors += len(raw)
                        if len(output) > limit or errors > 65536: raise ValueError('review_git_output_budget')
            try: returncode = process.wait(timeout=max(0.001, deadline-time.monotonic()))
            except subprocess.TimeoutExpired: raise ValueError('review_git_timeout') from None
            if returncode: raise ValueError('review_local_git_read_failed')
        except BaseException:
            try:
                if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
            except PermissionError:
                try: process.kill()
                except ProcessLookupError: pass
            except ProcessLookupError: pass
            process.wait()
            raise
    return bytes(output)


def directory(root, name):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in filter(None, name.split('/')):
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = following
        return fd
    except BaseException:
        os.close(fd); raise


def regular_file(root, name):
    canonical_paths([name])
    if any(p.casefold() == '.git' for p in name.split('/')): raise ValueError('review_git_metadata_input_forbidden')
    parts = name.rstrip('/').split('/')
    try:
        parent = directory(root, '/'.join(parts[:-1])) if len(parts) > 1 else directory(root, '')
    except FileNotFoundError: return None, None
    try:
        try: fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError: return None, None
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            os.close(fd); raise ValueError('review_regular_file_required')
        with os.fdopen(fd, 'rb') as stream:
            if before.st_size > MAX_FILE: raise ValueError('review_source_file_budget')
            raw = stream.read(MAX_FILE + 1); after = os.fstat(stream.fileno())
            if len(raw) > MAX_FILE: raise ValueError('review_source_file_budget')
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')
            if any(getattr(before, k) != getattr(after, k) for k in fields): raise ValueError('review_source_changed_during_read')
            return raw, before.st_mode & 0o777
    finally: os.close(parent)


def observe(repository, base_commit, paths, profile):
    root = Path(repository).resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root: raise ValueError('review_repository_root_required')
    head = git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    if not re.fullmatch(OBJECT_ID, head): raise ValueError('review_exact_commit_required')
    object_pattern = '[a-f0-9]{' + str(len(head)) + '}'
    merge = None
    if base_commit is not None:
        if not isinstance(base_commit, str) or not re.fullmatch(object_pattern, base_commit): raise ValueError('review_exact_base_commit_required')
        if git(root, 'rev-parse', '--verify', '--end-of-options', base_commit+'^{commit}').decode().strip() != base_commit: raise ValueError('review_exact_base_commit_required')
        merge = git(root, 'merge-base', base_commit, head).decode().strip()
    changed = set()
    commands = [('diff', '--name-only', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-relative', '-z', '--cached'),
                ('diff', '--name-only', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-relative', '-z'),
                ('ls-files', '--others', '--exclude-standard', '-z')]
    if merge: commands.append(('diff', '--name-only', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-relative', '-z', merge, head))
    for command in commands: changed.update(p.decode('utf-8') for p in git(root, *command).split(b'\0') if p)
    all_changed = canonical_paths(sorted(changed)); selected = canonical_paths(sorted(set(paths))) if paths else all_changed
    try:
        fd = directory(root, '.agents/roles')
        try: role_names = os.listdir(fd)
        finally: os.close(fd)
    except FileNotFoundError: raise ValueError('review_target_role_contracts_required') from None
    if len(role_names) > 1000: raise ValueError('review_role_directory_budget')
    role_paths = sorted('.agents/roles/' + n for n in role_names if n.endswith('.yaml'))
    canonical_paths(role_paths)
    if not role_paths: raise ValueError('review_target_role_contracts_required')
    names = set(selected) | set(profile['common_contracts']) | set(profile['optional_contracts']) | set(role_paths)
    files = {}; raw_files = {}; total = 0
    def read(name):
        nonlocal total
        raw, mode = regular_file(root, name)
        files[name] = None if raw is None else {'mode': mode, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if raw is not None:
            raw_files[name] = raw; total += len(raw)
            if total > MAX_TOTAL: raise ValueError('review_source_total_budget')
    for name in sorted(names): read(name)
    from lib.review_planning import yaml_object
    for name in role_paths:
        if name not in raw_files: raise ValueError('review_target_role_contracts_required')
        role = yaml_object(raw_files[name]); skill = role.get('skill')
        if not isinstance(skill, str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', skill): raise ValueError('invalid_review_skill')
        for extra in ('.agents/skills/' + skill + '/SKILL.md', profile['optional_role_contract'].format(role=Path(name).stem)):
            if extra not in files: read(extra)
    contracts(raw_files)
    index = {name: [] for name in selected}
    for entry in filter(None, git(root, 'ls-files', '--stage', '-z').split(b'\0')):
        metadata, name = entry.split(b'\t', 1); text = name.decode('utf-8'); parts = metadata.decode().split()
        if len(parts) != 3 or parts[0] not in ('100644', '100755', '120000', '160000') or not re.fullmatch(object_pattern, parts[1]) or parts[2] not in ('0', '1', '2', '3'): raise ValueError('invalid_review_index_entry')
        if text in index: index[text].append(entry.decode('utf-8'))
    facts = {'schema_version': 1, 'head_commit': head, 'target_commit': base_commit, 'merge_base_commit': merge,
        'selection_mode': 'explicit_paths' if paths else 'working_tree', 'changed_paths': selected,
        'observed_changed_paths': all_changed, 'role_paths': role_paths, 'files': files, 'index_entries': index}
    validate(facts, raw_files, profile)
    return facts, raw_files


def validate(facts, raw_files, profile):
    if set(facts) != {'schema_version', 'head_commit', 'target_commit', 'merge_base_commit', 'selection_mode', 'changed_paths', 'observed_changed_paths', 'role_paths', 'files', 'index_entries'} or type(facts['schema_version']) is not int or facts['schema_version'] != 1:
        raise ValueError('invalid_review_git_facts')
    head = facts['head_commit']
    if not isinstance(head, str) or not re.fullmatch(OBJECT_ID, head): raise ValueError('invalid_review_git_commit')
    object_pattern = '[a-f0-9]{' + str(len(head)) + '}'
    for key in ('head_commit', 'target_commit', 'merge_base_commit'):
        if facts[key] is None and key != 'head_commit': continue
        if not isinstance(facts[key], str) or not re.fullmatch(object_pattern, facts[key]): raise ValueError('invalid_review_git_commit')
    if (facts['target_commit'] is None) != (facts['merge_base_commit'] is None): raise ValueError('invalid_review_git_base')
    for key in ('changed_paths', 'observed_changed_paths', 'role_paths'): canonical_paths(facts[key])
    if facts['selection_mode'] not in ('explicit_paths', 'working_tree') or (facts['selection_mode'] == 'working_tree' and facts['changed_paths'] != facts['observed_changed_paths']): raise ValueError('invalid_review_git_selection')
    if not isinstance(facts['files'], dict) or len(facts['files']) > 11000 or set(raw_files) != {n for n, row in facts['files'].items() if row is not None}: raise ValueError('review_source_members_changed')
    if not isinstance(facts['index_entries'], dict) or not set(facts['changed_paths']) <= facts['files'].keys() or set(facts['index_entries']) != set(facts['changed_paths']): raise ValueError('review_index_members_changed')
    total = 0
    for name, row in facts['files'].items():
        canonical_paths([name])
        if any(p.casefold() == '.git' for p in name.split('/')): raise ValueError('review_git_metadata_input_forbidden')
        if row is None: continue
        if not isinstance(row, dict) or set(row) != {'mode', 'sha256', 'bytes'} or type(row['mode']) is not int or not 0 <= row['mode'] <= 0o777 or type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_FILE:
            raise ValueError('invalid_review_source_metadata')
        raw = raw_files[name]; total += len(raw)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']: raise ValueError('review_source_bytes_changed')
    if total > MAX_TOTAL: raise ValueError('review_source_total_budget')
    roles, _, _ = contracts(raw_files)
    expected = set(facts['changed_paths']) | set(profile['common_contracts']) | set(profile['optional_contracts']) | set(facts['role_paths'])
    if set(facts['role_paths']) != {'.agents/roles/' + role + '.yaml' for role in roles}: raise ValueError('review_role_members_changed')
    for role in roles.values(): expected.update(('.agents/skills/' + role['skill'] + '/SKILL.md', profile['optional_role_contract'].format(role=role['id'])))
    if set(facts['files']) != expected: raise ValueError('review_contract_members_changed')
    for name, entries in facts['index_entries'].items():
        if not isinstance(entries, list) or len(entries) > 3: raise ValueError('invalid_review_index_entry')
        stages = set()
        for entry in entries:
            if not isinstance(entry, str) or '\0' in entry: raise ValueError('invalid_review_index_entry')
            meta, separator, path = entry.partition('\t'); parts = meta.split()
            if not separator or path != name or len(parts) != 3 or parts[0] not in ('100644', '100755', '120000', '160000') or not re.fullmatch(object_pattern, parts[1]) or parts[2] not in ('0', '1', '2', '3') or parts[2] in stages: raise ValueError('invalid_review_index_entry')
            stages.add(parts[2])


def capture(repository, base_commit, paths, profile):
    first = observe(repository, base_commit, paths, profile)
    if observe(repository, base_commit, paths, profile) != first: raise ValueError('review_target_changed_during_capture')
    return first
