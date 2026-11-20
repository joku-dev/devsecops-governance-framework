"""Complete ordered export pre/postimage replay without current export access."""
from pathlib import PurePosixPath

from lib.operations_execution import FILES


class ReplayOutput:
    def __init__(self, calls, label):
        self.calls = calls
        self.label = label
        self.files = {}

    def snapshot(self, value):
        if not isinstance(value, dict) or type(value.get('exists')) is not bool:
            raise ValueError('operations_export_snapshot_changed')
        if value['exists']:
            if set(value) != {'exists', 'content', 'mode'} or type(value['mode']) is not int or not 0 <= value['mode'] <= 0o7777:
                raise ValueError('operations_export_snapshot_changed')
            self.calls.blob(value['content'])
        elif set(value) != {'exists'}:
            raise ValueError('operations_export_snapshot_changed')

    def mkdir(self):
        return self.calls.call('output_mkdir', {})

    def write(self, name, raw):
        if name not in FILES:
            raise ValueError('operations_export_name_changed')
        if self.calls.peek().get('action') == 'output_prepare':
            return self.calls.call('output_prepare', {'name': name})
        before = self.calls.take()
        if set(before) != {'kind', 'name', 'snapshot', 'payload'} or before.get('kind') != 'export-before' or before['name'] != name:
            raise ValueError('operations_export_before_changed')
        self.snapshot(before['snapshot'])
        if self.calls.blob(before['payload']) != raw:
            raise ValueError('operations_export_requested_bytes_changed')
        success = False
        try:
            result = self.calls.call('output_write', {'name': name, 'payload': before['payload']})
            if result != str(PurePosixPath(self.label) / name):
                raise ValueError('operations_export_result_path_changed')
            success = True
            return result
        finally:
            after = self.calls.take()
            if set(after) != {'kind', 'name', 'snapshot'} or after.get('kind') != 'export-after' or after['name'] != name:
                raise ValueError('operations_export_after_changed')
            self.snapshot(after['snapshot'])
            self.files[name] = after['snapshot']
            if success and (after['snapshot']['exists'] is not True or self.calls.blob(after['snapshot']['content']) != raw):
                raise ValueError('operations_export_success_bytes_changed')
