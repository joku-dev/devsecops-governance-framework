"""Finite bootstrap caller's bounded POSIX subprocess capture, before dependencies.

The owning adapter selects commands. This internal runner discovers no programs
from a consumer, grants no authority and claims no kernel or network isolation.
"""
from pathlib import Path
import hashlib
import os
import re
import selectors
import subprocess
import time

from lib.providers import process_groups
from lib.providers.environment_bootstrap_storage import owned_directory

MAX_TIMEOUT = 1800
MAX_STREAM = 4 * 1024 * 1024


def write_all(descriptor, raw):
    remaining = memoryview(raw)
    while remaining:
        count = os.write(descriptor, remaining)
        if count is None or count <= 0:
            raise OSError('bootstrap_native_short_write')
        remaining = remaining[count:]


class BootstrapProcesses:
    def __init__(self, journal):
        self.journal = journal
        self.directory = journal.root / 'native'
        self.directory.mkdir(mode=0o700, exist_ok=True)
        owned_directory(self.directory)

    def run(self, kind, command, *, cwd, environment, timeout, stream_limit=MAX_STREAM):
        phase = self.journal.phase
        if type(phase) is not int:
            raise ValueError('bootstrap_native_requires_durable_phase_intent')
        if (type(kind) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,63}', kind)
                or type(command) is not list or not 1 <= len(command) <= 128
                or any(type(arg) is not str or '\0' in arg for arg in command)
                or sum(len(arg.encode()) for arg in command) > 65536
                or not Path(command[0]).is_absolute()):
            raise ValueError('bootstrap_native_fixed_command_required')
        if (type(timeout) not in (int, float) or not 0 < timeout <= MAX_TIMEOUT
                or type(stream_limit) is not int or not 0 < stream_limit <= MAX_STREAM):
            raise ValueError('bootstrap_native_capture_bounds_required')
        owned_directory(self.directory)
        identifier = f'native-{self.journal.sequence:04d}'
        names = {channel: identifier + '-' + channel + '.bin' for channel in ('stdout', 'stderr')}
        self.journal.append({'kind': 'native-intent', 'phase': phase,
            'native_id': identifier, 'operation': kind, 'command': command,
            'cwd': str(cwd), 'timeout_seconds': timeout, 'stream_limit_bytes': stream_limit,
            'streams': names, 'OS_network_or_process_tree_isolation_attested': False})
        descriptors = {}
        counts = {channel: 0 for channel in names}
        hashes = {channel: hashlib.sha256() for channel in names}
        process = None
        completed = None
        started = time.monotonic()
        try:
            for channel, name in names.items():
                descriptors[channel] = os.open(self.directory / name,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            process = subprocess.Popen(command, cwd=cwd, env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True, umask=0o077)
            self.journal.append({'kind': 'native-started', 'phase': phase,
                'native_id': identifier, 'pid': process.pid})
            with selectors.DefaultSelector() as selector:
                for channel in names:
                    stream = getattr(process, channel)
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, channel)
                while selector.get_map() or process.poll() is None:
                    if time.monotonic() - started >= timeout:
                        raise TimeoutError('bootstrap_native_wall_budget')
                    for selected, _ in selector.select(min(.05, max(0, timeout - (time.monotonic() - started)))):
                        raw = os.read(selected.fd, 65536)
                        if not raw:
                            selector.unregister(selected.fileobj)
                            continue
                        channel = selected.data
                        if counts[channel] + len(raw) > stream_limit:
                            raise ValueError('bootstrap_native_stream_budget')
                        write_all(descriptors[channel], raw)
                        counts[channel] += len(raw)
                        hashes[channel].update(raw)
            exit_code = process.wait(timeout=max(.01, timeout - (time.monotonic() - started)))
            completed = {'native_id': identifier, 'command': command, 'cwd': str(cwd),
                'exit_code': exit_code, 'terminal_result_observed': True,
                'wall_seconds': time.monotonic() - started,
                'timeout_seconds': timeout, 'stream_limit_bytes': stream_limit,
                'streams': {channel: {'path': 'native/' + names[channel],
                    'bytes': counts[channel], 'sha256': hashes[channel].hexdigest()}
                    for channel in names}}
        finally:
            try:
                if process is not None:
                    process_groups.stop(process, graceful=process.poll() is None)
            finally:
                try:
                    if process is not None:
                        process.stdout.close()
                        process.stderr.close()
                    for descriptor in descriptors.values():
                        os.fsync(descriptor)
                finally:
                    for descriptor in descriptors.values():
                        os.close(descriptor)
        if self.journal.phase != phase:
            raise ValueError('bootstrap_native_phase_changed_during_execution')
        completed.update(process_groups.observations(process))
        self.journal.append({'kind': 'native-finished', 'phase': phase,
            'native_id': identifier, 'outcome': completed})
        return completed
