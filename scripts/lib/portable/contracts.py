"""Portable v1 contracts. No provider environment or network access."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
VERSION = '1.0.0'
SCHEMAS = ROOT / 'schemas'
UNKNOWN = {'', 'unknown', 'null', 'none', 'undefined'}


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def valid_id(value):
    return isinstance(value, str) and value.strip().lower() not in UNKNOWN and not any(ord(c) < 32 for c in value)


def endpoint(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('Expected an HTTPS instance origin without credentials, path, query or fragment')
    host = parsed.hostname.encode('idna').decode('ascii').lower()
    host = '[' + host + ']' if ':' in host else host
    port = parsed.port
    return 'https://' + host + (':' + str(port) if port and port != 443 else '')


def validate(kind, value):
    schema = json.loads((SCHEMAS / f'portable-{kind}-v1.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    ctx = value.get('context') if kind == 'result' else value if kind == 'context' else None
    reference = ctx['ci']['native_reference'] if ctx else None
    if reference and '://' in reference:
        native = urlsplit(reference)
        if native.username or native.password or native.query or native.fragment:
            raise ValueError('unsafe_native_reference')
    return value


def repository_key(identity):
    """Native IDs are opaque. Display paths never define a global identity."""
    if not valid_id(identity.get('provider')) or not valid_id(identity.get('native_id')):
        raise ValueError('Missing provider or native repository identity')
    return canonical_digest({'provider': identity['provider'], 'instance': endpoint(identity['instance']),
                             'native_id': identity['native_id']})


def execution_key(context):
    validate('context', context)
    ci = context['ci']
    if not all(valid_id(ci.get(name)) for name in ('provider', 'run_id', 'job_id')):
        raise ValueError('Incomplete CI identity')
    return canonical_digest({'repository': repository_key(context['scm']), 'domain':context['governance']['domain'],
                             'scope':context['governance']['scope'], 'provider': ci['provider'],
                             'instance': endpoint(ci['instance']), 'run_id': ci['run_id'],
                             'job_id': ci['job_id'], 'attempt': ci['attempt']})


def context_errors(context):
    validate('context', context)
    errors = []
    for area, names in {'scm': ('provider', 'native_id', 'path', 'url'),
                        'ci': ('provider', 'run_id', 'job_id'),
                        'revision': ('tested', 'source', 'branch')}.items():
        for name in names:
            if not valid_id(context[area].get(name)):
                errors.append(f'missing_context:{area}.{name}')
    for name in ('scm', 'ci'):
        try:
            endpoint(context[name]['instance'])
        except ValueError:
            errors.append(f'invalid_context:{name}.instance')
    import re
    for name in ('tested', 'source'):
        if not isinstance(context['revision'].get(name), str) or not re.fullmatch('[a-fA-F0-9]{40}|[a-fA-F0-9]{64}', context['revision'][name]):
            errors.append('invalid_context:revision.' + name)
    if context['ci']['event'] == 'unknown':
        errors.append('missing_context:ci.event')
    if type(context['ci'].get('attempt')) is not int or context['ci']['attempt'] < 1:
        errors.append('missing_context:ci.attempt')
    if context['revision']['mode'] in ('source-head', 'merge-result'):
        change = context.get('change_request')
        if not change or not valid_id(change.get('id')) or not valid_id(change.get('target_branch')):
            errors.append('missing_context:change_request')
        if context['revision']['mode'] == 'merge-result' and (not valid_id(context['revision'].get('target')) or not re.fullmatch('[a-fA-F0-9]{40}|[a-fA-F0-9]{64}', context['revision']['target'])):
            errors.append('missing_context:revision.target')
    if context['revision']['mode'] == 'source-head' and context['revision']['tested'] != context['revision']['source']:
        errors.append('revision_mismatch:source_head')
    return errors


def diagnostic_context(context):
    """Return safe canonical context; unknown native fields are never fabricated."""
    return deepcopy(context)
