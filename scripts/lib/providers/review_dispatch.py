"""Original ordinary dispatch inputs: path names and inert role/routing contracts."""
import hashlib
import json
import os
from pathlib import Path
import re

from lib.review_git import git, directory, regular_file, MAX_TOTAL, MAX_FACTS
from lib.review_metadata import normalize_path
from lib.review_planning import canonical_paths, contracts, yaml_object
from lib.providers.review_planning import review_dispatch_profile


def paths(values):
    if not isinstance(values, list) or len(values) > 10000 or any(not isinstance(v, str) or len(v.encode()) > 4096 for v in values):
        raise ValueError('invalid_dispatch_paths')
    return canonical_paths(sorted({normalize_path(v) for v in values}))


def reference(root, name):
    if not isinstance(name, str) or not name or len(name.encode()) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise ValueError('invalid_dispatch_base_ref')
    value = git(root, 'rev-parse', '--verify', '--end-of-options', name + '^{commit}').decode().strip()
    if not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', value): raise ValueError('invalid_dispatch_git_commit')
    return value


def git_paths(root, base_ref):
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('review_repository_root_required')
    head = reference(root, 'HEAD'); target = reference(root, base_ref) if base_ref is not None else None
    merge = git(root, 'merge-base', target, head).decode().strip() if target else None
    if any(v is not None and not re.fullmatch('[a-f0-9]{' + str(len(head)) + '}', v) for v in (target, merge)):
        raise ValueError('invalid_dispatch_git_commit')
    commands = [('diff', '--name-only', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-relative', '-z', '--cached'),
                ('diff', '--name-only', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-relative', '-z'),
                ('ls-files', '--others', '--exclude-standard', '-z')]
    if merge: commands.append(('diff', '--name-only', '--no-renames', '--no-ext-diff', '--no-textconv', '--no-relative', '-z', merge, head))
    observed = set()
    for command in commands: observed.update(p.decode('utf-8') for p in git(root, *command).split(b'\0') if p)
    return paths(sorted(observed)), {'head_commit': head, 'target_commit': target, 'merge_base_commit': merge}


def validate(facts, raw, profile_name):
    profile = review_dispatch_profile(profile_name)
    if not isinstance(facts, dict) or set(facts) != {'schema_version', 'selection_mode', 'changed_paths', 'git', 'role_paths', 'files'} or type(facts['schema_version']) is not int or facts['schema_version'] != 1:
        raise ValueError('invalid_dispatch_source_facts')
    if facts['changed_paths'] != paths(facts['changed_paths']): raise ValueError('invalid_dispatch_path_order')
    if facts['selection_mode'] == 'explicit_paths':
        if not facts['changed_paths'] or facts['git'] is not None: raise ValueError('invalid_explicit_dispatch_facts')
    elif facts['selection_mode'] == 'working_tree':
        value = facts['git']
        if not isinstance(value, dict) or set(value) != {'head_commit', 'target_commit', 'merge_base_commit'}:
            raise ValueError('invalid_dispatch_git_facts')
        head = value['head_commit']
        if not isinstance(head, str) or not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', head): raise ValueError('invalid_dispatch_git_commit')
        for key in ('target_commit', 'merge_base_commit'):
            if value[key] is not None and (not isinstance(value[key], str) or not re.fullmatch('[a-f0-9]{' + str(len(head)) + '}', value[key])):
                raise ValueError('invalid_dispatch_git_commit')
        if (value['target_commit'] is None) != (value['merge_base_commit'] is None): raise ValueError('invalid_dispatch_git_base')
    else: raise ValueError('invalid_dispatch_selection_mode')
    if not isinstance(raw, dict) or not isinstance(facts['files'], dict) or set(raw) != set(facts['files']) or len(raw) > 401:
        raise ValueError('invalid_dispatch_contract_members')
    total = 0
    for name, item in raw.items():
        row = facts['files'][name]
        if not isinstance(item, bytes) or len(item) > 1024**2: raise ValueError('dispatch_contract_byte_budget')
        total += len(item)
        if total > MAX_TOTAL: raise ValueError('dispatch_contract_total_budget')
        if (not isinstance(row, dict) or set(row) != {'mode', 'bytes', 'sha256'} or type(row['mode']) is not int
                or not 0 <= row['mode'] <= 0o777 or type(row['bytes']) is not int or row['bytes'] != len(item)
                or row['sha256'] != hashlib.sha256(item).hexdigest()): raise ValueError('dispatch_contract_bytes_changed')
    if len((json.dumps(facts, sort_keys=True, indent=2) + '\n').encode()) > MAX_FACTS:
        raise ValueError('dispatch_facts_budget')
    try: roles, routing, _ = contracts(raw, require_protocol=False)
    except (KeyError, TypeError): raise ValueError('invalid_dispatch_contracts') from None
    role_paths = sorted(profile['role_directory'] + '/' + name + '.yaml' for name in roles)
    if facts['role_paths'] != role_paths: raise ValueError('dispatch_role_members_changed')
    expected = set(profile['common_contracts']) | set(role_paths)
    expected.update(profile['skill_template'].format(skill=role['skill']) for role in roles.values())
    if set(raw) != expected: raise ValueError('dispatch_contract_members_changed')
    return roles, routing


def observe(repository, base_ref, explicit_paths, profile_name):
    profile = review_dispatch_profile(profile_name)
    root = Path(repository).expanduser().absolute()
    if any(p.is_symlink() for p in (root, *root.parents)): raise ValueError('dispatch_root_symlink_forbidden')
    root = root.resolve(); selected = paths(explicit_paths)
    if selected: source = None  # Original explicit paths do not consult Git/base-ref.
    else: selected, source = git_paths(root, base_ref)
    try: fd = directory(root, profile['role_directory'])
    except OSError: raise ValueError('dispatch_role_directory_unavailable') from None
    try: names = os.listdir(fd)
    finally: os.close(fd)
    if len(names) > 1000: raise ValueError('review_role_directory_budget')
    role_paths = sorted(profile['role_directory'] + '/' + name for name in names if name.endswith('.yaml'))
    if not role_paths or len(role_paths) > 200: raise ValueError('review_target_role_contracts_required')
    raw = {}; files = {}; total = 0
    def read(name):
        nonlocal total
        try: item, mode = regular_file(root, name)
        except OSError: raise ValueError('dispatch_contract_read_failed') from None
        if item is None: raise ValueError('dispatch_contract_required')
        if len(item) > 1024**2: raise ValueError('dispatch_contract_byte_budget')
        total += len(item)
        if total > MAX_TOTAL: raise ValueError('dispatch_contract_total_budget')
        raw[name] = item; files[name] = {'mode': mode, 'bytes': len(item), 'sha256': hashlib.sha256(item).hexdigest()}
    for name in sorted(set(profile['common_contracts']) | set(role_paths)): read(name)
    for name in role_paths:
        value = yaml_object(raw[name]); skill = value.get('skill')
        if not isinstance(skill, str) or not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', skill): raise ValueError('invalid_review_skill')
        name = profile['skill_template'].format(skill=skill)
        if name not in raw: read(name)
    facts = {'schema_version': 1, 'selection_mode': 'explicit_paths' if source is None else 'working_tree',
             'changed_paths': selected, 'git': source, 'role_paths': role_paths, 'files': files}
    validate(facts, raw, profile_name)
    return facts, raw


def capture(repository, base_ref, explicit_paths, profile_name):
    first = observe(repository, base_ref, explicit_paths, profile_name)
    if observe(repository, base_ref, explicit_paths, profile_name) != first:
        raise ValueError('dispatch_target_changed_during_capture')
    return first
