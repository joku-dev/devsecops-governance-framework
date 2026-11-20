"""Closed renderer file order and whole no-native input/output reconstruction."""
import hashlib
import json
from pathlib import PurePosixPath
from lib.workbook_import_io import ReplayIO as FileReplay, path_spec
from lib.requirement_validation_replay import IntegrityError
from lib.validation_files import MAX_FILE,MAX_TOTAL

class Gate:

    def __init__(self, root):
        path_spec({'path': root, 'label': root})
        self.root = PurePosixPath(root) / 'generated/documents'
        self.phase = 'mkdir'
        self.parent = self.md = self.html = self.docx = self.program = None

    def output(self, kind, path, label):
        path_spec({'path': path, 'label': label})
        selected = PurePosixPath(path)
        if path != label or not selected.is_relative_to(self.root):
            raise IntegrityError('document_output_scope_changed')
        if kind == 'mkdir':
            if self.phase != 'mkdir':
                raise IntegrityError('document_output_order_changed')
            self.parent = selected
            self.phase = 'markdown'
            return
        if self.phase == 'markdown':
            if selected.parent != self.parent or not path.endswith('.rendered.md'):
                raise IntegrityError('document_markdown_selection_changed')
            stem = path[:-len('.rendered.md')]
            self.md, self.html, self.docx = (path, stem + '.html', stem + '.docx')
            self.phase = 'html'
        elif self.phase == 'html':
            if path != self.html:
                raise IntegrityError('document_html_selection_changed')
            self.phase = 'which'
        else:
            raise IntegrityError('document_output_order_changed')

    def which(self, name):
        if name != 'pandoc' or self.phase != 'which':
            raise IntegrityError('document_tool_lookup_order_changed')
        self.phase = 'finding'

    def found(self, path):
        if self.phase != 'finding' or (path is not None and (type(path) is not str or not path or len(path) > 8192 or ('\x00' in path))):
            raise IntegrityError('document_tool_lookup_result_changed')
        self.program = path
        self.phase = 'mkdir' if path is None else 'process'

    def run(self, arguments, options):
        if self.phase != 'process' or arguments != [self.program, self.md, '-o', self.docx] or options != {'capture_output': True, 'text': True, 'check': False}:
            raise IntegrityError('document_tool_command_changed')
        self.phase = 'mkdir'

def projected(snapshot, blob):
    if type(snapshot) is not dict or snapshot.get('kind') not in ('missing', 'directory', 'file'):
        raise IntegrityError('document_projected_state_changed')
    if snapshot['kind'] == 'file':
        if set(snapshot) != {'kind', 'content'}:
            raise IntegrityError('document_projected_file_changed')
        blob(snapshot['content'])
    elif set(snapshot) != {'kind'}:
        raise IntegrityError('document_projected_state_changed')
    return snapshot

def output_read_matches(raw, info, expected):
    return expected.get('kind') == 'file' and info is not None and (info['mode'] == expected['mode']) and (info['identity'] == expected['identity']) and (len(raw) == expected['content']['bytes']) and (hashlib.sha256(raw).hexdigest() == expected['content']['sha256'])

def known_read_failure(error, expected):
    if expected is None:
        return True
    kind = expected.get('kind')
    return kind == 'missing' and isinstance(error, FileNotFoundError) or (kind == 'directory' and isinstance(error, IsADirectoryError)) or (kind == 'unreachable' and isinstance(error, NotADirectoryError))

