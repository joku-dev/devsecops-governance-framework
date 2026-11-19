"""Neutral finite environment creation/update orchestration.

Native interpreter/package/tool operations and persistent journals belong to
explicit adapters. Incomplete calls are never silently retried by this core.
"""
from dataclasses import dataclass
import re

PROFILES = frozenset(('validation-environment-v1', 'source-intake-environment-v1'))


class BootstrapFailure(RuntimeError):
    """Adapter-declared failure code; raw native diagnostics stay private."""
    def __init__(self, code):
        if type(code) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,99}', code):
            raise ValueError('invalid_bootstrap_failure_code')
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class BootstrapResult:
    profile: str
    state: str
    existing_environment_used: bool
    operations: int


def run(profile, ports, journal):
    """One explicit operation; caller owns source/path/profile admission.

    This finite action surface mirrors the original required branches without
    embedding command names, platform endpoints or package-manager invocation.
    Journal intent must be durable before perform; unknown exceptions and
    interruption leave that intent pending, with no invented native failure.
    """
    if type(profile) is not str or profile not in PROFILES:
        raise ValueError('unsupported_environment_bootstrap_profile')
    operations = 0

    def step(action, result_type=type(None)):
        nonlocal operations
        token = journal.before(action)
        try:
            value = ports.perform(action)
            if type(value) is not result_type:
                raise BootstrapFailure('invalid_bootstrap_adapter_result')
        except BootstrapFailure as error:
            journal.failed(token, error.code)
            raise
        journal.after(token, value)
        operations += 1
        return value

    step('preflight')
    existing = step('environment_python_executable', bool)
    if not existing:
        step('create_environment')
    # Existing environments still receive dependency updates, never a false
    # success based only on the presence of an interpreter.
    step('install_dependencies')
    if profile == 'validation-environment-v1':
        step('ensure_policy_tool')
        step('verify_policy_tool_version')
        step('check_dependency_consistency')
    step('render_ready_message')
    return BootstrapResult(profile, 'complete', existing, operations)


class RecordedPorts:
    """Strict declared-observation replay; never invokes a native program."""
    def __init__(self, observations):
        if type(observations) is not list:
            raise ValueError('invalid_bootstrap_observation_sequence')
        self.rows = observations
        self.position = 0

    def perform(self, action):
        if self.position >= len(self.rows):
            raise ValueError('bootstrap_observation_incomplete')
        row = self.rows[self.position]
        self.position += 1
        if (type(row) is not dict or set(row) not in ({'action', 'value'}, {'action', 'failure'})
                or row['action'] != action):
            raise ValueError('bootstrap_observation_order_mismatch')
        if 'failure' in row:
            raise BootstrapFailure(row['failure'])
        return row['value']

    def complete(self):
        if self.position != len(self.rows):
            raise ValueError('bootstrap_observation_unused')


def replay(profile, observations):
    """Re-derive a complete declared operation and reject trailing observations."""
    ports = RecordedPorts(observations)
    class ReadOnlyJournal:
        def before(self, action):
            return action
        def after(self, token, value):
            pass
        def failed(self, token, code):
            pass
    try:
        value = run(profile, ports, ReadOnlyJournal())
    except BootstrapFailure:
        ports.complete()
        raise
    ports.complete()
    return value
