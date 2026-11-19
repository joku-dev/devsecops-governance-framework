"""Complete wrapper decision replay from explicit retained port observations.

This layer starts no processes and writes no reports during replay. A record is
declared observation data, not authentication that a native operation occurred.
The application must durably bind it to the actual admitted source/suboperations.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from lib.compliance_result import ComplianceResult
from lib.portable.contracts import canonical_digest

MAX_EVENTS = 128
MAX_BYTES = 64 * 1024**2
ERRORS = {cls.__name__: cls for cls in (ValueError, TypeError, KeyError,
    IndexError, RuntimeError, FileNotFoundError, FileExistsError,
    IsADirectoryError, NotADirectoryError, PermissionError, OSError)}
PORTS = {'resolve', 'run', 'control_report', 'control_markdown',
         'write', 'exists', 'timestamp', 'print'}
AUTHORITY = {'official_acceptance': False, 'production_approval': False,
    'authority_transferred': False, 'independent_execution_attested': False}


def plain(value):
    """Freeze JSON values and reject unserializable/non-finite observations."""
    # Dict insertion order is part of the original JSON report wire. A sorted
    # clone would change nested report bytes before the core writes them.
    raw = json.dumps(value, allow_nan=False, ensure_ascii=False,
                     separators=(',', ':')).encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('compliance_observation_byte_budget')
    return json.loads(raw)


def failure(error):
    if type(error) is json.JSONDecodeError:
        return {'type': 'JSONDecodeError', 'args': [error.msg, error.doc, error.pos]}
    if type(error).__name__ not in ERRORS or ERRORS[type(error).__name__] is not type(error):
        raise ValueError('unreplayable_compliance_exception') from error
    value = {'type': type(error).__name__, 'args': plain(error.args)}
    if isinstance(error, OSError):
        value.update(filename=error.filename, filename2=error.filename2)
    return value


def raise_failure(value):
    if type(value) is not dict or type(value.get('args')) is not list:
        raise ValueError('invalid_compliance_exception_observation')
    kind = value.get('type')
    if kind == 'JSONDecodeError' and set(value) == {'type', 'args'}:
        raise json.JSONDecodeError(*value['args'])
    if kind not in ERRORS:
        raise ValueError('invalid_compliance_exception_observation')
    cls = ERRORS[kind]
    expected = {'type', 'args', 'filename', 'filename2'} if issubclass(cls, OSError) else {'type', 'args'}
    if set(value) != expected:
        raise ValueError('invalid_compliance_exception_observation')
    if issubclass(cls, OSError) and value['filename'] is not None:
        raise cls(*value['args'], value['filename'], None, value['filename2'])
    raise cls(*value['args'])


def checked_response(port, value):
    if port == 'resolve':
        if type(value) is not str or not Path(value).is_absolute():
            raise ValueError('invalid_compliance_resolved_path')
    elif port == 'run':
        if (type(value) is not dict or set(value) != {'returncode', 'stdout', 'stderr'}
                or type(value['returncode']) is not int
                or any(type(value[key]) is not str for key in ('stdout', 'stderr'))):
            raise ValueError('invalid_compliance_native_observation')
    elif port == 'control_report':
        if type(value) is not dict:
            raise ValueError('invalid_compliance_control_observation')
    elif port in ('control_markdown', 'timestamp'):
        if type(value) is not str:
            raise ValueError('invalid_compliance_text_observation')
    elif port == 'exists':
        if type(value) is not bool:
            raise ValueError('invalid_compliance_presence_observation')
    elif port in ('write', 'print'):
        if value is not None:
            raise ValueError('invalid_compliance_effect_observation')
    else:
        raise ValueError('unsupported_compliance_port')
    return plain(value)


class Ports:
    def resolve(self, path):
        return Path(self.consume('resolve', [str(path)]))

    def run(self, command):
        return SimpleNamespace(**self.consume('run', [command]))

    def control_report(self, path):
        return self.consume('control_report', [str(path)])

    def control_markdown(self, report):
        return self.consume('control_markdown', [report])

    def write(self, path, text):
        return self.consume('write', [str(path), text])

    def exists(self, path):
        return self.consume('exists', [str(path)])

    def timestamp(self):
        return self.consume('timestamp', [])

    def print(self, text):
        return self.consume('print', [text])


class RecordingEnvironment(Ports):
    def __init__(self, environment, *, on_event=None):
        self.environment = environment
        self.root, self.cwd = environment.root, environment.cwd
        self.events = []
        self.bytes = 0
        if on_event is not None and not callable(on_event):
            raise ValueError('compliance_event_callback_required')
        self.on_event = on_event

    def emit(self, phase, observation):
        if self.on_event is not None:
            self.on_event({'kind': 'compliance-port', 'phase': phase,
                'index': len(self.events), 'observation': deepcopy(observation)})

    def consume(self, port, arguments):
        if port not in PORTS or len(self.events) >= MAX_EVENTS:
            raise ValueError('compliance_observation_event_budget')
        event = {'port': port, 'arguments': plain(arguments)}
        self.events.append(event)
        self.emit('intent', event)
        args = deepcopy(arguments)
        if port in ('resolve', 'control_report', 'write', 'exists'):
            args[0] = Path(args[0])
        try:
            value = getattr(self.environment, port)(*args)
        except Exception as error:
            event['exception'] = failure(error)
            self.account(event)
            self.emit('finished', event)
            raise
        if port == 'resolve':
            value = str(value)
        elif port == 'run':
            value = {key: getattr(value, key) for key in ('returncode', 'stdout', 'stderr')}
        elif port in ('print', 'write'):
            value = None  # Ignore Path.write_text's native count, like the core.
        event['value'] = checked_response(port, value)
        self.account(event)
        self.emit('finished', event)
        return deepcopy(event['value'])

    def account(self, event):
        self.bytes += len(json.dumps(event, ensure_ascii=False, allow_nan=False).encode())
        if self.bytes > MAX_BYTES:
            raise ValueError('compliance_observation_byte_budget')


class ReplayEnvironment(Ports):
    def __init__(self, record):
        self.root, self.cwd = Path(record['root']), Path(record['cwd'])
        self.events = deepcopy(record['events'])
        self.position = 0

    def consume(self, port, arguments):
        if self.position >= len(self.events):
            raise ValueError('compliance_replay_observations_exhausted')
        event = self.events[self.position]
        if ({'port': port, 'arguments': arguments}
                != {key: event.get(key) for key in ('port', 'arguments')}):
            raise ValueError('compliance_replay_order_or_arguments_changed')
        self.position += 1
        if set(event) == {'port', 'arguments', 'exception'}:
            raise_failure(event['exception'])
        if set(event) != {'port', 'arguments', 'value'}:
            raise ValueError('invalid_compliance_replay_event')
        return deepcopy(checked_response(port, event['value']))


def observe(environment, options):
    try:
        code, report = ComplianceResult(environment).generate(**options)
        return {'kind': 'returned', 'original_exit_code': code, 'report': report}
    except Exception as error:
        return {'kind': 'raised', 'exception': failure(error)}


def record_generation(environment, *, output_file, target_repo=None,
                      input_file=None, skip_unit_tests=False, on_event=None):
    options = {'output_file': str(output_file),
        'target_repo': None if target_repo is None else str(target_repo),
        'input_file': None if input_file is None else str(input_file),
        'skip_unit_tests': skip_unit_tests}
    ports = RecordingEnvironment(environment, on_event=on_event)
    outcome = observe(ports, options)
    record = plain({'schema_version': 1, 'kind': 'complete-compliance-decision-observations',
        'root': str(ports.root), 'cwd': str(ports.cwd), 'options': options,
        'events': ports.events, 'outcome': outcome, **AUTHORITY})
    if len(json.dumps(record).encode()) > MAX_BYTES:
        raise ValueError('compliance_observation_byte_budget')
    return {**record, 'record_digest': canonical_digest(record)}


def inspect_generation(record):
    expected = {'schema_version', 'kind', 'root', 'cwd', 'options', 'events',
                'outcome', 'record_digest', *AUTHORITY}
    if (type(record) is not dict or set(record) != expected
            or type(record['schema_version']) is not int or record['schema_version'] != 1
            or record['kind'] != 'complete-compliance-decision-observations'
            or any(record[key] is not False for key in AUTHORITY)
            or any(type(record[key]) is not str or not Path(record[key]).is_absolute() for key in ('root', 'cwd'))
            or type(record['events']) is not list or len(record['events']) > MAX_EVENTS
            or canonical_digest({k: v for k, v in record.items() if k != 'record_digest'}) != record['record_digest']):
        raise ValueError('invalid_compliance_observation_record')
    record = plain(record)
    options = record['options']
    if (type(options) is not dict
            or set(options) != {'output_file', 'target_repo', 'input_file', 'skip_unit_tests'}
            or type(options['output_file']) is not str
            or any(value is not None and type(value) is not str
                   for value in (options['target_repo'], options['input_file']))
            or type(options['skip_unit_tests']) is not bool):
        raise ValueError('invalid_compliance_replay_options')
    environment = ReplayEnvironment(record)
    outcome = observe(environment, options)
    if outcome != record['outcome'] or environment.position != len(environment.events):
        raise ValueError('compliance_replay_outcome_or_unused_events')
    return {'state': 'declared_complete_decision_replay_consistent',
        'event_order_arguments_and_results_equal': True,
        'original_decision_outcome_equal': True, 'event_count': environment.position,
        'native_programs_reexecuted': False, 'export_files_written': False,
        'native_execution_authenticated': False, **AUTHORITY}
