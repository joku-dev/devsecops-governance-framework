"""Immutable private inputs/results and durable pending/completion records.

Reading a completed record verifies storage consistency only. The separate
engine replay must verify observations and effects before calling it replay
consistent. Interrupted operations are retained and never resumed.
"""
import base64
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import stat

from lib import repository_capture as capture
from lib import repository_operation as contract
from lib.ci_bundle_storage import reserve
from lib.providers.repository_journal import RepositoryJournal, read_journal, encoded, identity
from lib.providers.validation_worktree import signature
from lib.result_bytes import strict_json

MAX_REPLAY = 64 * 1024**2
RESERVED = {'operation-start', 'inputs-retained', 'operation-finished'}


def descriptor(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def output_descriptors(files):
    if (type(files) is not dict or len(files) > capture.MAX_FILES
            or any(type(raw) is not bytes or len(raw) > capture.MAX_FILE for raw in files.values())
            or sum(map(len, files.values())) > capture.MAX_TOTAL):
        raise ValueError('repository_operation_output_budget')
    for name in files:
        capture.path_name(name)
        if capture.private_name(name):raise ValueError('repository_operation_private_output')
    return {name: descriptor(raw) for name, raw in files.items()}


def read_file(parent, name, maximum):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_mode & 0o077 or before.st_size > maximum):
            raise ValueError('private_bounded_repository_operation_file_required')
        blocks, size = [], 0
        while raw := os.read(fd, min(65536, maximum + 1 - size)):
            blocks.append(raw); size += len(raw)
            if size > maximum:raise ValueError('repository_operation_file_budget')
        if (signature(before) != signature(os.fstat(fd))
                or signature(before) != signature(os.stat(name, dir_fd=parent, follow_symlinks=False))):
            raise ValueError('repository_operation_file_changed_during_read')
        return b''.join(blocks)
    finally:
        os.close(fd)


class RepositoryOperation:
    def __init__(self, root, header):
        self.header = deepcopy(contract.binding(header))
        self.journal = RepositoryJournal(root, self.header)
        self.failed, self.finished, self.inputs = False, False, None
        self.blobs, self.total = set(), 0
        self.content = None

    def __enter__(self):return self

    def __exit__(self, *args):self.close()

    def close(self):
        if self.content is not None:
            os.close(self.content); self.content = None
        self.journal.close()

    def check(self):
        if self.failed or self.finished:raise ValueError('repository_operation_not_appendable')
        self.journal.check()
        if self.content is not None:
            if (identity(os.fstat(self.content)) != self.content_identity
                    or identity(os.stat('content', dir_fd=self.journal.directory, follow_symlinks=False))
                       != self.content_identity):
                raise ValueError('repository_operation_content_directory_changed')

    def append(self, row):
        self.check()
        if type(row) is not dict or row.get('kind') in RESERVED:
            raise ValueError('repository_operation_reserved_event')
        try:return self.journal.append(row)
        except BaseException:
            self.failed = True; raise

    def write(self, parent, name, raw, maximum):
        self.check()
        if type(raw) is not bytes or len(raw) > maximum:
            raise ValueError('repository_operation_file_budget')
        reserve(self.journal.root, len(raw))
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            remaining = memoryview(raw)
            while remaining:
                count = os.write(fd, remaining)
                if count <= 0:raise OSError('repository_operation_short_write')
                remaining = remaining[count:]
            os.fsync(fd)
        finally:os.close(fd)
        os.fsync(parent)
        self.check()

    def blob(self, raw):
        name = descriptor(raw)['sha256']
        if name not in self.blobs:
            if self.total + len(raw) > 2 * capture.MAX_TOTAL or len(self.blobs) >= 2 * capture.MAX_FILES:
                raise ValueError('repository_operation_content_budget')
            self.write(self.content, name, raw, capture.MAX_FILE)
            self.blobs.add(name); self.total += len(raw)

    def retain_inputs(self, manifest, files, commit):
        self.check()
        if self.inputs is not None:raise ValueError('repository_operation_inputs_already_retained')
        capture.check_capture(manifest, files, commit, revision=self.header['source_revision'], tree=self.header['source_tree'])
        if (manifest['profile'] != self.header['profile'] or manifest['source_root'] != self.header['source_root']):
            raise ValueError('repository_operation_input_binding_differs')
        raw = encoded({'manifest': manifest, 'commit_base64': base64.b64encode(commit).decode('ascii')}) + b'\n'
        try:
            os.mkdir('content', mode=0o700, dir_fd=self.journal.directory)
            os.fsync(self.journal.directory)
            self.content = os.open('content', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.journal.directory)
            self.content_identity = identity(os.fstat(self.content))
            for value in files.values():self.blob(value)
            self.write(self.journal.directory, 'capture.json', raw, 2 * capture.MAX_MANIFEST)
            self.journal.append({'kind': 'inputs-retained', 'capture': descriptor(raw)})
            self.inputs = dict(files)
        except BaseException:
            self.failed = True; raise

    def finish(self, result, files, replay):
        self.check()
        contract.outcome(result)
        if self.inputs is None or type(replay) is not dict:
            raise ValueError('repository_operation_inputs_and_replay_required')
        output = output_descriptors(files)
        if (not self.inputs.keys() <= files.keys()
                or any(not name.startswith('generated/') and files[name] != raw for name, raw in self.inputs.items())
                or any(not name.startswith('generated/') for name in files.keys() - self.inputs.keys())):
            raise ValueError('repository_operation_non_generated_output_changed')
        raw = encoded({'result': result, 'output_files': output, 'replay': replay}) + b'\n'
        try:
            for value in files.values():self.blob(value)
            self.write(self.journal.directory, 'replay.json', raw, MAX_REPLAY)
            self.journal.append({'kind': 'operation-finished', 'execution': result['execution'], 'replay': descriptor(raw)})
            self.finished = True
        except BaseException:
            self.failed = True; raise


