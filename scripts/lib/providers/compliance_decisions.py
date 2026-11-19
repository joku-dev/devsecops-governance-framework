"""Durable declared wrapper decisions, distinct from complete native acquisition.

Every port intent is flushed before calling its implementation. Interrupted
records stay pending and cannot be resumed or called a successful native run.
Native suboperation/source/tool authentication is the application's separate duty.
"""
import hashlib
import json
import os
import re

from lib.compliance_replay import (record_generation, inspect_generation,
    MAX_BYTES, AUTHORITY)
from lib.providers.repository_journal import RepositoryJournal, read_journal, root_fd
from lib.providers.repository_operations import read_file
from lib.result_bytes import strict_json
from lib.result_snapshot_store import explicit_time

FIELDS = {'schema_version', 'kind', 'operation_id', 'node_id',
    'runtime_source_digest', 'source_revision', 'source_tree', 'package_sha256',
    'engine_profile', 'assessed_at', *AUTHORITY}


def decision_wire(value):
    # Keep insertion order inside native/control observations. The journal's
    # sorted encoding is suitable for its chain, but cannot serialize this wire.
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode() + b'\n'


def binding(value):
    if (type(value) is not dict or set(value) != FIELDS
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'product-compliance-decision-record'
            or value['engine_profile'] != 'legacy-extended-compliance-v1'
            or any(value[key] is not False for key in AUTHORITY)):
        raise ValueError('compliance_decision_binding_required')
    for name, size in (('operation_id', 64), ('node_id', 32),
            ('runtime_source_digest', 64), ('package_sha256', 64)):
        if type(value[name]) is not str or re.fullmatch('[a-f0-9]{' + str(size) + '}', value[name]) is None:
            raise ValueError('compliance_decision_exact_identity_required')
    revision, tree = value['source_revision'], value['source_tree']
    if (type(revision) is not str or re.fullmatch('(?:[a-f0-9]{40}|[a-f0-9]{64})', revision) is None
            or type(tree) is not str or re.fullmatch('[a-f0-9]{' + str(len(revision)) + '}', tree) is None):
        raise ValueError('compliance_decision_exact_source_required')
    explicit_time(value['assessed_at'])
    return value


def record(root, header, environment, *, on_event=None, **options):
    """The caller supplies a fresh private directory and admitted environment."""
    binding(header)
    if on_event is not None and not callable(on_event):
        raise ValueError('compliance_decision_forward_callback_required')
    with RepositoryJournal(root, header) as journal:
        def emit(row):
            journal.append(row)
            if on_event is not None:
                on_event(row)
        value = record_generation(environment, on_event=emit, **options)
        inspect_generation(value)
        raw = decision_wire(value)
        if len(raw) > MAX_BYTES:
            raise ValueError('compliance_decision_record_budget')
        # The journal checks identity before and after the exclusive write.
        journal.check()
        fd = os.open('decision.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=journal.directory)
        try:
            remaining = memoryview(raw)
            while remaining:
                count = os.write(fd, remaining)
                if count <= 0:
                    raise OSError('compliance_decision_short_write')
                remaining = remaining[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(journal.directory)
        journal.check()
        journal.append({'kind': 'compliance-decision-recorded',
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    return load(root, header)


def load(root, header):
    binding(header)
    rows = read_journal(root, expected_header=header)
    events = [row['payload'] for row in rows]
    terminals = [i for i, row in enumerate(events) if row.get('kind') == 'compliance-decision-recorded']
    if not terminals:
        return {'state': 'pending_incomplete', 'decision_replay_verified': False,
            'native_acquisition_verified': False, **AUTHORITY}
    if terminals != [len(events) - 1]:
        raise ValueError('compliance_decision_terminal_order_changed')
    terminal = events[-1]
    if set(terminal) != {'kind', 'bytes', 'sha256'} or type(terminal['bytes']) is not int:
        raise ValueError('compliance_decision_terminal_changed')
    root, parent, _ = root_fd(root)
    try:
        if set(os.listdir(parent)) != {'events.jsonl', 'decision.json'}:
            raise ValueError('compliance_decision_membership_changed')
        raw = read_file(parent, 'decision.json', MAX_BYTES)
    finally:
        os.close(parent)
    if len(raw) != terminal['bytes'] or hashlib.sha256(raw).hexdigest() != terminal['sha256']:
        raise ValueError('compliance_decision_retained_bytes_changed')
    value = strict_json(raw)
    if decision_wire(value) != raw:
        raise ValueError('compliance_decision_encoding_changed')
    replay = inspect_generation(value)
    expected = [{'kind': 'operation-start', 'binding': header}]
    for index, event in enumerate(value['events'], 1):
        intent = {key: event[key] for key in ('port', 'arguments')}
        expected += [{'kind': 'compliance-port', 'phase': 'intent', 'index': index, 'observation': intent},
            {'kind': 'compliance-port', 'phase': 'finished', 'index': index, 'observation': event}]
    if events[:-1] != expected:
        raise ValueError('compliance_decision_journal_trace_changed')
    return {'state': 'declared_decision_recorded_replay_consistent',
        'decision_replay_verified': True, 'native_acquisition_verified': False,
        'decision': value, 'replay': replay, **AUTHORITY}
