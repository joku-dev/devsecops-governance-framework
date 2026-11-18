"""Finite, individually journaled pinned OPA version and repository checks."""
import base64
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import time
from types import SimpleNamespace

from lib.providers import process_groups
from lib.providers.attestation_verification import executable
from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL, relative

MAX_STREAM = 65536


class RepositoryOPA:
    def __init__(self, tool, *, approved_hashes, workarea, on_intent, on_start, on_finish, timeout=60):
        if not all(callable(callback) for callback in (on_intent, on_start, on_finish)):
            raise ValueError('repository_native_journal_callbacks_required')
        if (type(approved_hashes) is not frozenset or not approved_hashes
                or any(type(value) is not str or re.fullmatch('[a-f0-9]{64}', value) is None for value in approved_hashes)):
            raise ValueError('explicit_repository_opa_hashes_required')
        self.tool = executable(tool)
        if self.tool[1] not in approved_hashes:
            raise ValueError('repository_opa_checksum_mismatch')
        workarea = Path(workarea)
        if workarea.is_symlink() or not workarea.is_dir() or workarea.stat().st_mode & 0o077:
            raise ValueError('private_repository_opa_workarea_required')
        if type(timeout) not in (int, float) or not 0 < timeout <= 60:
            raise ValueError('invalid_repository_opa_timeout')
        self.workarea = workarea.resolve()
        metadata = self.workarea.stat()
        self.workarea_identity = (metadata.st_dev, metadata.st_ino, metadata.st_mode)
        self.policy_roots = set()
        self.on_intent, self.on_start, self.on_finish = on_intent, on_start, on_finish
        self.timeout = timeout
        self.observations = []
        result = self.observe([self.tool[0], 'version'], {'operation': 'version', 'version': '1.18.2'})
        if result.returncode or re.search(r'^Version:\s*1\.18\.2\s*$', result.stdout, re.M) is None:
            raise ValueError('repository_opa_version_mismatch')

    def check(self, files, *, directory_present):
        self.check_workarea()
        if type(files) is not dict or type(directory_present) is not bool or len(files) > MAX_FILES:
            raise ValueError('invalid_repository_policy_inventory')
        files = dict(files)
        total = 0
        for name, raw in files.items():
            relative(name)
            if not name.startswith('policies/opa/') or len(Path(name).parts) > 100:
                raise ValueError('repository_policy_outside_check_scope')
            if type(raw) is not bytes or len(raw) > MAX_FILE:
                raise ValueError('repository_policy_file_budget')
            total += len(raw)
        if total > MAX_TOTAL or files and not directory_present:
            raise ValueError('invalid_repository_policy_inventory')
        request = {'operation': 'check', 'directory_present': directory_present,
                   'file_order': list(files),
                   'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                             for name, raw in files.items()}}
        with tempfile.TemporaryDirectory(prefix='repository-opa-', dir=self.workarea) as temporary:
            root = Path(temporary)
            policy_root = root / 'policies/opa'
            if directory_present:
                policy_root.mkdir(mode=0o700, parents=True)
            for name, raw in files.items():
                path = root / name
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
            self.policy_roots.add(str(policy_root))
            try:
                return self.observe([self.tool[0], 'check', str(policy_root)], request)
            finally:
                self.policy_roots.remove(str(policy_root))

    def check_workarea(self):
        metadata = self.workarea.lstat()
        if (metadata.st_dev, metadata.st_ino, metadata.st_mode) != self.workarea_identity:
            raise ValueError('repository_opa_workarea_identity_changed')

    def observe(self, argv, request):
        operation = request.get('operation') if type(request) is dict else None
        if operation == 'version':
            if argv != [self.tool[0], 'version'] or request != {'operation': 'version', 'version': '1.18.2'}:
                raise ValueError('unsupported_repository_opa_request')
        elif operation == 'check':
            if (type(argv) is not list or len(argv) != 3 or argv[:2] != [self.tool[0], 'check']
                    or set(request) != {'operation', 'directory_present', 'file_order', 'files'}):
                raise ValueError('unsupported_repository_opa_request')
            try:
                parts = Path(argv[2]).relative_to(self.workarea).parts
            except ValueError:
                raise ValueError('repository_opa_directory_outside_workarea') from None
            if len(parts) != 3 or not parts[0].startswith('repository-opa-') or parts[1:] != ('policies', 'opa'):
                raise ValueError('unsupported_repository_opa_directory')
            if argv[2] not in self.policy_roots:
                raise ValueError('repository_opa_directory_not_owned_by_operation')
        else:
            raise ValueError('unsupported_repository_opa_request')
        if executable(self.tool[0]) != self.tool:
            raise ValueError('repository_opa_tool_changed')
        self.check_workarea()
        row = {'request': request, 'argv': argv, 'tool_path': self.tool[0], 'tool_sha256': self.tool[1],
               'process_started': False, 'returncode': None, 'error_type': None,
               'timed_out': False, 'output_truncated': False}
        self.on_intent(deepcopy(row))
        self.observations.append(row)
        process = None
        streams = {'stdout': bytearray(), 'stderr': bytearray()}
        try:
            self.check_workarea()
            process = subprocess.Popen(argv, cwd=self.workarea, env={'LANG': 'C.UTF-8', 'PATH': ''},
                                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True, umask=0o077)
            row['process_started'] = True
            self.on_start(deepcopy(row))
            deadline = time.monotonic() + self.timeout
            with selectors.DefaultSelector() as selector:
                for name in streams:
                    stream = getattr(process, name)
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        row['timed_out'] = True
                        raise TimeoutError('repository_opa_timeout')
                    for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                        raw = os.read(key.fd, MAX_STREAM)
                        if not raw:
                            selector.unregister(key.fileobj)
                            continue
                        remaining = MAX_STREAM - len(streams[key.data])
                        streams[key.data].extend(raw[:remaining])
                        if len(raw) > remaining:
                            row['output_truncated'] = True
                            raise ValueError('repository_opa_output_budget')
            try:
                process.wait(timeout=max(.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                row['timed_out'] = True
                raise TimeoutError('repository_opa_timeout') from None
            row['returncode'] = process.returncode
            if executable(self.tool[0]) != self.tool:
                raise ValueError('repository_opa_tool_changed')
            self.check_workarea()
        except BaseException as error:
            row['error_type'] = type(error).__name__
            raise
        finally:
            try:
                if process is not None:
                    try:
                        process_groups.stop(process)
                    finally:
                        for name in ('stdin', 'stdout', 'stderr'):
                            stream = getattr(process, name)
                            if stream is not None:
                                stream.close()
            except BaseException as error:
                row['error_type'] = type(error).__name__
                raise
            finally:
                row.update(process_groups.observations(process))
                row.update({name + '_base64': base64.b64encode(bytes(raw)).decode('ascii') for name, raw in streams.items()})
                self.on_finish(deepcopy(row))
        return SimpleNamespace(returncode=row['returncode'], **{
            name: bytes(raw).decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
            for name, raw in streams.items()})