def load_operation(root, header):
    """Load only this node/runtime/source; never access or execute source paths."""
    contract.binding(header)
    rows = read_journal(root, expected_header=header)
    payloads = [row['payload'] for row in rows]
    terminal = [index for index, row in enumerate(payloads) if row.get('kind') == 'operation-finished']
    result = {'binding': deepcopy(header), 'journal': rows, 'state': 'pending_incomplete'}
    if not terminal:return result
    if terminal != [len(rows) - 1]:raise ValueError('repository_operation_terminal_order_changed')
    retained = [row for row in payloads if row.get('kind') == 'inputs-retained']
    if (len(retained) != 1 or set(retained[0]) != {'kind', 'capture'}
            or set(payloads[-1]) != {'kind', 'execution', 'replay'}):
        raise ValueError('repository_operation_completion_contract_changed')
    root = Path(root)
    parent = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    content = None
    try:
        before = os.fstat(parent)
        if before.st_mode & 0o077:raise ValueError('private_repository_operation_required')
        if set(os.listdir(parent)) != {'content', 'capture.json', 'replay.json', 'events.jsonl'}:
            raise ValueError('repository_operation_membership_changed')
        content = os.open('content', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        content_before = os.fstat(content)
        if content_before.st_mode & 0o077:raise ValueError('private_repository_operation_content_required')
        raw = read_file(parent, 'capture.json', 2 * capture.MAX_MANIFEST)
        if encoded(descriptor(raw)) != encoded(retained[0]['capture']):
            raise ValueError('repository_operation_capture_digest_changed')
        captured = strict_json(raw)
        if set(captured) != {'manifest', 'commit_base64'} or type(captured['commit_base64']) is not str:
            raise ValueError('repository_operation_capture_contract_changed')
        try:commit = base64.b64decode(captured['commit_base64'], validate=True)
        except ValueError:raise ValueError('repository_operation_commit_bytes_changed') from None
        if base64.b64encode(commit).decode('ascii') != captured['commit_base64']:
            raise ValueError('repository_operation_commit_bytes_changed')
        raw = read_file(parent, 'replay.json', MAX_REPLAY)
        if encoded(descriptor(raw)) != encoded(payloads[-1]['replay']):
            raise ValueError('repository_operation_replay_digest_changed')
        replay = strict_json(raw)
        if set(replay) != {'result', 'output_files', 'replay'} or type(replay['replay']) is not dict:
            raise ValueError('repository_operation_replay_contract_changed')
        contract.outcome(replay['result'])
        if payloads[-1]['execution'] != replay['result']['execution']:
            raise ValueError('repository_operation_execution_changed')
        manifest = captured['manifest']
        if type(manifest) is not dict or type(manifest.get('files')) is not dict:
            raise ValueError('repository_operation_capture_contract_changed')
        names = set()
        cache = {}
        def materialize(expected):
            if type(expected) is not dict or len(expected) > capture.MAX_FILES:
                raise ValueError('repository_operation_content_budget')
            files = {}
            for name, value in expected.items():
                capture.path_name(name)
                if (type(value) is not dict or type(value.get('sha256')) is not str
                        or re.fullmatch('[a-f0-9]{64}', value['sha256']) is None
                        or type(value.get('bytes')) is not int or not 0 <= value['bytes'] <= capture.MAX_FILE):
                    raise ValueError('repository_operation_content_descriptor_required')
                digest = value['sha256']; names.add(digest)
                if digest not in cache:
                    cache[digest] = read_file(content, digest, capture.MAX_FILE)
                    if sum(map(len, cache.values())) > 2 * capture.MAX_TOTAL:
                        raise ValueError('repository_operation_content_budget')
                files[name] = cache[digest]
                if descriptor(files[name]) != {key: value[key] for key in ('sha256', 'bytes')}:
                    raise ValueError('repository_operation_content_bytes_changed')
            return files
        inputs = materialize(manifest['files']); outputs = materialize(replay['output_files'])
        capture.check_capture(manifest, inputs, commit, revision=header['source_revision'], tree=header['source_tree'])
        if (manifest['profile'] != header['profile'] or manifest['source_root'] != header['source_root']
                or output_descriptors(outputs) != replay['output_files']
                or not inputs.keys() <= outputs.keys()
                or any(not name.startswith('generated/') and outputs[name] != raw for name, raw in inputs.items())
                or any(not name.startswith('generated/') for name in outputs.keys() - inputs.keys())):
            raise ValueError('repository_operation_input_or_output_binding_changed')
        if (set(os.listdir(content)) != names or signature(before) != signature(os.fstat(parent))
                or signature(before) != signature(os.stat(root, follow_symlinks=False))
                or signature(content_before) != signature(os.fstat(content))
                or signature(content_before) != signature(os.stat('content', dir_fd=parent, follow_symlinks=False))
                or read_journal(root, expected_header=header) != rows):
            raise ValueError('repository_operation_changed_during_read')
        result.update(state='recorded_' + replay['result']['execution'] + '_replay_unverified',
            manifest=manifest, commit=commit, inputs=inputs, outputs=outputs,
            outcome=replay['result'], replay=replay['replay'])
        return result
    finally:
        if content is not None:os.close(content)
        os.close(parent)
