"""Owned read-only replay subprocess, bounded pipes, CPU, wall time and observed RSS.

The fixed child loads only its own admitted runtime and a private retained
operation. It never executes the inspected producer's programs or native ports.
RSS enforcement is polling, not a claim of a kernel-enforced peak RSS ceiling.
"""
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

# The isolated child starts this fixed admitted file, never a caller-selected
# module. -I excludes caller cwd, Python environment settings and user site.
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib import repository_worker_protocol as protocol
from lib.providers import process_groups
from lib.providers.attestation_verification import executable
from lib.result_bytes import strict_json


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def child():
    import resource
    # Apply these before importing or materializing the potentially large
    # retained operation. Darwin has no supported RLIMIT_AS/DATA restriction;
    # the parent uses measured RSS on both systems and reports that distinction.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (protocol.CPU_SECONDS, protocol.CPU_SECONDS + 1))
    address_space = None
    if sys.platform.startswith('linux'):
        address_space = 2 * protocol.MEMORY_BYTES
        resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    raw = sys.stdin.buffer.read(protocol.MAX_REQUEST + 1)
    if len(raw) > protocol.MAX_REQUEST:
        raise ValueError('repository_replay_worker_request_budget')
    packet = protocol.request(strict_json(raw))
    from lib.portable.runtime import source_digest, approved_opa_hashes
    from lib.providers.repository_operations import load_operation
    from lib.providers.repository_profiles import repository_engine_profile
    from lib.repository_inspection import inspect_repository_operation
    header = packet['binding']
    if source_digest() != header['runtime_source_digest']:
        raise ValueError('repository_replay_worker_runtime_changed')
    retained = load_operation(Path(packet['record_root']), header)
    profile = header['engine_profile']
    result = inspect_repository_operation(retained, **repository_engine_profile(profile),
        engine_profile=profile, approved_opa_hashes=frozenset(approved_opa_hashes('1.18.2')))
    if source_digest() != header['runtime_source_digest']:
        raise ValueError('repository_replay_worker_runtime_changed')
    reply = {'schema_version': 1, 'profile': protocol.PROFILE, 'inspection': result,
             'limits': {'cpu_seconds': protocol.CPU_SECONDS, 'address_space_bytes': address_space}}
    protocol.response(reply, header)
    raw = encoded(reply)
    if len(raw) > protocol.MAX_RESPONSE:
        raise ValueError('repository_replay_worker_response_budget')
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def resident_bytes(pid, ps_tool):
    try:
        result = subprocess.run([ps_tool, '-o', 'rss=', '-p', str(pid)], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=1,
            env={'PATH': '', 'LANG': 'C'}, start_new_session=True)
    except subprocess.TimeoutExpired:
        raise ValueError('repository_replay_worker_memory_observation_failed') from None
    raw = result.stdout.strip()
    if result.returncode == 1 and not raw:
        return None  # A finished child is still held, so its pid cannot be reused.
    if result.returncode or not raw.isdigit() or len(raw) > 16:
        raise ValueError('repository_replay_worker_memory_observation_failed')
    return int(raw) * 1024


