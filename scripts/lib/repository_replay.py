"""Retained native/clock facts for the whole engine; no native execution.

Replay establishes declared consistency of exact retained observations. It
never independently authenticates the provider, execution or human approval.
"""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import re
from types import SimpleNamespace

from lib.provider_ports import native_cleanup_observation_valid, attestation_crypto_outcome
from lib.result_snapshot_store import explicit_time

MAX_STREAM = 65536
OPA_FIELDS = {'request', 'argv', 'tool_path', 'tool_sha256', 'process_started', 'returncode',
    'error_type', 'timed_out', 'output_truncated', 'cleanup_signal_permission_denied',
    'cleanup_absence_check', 'stdout_base64', 'stderr_base64'}


def raw_stream(row, name, *, maximum=MAX_STREAM):
    value = row.get(name + '_base64')
    if type(value) is not str or len(value) > 4 * ((maximum + 2) // 3):
        raise ValueError('repository_replay_stream_budget')
    try: raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):raise ValueError('invalid_repository_replay_stream') from None
    if len(raw) > maximum or base64.b64encode(raw).decode('ascii') != value:
        raise ValueError('invalid_repository_replay_stream')
    return raw


def native_complete(row):
    if (row.get('process_started') is not True or type(row.get('returncode')) is not int
            or row.get('error_type') is not None or row.get('timed_out') is not False
            or row.get('output_truncated') is not False or not native_cleanup_observation_valid(row)):
        raise ValueError('repository_replay_native_execution_incomplete')


def tool_identity(path, digest):
    if (type(path) is not str or not PurePosixPath(path).is_absolute()
            or str(PurePosixPath(path)) != path or '..' in PurePosixPath(path).parts
            or len(path) > 8192 or any(ord(c) < 32 for c in path)
            or type(digest) is not str or re.fullmatch('[a-f0-9]{64}', digest) is None):
        raise ValueError('repository_replay_tool_identity_required')


class ReplayRepositoryClock:
    def __init__(self, values):
        if type(values) is not list or len(values) > 1024:
            raise ValueError('repository_replay_clock_budget')
        for value in values:
            if type(value) is not str:raise ValueError('repository_replay_clock_value_required')
            explicit_time(value)
        self.values, self.position = list(values), 0

    def __call__(self):
        if self.position >= len(self.values):
            raise ValueError('repository_replay_clock_observation_missing')
        value = self.values[self.position]
        self.position += 1
        return value

    def finish(self):
        if self.position != len(self.values):raise ValueError('repository_replay_clock_observations_unused')


