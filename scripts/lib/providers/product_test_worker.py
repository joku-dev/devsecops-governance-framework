"""Fixed own-product test worker from exact admitted bytes; never consumer code.

No kernel network/process-tree isolation or independent execution is attested.
The engineering controller retains the complete original suite and reference data.
"""
from pathlib import Path
import hashlib
import os
import re
import selectors
import shutil
import stat
import subprocess
import sys
import time

from lib.portable.contracts import ROOT
from lib.runtime_package import admit, digest, git, text_json, MAX_TOTAL
from lib.result_bytes import strict_json, safe_bytes
from lib.providers import process_groups
from lib.providers.attestation_verification import executable

CONTROLLER = 'tests/integration/run_product_unit_tests.py'
OWN_MODULE = 'scripts/lib/providers/product_test_worker.py'
STREAM_LIMIT = 65536
WALL_LIMIT = 4200
AUTHORITY = {'official_acceptance': False, 'production_approval': False,
    'authority_transferred': False, 'independent_execution_attested': False}


def retain_package(source, pin, destination):
    """Freeze one bounded ordinary input, without a live caller-path dependency."""
    if type(pin) is not str or re.fullmatch('[a-f0-9]{64}', pin) is None:
        raise ValueError('independent_product_test_package_pin_required')
    source, destination = Path(source), Path(destination)
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        maximum = MAX_TOTAL + 16 * 1024**2
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            raise ValueError('bounded_ordinary_product_test_package_required')
        digestor = hashlib.sha256(); size = 0
        with destination.open('xb', buffering=0) as output:
            destination.chmod(0o600)
            while raw := os.read(fd, 1024**2):
                size += len(raw)
                if size > maximum:
                    raise ValueError('product_test_package_capture_budget')
                digestor.update(raw)
                remaining = memoryview(raw)
                while remaining:
                    count = output.write(remaining)
                    if count is None or count <= 0:
                        raise OSError('product_test_package_short_write')
                    remaining = remaining[count:]
            os.fsync(output.fileno())
        def signature(row):
            return (row.st_dev, row.st_ino, row.st_mode, row.st_size,
                    row.st_mtime_ns, row.st_ctime_ns)
        if (size != before.st_size or signature(before) != signature(os.fstat(fd))
                or signature(before) != signature(os.stat(source, follow_symlinks=False))
                or digestor.hexdigest() != pin):
            raise ValueError('product_test_package_changed_or_checksum_mismatch')
        return {'path': destination.name, 'bytes': size, 'sha256': pin}
    finally:
        os.close(fd)


