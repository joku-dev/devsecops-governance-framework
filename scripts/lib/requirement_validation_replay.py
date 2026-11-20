"""Replay exact source and read-only history observations without native access."""
import stat
from lib.operations_sources import text
from referencing.exceptions import NoSuchResource
from lib.validation_files import MAX_FILE, MAX_TOTAL, relative

MAX_CALLS = 20000
class IntegrityError(ValueError):
    pass


ERRORS = {'ValueError': ValueError, 'OSError': OSError, 'FileNotFoundError': FileNotFoundError,
          'PermissionError': PermissionError, 'NotADirectoryError': NotADirectoryError,
          'IsADirectoryError': IsADirectoryError}


def decode_history(action, rows, blob):
    last = rows[-1]
    if action == 'existed':
        if last['completed_successfully']: blob(last['stdout'])
        return last['completed_successfully']
    if not last['completed_successfully']: return None if action == 'previous' else set()
    value = text(blob(last['stdout']))
    return value if action == 'previous' else set(value.splitlines())


def stat_value(value):
    if value is None: return None
    if (type(value) is not dict or set(value) != {'kind', 'bytes', 'mode'}
            or value['kind'] not in ('file', 'directory', 'symlink', 'other')
            or type(value['bytes']) is not int or value['bytes'] < 0
            or type(value['mode']) is not int or not 0 <= value['mode'] <= 0o177777):
        raise IntegrityError('requirement_retained_stat_invalid')
    expected=('file' if stat.S_ISREG(value['mode']) else 'directory' if stat.S_ISDIR(value['mode']) else 'symlink' if stat.S_ISLNK(value['mode']) else 'other')
    if value['kind'] != expected:
        raise IntegrityError('requirement_retained_stat_kind_changed')
    return value


class Replay:
    def __init__(self, trace, history_events, blob, resources=()):
        if not isinstance(trace, list) or len(trace) > MAX_CALLS:
            raise IntegrityError('requirement_retained_trace_budget')
        self.resources={row['uri']:row['label'] for row in resources}
        self.trace, self.history_events = trace, history_events
        def guarded_blob(ref):
            try: return blob(ref)
            except (ValueError,OSError,KeyError,TypeError) as error: raise IntegrityError('requirement_retained_blob_invalid') from error
        self.blob = guarded_blob
        self.position = self.total = 0
        self.used = set()
        self.observed = {}

    def next(self, request):
        if self.position >= len(self.trace): raise IntegrityError('requirement_retained_trace_short')
        row = self.trace[self.position]; self.position += 1
        if (not isinstance(row, dict) or any(row.get(k) != v for k, v in request.items())
                or not set(row) <= set(request) | {'failure', 'value', 'operation'}):
            raise IntegrityError('requirement_retained_trace_order_changed')
        return row

    def source(self, action, path):
        if path and action!='resource': relative(path)
        request = {'kind': 'source', 'action': action, 'path': path}
        row = self.next(request)
        if 'failure' in row:
            if set(row) != set(request) | {'failure'}: raise IntegrityError('requirement_retained_failure_invalid')
            error = row['failure']
            if (type(error) is not dict or set(error) != {'type', 'message', 'errno', 'strerror', 'filename'}
                    or error['type'] not in ERRORS or type(error['message']) is not str or len(error['message']) > 65536):
                raise IntegrityError('requirement_retained_failure_invalid')
            if (error['errno'] is not None and type(error['errno']) is not int
                    or error['strerror'] is not None and type(error['strerror']) is not str
                    or error['filename'] is not None and (type(error['filename']) is not str or len(error['filename'])>16384)):
                raise IntegrityError('requirement_retained_failure_invalid')
            if error['type'] == 'ValueError':
                if any(error[k] is not None for k in ('errno','strerror','filename')):
                    raise IntegrityError('requirement_retained_failure_invalid')
                raise ValueError(error['message'])
            if error['errno'] is None: raise ERRORS[error['type']](error['message'])
            failure = ERRORS[error['type']](error['errno'], error['strerror'], error['filename'])
            if str(failure) != error['message']: raise IntegrityError('requirement_retained_failure_changed')
            raise failure
        if set(row) != set(request) | {'value'}: raise IntegrityError('requirement_retained_value_invalid')
        value = row['value']
        key = (action, path)
        if key in self.observed and self.observed[key] != value: raise IntegrityError('requirement_retained_source_drift')
        self.observed[key] = value
        if action in ('read','resource'):
            if type(value) is not dict or set(value) != {'blob'}: raise IntegrityError('requirement_retained_read_invalid')
            raw = self.blob(value['blob']); self.total += len(raw)
            if len(raw) > MAX_FILE or self.total > MAX_TOTAL: raise IntegrityError('requirement_retained_read_budget')
            return raw
        if action == 'stat': return stat_value(value)
        if action != 'entries' or not isinstance(value, list) or len(value) > MAX_CALLS:
            raise IntegrityError('requirement_retained_entries_invalid')
        names = set()
        for child in value:
            if type(child) is not dict or set(child) != {'name', 'kind', 'bytes', 'mode'}: raise IntegrityError('requirement_retained_entries_invalid')
            name = child['name']
            if type(name) is not str or '/' in name or name in names: raise IntegrityError('requirement_retained_entries_invalid')
            relative(name); names.add(name); stat_value({k:v for k,v in child.items() if k != 'name'})
        return value

    def stat(self, path): return self.source('stat', path)
    def read(self, path): return self.source('read', path)
    def entries(self, path): return self.source('entries', path)
    def resource(self, uri):
        if uri not in self.resources: raise NoSuchResource(ref=uri)
        return self.source('resource',uri)

    def history(self, action, base, path=None):
        request = {'kind': 'history', 'action': action, 'base': base, 'path': path}
        row = self.next(request)
        if set(row) != set(request) | {'operation'} or type(row['operation']) is not int or row['operation'] in self.used:
            raise IntegrityError('requirement_retained_history_identity_invalid')
        self.used.add(row['operation'])
        value = self.history_events.get(row['operation'])
        if not value or value['request'] != {k:v for k,v in request.items() if k != 'kind'}:
            raise IntegrityError('requirement_retained_history_request_changed')
        return decode_history(action, value['rows'], self.blob)

    def previous(self, base, path): return self.history('previous', base, path)
    def existed(self, base, path): return self.history('existed', base, path)
    def changed(self, base): return self.history('changed', base)

    def finish(self):
        if self.position != len(self.trace) or self.used != set(self.history_events):
            raise IntegrityError('requirement_retained_trace_unused')
