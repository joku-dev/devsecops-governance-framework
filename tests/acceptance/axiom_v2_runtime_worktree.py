"""Installed current-file validation against complete unchanged V1 programs.

Fixtures are a separately hash-pinned test archive, never a production input.
The installed application never executes their Python programs; only this
explicit trusted comparison harness invokes the frozen original CLI.
"""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prefix', 'fixtures', 'output'): parser.add_argument(name, type=Path)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args(); prefix = args.prefix.resolve(); fixtures = args.fixtures.resolve()
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    source = Path(settings['source_root']); assert source.is_relative_to(prefix)
    bindings = json.loads((fixtures / 'bindings.json').read_text())
    for name, digest in bindings.items():
        path = fixtures / name
        assert path.resolve().is_relative_to(fixtures) and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    os.environ['PATH'] = str(prefix / 'venv/bin') + os.pathsep + os.environ.get('PATH', '')
    os.environ.pop('AXIOM_TEST_PRODUCT_ROOT', None)
    sys.path.insert(0, str(source / 'scripts')); sys.dont_write_bytecode = True
    from lib.v2_distribution import verify_source
    from lib.validation_sources import SCOPES
    verify_source(source)
    cases = {}; whole_files = {}
    with tempfile.TemporaryDirectory(prefix='installed-working-runtime-', dir=args.output.resolve().parent) as temporary:
        base = Path(temporary); tests = base / 'tests'; tests.mkdir(mode=0o700); (tests / 'acceptance').mkdir(mode=0o700)
        shutil.copyfile(fixtures / 'test_v2_runtime_worktree.py', tests / 'test_v2_runtime_worktree.py')
        shutil.copyfile(fixtures / 'oracle.py', tests / 'acceptance/v1_runtime_validation_oracle.py')
        spec = importlib.util.spec_from_file_location('installed_runtime_worktree', tests / 'test_v2_runtime_worktree.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.ROOT = source; module.DIRECTORY = fixtures / 'v1'; module.OPA = prefix / 'venv/bin/opa'
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.RuntimeWorkingTree)
        names = unittest.defaultTestLoader.getTestCaseNames(module.RuntimeWorkingTree)
        log = io.StringIO(); result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        assert result.wasSuccessful(), log.getvalue()
        assert result.testsRun == len(names) == 26 and not result.skipped
        cases.update({name: {'passed': True, 'scope': 'whole_original_working_data_or_explicit_native_guard'} for name in names})
        candidate = base / 'current-product'; shutil.copytree(source, candidate)
        original = module.oracle.Original(fixtures / 'v1', candidate)
        operations = []
        for name in ('pristine', 'dirty-marker'):
            if name == 'dirty-marker':
                import yaml
                path = candidate / 'architecture/quality-markers.yaml'
                value = yaml.safe_load(path.read_bytes()); value['markers'][0]['id'] = 'INSTALLED-DIRTY-MARKER'
                path.write_text(yaml.safe_dump(value, sort_keys=False))
            before = module.oracle.snapshot(candidate)
            command = [str(prefix / 'axiom-v2'), 'validation', 'runtime', '--source-worktree', str(candidate), '--at', '2026-11-18T13:00:00Z']
            native = subprocess.run(command, capture_output=True, timeout=180)
            assert native.returncode == (0 if name == 'pristine' else 1), native.stderr
            value = json.loads(native.stdout); operations.append((value['assessment_id'], {k: v for k, v in value.items() if k != 'assessment_id'}))
            assert value['source_revision'] == args.expected_source and value['runtime_source_digest'] == settings['runtime_source_digest']
            assert value['working_tree_used'] is True and value['kind'] == 'working-tree-product-runtime-validation'
            assert value['node_id'] == settings['node_id'] and not value['official_acceptance'] and not value['published']
            old_code, old_stdout, old_stderr, after = original.run(opa=prefix / 'venv/bin/opa')
            assert (value['exit_code'], base64.b64decode(value['stdout_base64']), base64.b64decode(value['stderr_base64'])) == (old_code, old_stdout, old_stderr)
            retained = prefix / 'instance/state/validation/operations' / value['assessment_id'] / 'outputs'
            new_files = {p.relative_to(retained).as_posix(): p.read_bytes() for p in retained.rglob('*') if p.is_file()}
            selected = lambda n: any(n.startswith(scope + '/') for scope in SCOPES) or n == 'generated/csv/architecture_runtime_traceability.csv'
            assert {n: raw for n, raw in after.items() if selected(n)} == new_files
            assert {n: raw for n, raw in before.items() if not selected(n)} == {n: raw for n, raw in after.items() if not selected(n)}
            whole_files[name] = {'files': len(new_files), 'whole_file_map_sha256': hashlib.sha256(json.dumps({n: hashlib.sha256(raw).hexdigest() for n, raw in sorted(new_files.items())}, sort_keys=True).encode()).hexdigest()}
            cases['installed_working_tree_' + name + '_whole_original_cli_and_files'] = {'passed': True}
        legacy = subprocess.run([*command, '--output', 'legacy'], capture_output=True, timeout=180)
        assert (legacy.returncode, legacy.stdout, legacy.stderr) == (old_code, old_stdout, old_stderr)
        shutil.rmtree(candidate)
        for operation, expected in operations:
            replay = subprocess.run([str(prefix / 'axiom-v2'), 'validation', 'inspect', '--assessment', operation], capture_output=True, timeout=180)
            assert replay.returncode == 0, replay.stderr
            assert json.loads(replay.stdout) == expected
        cases['installed_legacy_wire_and_deleted_caller_replay'] = {'passed': True}
    verify_source(source)
    value = {'schema_version': 1, 'source_revision': args.expected_source, 'runtime_source_digest': settings['runtime_source_digest'],
        'node_id': settings['node_id'], 'case_count': len(cases), 'cases': cases, 'complete_original_file_maps': whole_files,
        'whole_original_cli_and_files_compared_per_host': True, 'caller_python_executed_by_product': False,
        'native_opa_actually_executed': True, 'explicit_file_resolving_builtin_guard': True,
        'cross_host_raw_native_wire_identity_claimed': False, 'independent_execution_attested': False,
        'official_acceptance': False, 'full_functional_parity': False}
    value['business_digest'] = hashlib.sha256(json.dumps({'cases': cases, 'whole_files': whole_files}, sort_keys=True).encode()).hexdigest()
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n'); args.output.chmod(0o600)
    print(json.dumps({k: v for k, v in value.items() if k not in ('cases', 'complete_original_file_maps')}, sort_keys=True))


if __name__ == '__main__': main()
