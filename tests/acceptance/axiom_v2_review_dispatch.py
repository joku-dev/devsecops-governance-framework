"""Installed dispatcher: independent V1 selection, whole wires and native effects."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


STATE = 'generated/agent-usage/recording-state.json'
LOG = 'generated/agent-usage/agent-usage.jsonl'
AT = '2026-11-17T17:00:00Z'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    before = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(value)
    finally:
        sys.dont_write_bytecode = before
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--real-repo', type=Path)
    args = parser.parse_args()
    prefix, fixtures, output = (p.resolve() for p in (args.prefix, args.fixtures, args.output))
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    bindings = json.loads((fixtures / 'bindings.json').read_text())
    reference, metadata = fixtures / 'review-planning', fixtures / 'review-metadata'
    for directory in (reference, metadata):
        for path in directory.iterdir():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == bindings[directory.name + '/' + path.name]
    planning = module('installed_dispatch_planning_oracle', reference / 'oracle.py')
    oracle = module('installed_dispatch_recording_oracle', reference / 'dispatch-oracle.py')
    results, generations, external_ids = {}, [], []

    def command(*arguments, expected=0):
        run = subprocess.run([str(prefix / 'axiom-v2'), 'review-dispatch', *map(str, arguments)],
                             capture_output=True, timeout=180)
        assert run.returncode == expected, run.stderr.decode()
        if not expected:
            assert not run.stderr
        return run

    def receipt(*arguments):
        value = json.loads(command(*arguments).stdout)
        assert value['source_revision'] == args.expected_source
        assert value['runtime_source_digest'] == settings['runtime_source_digest']
        assert value['node_id'] == settings['node_id'] and not value['provider_invoked']
        assert value['mode'] == 'report-only' and value['evidence_trust'] == 'unverified'
        for flag in ('official_acceptance', 'human_approval_verified', 'authority_transferred', 'published'):
            assert not value[flag]
        return value

    def target(root, object_format=None):
        root.mkdir(mode=0o700)
        for name, row in planning.target_files(reference).items():
            if not name.startswith(('.agents/roles/', '.agents/skills/', '.agents/routing/')):
                continue
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(row['bytes'])
            path.chmod(row['mode'])
        if object_format:
            (root / 'docs').mkdir()
            (root / 'docs/original.md').write_text('original\n')
            planning.git(root, 'init', '-q', '-b', 'main', '--object-format=' + object_format)
            planning.git(root, 'add', '--all')
            planning.git(root, 'commit', '-qm', 'fixed fixture')
        return root

    def contents(paths):
        return {str(p): p.read_bytes() if p.exists() else None for p in paths}

    def restore(before):
        for name, raw in before.items():
            path = Path(name)
            if raw is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)

    with tempfile.TemporaryDirectory(prefix='installed-dispatch-', dir=output.parent) as temporary:
        base = Path(temporary)
        caller = target(base / 'caller')
        original = planning.OriginalReview(reference, metadata, caller)
        roles = original.review.ROLE_CONTRACTS
        selected = ['docs/example.md']
        dispatch = original.dispatch.build_dispatch(selected)
        command('init', '--workspace', 'installed-dispatch', '--profile', 'legacy-role-dispatch-v1')
        sequence = [('--record-next', '2', '--json'), (*selected, '--json'),
                    (*selected, '--provider-review', 'codex'), tuple(selected),
                    ('--recording-status', '--json'), ('--record-continuous',),
                    (*selected, '--provider-review', 'mistral'), ('--usage-summary', '--json'), ('--usage-summary',)]
        try:
            for index, options in enumerate(sequence):
                code, stdout, stderr = oracle.main(reference, caller, roles, AT, list(options), dispatch)
                assert code == 0 and not stderr
                extra = ['--repo', caller] if options[0] == selected[0] else []
                value = receipt('run', '--workspace', 'installed-dispatch', '--at', AT,
                                *extra, *options, '--format', 'receipt')
                assert Path(value['stdout_file']).read_bytes() == stdout
                actual_root = Path(value['data_directory'])
                files = {}
                for name in (STATE, LOG):
                    expected_path, actual_path = caller / name, actual_root / name
                    assert expected_path.exists() == actual_path.exists()
                    if expected_path.exists():
                        assert actual_path.read_bytes() == expected_path.read_bytes()
                        files[name] = actual_path.read_text()
                results['private-' + str(index)] = {'stdout': stdout.decode(), 'files': files,
                                                    'complete_original_wires_and_effects_equal': True}
                generations.append(value['generation'])
            shutil.rmtree(caller / 'generated')

            def native(name, options, tracked=None):
                paths = tracked or [caller / STATE, caller / LOG]
                before = contents(paths)
                code, stdout, stderr = oracle.main(reference, caller, roles, AT, list(options), dispatch)
                assert code == 0 and not stderr
                expected = contents(paths)
                restore(before)
                actual = command('run', '--external-files', '--file-profile', 'legacy-local-dispatch-files-v1',
                                 '--repo', caller, '--at', AT, *options)
                assert actual.stdout == stdout and contents(paths) == expected
                results[name] = {'stdout': stdout.decode(), 'complete_original_wires_and_effects_equal': True,
                                 'files': [raw.decode() if raw is not None else None for raw in expected.values()]}

            for index, options in enumerate(sequence):
                native('native-' + str(index), options)
            outside_log, outside_state = base / 'custom.jsonl', base / 'custom-state.json'
            outside_log.write_bytes(b'{}\n')
            outside_state.write_bytes(b'{corrupt obsolete state')
            custom = ['--usage-log', str(outside_log), '--usage-state', str(outside_state)]
            native('custom-window-large', ['--record-next', str(10**30), *custom], [outside_state, outside_log])
            native('custom-provider-declaration', [*selected, '--provider-review', 'codex', *custom], [outside_state, outside_log])
            native('lexical-label', ['--record-next', '2', '--usage-log', 'logs/../lexical.jsonl'])

            # This is an explicit installed test fault, not an observed natural crash.
            fault = base / 'inject-file-fault.py'
            fault.write_text("""import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import axiom_v2
