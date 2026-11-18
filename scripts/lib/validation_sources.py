"""Committed product self-validation data; no executable caller source."""
import hashlib
import json
from pathlib import PurePosixPath

import yaml

from lib.functional_parity import git_read
from lib.portable.contracts import canonical_digest
from lib.validation_files import MAX_FILES, ValidationFiles, relative

SCOPES = ('architecture', 'schemas', 'policies', 'generated/demo')
WORKTREE_SCOPE = 'working-tree-product-runtime-validation-v1'


def working_refs(files):
    """Original policy-rule exists() operands, never executable source bytes."""
    refs = set()
    for name, raw in files.items():
        path = PurePosixPath(name)
        if path.parent.as_posix() != 'architecture' or not path.match('arch-*.yaml'):
            continue
        # Bound composition before SafeLoader construction. Malformed original
        # values are left for the original validator's own failure semantics.
        depth = aliases = count = 0
        try:
            for event in yaml.parse(raw):
                count += 1
                if isinstance(event, yaml.events.CollectionStartEvent): depth += 1
                if isinstance(event, yaml.events.CollectionEndEvent): depth -= 1
                if isinstance(event, yaml.events.AliasEvent): aliases += 1
                if count > 100000 or depth > 100 or aliases > 1000:
                    raise ValueError('validation_worktree_yaml_budget')
            value = yaml.safe_load(raw)
        except (yaml.YAMLError, UnicodeError, RecursionError):
            continue
        if not isinstance(value, dict) or not isinstance(value.get('requirements'), list):
            continue
        if len(value['requirements']) > MAX_FILES:
            raise ValueError('validation_worktree_requirement_budget')
        for item in value['requirements']:
            if not isinstance(item, dict) or not isinstance(item.get('policy_as_code'), dict): continue
            rule = item['policy_as_code'].get('rule')
            if item['policy_as_code'].get('candidate') and isinstance(rule, str) and rule:
                relative(rule)
                if len(rule) > 4096: raise ValueError('validation_worktree_reference_budget')
                refs.add(rule)
        if len(refs) > MAX_FILES: raise ValueError('validation_worktree_reference_budget')
    return refs


def offline_working_schemas(files):
    """Bound schema composition; actual reference access uses an offline Registry.

    Do not reject unused schemas merely because they contain external references:
    the original validator never evaluates those schemas. The execution registry
    rejects retrieval only if a validated schema actually requests it.
    """
    for name, raw in files.items():
        if not name.startswith('schemas/') or not name.endswith('.json'): continue
        try: value = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError): continue
        pending = [(value, 0)]; count = 0
        while pending:
            item, depth = pending.pop(); count += 1
            if count > 100000 or depth > 100: raise ValueError('validation_worktree_schema_budget')
            if isinstance(item, dict):
                pending.extend((v, depth + 1) for v in item.values())
            elif isinstance(item, list): pending.extend((v, depth + 1) for v in item)


def working_manifest(files, membership, *, revision, tree, source):
    ValidationFiles(files, membership)
    value = {'schema_version': 1, 'scope': WORKTREE_SCOPE, 'commit': revision, 'tree': tree,
        'source_root': str(source), 'membership': sorted(membership),
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                  for name, raw in files.items()}}
    if len(json.dumps(value).encode()) > 4 * 1024**2: raise ValueError('validation_manifest_byte_budget')
    return value


def check_working_manifest(value, files, *, revision, tree):
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'scope', 'commit', 'tree', 'source_root', 'membership', 'files'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['scope'] != WORKTREE_SCOPE or value['commit'] != revision or value['tree'] != tree
            or not isinstance(value['membership'], list) or not all(isinstance(v, str) for v in value['membership'])
            or len(value['membership']) > MAX_FILES or value['membership'] != sorted(set(value['membership']))):
        raise ValueError('invalid_validation_worktree_manifest')
    ValidationFiles(files, value['membership'], label=value['source_root'])
    if any(not any(name.startswith(scope + '/') for scope in SCOPES) for name in files):
        raise ValueError('validation_worktree_input_scope_changed')
    if not set(value['membership']) <= set(files) | working_refs(files):
        raise ValueError('validation_worktree_membership_changed')
    offline_working_schemas(files)
    if working_manifest(files, value['membership'], revision=revision, tree=tree, source=value['source_root']) != value:
        raise ValueError('validation_worktree_manifest_changed')


def capture(source, revision):
    from lib import report_sources
    inventory = report_sources.inventory(source, revision)
    data = {}
    total = 0
    for name, meta in inventory['membership'].items():
        if not any(name == scope or name.startswith(scope + '/') for scope in SCOPES):
            continue
        total += meta['bytes']
        if meta['bytes'] > report_sources.MAX_FILE or total > report_sources.MAX_TOTAL:
            raise ValueError('validation_input_byte_budget')
        raw = git_read(source, 'cat-file', 'blob', meta['git_blob'])
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False).hexdigest()
        if len(raw) != meta['bytes'] or blob != meta['git_blob']:
            raise ValueError('validation_committed_input_changed')
        data[name] = raw
    # Code membership is retained only for original exists() decisions. No
    # Python, shell, or inspected application program is read into this view.
    manifest = {'schema_version': 1, 'scope': 'committed-product-runtime-validation-v1',
        'commit': revision, 'tree': inventory['tree'], 'membership': sorted(inventory['membership']),
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                  for name, raw in data.items()}}
    ValidationFiles(data, manifest['membership'])
    return data, manifest


def digest(manifest):
    return canonical_digest(manifest)