class ReplayIO(FileReplay):

    def __init__(self, events, blob, mode, root, native_context=None):
        super().__init__(events, blob, mode, root)
        self.gate = Gate(root)
        self.native_context=native_context
        self.projected = {}
        self.versions = {}
        self.read_versions = {}
        self.tool_files = {}

    def expected(self, kind, path, label):
        self.gate.output(kind, path, label)

    def read(self, path, label):
        spec = path_spec({'path': path, 'label': label})
        if self.mode == 'private-candidate' and path in self.projected:
            value = projected(self.projected[path], self.blob)
            ok, result = self.outcome('document-projected-read', {'selection': spec, 'projection': value}, 'bytes')
            if value['kind'] == 'file':
                raw = self.blob(value['content'])
                self.total+=len(raw)
                if len(raw)>MAX_FILE or self.total>MAX_TOTAL:raise IntegrityError('document_projected_input_byte_budget')
                if not ok or result != raw:
                    raise IntegrityError('document_projected_read_bytes_changed')
                return raw
            expected = 'FileNotFoundError' if value['kind'] == 'missing' else 'IsADirectoryError'
            import errno
            code = errno.ENOENT if expected == 'FileNotFoundError' else errno.EISDIR
            message = 'No such file or directory' if expected == 'FileNotFoundError' else 'Is a directory'
            failure = FileNotFoundError(code, message, label) if expected == 'FileNotFoundError' else IsADirectoryError(code, message, label)
            if ok or result['exception'] != expected or result['message'] != str(failure):
                raise IntegrityError('document_projected_read_error_changed')
            raise failure
        version = self.versions.get(path, 0)
        if version > self.read_versions.get(path, 0):
            self.reads.pop(path, None)
        self.selected = {'inputs': [spec]}
        try:
            raw = super().read(path, label)
        except OSError as error:
            if not known_read_failure(error, self.observed.get(path)):
                raise IntegrityError('document_input_after_own_export_changed') from error
            raise
        if path in self.observed and (not output_read_matches(raw, self.reads[path][1], self.observed[path])):
            raise IntegrityError('document_input_after_own_export_changed')
        self.read_versions[path] = version
        return raw

    def write_text(self, path, data, encoding, label):
        try:
            return super().write_text(path, data, encoding, label)
        finally:
            if path in self.files:
                self.projected[path] = {'kind': 'file', 'content': self.files[path]}
            if path in self.observed:
                self.versions[path] = self.versions.get(path, 0) + 1

    def outcome(self, action, arguments, encoding):
        if not action.startswith('document-tool-'):
            return FileReplay.outcome(self, action, arguments, encoding)
        token = self.position
        intent = self.row()
        if intent != {'kind': 'intent', 'operation': token, 'action': action, 'arguments': arguments}:
            raise IntegrityError('document_tool_intent_changed')
        value = self.row()
        if value.get('operation') != token:
            raise IntegrityError('document_tool_operation_changed')
        if value.get('kind') == 'failed':
            from lib.workbook_import_io import READ_ERRORS
            allowed = set(READ_ERRORS) | {'UnicodeDecodeError'}
            if set(value) != {'kind', 'operation', 'exception', 'message'} or value['exception'] not in allowed or type(value['message']) is not str or (len(value['message']) > 65536):
                raise IntegrityError('document_tool_failure_changed')
            return (False, value)
        if set(value) != {'kind', 'operation', 'encoding', 'value'} or value.get('kind') != 'returned' or value['encoding'] != 'json' or (encoding != 'json'):
            raise IntegrityError('document_tool_outcome_changed')
        return (True, parse_tool_json(self.blob(value['value'])))

    def which(self, name):
        from lib.requirement_review_output import RetainedOutputError
        self.gate.which(name)
        ok, value = self.outcome('document-tool-find', {'name': name}, 'json')
        if not ok:
            raise RetainedOutputError(value['exception'], value['message'])
        if type(value) is not dict or set(value) != {'path', 'identity', 'context'}:
            raise IntegrityError('document_tool_find_capture_changed')
        context=value['context']
        if context is not None:
            if type(context) is not dict or set(context)!={'cwd','PATH'} or context['PATH'] is not None and (type(context['PATH']) is not str or len(context['PATH'])>32768):raise IntegrityError('document_tool_lookup_context_changed')
            path_spec({'path':context['cwd'],'label':context['cwd']})
        if self.native_context is not None and context!={'cwd':self.native_context['cwd_label'],'PATH':self.native_context['tool_path']}:raise IntegrityError('document_tool_request_context_changed')
        if value['path'] is None:
            if value['identity'] is not None:
                raise IntegrityError('document_tool_absence_identity_changed')
        else:
            program_value(value['identity'], value['path'])
            if PurePosixPath(value['identity']['resolved']).is_relative_to(self.gate.root.parents[1]):
                raise IntegrityError('document_caller_program_forbidden')
        if getattr(self, 'lookup_seen', False) and value != self.lookup_value:
            raise IntegrityError('document_tool_discovery_changed')
        self.lookup_seen = True
        self.lookup_value = value
        self.gate.found(value['path'])
        self.program_identity = value['identity']
        return value['path']

    def mkdir(self, path, mode, parents, exist_ok, label):
        obstacle = projected_mkdir_obstacle(self.projected, path) if self.mode == 'private-candidate' else None
        if obstacle is None:
            return FileReplay.mkdir(self, path, mode, parents, exist_ok, label)
        self.expected('mkdir', path, label)
        if (mode, parents, exist_ok) != (511, True, True):
            raise IntegrityError('document_projected_mkdir_options_changed')
        name, kind = obstacle
        state = projected(self.projected[name], self.blob)
        arguments = {'path': path, 'label': label, 'mode': mode, 'parents': parents, 'exist_ok': exist_ok, 'obstacle': {'path': name, 'state': state}}
        ok, value = self.outcome('document-projected-mkdir', arguments, 'json')
        error = projected_mkdir_failure(kind, label)
        if ok or value['exception'] != kind or value['message'] != str(error):
            raise IntegrityError('document_projected_mkdir_failure_changed')
        raise error

    def run(self, arguments, **options):
        from types import SimpleNamespace
        import math
        from lib.requirement_review_output import snapshot, RetainedOutputError
        self.gate.run(arguments, options)
        gate = self.gate
        before = self.row()
        keys = {'kind', 'original_arguments', 'options', 'export_mode', 'cwd', 'SOURCE_DATE_EPOCH', 'program', 'timeout_seconds', 'stream_limit_bytes', 'encoding', 'anchor', 'source_preimage', 'logical_before', 'inputs', 'workspace', 'effective_arguments'}
        if set(before) != keys or before['kind'] != 'document-tool-before' or before['original_arguments'] != arguments or (before['options'] != options) or (before['export_mode'] != self.mode) or (before['program'] != self.program_identity) or (type(before['timeout_seconds']) not in (int, float)) or (not math.isfinite(before['timeout_seconds'])) or (not 0 < before['timeout_seconds'] <= 600) or (before['stream_limit_bytes'] != 256 * 1024) or (before['SOURCE_DATE_EPOCH'] is not None and (type(before['SOURCE_DATE_EPOCH']) is not str or len(before['SOURCE_DATE_EPOCH']) > 8192)) or (type(before['inputs']) is not dict) or (set(before['inputs']) != {gate.md, gate.html}):
            raise IntegrityError('document_tool_before_changed')
        path_spec({'path': before['cwd'], 'label': before['cwd']})
        if self.native_context is not None and (before['cwd']!=self.native_context['cwd_label'] or before['SOURCE_DATE_EPOCH']!=self.native_context['source_date_epoch'] or before['timeout_seconds']!=self.native_context['tool_timeout']):raise IntegrityError('document_tool_request_context_changed')
        if self.mode == 'selected-files':
            if before['workspace'] is not None or before['logical_before'] is not None or before['effective_arguments'] != arguments or (before['anchor']['path'] != str(PurePosixPath(gate.docx).parent)):
                raise IntegrityError('document_native_tool_scope_changed')
            self.anchor(before['anchor'], gate.docx)
            self.prior(gate.docx, before['source_preimage'])
            for name, value in before['inputs'].items():
                self.prior(name, value)
                if value.get('kind') != 'file' or value['content'] != self.files[name]:
                    raise IntegrityError('document_native_tool_input_changed')
        else:
            if before['anchor'] is not None:
                raise IntegrityError('document_private_tool_anchor_changed')
            workspace = before['workspace']
            path_spec({'path': workspace, 'label': workspace})
            effective = [arguments[0], str(PurePosixPath(workspace) / PurePosixPath(gate.md).name), '-o', str(PurePosixPath(workspace) / PurePosixPath(gate.docx).name)]
            if before['effective_arguments'] != effective:
                raise IntegrityError('document_private_tool_command_changed')
            for name, value in before['inputs'].items():
                projected(value, self.blob)
                if value != self.projected[name] or value.get('kind') != 'file' or value['content'] != self.files[name]:
                    raise IntegrityError('document_private_tool_input_changed')
            logical = projected(before['logical_before'], self.blob)
            if gate.docx in self.projected:
                if before['source_preimage'] is not None or logical != self.projected[gate.docx]:
                    raise IntegrityError('document_private_tool_prior_projection_changed')
            else:
                source = before['source_preimage']
                snapshot(source, self.blob)
                expected = {'kind': 'file', 'content': source['content']} if source['kind'] == 'file' else {'kind': 'directory'} if source['kind'] == 'directory' else {'kind': 'missing'}
                if logical != expected:
                    raise IntegrityError('document_private_tool_source_preimage_changed')
        ok, value = self.outcome('document-tool-run', {'arguments': arguments, 'options': options, 'export_mode': self.mode}, 'json')
        after = self.row()
        if set(after) != {'kind', 'output', 'snapshot', 'process'} or after['kind'] != 'document-tool-after' or after['output'] != gate.docx:
            raise IntegrityError('document_tool_after_changed')
        state = after['snapshot']
        snapshot(state, self.blob)
        if state['kind'] not in ('file', 'missing', 'directory'):
            raise IntegrityError('document_tool_output_changed')
        calculated, error = decode_process(after['process'], self.blob, before['encoding'])
        if ok:
            if error is not None or type(value) is not dict or set(value)!={'returncode','stdout','stderr'} or type(value['returncode']) is not int or any(type(value[k]) is not str for k in ('stdout','stderr')) or value != calculated:
                raise IntegrityError('document_tool_complete_result_changed')
        elif error is None or value['exception'] != error['type'] or value['message'] != error['message']:
            raise IntegrityError('document_tool_original_failure_changed')
        logical = {'kind': 'file', 'content': state['content']} if state['kind'] == 'file' else {'kind': state['kind']}
        self.projected[gate.docx] = logical
        if state['kind'] == 'file':
            self.tool_files[gate.docx] = state['content']
        else:
            self.tool_files.pop(gate.docx, None)
        if self.mode == 'selected-files':
            self.observed[gate.docx] = state
            self.touched[gate.docx] = state
            self.versions[gate.docx] = self.versions.get(gate.docx, 0) + 1
        if not ok:
            raise RetainedOutputError(error['type'], error['message'])
        return SimpleNamespace(**calculated)