from lib.providers import review_dispatch_files as native
replace = native.replace
def fail(path, raw, mode):
    if path.name == 'recording-state.json': raise OSError('synthetic installed fault')
    return replace(path, raw, mode)
with patch.object(native, 'replace', side_effect=fail):
    raise SystemExit(axiom_v2.main(sys.argv[2:]))
""")
            # Restore the default recording log before the controlled two-file interruption.
            command('run', '--external-files', '--file-profile', 'legacy-local-dispatch-files-v1',
                    '--repo', caller, '--at', AT, '--record-next', '2')
            before_events = len((caller / LOG).read_text().splitlines())
            fault_run = subprocess.run([str(prefix / 'venv/bin/python'), str(fault),
                str(Path(settings['source_root']) / 'scripts'), '--instance', str(prefix / 'instance'),
                'review-dispatch', 'run', '--external-files', '--file-profile', 'legacy-local-dispatch-files-v1',
                '--repo', str(caller), '--at', AT, *selected, '--provider-review', 'codex'], capture_output=True, timeout=180)
            assert fault_run.returncode == 2 and not fault_run.stdout
            error = json.loads(fault_run.stderr)
            assert error['diagnostics'] == ['external_dispatch_apply_failed']
            identifier = error['assessment_id']
            assert json.loads(command('external-pending').stdout)['pending_assessment_ids'] == [identifier]
            recovered = receipt('external-apply', '--id', identifier)
            assert recovered['execution_state'] == 'applied' and recovered['resumed_partial_operation']
            assert len((caller / LOG).read_text().splitlines()) == before_events + 1
            assert receipt('external-apply', '--id', identifier)['idempotent_apply']
            assert json.loads(command('external-pending').stdout)['pending_assessment_ids'] == []
            external_ids.append(identifier)
            results['injected-partial-recovery'] = {'injected_test_fault': True, 'fresh_process_resume': True,
                'single_append': True, 'completed_retry_only_verifies': True}
            (caller / STATE).write_bytes(b'operator changed this')
            failed = command('external-apply', '--id', identifier, expected=2)
            assert json.loads(failed.stderr)['diagnostics'] == ['dispatch_native_output_verification_failed']
            assert (caller / STATE).read_bytes() == b'operator changed this'
            plan = receipt('run', '--external-files', '--file-profile', 'legacy-local-dispatch-files-v1',
                           '--repo', caller, '--at', AT, '--record-next', '1', '--prepare-only')
            abandoned = receipt('external-abandon', '--id', plan['assessment_id'], '--reason', 'Synthetic explicit non-success')
            assert abandoned['execution_state'] == 'abandoned' and not abandoned['abandonment']['native_files_reverted']
            assert (caller / STATE).read_bytes() == b'operator changed this'
            external_ids.append(plan['assessment_id'])
            results['operator-edit-and-abandon'] = {'completed_operation_never_reverts_edit': True,
                                                   'abandonment_does_not_revert_or_certify': True}
        finally:
            original.close()

        for object_format in ('sha1', 'sha256'):
            repository = target(base / object_format, object_format)
            planning.git(repository, 'branch', 'original-base')
            old = planning.OriginalReview(reference, metadata, repository)
            try:
                def compare(name, extra=()):
                    paths = old.review.changed_files(repository, 'original-base')
                    expected = old.dispatch.build_dispatch(paths)
                    actual = command('run', '--workspace', 'installed-dispatch', '--repo', repository,
                                     '--base-ref', 'original-base', '--at', AT, '--json', *extra)
                    assert actual.stdout == (json.dumps(expected, indent=2, sort_keys=True) + '\n').encode()
                    results[object_format + '-' + name] = {'complete_original_selection_and_stdout_equal': True,
                                                         'changed_paths': paths, 'dispatch': expected}
                compare('empty')
                (repository / 'docs/committed.md').write_text('committed\n')
                planning.git(repository, 'add', '--all'); planning.git(repository, 'commit', '-qm', 'branch change')
                (repository / 'docs/staged.md').write_text('staged\n')
                planning.git(repository, 'add', '--all'); (repository / 'docs/staged.md').unlink()
                planning.git(repository, 'mv', 'docs/original.md', 'docs/renamed ü.md')
                (repository / 'docs/untracked.md').write_text('untracked\n')
                compare('working-and-branch')
            finally:
                old.close()
            shutil.rmtree(repository)

        shutil.rmtree(caller)
        for generation in generations:
            value = receipt('inspect', '--workspace', 'installed-dispatch', '--generation', generation)
            assert value['retained_complete_outputs_reverified'] and not value['target_current_state_rechecked']
        for identifier in external_ids:
            value = receipt('external-inspect', '--id', identifier)
            assert value['retained_complete_outputs_reverified'] and not value['native_outputs_rechecked']
        results['offline-replay'] = {'all_callers_deleted': True, 'complete_outputs_rederived': True,
                                    'current_target_or_native_checks_claimed': False}
        if args.real_repo:
            real = args.real_repo.resolve()
            pin = '5c3b5cb50d2260bfbde736c9ac80667271406d99'
            assert planning.git(real, 'rev-parse', 'HEAD') == pin and not planning.git(real, 'status', '--porcelain')
            try:
                real_old = planning.OriginalReview(reference, metadata, real)
            except ValueError:
                pass
            else:
                real_old.close()
                raise AssertionError('Original unexpectedly accepted missing consumer role contracts')
            failed = command('run', '--workspace', 'installed-dispatch', '--repo', real,
                             '--at', AT, 'docs/example.md', '--json', expected=2)
            assert json.loads(failed.stderr)['diagnostics'] == ['dispatch_role_directory_unavailable']
            assert not planning.git(real, 'status', '--porcelain')
            results['real-consumer-boundary'] = {'unchanged_consumer_commit': pin,
                'original_and_product_reject_missing_role_contracts': True, 'contracts_injected': False}

    value = {'schema_version': 1, 'source_revision': args.expected_source,
             'runtime_source_digest': settings['runtime_source_digest'], 'node_id': settings['node_id'],
             'oracle_mode': 'unchanged_original_git_routing_and_dispatch_recording_orchestration',
             'normalized_fields': [], 'provider_invoked': False, 'independent_human_approval': False,
             'full_functional_parity': False, 'results': results,
             'business_digest': hashlib.sha256(json.dumps(results, sort_keys=True, separators=(',', ':'),
                                                        ensure_ascii=False, allow_nan=False).encode()).hexdigest()}
    output.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    output.chmod(0o600)
    print(json.dumps({k: v for k, v in value.items() if k != 'results'}, sort_keys=True))


if __name__ == '__main__':
    main()