def supervise(command, raw, *, timeout, memory_limit, ps_tool):
    """Internal POSIX supervisor; production supplies only the fixed child command."""
    if (type(raw) is not bytes or not 0 < len(raw) <= protocol.MAX_REQUEST
            or type(timeout) not in (int, float) or not 0 < timeout <= protocol.WALL_SECONDS
            or type(memory_limit) is not int or not 0 < memory_limit <= protocol.MEMORY_BYTES):
        raise ValueError('repository_replay_worker_supervisor_budget')
    started = time.monotonic()
    process = None
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    observation = {}
    peak = 0
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd='/', env={'PATH': '', 'LANG': 'C.UTF-8'}, start_new_session=True, umask=0o077)
        remaining = memoryview(raw)
        next_memory = started
        with selectors.DefaultSelector() as selector:
            for name in (*streams, 'stdin'):
                stream = getattr(process, name); os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_WRITE if name == 'stdin' else selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                now = time.monotonic()
                if now - started >= timeout:
                    raise TimeoutError('repository_replay_worker_wall_budget')
                if now >= next_memory and process.poll() is None:
                    resident = resident_bytes(process.pid, ps_tool)
                    if resident is None and process.poll() is None:
                        raise ValueError('repository_replay_worker_memory_observation_failed')
                    if resident is not None:
                        peak = max(peak, resident)
                        if resident > memory_limit:
                            raise ValueError('repository_replay_worker_resident_budget')
                    next_memory = time.monotonic() + .1
                for key, _ in selector.select(min(.05, max(0, timeout - (time.monotonic() - started)))):
                    if key.data == 'stdin':
                        try: count = os.write(key.fd, remaining[:8192])
                        except BrokenPipeError:
                            raise ValueError('repository_replay_worker_request_delivery_failed') from None
                        remaining = remaining[count:]
                        if not remaining:
                            selector.unregister(key.fileobj); key.fileobj.close()
                    else:
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj); continue
                        maximum = protocol.MAX_RESPONSE if key.data == 'stdout' else 65536
                        if len(streams[key.data]) + len(chunk) > maximum:
                            raise ValueError('repository_replay_worker_stream_budget')
                        streams[key.data].extend(chunk)
        process.wait(timeout=max(.001, timeout - (time.monotonic() - started)))
        if process.returncode != 0:
            raise ValueError('repository_replay_worker_process_failed')
        observation.update(profile=protocol.PROFILE, wall_seconds_limit=timeout,
            process_started=True, returncode=process.returncode,
            wall_seconds_observed=time.monotonic() - started,
            cpu_seconds_limit=protocol.CPU_SECONDS, resident_bytes_limit=memory_limit,
            resident_bytes_observed_peak=peak, resident_limit_mechanism='parent_polled_rss',
            poll_seconds=.1, kernel_peak_rss_ceiling_claimed=False,
            stderr_bytes=len(streams['stderr']), stderr_sha256=hashlib.sha256(streams['stderr']).hexdigest(),
            independent_execution_attested=False)
        return bytes(streams['stdout']), observation
    finally:
        if process is not None:
            try: process_groups.stop(process)
            finally:
                observation.update(process_groups.observations(process))
                for name in ('stdin', 'stdout', 'stderr'):
                    stream = getattr(process, name)
                    if stream is not None and not stream.closed:stream.close()


def inspect_operation(root, header):
    packet = protocol.request({'schema_version': 1, 'profile': protocol.PROFILE,
                               'record_root': str(root), 'binding': header})
    worker = Path(__file__).resolve()
    # Hash both executable and script identity before and after the operation.
    python_identity = executable(sys.executable)
    worker_bytes = worker.read_bytes()
    ps_identity = executable('/bin/ps')
    raw, observation = supervise([sys.executable, '-I', '-B', str(worker)], encoded(packet),
        timeout=protocol.WALL_SECONDS, memory_limit=protocol.MEMORY_BYTES, ps_tool=ps_identity[0])
    if (executable(sys.executable) != python_identity or worker.read_bytes() != worker_bytes
            or executable('/bin/ps') != ps_identity):
        raise ValueError('repository_replay_worker_executable_changed')
    reply = protocol.response(strict_json(raw), header)
    if sys.platform.startswith('linux') != (reply['limits']['address_space_bytes'] is not None):
        raise ValueError('repository_replay_worker_address_limit_changed')
    observation.update(address_space_bytes_limit=reply['limits']['address_space_bytes'],
        python_sha256=python_identity[1], worker_sha256=hashlib.sha256(worker_bytes).hexdigest(),
        ps_sha256=ps_identity[1])
    return {**reply['inspection'], 'worker_observation': observation}


if __name__ == '__main__':
    try:child()
    except Exception as error:
        # Keep retained inputs, exception text and local tracebacks out of IPC.
        sys.stderr.write(type(error).__name__ + '\n')
        raise SystemExit(2)
