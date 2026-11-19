"""Private append-only bootstrap intent/outcome storage; standard library only.

A consistent record is declared technical evidence. It cannot authenticate a
reviewer, establish current process liveness, grant Trust or authorize operation.
There is deliberately no implicit resume, retry or overwrite API.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import stat

from lib.environment_bootstrap import replay, BootstrapFailure

MAX_METADATA = 1024 * 1024
MAX_JOURNAL = 8 * 1024 * 1024
MAX_EVENTS = 512
ACTIONS = frozenset(('preflight', 'environment_python_executable', 'create_environment',
    'install_dependencies', 'ensure_policy_tool', 'verify_policy_tool_version',
    'check_dependency_consistency', 'render_ready_message'))
AUTHORITY = {'official_acceptance': False, 'production_approval': False,
             'independent_execution_authenticated': False, 'authority_transferred': False}


def encoded(value):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')) + '\n').encode('utf-8')
    if len(raw) > MAX_METADATA:
        raise ValueError('bootstrap_metadata_byte_budget')
    return raw


def document(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('bootstrap_duplicate_metadata_key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('bootstrap_nonfinite_metadata')
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    if type(value) is not dict:
        raise ValueError('bootstrap_metadata_object_required')
    return value


def owned_directory(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('bootstrap_storage_symlink_forbidden')
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ValueError('bootstrap_private_owned_storage_required')
    return path


def write_new(path, value):
    raw = encoded(value)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        while view:
            size = os.write(fd, view)
            if size <= 0:
                raise OSError('bootstrap_metadata_short_write')
            view = view[size:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_private(path, maximum=MAX_METADATA):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('bootstrap_storage_symlink_forbidden')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.geteuid() or before.st_mode & 0o077
                or before.st_size > maximum):
            raise ValueError('bootstrap_private_regular_bounded_file_required')
        raw = bytearray()
        while part := os.read(fd, min(65536, maximum + 1 - len(raw))):
            raw.extend(part)
            if len(raw) > maximum:
                raise ValueError('bootstrap_storage_byte_budget')
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')
        if any(getattr(before, key) != getattr(row, key) for row in (after, current) for key in fields):
            raise ValueError('bootstrap_storage_changed_during_read')
        return bytes(raw)
    finally:
        os.close(fd)


class BootstrapJournal:
    """One new owned operation; intent is fsynced before returning its token."""
    def __init__(self, directory, request, source):
        parent = owned_directory(directory)
        self.identifier = secrets.token_hex(16)
        self.root = parent / self.identifier
        self.root.mkdir(mode=0o700, exist_ok=False)
        self.sequence = 0
        self.previous = '0' * 64
        self.size = 0
        self.phase = None
        self.phase_action = None
        self.observations = []
        self.profile = document(encoded(request)).get('profile')
        self.phases = 0
        self.failed_phase = False
        self.terminal = False
        self.fd = None
        request_binding = write_new(self.root / 'request.json', request)
        source_binding = write_new(self.root / 'source.json', source)
        header = {'schema_version': 1, 'kind': 'environment-bootstrap-operation',
                  'operation_id': self.identifier, 'request': request_binding,
                  'source': source_binding, **AUTHORITY}
        write_new(self.root / 'header.json', header)
        self.fd = os.open(self.root / 'events.jsonl',
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        self.identity = os.fstat(self.fd)
        try:
            self.append({'kind': 'opened'})
        except BaseException:
            self.close()
            raise

    def append(self, payload):
        if self.fd is None or self.terminal or self.sequence >= MAX_EVENTS:
            raise ValueError('bootstrap_journal_closed_or_event_budget')
        info = os.fstat(self.fd)
        current = os.stat(self.root / 'events.jsonl', follow_symlinks=False)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('bootstrap_private_journal_required')
        if (info.st_ino, info.st_dev, info.st_size, info.st_nlink) != (
                self.identity.st_ino, self.identity.st_dev, self.size, 1):
            raise ValueError('bootstrap_journal_changed_before_append')
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError('bootstrap_journal_path_replaced')
        unsigned = {'sequence': self.sequence, 'previous': self.previous, 'payload': payload}
        digest = hashlib.sha256(encoded(unsigned)).hexdigest()
        raw = encoded({**unsigned, 'sha256': digest})
        if self.size + len(raw) > MAX_JOURNAL:
            raise ValueError('bootstrap_journal_byte_budget')
        remaining = memoryview(raw)
        while remaining:
            count = os.write(self.fd, remaining)
            if count <= 0:
                raise OSError('bootstrap_journal_short_write')
            remaining = remaining[count:]
        os.fsync(self.fd)
        self.size += len(raw)
        if os.fstat(self.fd).st_size != self.size:
            raise ValueError('bootstrap_journal_changed_during_append')
        self.sequence += 1
        self.previous = digest

    def before(self, action):
        if type(action) is not str or action not in ACTIONS or self.phase is not None or self.failed_phase:
            raise ValueError('bootstrap_invalid_phase_transition')
        token = self.phases
        self.append({'kind': 'phase-intent', 'phase': token, 'action': action})
        self.phase = token
        self.phase_action = action
        self.phases += 1
        return token

    def after(self, token, value):
        if type(token) is not int or self.phase is None or token != self.phase or type(value) not in (bool, type(None)):
            raise ValueError('bootstrap_phase_result_mismatch')
        self.append({'kind': 'phase-result', 'phase': token, 'state': 'returned', 'value': value})
        self.observations.append({'action': self.phase_action, 'value': value})
        self.phase = None
        self.phase_action = None

    def failed(self, token, code):
        if type(token) is not int or self.phase is None or token != self.phase or type(code) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,99}', code):
            raise ValueError('bootstrap_phase_failure_mismatch')
        self.append({'kind': 'phase-result', 'phase': token, 'state': 'failed', 'code': code})
        self.observations.append({'action': self.phase_action, 'failure': code})
        self.phase = None
        self.phase_action = None
        self.failed_phase = True

    def finish(self, result):
        state = result.get('state')
        if (state not in ('complete', 'failed', 'incomplete')
                or (state == 'complete' and (self.phase is not None or self.failed_phase))
                or (state == 'failed' and not self.failed_phase)):
            raise ValueError('bootstrap_terminal_result_mismatch')
        if state == 'complete':
            derived = replay(self.profile, self.observations)
            if type(result.get('operations')) is not int or result['operations'] != derived.operations:
                raise ValueError('bootstrap_completed_operation_count_mismatch')
        elif state == 'failed':
            try:
                replay(self.profile, self.observations)
            except BootstrapFailure:
                pass
            else:
                raise ValueError('bootstrap_declared_failure_not_reproduced')
        binding = write_new(self.root / 'result.json', {**result, **AUTHORITY})
        self.append({'kind': 'finished', 'result': binding, 'state': state})
        self.terminal = True
        return {'operation_id': self.identifier, 'record_root': str(self.root),
                'state': state, **AUTHORITY}

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *ignored):
        self.close()


def inspect(directory):
    """Check retained declared bytes/order; do not re-run tools or infer liveness."""
    from lib.environment_bootstrap import run, RecordedPorts, BootstrapFailure
    from lib.providers import process_groups
    root = owned_directory(directory)
    if not re.fullmatch('[a-f0-9]{32}', root.name):
        raise ValueError('bootstrap_operation_identifier_required')
    header = document(read_private(root/'header.json'))
    if (set(header) != {'schema_version','kind','operation_id','request','source',*AUTHORITY}
            or type(header['schema_version']) is not int or header['schema_version'] != 1
            or header['kind'] != 'environment-bootstrap-operation' or header['operation_id'] != root.name
            or any(header.get(k) is not False for k in AUTHORITY)):
        raise ValueError('bootstrap_operation_header_invalid')
    values = {}
    for name in ('request','source'):
        raw = read_private(root/(name+'.json'))
        if header[name] != {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:
            raise ValueError('bootstrap_operation_input_binding_changed')
        values[name] = document(raw)
    raw = read_private(root/'events.jsonl', MAX_JOURNAL)
    if not raw or not raw.endswith(b'\n'):
        raise ValueError('bootstrap_journal_truncated_or_empty')
    lines = raw.splitlines(keepends=True)
    if not 1 <= len(lines) <= MAX_EVENTS:
        raise ValueError('bootstrap_journal_event_budget')
    previous = '0'*64
    payloads = []
    for sequence,line in enumerate(lines):
        row = document(line)
        if (set(row) != {'sequence','previous','payload','sha256'}
                or type(row['sequence']) is not int or row['sequence'] != sequence
                or row['previous'] != previous or type(row['payload']) is not dict
                or encoded(row) != line):
            raise ValueError('bootstrap_journal_envelope_invalid')
        unsigned = {key:row[key] for key in ('sequence','previous','payload')}
        expected = hashlib.sha256(encoded(unsigned)).hexdigest()
        if row['sha256'] != expected:
            raise ValueError('bootstrap_journal_digest_changed')
        previous = expected
        payloads.append(row['payload'])
    if payloads[0] != {'kind':'opened'}:
        raise ValueError('bootstrap_journal_open_event_required')
    phase = None; action = None; phases = 0; observed = []; failed = False
    natives = {}; expected_native_files = set(); finished = None
    native_source=values['source'].get('kind')=='own_registered_bootstrap_source'
    def check_native_phase(action,token,value):
        if not native_source:return
        rows=[row for row in natives.values() if row['intent']['phase']==token]
        operations=[row['intent']['operation'] for row in rows]
        expected={
            'preflight':(['interpreter_probe'],['interpreter_probe','source_git_identity','source_git_status']),
            'environment_python_executable':(['interpreter_probe'] if value else [],),
            'create_environment':(['environment_creation','interpreter_probe'],),
            'install_dependencies':(['interpreter_probe','dependency_install','dependency_versions'],),
            'ensure_policy_tool':(['policy_tool_install'],),
            'verify_policy_tool_version':(['policy_tool_version'],),
            'check_dependency_consistency':(['dependency_consistency'],),
            'render_ready_message':([],)}[action]
        if operations not in expected or any(row['finished'] is None or row['finished']['exit_code']!=0 for row in rows):
            raise ValueError('bootstrap_successful_phase_native_evidence_mismatch')
    for index,payload in enumerate(payloads[1:],1):
        kind = payload.get('kind')
        if finished is not None:
            raise ValueError('bootstrap_events_after_terminal')
        if kind == 'phase-intent':
            if (set(payload) != {'kind','phase','action'} or phase is not None or failed
                    or type(payload['phase']) is not int or payload['phase'] != phases
                    or type(payload['action']) is not str or payload['action'] not in ACTIONS):
                raise ValueError('bootstrap_record_phase_intent_invalid')
            phase=payload['phase'];action=payload['action'];phases+=1
        elif kind == 'phase-result':
            if phase is None or type(payload.get('phase')) is not int or payload['phase'] != phase:
                raise ValueError('bootstrap_record_phase_result_unmatched')
            if payload.get('state') == 'returned':
                if set(payload) != {'kind','phase','state','value'} or type(payload['value']) not in (bool,type(None)):
                    raise ValueError('bootstrap_record_phase_value_invalid')
                check_native_phase(action,phase,payload['value'])
                observed.append({'action':action,'value':payload['value']})
            elif payload.get('state') == 'failed':
                code=payload.get('code')
                if set(payload) != {'kind','phase','state','code'} or type(code) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,99}',code):
                    raise ValueError('bootstrap_record_phase_failure_invalid')
                observed.append({'action':action,'failure':code});failed=True
            else:
                raise ValueError('bootstrap_record_phase_state_invalid')
            phase=None;action=None
        elif kind == 'native-intent':
            identity=payload.get('native_id');streams=payload.get('streams')
            command=payload.get('command');operation=payload.get('operation');cwd=payload.get('cwd')
            timeout=payload.get('timeout_seconds');limit=payload.get('stream_limit_bytes')
            if (set(payload)!={'kind','phase','native_id','operation','command','cwd','timeout_seconds','stream_limit_bytes','streams','OS_network_or_process_tree_isolation_attested'}
                    or type(payload.get('phase')) is not int
                    or type(operation) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,63}',operation)
                    or type(command) is not list or not 1<=len(command)<=128
                    or any(type(arg) is not str or '\0' in arg for arg in command)
                    or sum(len(arg.encode()) for arg in command)>65536
                    or not Path(command[0]).is_absolute()
                    or type(cwd) is not str or not Path(cwd).is_absolute() or '\0' in cwd
                    or type(timeout) not in (int,float) or not 0<timeout<=1800
                    or type(limit) is not int or not 0<limit<=4*1024*1024
                    or any(row['finished'] is None for row in natives.values())):
                raise ValueError('bootstrap_native_intent_types_or_overlap_invalid')
            if (phase is None or payload.get('phase') != phase
                    or type(identity) is not str or not re.fullmatch('native-[0-9]{4}',identity)
                    or identity in natives or type(streams) is not dict
                    or streams != {c:identity+'-'+c+'.bin' for c in ('stdout','stderr')}
                    or payload.get('OS_network_or_process_tree_isolation_attested') is not False):
                raise ValueError('bootstrap_native_intent_invalid')
            natives[identity]={'intent':payload,'started':None,'finished':None}
            expected_native_files.update(streams.values())
        elif kind == 'native-started':
            identity=payload.get('native_id');record=natives.get(identity)
            if (set(payload) != {'kind','phase','native_id','pid'} or record is None
                    or payload['phase'] != phase or record['intent']['phase'] != phase
                    or record['started'] is not None or type(payload['pid']) is not int or payload['pid']<=0):
                raise ValueError('bootstrap_native_start_unmatched')
            record['started']=payload
        elif kind == 'native-finished':
            identity=payload.get('native_id');record=natives.get(identity);outcome=payload.get('outcome')
            if (set(payload) != {'kind','phase','native_id','outcome'} or record is None
                    or phase is None or payload['phase'] != phase or record['intent']['phase'] != phase
                    or record['started'] is None or record['finished'] is not None or type(outcome) is not dict):
                raise ValueError('bootstrap_native_outcome_unmatched')
            intent=record['intent']
            if (outcome.get('native_id') != identity or outcome.get('command') != intent['command']
                    or outcome.get('cwd') != intent['cwd'] or outcome.get('timeout_seconds') != intent['timeout_seconds']
                    or outcome.get('stream_limit_bytes') != intent['stream_limit_bytes']
                    or outcome.get('terminal_result_observed') is not True
                    or type(outcome.get('exit_code')) is not int or not -128<=outcome['exit_code']<=255
                    or type(outcome.get('wall_seconds')) not in (int,float) or not 0<=outcome['wall_seconds']<=intent['timeout_seconds']+5
                    or not process_groups.consistent(outcome) or set(outcome.get('streams',{})) != {'stdout','stderr'}):
                raise ValueError('bootstrap_native_outcome_binding_changed')
            for channel,row in outcome['streams'].items():
                expected='native/'+intent['streams'][channel]
                if (type(row) is not dict or set(row) != {'path','bytes','sha256'} or row['path'] != expected
                        or type(row['bytes']) is not int or not 0<=row['bytes']<=intent['stream_limit_bytes']):
                    raise ValueError('bootstrap_native_stream_binding_invalid')
                captured=read_private(root/expected,intent['stream_limit_bytes'])
                if len(captured)!=row['bytes'] or hashlib.sha256(captured).hexdigest()!=row['sha256']:
                    raise ValueError('bootstrap_native_stream_bytes_changed')
            record['finished']=outcome
        elif kind == 'finished':
            if (set(payload) != {'kind','state','result'} or index != len(payloads)-1
                    or payload['state'] not in ('complete','failed','incomplete')):
                raise ValueError('bootstrap_terminal_event_invalid')
            result_raw=read_private(root/'result.json')
            if payload['result'] != {'bytes':len(result_raw),'sha256':hashlib.sha256(result_raw).hexdigest()}:
                raise ValueError('bootstrap_terminal_bytes_changed')
            finished=document(result_raw)
            if finished.get('state') != payload['state'] or any(finished.get(k) is not False for k in AUTHORITY):
                raise ValueError('bootstrap_terminal_state_or_authority_changed')
        else:
            raise ValueError('bootstrap_unknown_event_kind')
    class Pending(Exception):
        pass
    class PrefixPorts(RecordedPorts):
        def perform(self,expected):
            if self.position==len(self.rows):
                if phase is not None and action!=expected:
                    raise ValueError('bootstrap_pending_phase_order_mismatch')
                raise Pending()
            return super().perform(expected)
    class Observer:
        def before(self,value):return value
        def after(self,*ignored):pass
        def failed(self,*ignored):pass
    ports=PrefixPorts(observed);decision='incomplete'
    try:
        derived=run(values['request'].get('profile'),ports,Observer())
        decision='complete'
    except Pending:
        pass
    except BootstrapFailure:
        decision='failed'
    ports.complete()
    pending_natives=[key for key,row in natives.items() if row['finished'] is None]
    if finished is not None:
        state=finished['state']
        if state in ('complete','failed') and (decision!=state or phase is not None or pending_natives):
            raise ValueError('bootstrap_terminal_decision_not_reproduced')
        if state=='complete' and (type(finished.get('operations')) is not int or finished['operations']!=derived.operations):
            raise ValueError('bootstrap_terminal_operation_count_changed')
    expected={'header.json','request.json','source.json','events.jsonl'}
    if (root/'result.json').exists():expected.add('result.json')
    if expected_native_files or (root/'native').exists():
        native=owned_directory(root/'native')
        actual={p.name for p in native.iterdir()}
        if not actual<=expected_native_files or any(p.is_symlink() or not p.is_file() for p in native.iterdir()):
            raise ValueError('bootstrap_native_file_membership_changed')
        expected.add('native')
    captured_inputs=values['source'].get('captured_inputs',{})
    if type(captured_inputs) is not dict or len(captured_inputs)>32:
        raise ValueError('bootstrap_captured_input_manifest_invalid')
    if captured_inputs:
        from pathlib import PurePosixPath
        directory=owned_directory(root/'inputs');wanted=set()
        for name,row in captured_inputs.items():
            path=PurePosixPath(name)
            if (type(name) is not str or str(path)!=name or path.is_absolute()
                    or '..' in path.parts or '.git' in path.parts or '\\' in name or ':' in name
                    or type(row) is not dict or set(row)!={'bytes','sha256'}
                    or type(row['bytes']) is not int or not 0<=row['bytes']<=MAX_METADATA):
                raise ValueError('bootstrap_captured_input_descriptor_invalid')
            raw=read_private(directory/name)
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
                raise ValueError('bootstrap_captured_input_bytes_changed')
            wanted.add(name)
        actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
        if actual!=wanted or any(p.is_symlink() for p in directory.rglob('*')):
            raise ValueError('bootstrap_captured_input_membership_changed')
        expected.add('inputs')
    if {p.name for p in root.iterdir()}!=expected:
        raise ValueError('bootstrap_record_file_membership_changed')
    return {'schema_version':1,'kind':'retained-environment-bootstrap-inspection',
            'operation_id':root.name,'profile':values['request'].get('profile'),
            'state':'pending_incomplete' if finished is None else 'retained_declared_environment_bootstrap_consistent',
            'declared_result':None if finished is None else finished['state'],
            'phase_observations':len(observed),'native_capture_outcomes_consistent':len(natives)-len(pending_natives),
            'incomplete_native_captures':pending_natives,'current_environment_rechecked':False,
            'current_process_liveness_checked':False,'retained_observations_only':True,**AUTHORITY}
