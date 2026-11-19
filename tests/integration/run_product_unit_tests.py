#!/usr/bin/env python3
"""Run the complete own-product suite from a pinned package, without parent history.

Use the prepared candidate's Python environment. No inspected repository or
caller-selected program is executed; archived references are comparison data.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import selectors
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from acceptance.product_reference_inputs import prepare
from acceptance.product_generated_effects import (GENERATED, GENERATED_ADDITIONS,
    retain_effects, retain_additions)
from lib.runtime_package import admit, git, text_json
from lib.providers import process_groups
from lib.providers.attestation_verification import executable

MAX_STREAM = 8 * 1024**2
TIMEOUT = 3600
AUTHORITY = {'official_acceptance': False, 'production_approval': False,
    'authority_transferred': False, 'independent_execution_attested': False}


def run_command(kind, source, environment, directory, *, timeout=TIMEOUT):
    commands = {'preflight': ['/bin/bash', './scripts/validate_all.sh', '--check-tools'],
        'unit-tests': [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests'],
        'viewer-projection': [sys.executable, '-B', '-c',
            'from pathlib import Path; import sys,json; '
            'sys.path.insert(0,str(Path.cwd()/"scripts")); '
            'from lib.viewer_app import project_data; '
            'sys.stdout.write(json.dumps(project_data(Path.cwd()),ensure_ascii=False,indent=2)+"\\n")']}
    if kind not in commands or type(timeout) not in (int, float) or not 0 < timeout <= TIMEOUT:
        raise ValueError('closed_product_test_command_required')
    files = {name: directory / (kind + '-' + name + '.bin') for name in ('stdout', 'stderr')}
    counts = {name: 0 for name in files}
    digests = {name: hashlib.sha256() for name in files}
    process = None
    streams = {}
    started = time.monotonic()
    try:
        for name, path in files.items():
            streams[name] = path.open('xb')
        process = subprocess.Popen(commands[kind], cwd=source, env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, umask=0o077)
        deadline = started + timeout
        with selectors.DefaultSelector() as selector:
            for name in files:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError('product_unit_test_wall_budget')
                for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                    raw = os.read(key.fd, 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    name = key.data
                    if counts[name] + len(raw) > MAX_STREAM:
                        raise ValueError('product_unit_test_output_budget')
                    counts[name] += len(raw)
                    digests[name].update(raw)
                    streams[name].write(raw)
        process.wait(timeout=max(.01, deadline - time.monotonic()))
        return {'command': commands[kind], 'returncode': process.returncode,
            'wall_seconds': time.monotonic() - started, 'wall_seconds_limit': timeout,
            'stream_byte_limit': MAX_STREAM, 'outputs': {name: {'path': path.name,
                'bytes': counts[name], 'sha256': digests[name].hexdigest()} for name, path in files.items()}}
    finally:
        if process is not None:
            try:
                process_groups.stop(process, graceful=process.poll() is None)
            finally:
                for name in ('stdout', 'stderr'):
                    getattr(process, name).close()
        for stream in streams.values():
            stream.close()


def source_files(source, manifest, *, generated_effects=False):
    result = {}
    for row in manifest['files']:
        if not row['path'].startswith('source/'):
            continue
        name = row['path'][7:]
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('product_test_source_membership_changed')
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if (len(raw) != row['size'] or sha != row['sha256']) and not (generated_effects and name in GENERATED):
            raise ValueError('product_test_source_bytes_changed')
        if ('100755' if path.stat().st_mode & 0o111 else '100644') != row['mode']:
            raise ValueError('product_test_source_mode_changed')
        result[name] = {'sha256': sha, 'bytes': len(raw), 'mode': row['mode']}
    return result


def execute(package, pin, output):
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(ROOT) or ROOT.is_relative_to(output):
        raise ValueError('fresh_separate_product_test_output_required')
    output.mkdir(mode=0o700, parents=True)
    manifest = admit(package, pin, output / 'admitted')
    source = output / 'admitted/source'
    source.chmod(0o700)
    revision = manifest['source_commit']
    if git(ROOT, 'rev-parse', 'HEAD').decode().strip() != revision:
        raise ValueError('product_test_controller_revision_mismatch')
    for name in ('tests/integration/run_product_unit_tests.py',
                 'tests/acceptance/product_reference_inputs.py',
                 'tests/acceptance/product_generated_effects.py',
                 'tests/acceptance/freeze_product_reference_inputs.py'):
        if (ROOT / name).read_bytes() != (source / name).read_bytes():
            raise ValueError('product_test_controller_bytes_mismatch')
    if (not manifest['prepared_dependencies'] or manifest['opa'] is None
            or manifest['target']['system'] != platform.system()
            or manifest['target']['machine'] != platform.machine()):
        raise ValueError('prepared_native_product_test_package_required')
    before = source_files(source, manifest)
    generated_before = {name: (source / name).read_bytes() for name in GENERATED if name in before}
    example_sha = before['docs/examples/evidence-attestation.example.json']['sha256']
    # Source-intake tests require their pinned optional extraction dependency too.
    for name, version in re.findall(r'^([A-Za-z0-9_.-]+)==([^\s;]+)',
            (source / 'requirements-source-document-intake.lock').read_text(), re.M):
        if importlib.metadata.version(name) != version:
            raise ValueError('pinned_product_test_dependency_required')
    tools = {}
    tool_root = output / 'tools'
    tool_root.mkdir(mode=0o700)
    for name in ('git', 'node', 'openssl'):
        found = shutil.which(name)
        if found is None:
            raise ValueError('product_test_tool_missing')
        path, sha = executable(found)
        tools[name] = {'path': path, 'sha256': sha}
        (tool_root / name).symlink_to(path)
    opa = output / 'admitted/opa'
    path, sha = executable(opa)
    if sha != manifest['opa']['sha256']:
        raise ValueError('product_test_opa_changed')
    tools['opa'] = {'path': path, 'sha256': sha}
    (tool_root / 'opa').symlink_to(path)
    path, sha = executable(Path(sys.prefix) / 'bin/opa')
    if sha != manifest['opa']['sha256']:
        raise ValueError('pinned_product_test_environment_opa_required')
    tools['environment-opa'] = {'path': path, 'sha256': sha}
    path, sha = executable(sys.executable)
    tools['python'] = {'path': path, 'sha256': sha}
    temporary = output / 'tmp'
    temporary.mkdir(mode=0o700)
    environment = {'PATH': os.pathsep.join([str(tool_root), str(Path(sys.executable).parent), '/usr/bin', '/bin']),
        'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
        'PIP_NO_INDEX': '1', 'PIP_FIND_LINKS': str(output / 'admitted/wheels'),
        'VALIDATION_VENV': sys.prefix, 'TMPDIR': str(temporary),
        'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_COUNT': '0',
        'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false'}
    initial = {'schema_version': 1, 'kind': 'complete-own-product-unit-test',
        'source_revision': revision, 'source_tree': manifest['source_tree'], 'package_sha256': pin,
        'state': 'pending', 'unit_tests': 'not_run', 'source_files': len(before), **AUTHORITY}
    (output / 'intent.json').write_text(text_json(initial))
    references = prepare(source, revision,
        source / 'tests/fixtures/product-test-reference-inputs', output / 'reference-inputs')
    preflight = run_command('preflight', source, environment, output, timeout=120)
    if preflight['returncode']:
        raise ValueError('product_test_toolchain_preflight_failed')
    outcome = run_command('unit-tests', source, environment, output)
    raw = (output / 'unit-tests-stderr.bin').read_bytes()
    matches = list(re.finditer(rb'^Ran ([0-9]+) tests? in ([0-9.]+)s\s*$', raw, re.M))
    if not matches or int(matches[-1][1]) <= 0 or outcome['returncode'] not in (0, 1):
        raise ValueError('complete_product_unit_test_outcome_required')
    summary = re.search(rb'^(OK(?: \(skipped=([0-9]+)\))?|FAILED \([^\n]+\))$', raw[matches[-1].end():], re.M)
    if not summary or (outcome['returncode'] == 0) != summary[1].startswith(b'OK'):
        raise ValueError('product_unit_test_status_mismatch')
    skips = re.search(rb'skipped=([0-9]+)', summary[1])
    after = source_files(source, manifest, generated_effects=True)
    effects = retain_effects(source, generated_before, output / 'generated-effects', example_sha)
    changed = {name for name in before if before[name] != after[name]}
    physical = {p.relative_to(source).as_posix() for p in source.rglob('*')
        if p.is_file() and p.relative_to(source).parts[0] != '.git'}
    additions = physical - set(before)
    if additions - GENERATED_ADDITIONS:
        raise ValueError('unknown_product_test_generated_output')
    projection = None
    expected = None
    if additions:
        projection = run_command('viewer-projection', source, environment, output, timeout=120)
        if projection['returncode'] != 0:
            raise ValueError('product_test_viewer_projection_incomplete')
        expected = (output / 'viewer-projection-stdout.bin').read_bytes()
    artifacts = retain_additions(source, additions, expected, output / 'generated-artifacts')
    if after != source_files(source, manifest, generated_effects=True):
        raise ValueError('product_test_viewer_projection_changed_source')
    final_physical = {p.relative_to(source).as_posix() for p in source.rglob('*')
        if p.is_file() and p.relative_to(source).parts[0] != '.git'}
    status = git(source, 'status', '--porcelain', '--untracked-files=all', '-z').split(b'\0')
    if (changed != {r['path'] for r in effects}
            or git(source, 'rev-parse', 'HEAD').decode().strip() != revision
            or git(source, 'rev-parse', 'HEAD^{tree}').decode().strip() != manifest['source_tree']
            or any(row[:2] != b' M' for row in status if row)
            or {row[3:].decode() for row in status if row} != changed
            or final_physical != set(before) | {row['path'] for row in artifacts}):
        raise ValueError('product_test_working_source_changed')
    for value in tools.values():
        if executable(value['path']) != (value['path'], value['sha256']):
            raise ValueError('product_test_tool_changed')
    result = {**initial, 'state': 'complete', 'unit_tests': 'pass' if outcome['returncode'] == 0 else 'fail',
        'tests_run': int(matches[-1][1]), 'seconds': float(matches[-1][2]),
        'skipped': int(skips[1]) if skips else 0,
        'native_outcome': outcome, 'preflight': preflight, 'native_tools': tools,
        'reference_inputs': references, 'original_non_generated_source_files_unchanged': True,
        'generated_metadata_effects': effects, 'generated_before_after_bytes_retained': True,
        'generated_artifacts': artifacts, 'viewer_projection_native_outcome': projection,
        'source_worktree_clean_after': not bool(changed),
        'parent_history_downloaded': False, 'inspected_consumer_programs_executed': False,
        'full_governance_compliance_orchestrator_executed': False,
        'OS_network_or_process_tree_isolation_attested': False}
    (output / 'report.json').write_text(text_json(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        value = execute(args.package, args.sha256, args.output_root)
        print(text_json({k: value[k] for k in ('source_revision', 'source_tree', 'unit_tests', 'tests_run', 'skipped', *AUTHORITY)}), end='')
        return 0 if value['unit_tests'] == 'pass' else 1
    except (ValueError, OSError, subprocess.SubprocessError, TimeoutError, KeyError, TypeError,
            zipfile.BadZipFile, importlib.metadata.PackageNotFoundError) as error:
        message = str(error)
        diagnostic = message if isinstance(error, ValueError) and re.fullmatch('[a-z][a-z0-9_]{0,100}', message) else 'product_unit_test_execution_error'
        print(text_json({'execution': 'incomplete', 'error_type': type(error).__name__,
            'diagnostics': [diagnostic], **AUTHORITY}), file=sys.stderr, end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
