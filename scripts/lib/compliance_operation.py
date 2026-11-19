"""Closed source/node/package bindings for the complete compliance operation."""
from copy import deepcopy
from datetime import timezone
from pathlib import PurePosixPath
import re

from lib.repository_operation import AUTHORITY
from lib.result_snapshot_store import explicit_time

PROFILE = 'legacy-extended-compliance-v1'
FIELDS = {'schema_version', 'kind', 'operation_id', 'node_id', 'runtime_source_digest',
    'source_revision', 'source_tree', 'product_source_root', 'instance_root',
    'package_sha256', 'assessed_at', 'engine_profile', *AUTHORITY}
OPTION_FIELDS = {'cwd', 'output_file', 'target_repo', 'input_file', 'skip_unit_tests', 'fail_on_findings'}


def legacy_timestamp(value):
    """The original main renders the supplied instant as UTC whole seconds."""
    return explicit_time(value).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def path_label(value, *, absolute=False):
    if (type(value) is not str or not value or len(value.encode()) > 8192
            or '\x00' in value):
        raise ValueError('compliance_path_label_required')
    if absolute:
        path = PurePosixPath(value)
        if not path.is_absolute() or str(path) != value or '..' in path.parts:
            raise ValueError('compliance_canonical_absolute_path_required')
    return value


def binding(value):
    if (type(value) is not dict or set(value) != FIELDS
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'product-complete-compliance'
            or value['engine_profile'] != PROFILE
            or any(type(value[key]) is not type(expected) or value[key] != expected
                   for key, expected in AUTHORITY.items())):
        raise ValueError('complete_compliance_binding_or_authority_changed')
    for name, size in (('operation_id', 64), ('node_id', 32), ('runtime_source_digest', 64),
                       ('source_revision', 40), ('source_tree', 40), ('package_sha256', 64)):
        if type(value[name]) is not str or re.fullmatch('[a-f0-9]{'+str(size)+'}', value[name]) is None:
            raise ValueError('complete_compliance_exact_binding_required')
    for name in ('instance_root', 'product_source_root'):
        path_label(value[name], absolute=True)
    explicit_time(value['assessed_at'])
    return value


def options(value):
    if type(value) is not dict or set(value) != OPTION_FIELDS:
        raise ValueError('complete_compliance_explicit_options_required')
    path_label(value['cwd'], absolute=True); path_label(value['output_file'])
    for name in ('target_repo', 'input_file'):
        if value[name] is not None:
            path_label(value[name])
    if any(type(value[name]) is not bool for name in ('skip_unit_tests', 'fail_on_findings')):
        raise ValueError('complete_compliance_explicit_mode_required')
    return value


def request(value):
    if type(value) is not dict or set(value) != {'binding', 'options', 'record_root', 'package'}:
        raise ValueError('complete_compliance_worker_request_required')
    header = binding(value['binding']); options(value['options'])
    expected = PurePosixPath(header['instance_root']) / 'state/compliance/operations' / header['operation_id']
    if value['record_root'] != str(expected) or value['package'] != str(expected / 'input.zip'):
        raise ValueError('complete_compliance_owned_operation_required')
    return value


def decision_binding(header):
    binding(header)
    from lib.compliance_replay import AUTHORITY as DECISION_AUTHORITY
    names = ('operation_id', 'node_id', 'runtime_source_digest', 'source_revision',
             'source_tree', 'package_sha256', 'engine_profile', 'assessed_at')
    return {'schema_version': 1, 'kind': 'product-compliance-decision-record',
            **{name: deepcopy(header[name]) for name in names}, **DECISION_AUTHORITY}


def result_status(decision, *, integration, repository, unit, opa, skip_unit_tests):
    """Keep legacy findings, own readiness and incomplete acquisition separate."""
    if type(skip_unit_tests) is not bool:
        raise ValueError('complete_compliance_explicit_unit_scope_required')
    original = decision.get('original_exit_code') if decision.get('kind') == 'returned' else None
    if decision.get('kind') == 'returned' and (type(original) is not int or original not in (0, 1)):
        raise ValueError('complete_compliance_original_exit_required')
    incomplete = {'execution': 'incomplete', 'original_finding_exit': original, 'modern_exit': 2}
    expected = ['not_run'] if skip_unit_tests else ['pass', 'fail']
    if unit not in expected:
        return incomplete
    if (decision.get('kind') != 'returned' or integration != 'complete' or repository not in ('pass', 'fail')
            or opa not in ('pass', 'findings')):
        return incomplete
    return {'execution': 'complete', 'original_finding_exit': original,
            'modern_exit': 1 if repository == 'fail' or unit == 'fail' else 0}