class ReplayRepositoryOPA:
    def __init__(self, context, observations, *, approved_hashes):
        if (type(context) is not dict or set(context) != {'tool_path', 'tool_sha256', 'workarea'}
                or type(observations) is not list or not 1 <= len(observations) <= 1024):
            raise ValueError('invalid_repository_opa_replay_context')
        tool_identity(context['tool_path'], context['tool_sha256'])
        if context['tool_sha256'] not in approved_hashes:
            raise ValueError('repository_opa_replay_checksum_differs')
        workarea = context['workarea']
        if (type(workarea) is not str or not PurePosixPath(workarea).is_absolute()
                or str(PurePosixPath(workarea)) != workarea or '..' in PurePosixPath(workarea).parts
                or len(workarea) > 8192 or any(ord(c) < 32 for c in workarea)):
            raise ValueError('invalid_repository_opa_replay_workarea')
        self.context, self.rows = deepcopy(context), deepcopy(observations)
        self.position = 0
        row = self.next({'operation': 'version', 'version': '1.18.2'})
        if row['argv'] != [context['tool_path'], 'version'] or row['returncode'] != 0:
            raise ValueError('repository_opa_replay_version_differs')
        text = raw_stream(row, 'stdout').decode('utf-8')
        if re.search(r'^Version:\s*1\.18\.2\s*$', text, re.M) is None:
            raise ValueError('repository_opa_replay_version_differs')

    def next(self, request):
        if self.position >= len(self.rows):raise ValueError('repository_opa_replay_observation_missing')
        row = self.rows[self.position]
        if (type(row) is not dict or set(row) != OPA_FIELDS
                or json.dumps(row['request'], sort_keys=True, allow_nan=False) != json.dumps(request, sort_keys=True, allow_nan=False)
                or row['tool_path'] != self.context['tool_path'] or row['tool_sha256'] != self.context['tool_sha256']):
            raise ValueError('repository_opa_replay_request_differs')
        native_complete(row)
        raw_stream(row, 'stdout'); raw_stream(row, 'stderr')
        self.position += 1
        return row

    def check(self, files, *, directory_present):
        request = {'operation': 'check', 'directory_present': directory_present, 'file_order': list(files),
            'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in files.items()}}
        row = self.next(request)
        argv = row['argv']
        if type(argv) is not list or len(argv) != 3 or argv[:2] != [self.context['tool_path'], 'check']:
            raise ValueError('repository_opa_replay_argv_differs')
        if (type(argv[2]) is not str or str(PurePosixPath(argv[2])) != argv[2]
                or any(ord(c) < 32 for c in argv[2])):
            raise ValueError('repository_opa_replay_argv_differs')
        try: parts = PurePosixPath(argv[2]).relative_to(self.context['workarea']).parts
        except (TypeError, ValueError):raise ValueError('repository_opa_replay_argv_differs') from None
        if len(parts) != 3 or not parts[0].startswith('repository-opa-') or parts[1:] != ('policies', 'opa'):
            raise ValueError('repository_opa_replay_argv_differs')
        return SimpleNamespace(returncode=row['returncode'], **{
            name: raw_stream(row, name).decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
            for name in ('stdout', 'stderr')})

    def finish(self):
        if self.position != len(self.rows):raise ValueError('repository_opa_replay_observations_unused')


CRYPTO_FIELDS = {'attempted', 'process_started', 'tool_path', 'tool_sha256', 'returncode',
    'timed_out', 'error_type', 'failure_stage', 'signature_valid', 'reason',
    'cleanup_signal_permission_denied', 'cleanup_absence_check'}


def crypto_input(key, statement, signature):
    if (type(key) is not str or len(key.encode('utf-8')) > 65536
            or type(statement) is not bytes or len(statement) > 1024**2
            or type(signature) is not bytes or len(signature) > 16384):
        raise ValueError('repository_crypto_replay_input_budget')
    return {name + '_sha256': hashlib.sha256(raw).hexdigest()
            for name, raw in (('key', key.encode('utf-8')), ('statement', statement), ('signature', signature))}


class ReplayRepositoryCrypto:
    def __init__(self, packets):
        if type(packets) is not list or len(packets) > 1024:
            raise ValueError('repository_crypto_replay_packet_budget')
        self.rows, self.position = deepcopy(packets), 0

    def __call__(self, key, statement, signature):
        if self.position >= len(self.rows):raise ValueError('repository_crypto_replay_observation_missing')
        packet = self.rows[self.position]
        if (type(packet) is not dict or set(packet) != {'profile', 'input', 'observation', 'stdout_base64', 'stderr_base64'}
                or packet['profile'] != 'legacy-attestation-pilot-v1'
                or packet['input'] != crypto_input(key, statement, signature)):
            raise ValueError('repository_crypto_replay_request_differs')
        row = packet['observation']
        if (type(row) is not dict or set(row) != CRYPTO_FIELDS or row['attempted'] is not True
                or type(row['process_started']) is not bool or type(row['timed_out']) is not bool
                or row['returncode'] is not None and type(row['returncode']) is not int):
            raise ValueError('invalid_repository_crypto_replay_observation')
        if row['tool_path'] is not None or row['tool_sha256'] is not None:
            tool_identity(row['tool_path'], row['tool_sha256'])
        if row['process_started'] and (row['tool_path'] is None or row['failure_stage'] is not None):
            raise ValueError('invalid_repository_crypto_replay_tool_binding')
        stdout, stderr = raw_stream(packet, 'stdout'), raw_stream(packet, 'stderr')
        if not row['process_started'] and (stdout or stderr):
            raise ValueError('repository_crypto_replay_unstarted_streams')
        result = attestation_crypto_outcome(row)
        if (type(row['signature_valid']) is not bool or type(row['reason']) is not str
                or result != (row['signature_valid'], row['reason'])):
            raise ValueError('repository_crypto_replay_outcome_differs')
        self.position += 1
        return result

    def finish(self):
        if self.position != len(self.rows):raise ValueError('repository_crypto_replay_observations_unused')