def program_value(value, label):
    import re
    if type(value) is not dict or set(value) != {'label', 'resolved', 'sha256', 'bytes', 'mode', 'uid', 'identity'} or value['label'] != label or (type(label) is not str) or (not label) or (len(label) > 8192) or (type(value['sha256']) is not str) or (re.fullmatch('[a-f0-9]{64}', value['sha256']) is None) or (type(value['bytes']) is not int) or (not 0 < value['bytes'] <= 256 * 1024 ** 2) or (type(value['mode']) is not int) or (not 0 <= value['mode'] <= 511) or (value['mode'] & 18) or (not value['mode'] & 73) or (type(value['uid']) is not int) or (value['uid'] < 0) or (type(value['identity']) is not list) or (len(value['identity']) != 2) or any((type(x) is not int or x < 0 for x in value['identity'])):
        raise IntegrityError('document_program_identity_changed')
    path_spec({'path': value['resolved'], 'label': value['resolved']})
    return value

def projected_mkdir_obstacle(projected_states, path):
    for part in (str(p) for p in reversed(PurePosixPath(path).parents)):
        if projected_states.get(part, {}).get('kind') == 'file':
            return (part, 'NotADirectoryError')
    if projected_states.get(path, {}).get('kind') == 'file':
        return (path, 'FileExistsError')
    return None

