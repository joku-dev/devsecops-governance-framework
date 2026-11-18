"""Recompute local validation decisions from explicitly declared observations.

Hashes detect local inconsistency. They do not authenticate execution or grant
approval. Replaying retained OPA responses never claims to invoke a native tool.
"""
import base64
from copy import deepcopy

from lib.provider_ports import native_cleanup_observation_valid
from lib.portable.contracts import canonical_digest
from lib.portable.runtime import approved_opa_hashes
from lib.validation_queries import MAX_STREAM, request

MAX_NATIVE = 32 * 1024**2


def encoded(observations):
    output = []
    total = 0
    for item in observations:
        row = deepcopy(item)
        for name in ('stdout', 'stderr'):
            raw = row.pop(name, b'')
            total += len(raw)
            if not isinstance(raw, bytes) or len(raw) > MAX_STREAM or total > MAX_NATIVE:
                raise ValueError('validation_native_observation_budget')
            row[name + '_base64'] = base64.b64encode(raw).decode('ascii')
        output.append(row)
    return output


class ReplayOPA:
    def __init__(self, observations, *, available, tool_sha256):
        if type(available) is not bool or not isinstance(observations, list) or len(observations) > 8:
            raise ValueError('invalid_validation_native_observations')
        if ((not available and (observations or tool_sha256 is not None))
                or available and (not isinstance(tool_sha256, str) or len(tool_sha256) != 64
                    or any(c not in '0123456789abcdef' for c in tool_sha256))):
            raise ValueError('invalid_validation_native_tool_binding')
        if available and tool_sha256 not in approved_opa_hashes('1.18.2'):
            raise ValueError('validation_native_tool_not_approved')
        self.available = available
        self.tool_sha256 = tool_sha256
        self.observations = deepcopy(observations)
        self.position = 0
        self.total = 0

    def run(self, command, files):
        from types import SimpleNamespace
        selected = request(command, files)
        if not self.available or self.position >= len(self.observations):
            raise ValueError('validation_native_observation_missing')
        row = self.observations[self.position]
        expected = {'request', 'tool_sha256', 'process_started', 'returncode', 'error_type',
            'cleanup_signal_permission_denied', 'cleanup_absence_check', 'stdout_base64', 'stderr_base64', 'output_truncated'}
        if (not isinstance(row, dict) or set(row) != expected or canonical_digest(row['request']) != canonical_digest(selected)
                or row['tool_sha256'] != self.tool_sha256 or row['process_started'] is not True
                or type(row['returncode']) is not int or not -128 <= row['returncode'] <= 255
                or row['error_type'] is not None or row['output_truncated'] is not False
                or not native_cleanup_observation_valid(row)):
            raise ValueError('validation_native_observation_changed_or_incomplete')
        streams = {}
        for name in ('stdout', 'stderr'):
            value = row[name + '_base64']
            if not isinstance(value, str) or len(value) > (MAX_STREAM + 2) // 3 * 4:
                raise ValueError('validation_native_observation_budget')
            try:
                raw = base64.b64decode(value, validate=True)
                if base64.b64encode(raw).decode('ascii') != value:
                    raise ValueError('noncanonical_validation_native_bytes')
                streams[name] = raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
            except (ValueError, UnicodeError):
                raise ValueError('invalid_validation_native_bytes') from None
            self.total += len(raw)
            if len(raw) > MAX_STREAM or self.total > MAX_NATIVE:
                raise ValueError('validation_native_observation_budget')
        self.position += 1
        return SimpleNamespace(returncode=row['returncode'], **streams)

    def finish(self):
        if self.position != len(self.observations):
            raise ValueError('validation_native_observation_unused')
