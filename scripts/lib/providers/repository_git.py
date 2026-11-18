"""Finite read-only local Git calls with individual durable process hooks."""
import base64
from copy import deepcopy
import os
from pathlib import Path
import re
import selectors
import subprocess
import time

from lib.providers import process_groups
from lib.providers.attestation_verification import executable
from lib.repository_capture import MAX_MANIFEST
from lib.release_reference_facts import release_name, MAX_OBJECT
from lib.validation_files import MAX_FILE


class RepositoryGit:
    def __init__(self, source, tool, *, on_intent, on_start, on_finish, timeout=30):
        if not all(callable(callback) for callback in (on_intent, on_start, on_finish)):
            raise ValueError('repository_git_journal_callbacks_required')
        source = Path(source)
        if source.is_symlink() or not source.is_dir():
            raise ValueError('ordinary_repository_git_source_required')
        if type(timeout) not in (int, float) or not 0 < timeout <= 30:
            raise ValueError('invalid_repository_git_timeout')
        self.source = source.resolve(strict=True)
        metadata = self.source.stat()
        self.identity = (metadata.st_dev, metadata.st_ino, metadata.st_mode)
        self.tool = executable(tool)
        if Path(self.tool[0]).is_relative_to(self.source):
            raise ValueError('repository_git_tool_inside_inspected_source')
        self.on_intent, self.on_start, self.on_finish = on_intent, on_start, on_finish
        self.timeout, self.observations = timeout, []
        self.environment = {'LANG': 'C.UTF-8', 'PATH': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_COUNT': '0',
            'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false', 'GIT_NO_REPLACE_OBJECTS': '1',
            'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0', 'GIT_ATTR_NOSYSTEM': '1'}
        self.prefix = [self.tool[0], '--no-optional-locks', '--literal-pathspecs',
            '-c', 'safe.directory=' + str(self.source), '-c', 'core.hooksPath=/dev/null',
            '-c', 'core.fsmonitor=false', '-c', 'core.attributesFile=/dev/null', '-c', 'protocol.allow=never']
        self.version = self.read('--version').decode('utf-8').strip()
        if not self.version.startswith('git version '):
            raise ValueError('repository_git_version_response_required')

    def check_source(self):
        current = self.source.lstat()
        if (current.st_dev, current.st_ino, current.st_mode) != self.identity:
            raise ValueError('repository_git_source_identity_changed')
        if executable(self.tool[0]) != self.tool:
            raise ValueError('repository_git_tool_changed')

    @staticmethod
    def limit(arguments):
        if arguments in (('--version',), ('rev-parse', '--show-toplevel'), ('rev-parse', '--show-object-format'),
                          ('rev-parse', '--verify', 'HEAD^{commit}'), ('rev-parse', '--verify', 'HEAD^{tree}')):
            return 8192
        if (len(arguments) == 7 and arguments[:6] == ('ls-tree', '-r', '-t', '-l', '-z', '--full-tree')
                and re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', arguments[6])):
            return MAX_MANIFEST
        if (len(arguments) == 7 and arguments[:6] == ('-c', 'color.ui=false', '-c', 'column.ui=never', 'tag', '--list')
                and arguments[6] in ('*baseline*', 'v*-public-adoption')):
            return 1024**2
        if len(arguments) == 4 and arguments[:3] == ('rev-parse', '--verify', '--end-of-options'):
            name = arguments[3]
            if not name.startswith('refs/tags/'):
                raise ValueError('unsupported_repository_git_read')
            release_name(name.removeprefix('refs/tags/'))
            return 8192
        if (len(arguments) == 3 and arguments[:2] in (('cat-file', 'blob'), ('cat-file', 'commit'),
                ('cat-file', 'tag'), ('cat-file', 'tree'), ('cat-file', '-t'))
                and re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', arguments[2])):
            if arguments[1] == 'blob':return MAX_FILE
            if arguments[1] == 'commit':return MAX_MANIFEST
            if arguments[1] == '-t':return 32
            return MAX_OBJECT
        raise ValueError('unsupported_repository_git_read')

    def read(self, *arguments, limit=None):
        if len(self.observations) >= 20064:
            raise ValueError('repository_git_operation_budget')
        if any(type(value) is not str or '\0' in value or len(value) > 8192 for value in arguments):
            raise ValueError('unsupported_repository_git_read')
        maximum = self.limit(arguments)
        if limit is not None and (type(limit) is not int or not 0 < limit <= maximum):
            raise ValueError('repository_git_requested_limit_differs')
        limit = maximum if limit is None else limit
        self.check_source()
        argv = self.prefix + list(arguments)
        row = {'arguments': list(arguments), 'argv': argv, 'source_root': str(self.source),
               'tool_path': self.tool[0], 'tool_sha256': self.tool[1], 'process_started': False,
               'returncode': None, 'error_type': None, 'timed_out': False, 'output_truncated': False,
               'stdout_limit': limit}
        self.on_intent(deepcopy(row))
        self.observations.append(row)
        process = None
        streams = {'stdout': bytearray(), 'stderr': bytearray()}
        try:
            self.check_source()
            process = subprocess.Popen(argv, cwd=self.source, env=self.environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, umask=0o077)
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
                        raise TimeoutError('repository_git_timeout')
                    for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                        raw = os.read(key.fd, 65536)
                        if not raw:
                            selector.unregister(key.fileobj)
                            continue
                        maximum = limit if key.data == 'stdout' else 65536
                        available = maximum - len(streams[key.data])
                        streams[key.data].extend(raw[:available])
                        if len(raw) > available:
                            row['output_truncated'] = True
                            raise ValueError('repository_git_stream_budget')
            try:
                process.wait(timeout=max(.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                row['timed_out'] = True
                raise TimeoutError('repository_git_timeout') from None
            row['returncode'] = process.returncode
            self.check_source()
            if row['returncode']:
                raise ValueError('repository_git_read_failed')
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
        return bytes(streams['stdout'])