def projected_mkdir_failure(kind, label):
    import errno
    return FileExistsError(errno.EEXIST, 'File exists', label) if kind == 'FileExistsError' else NotADirectoryError(errno.ENOTDIR, 'Not a directory', label)

def parse_tool_json(raw):

    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value:
                raise IntegrityError('document_tool_duplicate_key')
            value[key] = item
        return value

    def bad(_):
        raise IntegrityError('document_tool_nonfinite_number')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    except (ValueError, UnicodeError, TypeError) as error:
        raise IntegrityError('document_tool_return_invalid') from error

def decode_process(value, blob, encoding):
    expected = {'started', 'terminal_observed', 'returncode', 'stdout', 'stderr', 'start_error', 'timed_out', 'stream_budget_exceeded', 'OS_network_or_process_tree_isolation_attested'}
    if type(value) is not dict or set(value) != expected or any((type(value[k]) is not bool for k in ('started', 'terminal_observed', 'timed_out', 'stream_budget_exceeded'))) or (value['OS_network_or_process_tree_isolation_attested'] is not False) or value['timed_out'] or value['stream_budget_exceeded'] or (type(encoding) is not str) or (not encoding) or (len(encoding) > 128):
        raise IntegrityError('document_process_observation_changed')
    raw = {name: blob(value[name]) for name in ('stdout', 'stderr')}
    if any((len(part) > 256 * 1024 for part in raw.values())):
        raise IntegrityError('document_process_stream_budget')
    if not value['started']:
        error = value['start_error']
        from lib.workbook_import_io import READ_ERRORS
        if value['terminal_observed'] or value['returncode'] is not None or any(raw.values()) or (type(error) is not dict) or (set(error) != {'type', 'message'}) or (error['type'] not in READ_ERRORS) or (type(error['message']) is not str) or (len(error['message']) > 65536):
            raise IntegrityError('document_process_start_error_changed')
        return (None, error)
    if not value['terminal_observed'] or type(value['returncode']) is not int or value['start_error'] is not None:
        raise IntegrityError('document_process_terminal_changed')
    try:
        streams = {name: raw[name].decode(encoding).replace('\r\n', '\n').replace('\r', '\n') for name in ('stdout', 'stderr')}
    except UnicodeDecodeError as error:
        return (None, {'type': type(error).__name__, 'message': str(error)})
    except (LookupError, TypeError, ValueError) as error:
        raise IntegrityError('document_process_encoding_changed') from error
    return ({'returncode': value['returncode'], **streams}, None)
