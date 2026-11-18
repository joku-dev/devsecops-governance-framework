"""Whole retained operation replay with one exact ordered effect/native trace."""
from copy import deepcopy

from lib import repository_operation as contract
from lib.provider_ports import audit_repository_acquisition
from lib.repository_engine import RepositoryEngine
from lib.repository_replay import (ReplayRepositoryClock, ReplayRepositoryCrypto,
    ReplayRepositoryOPA, crypto_input)
from lib.release_replay import ReplayReleaseEnvironment
from lib.portable.contracts import canonical_digest

REPLAY_FIELDS = {'schema_version', 'opa_context', 'release_context', 'references'}
NATIVE_FINAL_ONLY = {'cleanup_signal_permission_denied', 'cleanup_absence_check', 'stdout_base64', 'stderr_base64'}


class RepositoryTrace:
    def __init__(self, events):
        self.events, self.position = deepcopy(events), 0

    def expect(self, value):
        if self.position >= len(self.events) or canonical_digest(self.events[self.position]) != canonical_digest(value):
            raise ValueError('repository_replay_global_event_order_or_bytes_changed')
        self.position += 1

    def native(self, port, row):
        initial = {key: value for key, value in row.items() if key not in NATIVE_FINAL_ONLY}
        initial.update(process_started=False, returncode=None)
        for phase, observation in (('intent', initial), ('started', initial | {'process_started': True}), ('finished', row)):
            self.expect({'kind': 'native', 'port': port, 'phase': phase, 'observation': observation})

    def engine(self, row):self.expect({'kind': 'engine-event', 'event': row})

    def finish(self):
        if self.position != len(self.events):raise ValueError('repository_replay_global_events_unused')


class TraceOPA(ReplayRepositoryOPA):
    def __init__(self, trace, *args, **options):
        self.trace = trace
        super().__init__(*args, **options)

    def next(self, request):
        row = super().next(request)
        self.trace.native('opa', row)
        return row


class TraceRelease(ReplayReleaseEnvironment):
    def __init__(self, trace, *args):
        self.trace = trace
        super().__init__(*args, label_only=True)

    def consume(self, *args, **options):
        result = super().consume(*args, **options)
        self.trace.native('release', self.observations[self.position - 1])
        return result


class TraceClock(ReplayRepositoryClock):
    def __init__(self, trace, values):
        self.trace = trace
        super().__init__(values)

    def __call__(self):
        value = super().__call__()
        self.trace.expect({'kind': 'clock', 'value': value})
        return value


class TraceCrypto(ReplayRepositoryCrypto):
    def __init__(self, trace, packets):
        self.trace = trace
        super().__init__(packets)

    def __call__(self, key, statement, signature):
        result = super().__call__(key, statement, signature)
        packet = self.rows[self.position - 1]
        self.trace.expect({'kind': 'crypto', 'phase': 'intent', 'profile': packet['profile'],
                           'input': crypto_input(key, statement, signature)})
        row = packet['observation']
        if row['process_started']:
            started = {name: value for name, value in row.items() if name not in NATIVE_FINAL_ONLY}
            started.update(returncode=None, error_type=None, failure_stage=None, signature_valid=None, reason=None,
                           timed_out=False)
            self.trace.expect({'kind': 'crypto', 'phase': 'started', 'observation': started})
        self.trace.expect({'kind': 'crypto', 'phase': 'finished', 'packet': packet})
        return result


def inspect_repository_operation(value, *, capture_adapter_factory, schema_identifier_bases,
                                 source_configuration_profile, approved_opa_hashes, engine_profile):
    """Replay a storage-checked record; caller must first use load_operation."""
    header = contract.binding(value['binding'])
    if header['engine_profile'] != engine_profile:
        raise ValueError('repository_operation_engine_profile_changed')
    if value['state'] != 'recorded_complete_replay_unverified':
        raise ValueError('repository_operation_incomplete_cannot_replay')
    contract.outcome(value['outcome'])
    metadata = value['replay']
    if (type(metadata) is not dict or set(metadata) != REPLAY_FIELDS
            or type(metadata['schema_version']) is not int or metadata['schema_version'] != 1):
        raise ValueError('repository_operation_replay_profile_required')
    payloads = [row['payload'] for row in value['journal']]
    if payloads[0] != {'kind': 'operation-start', 'binding': header}:
        raise ValueError('repository_operation_replay_binding_changed')
    boundary = [index for index, row in enumerate(payloads) if row.get('kind') == 'inputs-retained']
    if len(boundary) != 1:raise ValueError('repository_operation_input_boundary_required')
    acquisition = payloads[1:boundary[0]]
    if any(type(row) is not dict or set(row) != {'kind', 'phase', 'observation'}
           or row['kind'] != 'source-git' for row in acquisition):
        raise ValueError('repository_operation_acquisition_event_required')
    source = audit_repository_acquisition(value['manifest'], value['inputs'], value['commit'], metadata['references'],
        [{key: row[key] for key in ('phase', 'observation')} for row in acquisition])
    events = payloads[boundary[0] + 1:-1]
    trace = RepositoryTrace(events)
    def native_rows(port):
        return [row['observation'] for row in events if row.get('kind') == 'native'
                and row.get('port') == port and row.get('phase') == 'finished']
    opa = None if metadata['opa_context'] is None else TraceOPA(trace, metadata['opa_context'], native_rows('opa'),
        approved_hashes=approved_opa_hashes)
    release = TraceRelease(trace, value['manifest']['source_root'], value['inputs'], metadata['references'],
        metadata['release_context'], native_rows('release'))
    clock = TraceClock(trace, [row['value'] for row in events if row.get('kind') == 'clock'])
    crypto = TraceCrypto(trace, [row['packet'] for row in events if row.get('kind') == 'crypto'
                               and row.get('phase') == 'finished'])
    engine = RepositoryEngine(value['manifest'], value['inputs'], value['commit'],
        capture_adapter_factory=capture_adapter_factory, schema_identifier_bases=schema_identifier_bases,
        source_configuration_profile=source_configuration_profile, clock=clock, verify_attestation=crypto,
        release_port=release, opa_port=opa, append_event=trace.engine)
    outcome = engine.execute()
    if opa is not None:opa.finish()
    release.finish(); clock.finish(); crypto.finish(); trace.finish()
    if canonical_digest(outcome) != canonical_digest(value['outcome']) or engine.dataset.files != value['outputs']:
        raise ValueError('repository_operation_whole_result_or_output_bytes_changed')
    return {'binding': deepcopy(header), 'state': 'retained_declared_replay_consistent',
        'execution': outcome['execution'], 'exit_code': outcome['exit_code'],
        'source_native_reads': source['native_reads'], 'files_compared': len(value['outputs']),
        'journal_records': len(value['journal']), 'journal_last_sha256': value['journal'][-1]['sha256'],
        'whole_event_order_and_bytes_equal': True, 'whole_output_bytes_equal': True, **contract.AUTHORITY}