def supervise(command, cwd, environment, target, *, timeout=WALL_LIMIT, stream_limit=STREAM_LIMIT):
    """Internal native supervisor; production supplies the one closed command."""
    if type(timeout) not in (int, float) or not 0 < timeout <= WALL_LIMIT:
        raise ValueError('product_test_parent_wall_budget_required')
    if type(stream_limit) is not int or not 0 < stream_limit <= 8 * 1024**2:
        raise ValueError('product_test_parent_stream_budget_required')
    started = time.monotonic()
    process = None
    streams = {}
    counts = {'stdout': 0, 'stderr': 0}
    hashes = {key: hashlib.sha256() for key in counts}
    try:
        for name in counts:
            path = target / ('controller-' + name + '.bin')
            streams[name] = path.open('xb', buffering=0)
            path.chmod(0o600)
        process = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, umask=0o077)
        with selectors.DefaultSelector() as selector:
            for name in counts:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                if time.monotonic() - started >= timeout:
                    raise TimeoutError('product_test_parent_wall_budget')
                for key, _ in selector.select(.05):
                    raw = os.read(key.fd, 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    name = key.data
                    if counts[name] + len(raw) > stream_limit:
                        raise ValueError('product_test_parent_stream_budget')
                    remaining = memoryview(raw)
                    while remaining:
                        count = streams[name].write(remaining)
                        if count is None or count <= 0:
                            raise OSError('product_test_parent_short_write')
                        remaining = remaining[count:]
                    counts[name] += len(raw)
                    hashes[name].update(raw)
        code = process.wait(timeout=max(.01, timeout - (time.monotonic() - started)))
        return {'exit_code': code, 'command': command, 'wall_seconds': time.monotonic() - started,
            'wall_limit_seconds': timeout, 'stream_limit_bytes': stream_limit,
            'streams': {name: {'path': 'controller-' + name + '.bin', 'bytes': counts[name],
                'sha256': hashes[name].hexdigest()} for name in counts}}
    finally:
        if process is not None:
            try:
                process_groups.stop(process, graceful=process.poll() is None)
            finally:
                for name in counts:
                    getattr(process, name).close()
        for stream in streams.values():
            stream.close()


def execute_own_suite(package, package_pin, operation_root):
    """The application owns the fresh private operation path and quota admission."""
    revision = git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    # A working override of this trusted worker cannot execute an older package.
    if git(ROOT, 'show', revision + ':' + OWN_MODULE) != Path(__file__).read_bytes():
        raise ValueError('committed_product_test_worker_required')
    target = Path(operation_root).absolute()
    if (target.exists() or target.is_symlink() or any(p.is_symlink() for p in target.parents)
            or target.is_relative_to(ROOT.resolve()) or ROOT.resolve().is_relative_to(target)):
        raise ValueError('fresh_separate_product_test_operation_required')
    target.mkdir(mode=0o700)
    def state(value, **details):
        record = {'schema_version': 1, 'kind': 'complete-own-product-test-worker',
            'source_revision': revision, 'package_sha256': package_pin, 'state': value,
            'OS_network_or_process_tree_isolation_attested': False, **AUTHORITY, **details}
        temporary = target / '.state-incoming.json'
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(text_json(record)); stream.flush(); os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, target / 'state.json')
        return record
    state('acquiring', unit_tests='not_run')
    try:
        captured = retain_package(package, package_pin, target / 'input.zip')
        retained = target / 'input.zip'
        manifest = admit(retained, package_pin, target / 'controller-source')
        source = target / 'controller-source/source'
        if (manifest['source_commit'] != revision
                or manifest['source_tree'] != git(ROOT, 'rev-parse', 'HEAD^{tree}').decode().strip()
                or not manifest['prepared_dependencies'] or manifest['opa'] is None):
            raise ValueError('current_prepared_product_test_package_required')
        for name in (CONTROLLER, OWN_MODULE):
            if (source / name).read_bytes() != git(ROOT, 'show', revision + ':' + name):
                raise ValueError('product_test_worker_source_binding_changed')
        native = {}
        tools = target / 'tools'; tools.mkdir(mode=0o700)
        for name in ('git', 'node', 'openssl'):
            found = shutil.which(name)
            if found is None:
                raise ValueError('product_test_worker_tool_missing')
            path, sha = executable(found)
            native[name] = {'path': path, 'sha256': sha}
            (tools / name).symlink_to(path)
        path, sha = executable(sys.executable)
        native['python'] = {'path': path, 'sha256': sha}
        environment = {'PATH': os.pathsep.join([str(tools), str(Path(sys.executable).parent), '/usr/bin', '/bin']),
            'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'PIP_NO_INDEX': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_COUNT': '0', 'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false'}
        command = [sys.executable, '-B', str(source / CONTROLLER), '--package', str(retained),
            '--sha256', package_pin, '--output-root', str(target / 'run')]
        state('running', unit_tests='running', source_tree=manifest['source_tree'], native_tools=native)
        outcome = supervise(command, source, environment, target)
        if outcome['exit_code'] not in (0, 1):
            raise ValueError('product_test_controller_execution_incomplete')
        report_raw = safe_bytes(target / 'run/report.json', limit=8 * 1024**2)
        report = strict_json(report_raw)
        if (type(report) is not dict or report.get('state') != 'complete' or report.get('kind') != 'complete-own-product-unit-test'
                or report.get('source_revision') != revision or report.get('source_tree') != manifest['source_tree']
                or report.get('package_sha256') != package_pin
                or any(report.get(k) is not False for k in AUTHORITY)
                or type(report.get('tests_run')) is not int or report['tests_run'] <= 0
                or type(report.get('skipped')) is not int or not 0 <= report['skipped'] <= report['tests_run']
                or report.get('unit_tests') != ('pass' if outcome['exit_code'] == 0 else 'fail')
                or report.get('original_non_generated_source_files_unchanged') is not True
                or report.get('full_governance_compliance_orchestrator_executed') is not False
                or report['native_outcome']['command'] != [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests']
                or report['native_outcome']['returncode'] != outcome['exit_code']):
            raise ValueError('product_test_controller_outcome_mismatch')
        for name in ('stdout', 'stderr'):
            row = report['native_outcome']['outputs'][name]
            if row['path'] != 'unit-tests-' + name + '.bin':
                raise ValueError('closed_product_test_output_required')
            raw = safe_bytes(target / 'run' / row['path'], limit=8 * 1024**2)
            if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('product_test_raw_output_changed')
        for row in manifest['files']:
            path = target / 'controller-source' / row['path']
            if path.is_symlink() or not path.is_file() or digest(path) != row['sha256']:
                raise ValueError('product_test_controller_source_changed')
        if digest(retained) != package_pin or git(ROOT, 'rev-parse', 'HEAD').decode().strip() != revision:
            raise ValueError('product_test_package_or_revision_changed')
        for row in native.values():
            if executable(row['path']) != (row['path'], row['sha256']):
                raise ValueError('product_test_native_tool_changed')
        return state('complete', unit_tests=report['unit_tests'], tests_run=report['tests_run'],
            skipped=report['skipped'], source_tree=manifest['source_tree'], native_tools=native,
            native_outcome=outcome, retained_package=captured,
            report_sha256=hashlib.sha256(report_raw).hexdigest())
    except (ValueError, OSError, KeyError, TypeError, TimeoutError, subprocess.SubprocessError) as error:
        state('incomplete', unit_tests='not_proven', error_type=type(error).__name__)
        raise
