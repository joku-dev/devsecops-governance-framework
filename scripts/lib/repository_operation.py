"""Versioned private repository operation bindings; no acceptance or authority."""
from pathlib import PurePosixPath
import re

from lib.repository_capture import PROFILES
from lib.result_snapshot_store import explicit_time

AUTHORITY = {'mode': 'report-only', 'official_acceptance': False, 'production_approval': False,
    'risk_acceptance': False, 'authority_transferred': False, 'operating_acceptance_inherited': False,
    'published': False, 'independent_execution_attested': False}
FIELDS = {'schema_version', 'kind', 'operation_id', 'node_id', 'runtime_source_digest',
    'source_revision', 'source_tree', 'profile', 'engine_profile', 'source_root', 'assessed_at', *AUTHORITY}


def binding(value):
    if (type(value) is not dict or set(value) != FIELDS
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'product-repository-validation'
            or any(type(value[key]) is not type(expected) or value[key] != expected
                   for key, expected in AUTHORITY.items())):
        raise ValueError('repository_operation_binding_or_authority_changed')
    for key, size in (('operation_id', 64), ('node_id', 32), ('runtime_source_digest', 64)):
        if type(value[key]) is not str or re.fullmatch('[a-f0-9]{' + str(size) + '}', value[key]) is None:
            raise ValueError('repository_operation_identity_required')
    revision, tree = value['source_revision'], value['source_tree']
    if (type(revision) is not str or re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', revision) is None
            or type(tree) is not str or re.fullmatch('[a-f0-9]{' + str(len(revision)) + '}', tree) is None
            or value['profile'] not in PROFILES):
        raise ValueError('repository_operation_exact_source_required')
    root = value['source_root']
    if (type(root) is not str or not PurePosixPath(root).is_absolute()
            or str(PurePosixPath(root)) != root or '..' in PurePosixPath(root).parts
            or '\\' in root or len(root) > 8192 or any(ord(c) < 32 for c in root)):
        raise ValueError('repository_operation_display_root_required')
    if type(value['assessed_at']) is not str:
        raise ValueError('repository_operation_time_required')
    explicit_time(value['assessed_at'])
    if type(value['engine_profile']) is not str or re.fullmatch('[a-z][a-z0-9-]{0,95}', value['engine_profile']) is None:
        raise ValueError('repository_operation_engine_profile_required')
    return value


def outcome(value):
    if (type(value) is not dict
            or set(value) != {'execution', 'exception_type', 'exit_code', 'stdout', 'stderr'}
            or type(value['exit_code']) is not int
            or any(type(value[name]) is not str or len(value[name].encode('utf-8')) > 1024**2
                   for name in ('stdout', 'stderr'))):
        raise ValueError('repository_operation_outcome_required')
    if value['execution'] == 'complete':
        if value['exit_code'] not in (0, 1) or value['exception_type'] is not None:
            raise ValueError('repository_operation_complete_outcome_differs')
    elif value['execution'] == 'incomplete':
        if (value['exit_code'] != 2 or type(value['exception_type']) is not str
                or re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,127}', value['exception_type']) is None):
            raise ValueError('repository_operation_incomplete_outcome_differs')
    else:
        raise ValueError('repository_operation_execution_required')
    return value
