"""Closed read-only replay worker messages; execution declarations convey no authority."""
from pathlib import PurePosixPath
import re

from lib.repository_operation import AUTHORITY, binding

PROFILE = 'repository-replay-worker-v1'
MAX_REQUEST = 32768
MAX_RESPONSE = 1024 * 1024
WALL_SECONDS = 120
CPU_SECONDS = 60
MEMORY_BYTES = 1024**3


def request(value):
    if (type(value) is not dict or set(value) != {'schema_version', 'profile', 'record_root', 'binding'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['profile'] != PROFILE):
        raise ValueError('repository_replay_worker_request_required')
    header = binding(value['binding'])
    name = value['record_root']
    if (type(name) is not str or len(name) > 8192 or any(ord(c) < 32 for c in name)
            or '\\' in name or not PurePosixPath(name).is_absolute()
            or str(PurePosixPath(name)) != name or '..' in PurePosixPath(name).parts
            or PurePosixPath(name).name != header['operation_id']):
        raise ValueError('repository_replay_worker_operation_root_required')
    return value


def inspection(value, header):
    fields = {'binding', 'state', 'execution', 'exit_code', 'source_native_reads', 'files_compared',
              'journal_records', 'journal_last_sha256', 'whole_event_order_and_bytes_equal',
              'whole_output_bytes_equal', *AUTHORITY}
    if (type(value) is not dict or set(value) != fields or binding(value['binding']) != header
            or value['state'] != 'retained_declared_replay_consistent' or value['execution'] != 'complete'
            or type(value['exit_code']) is not int or value['exit_code'] not in (0, 1)
            or any(type(value[key]) is not type(expected) or value[key] != expected
                   for key, expected in AUTHORITY.items())
            or value['whole_event_order_and_bytes_equal'] is not True
            or value['whole_output_bytes_equal'] is not True):
        raise ValueError('repository_replay_worker_complete_inspection_required')
    for name, maximum in [('source_native_reads', 20064), ('files_compared', 10000), ('journal_records', 65536)]:
        if type(value[name]) is not int or not 0 < value[name] <= maximum:
            raise ValueError('repository_replay_worker_inspection_budget')
    if (type(value['journal_last_sha256']) is not str
            or re.fullmatch('[a-f0-9]{64}', value['journal_last_sha256']) is None):
        raise ValueError('repository_replay_worker_journal_identity_required')
    return value


def response(value, header):
    if (type(value) is not dict or set(value) != {'schema_version', 'profile', 'inspection', 'limits'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['profile'] != PROFILE):
        raise ValueError('repository_replay_worker_response_required')
    inspection(value['inspection'], header)
    limits = value['limits']
    if (type(limits) is not dict or set(limits) != {'cpu_seconds', 'address_space_bytes'}
            or type(limits['cpu_seconds']) is not int or limits['cpu_seconds'] != CPU_SECONDS
            or (limits['address_space_bytes'] is not None
                and (type(limits['address_space_bytes']) is not int
                     or limits['address_space_bytes'] != 2 * MEMORY_BYTES))):
        raise ValueError('repository_replay_worker_limits_required')
    return value
