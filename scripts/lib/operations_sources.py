"""Decode retained operational inputs without reading files or running programs."""
import io
import json
from pathlib import PurePosixPath

import yaml

from lib.review_planning import bounded_contract_graph
from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL, relative


def text(raw):
    # Path.read_text() uses universal newlines. Keep the original JSON/YAML
    # errors by decoding the retained bytes, including an invalid first file.
    if not isinstance(raw, bytes) or len(raw) > MAX_FILE:
        raise ValueError('operations_source_file_budget')
    with io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8', newline=None) as stream:
        return stream.read()


class SourceLoader(yaml.SafeLoader):
    """SafeLoader semantics with finite composition and expanded alias limits."""
    def __init__(self, stream):
        super().__init__(stream)
        self.nodes = self.depth = self.aliases = 0

    def compose_node(self, parent, index):
        self.nodes += 1
        self.depth += 1
        try:
            if self.check_event(yaml.AliasEvent):
                self.aliases += 1
            if self.nodes > 100000 or self.depth > 64 or self.aliases > 4096:
                raise ValueError('operations_source_yaml_budget')
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1

    def construct_document(self, node):
        bounded_contract_graph(node)
        return super().construct_document(node)


def yaml_value(raw):
    return yaml.load(text(raw), Loader=SourceLoader)


def record_value(raw, name):
    return dict(json.loads(text(raw)), _source_file=name)


FILE_ERRORS = {'OSError': OSError, 'FileNotFoundError': FileNotFoundError,
               'PermissionError': PermissionError, 'NotADirectoryError': NotADirectoryError,
               'IsADirectoryError': IsADirectoryError, 'ValueError': ValueError}


def record_values(value, blob, *, directory):
    """Recompute ordered reads and the exact first parse/read failure.

    A whole directory uses one journal outcome. Thousands of individual source
    files therefore do not consume thousands of intent/outcome events.
    """
    if (not isinstance(value, dict) or set(value) != {'members', 'reads', 'stopped'}
            or not isinstance(value['members'], list) or not isinstance(value['reads'], list)
            or len(value['members']) > MAX_FILES or len(value['reads']) > MAX_FILES):
        raise ValueError('operations_source_group_invalid')
    names = value['members']
    prefix = 'status/' + directory + '/'
    for name in names:
        relative(name)
        if not name.startswith(prefix) or not name.endswith('.json'):
            raise ValueError('operations_source_member_changed')
    if names != sorted(set(names), key=PurePosixPath):
        raise ValueError('operations_source_members_not_ordered_unique')
    reads = value['reads']
    stopped = value['stopped']
    if stopped is not None and (not isinstance(stopped, dict) or set(stopped) != {'kind', 'name', 'exception', 'message'}):
        raise ValueError('operations_source_stop_invalid')
    if stopped is None and len(reads) != len(names):
        raise ValueError('operations_source_group_incomplete')
    if stopped is not None:
        count = len(reads)
        offset = count - 1 if stopped['kind'] == 'decode' else count
        if stopped['kind'] not in ('decode', 'read') or not 0 <= offset < len(names) or stopped['name'] != names[offset]:
            raise ValueError('operations_source_stop_order_changed')
    result = []
    total = 0
    for index, row in enumerate(reads):
        if (index >= len(names) or not isinstance(row, dict) or set(row) != {'name', 'body'}
                or row['name'] != names[index]):
            raise ValueError('operations_source_read_order_changed')
        raw = blob(row['body'])
        total += len(raw)
        if total > MAX_TOTAL:
            raise ValueError('operations_source_group_byte_budget')
        try:
            item = record_value(raw, row['name'])
        except (ValueError, TypeError) as error:
            if (stopped is None or stopped['kind'] != 'decode' or index != len(reads) - 1
                    or stopped['exception'] != type(error).__name__ or stopped['message'] != str(error)):
                raise ValueError('operations_source_decode_failure_changed') from None
            raise
        result.append(item)
    if stopped is not None:
        if stopped['kind'] != 'read' or stopped['exception'] not in FILE_ERRORS or not isinstance(stopped['message'], str):
            raise ValueError('operations_source_failure_changed')
        raise FILE_ERRORS[stopped['exception']](stopped['message'])
    return result
