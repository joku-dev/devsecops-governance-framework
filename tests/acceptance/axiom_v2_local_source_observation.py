"""Installed explicit worktree mode versus unchanged V1 on each host's real directory."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path); parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path); parser.add_argument('--expected-source', required=True)
    parser.add_argument('--real-repo', type=Path)
    args = parser.parse_args(); prefix = args.prefix.resolve(); fixtures = args.fixtures.resolve()
    output = args.output.resolve(); settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    bindings = json.loads((fixtures / 'bindings.json').read_text()); reference = fixtures / 'source-inspection'
    for path in reference.iterdir():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == bindings['source-inspection/' + path.name]
    spec = importlib.util.spec_from_file_location('pinned_original_native_oracle', reference / 'oracle.py')
    oracle = importlib.util.module_from_spec(spec); previous = sys.dont_write_bytecode; sys.dont_write_bytecode = True
    try: spec.loader.exec_module(oracle)
    finally: sys.dont_write_bytecode = previous
    contract = oracle.load_fixture(reference); paths = contract['logical_outputs']

    def call(*arguments, expected=0, legacy=False):
        result = subprocess.run([str(prefix / 'axiom-v2'), 'source-inspection', *map(str, arguments)],
                                capture_output=True, timeout=180)
        assert result.returncode == expected, result.stderr.decode()
        return result.stdout if legacy else json.loads(result.stdout if expected in (0, 1) else result.stderr)

    def leaves(value, prefix=''):
        if isinstance(value, dict):
            return {k: digest for key, child in value.items() for k, digest in leaves(child, prefix + '/' + key.replace('~', '~0').replace('/', '~1')).items()}
        if isinstance(value, list):
            return {k: digest for index, child in enumerate(value) for k, digest in leaves(child, prefix + '/' + str(index)).items()}
        raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
        return {prefix: hashlib.sha256(raw).hexdigest()}

    results = {}; raw_results = {}
    with tempfile.TemporaryDirectory(prefix='local-source-oracle-', dir=output.parent) as temporary:
        base = Path(temporary).resolve(); rows = []
        for case in contract['cases']:
            root = base / case['id']; oracle.make_repository(root, case); shutil.rmtree(root / '.git')
            rows.append((case['id'], root, 'synthetic/' + case['id'], True))
        root = base / 'dirty'; oracle.make_repository(root, contract['cases'][0])
        (root / '.github/workflows/ci.yml').write_bytes(b'name: Dirty\r\njobs: {}\r\n')
        (root / '.github/workflows/untracked.yml').write_text('# devsecops-governance-framework\n')
        marker = base / 'executed'; poison = root / 'scripts/poison.py'; poison.parent.mkdir(exist_ok=True)
        poison.write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n')
        rows.append(('dirty-untracked', root, 'synthetic/dirty', True))
        empty = base / 'empty'; empty.mkdir(); rows.append(('empty', empty, 'synthetic/empty', True))
        if args.real_repo:
            root = args.real_repo.resolve()
            assert oracle.git(root, 'rev-parse', 'HEAD') == '5c3b5cb50d2260bfbde736c9ac80667271406d99'
            assert not oracle.git(root, 'status', '--porcelain')
            rows.append(('ha-CPsWMS', root, 'joku-dev/ha-CPsWMS', False))
        for name, repository, repository_id, removable in rows:
            original, exits = oracle.original_files(reference, base / ('original-' + name), repository, repository_id, contract['at'])
            raw_results[name] = {path: raw.decode() for path, raw in original.items()}
            arguments = ['observe', '--kind', 'all', '--repo', repository, '--repository-id', repository_id,
                         '--profile', 'legacy-worktree-signatures-v1', '--at', contract['at']]
            receipt = call(*arguments); identifier = receipt['assessment_id']
            inspection = call('inspect-observation', '--id', identifier); value = inspection['assessment']
            assert inspection['retained_observation_and_complete_outputs_reverified'] and not inspection['live_directory_rechecked']
            assert value['node_id'] == settings['node_id'] and value['runtime_source_digest'] == settings['runtime_source_digest']
            assert value['source_revision'] == args.expected_source and value['source_worktree_clean']
            assert value['working_tree_used'] and value['evidence_trust'] == 'unverified'
            assert not value['content_commit_verified'] and 'consumer_commit' not in value and 'consumer_tree' not in value
            assert not any(value[k] for k in ('repository_identity_verified', 'provider_invoked', 'official_acceptance',
                'production_approval', 'risk_acceptance', 'authority_transferred', 'operating_acceptance_inherited', 'published'))
            assert receipt['original_finding_exit'] == max(exits) and not receipt['finding_exit_requested']
            assert call(*arguments, '--fail-on-findings', expected=max(exits))['assessment_id'] == identifier
            for path, raw in original.items():
                assert (Path(receipt['artifact_directory']) / Path(path).name).read_bytes() == raw
            # Native V1 is run against this exact host directory. No CI iterator,
            # output field or descriptive path is substituted in this comparison.
            results[name] = {'complete_original_native_wires_equal': True, 'original_exits': list(exits),
                'file_sha256': {path: hashlib.sha256(raw).hexdigest() for path, raw in original.items()},
                'json_leaf_sha256': {path: leaves(json.loads(raw)) for path, raw in original.items() if path.endswith('.json')},
                'retained_input_id': value['input_id']}
            for kind, logical, options in [('integration', paths['integration'], []),
                    ('onboarding', paths['onboarding_json'], ['--repository-id', repository_id])]:
                cli = ['observe', '--kind', kind, '--target-repo', repository, '--profile', 'legacy-worktree-signatures-v1',
                       '--at', contract['at'], '--format', 'legacy', '--fail-on-findings', *options]
                expected_exit = exits[0] if kind == 'integration' else exits[1]
                assert call(*cli, expected=expected_exit, legacy=True) == original[logical]
                export = base / (name + '-' + kind + '.json')
                flag = '--output-file' if kind == 'integration' else '--output-json'
                assert call(*cli, flag, export, expected=expected_exit, legacy=True) == f'Wrote {export}\n'.encode()
                assert export.read_bytes() == original[logical]
            if removable:
                shutil.rmtree(repository)
                assert call('inspect-observation', '--id', identifier)['retained_observation_and_complete_outputs_reverified']
                artifact = Path(receipt['artifact_directory']) / Path(paths['integration']).name
                saved = artifact.read_bytes(); artifact.write_bytes(b'changed')
                assert call('inspect-observation', '--id', identifier, expected=2)['diagnostics'] == ['local_source_output_changed']
                artifact.write_bytes(saved)
        assert not marker.exists()
    proof = {'schema_version': 1, 'source_revision': args.expected_source, 'node_id': settings['node_id'],
        'runtime_source_digest': settings['runtime_source_digest'], 'comparison_profile': 'legacy-worktree-signatures-v1',
        'oracle_mode': 'unchanged_v1_on_identical_physical_directory', 'normalized_fields': [],
        'complete_original_native_wires_equal': True, 'caller_removal_replay_checked': True,
        'output_tamper_rejected': True, 'poison_executed': False, 'official_acceptance': False,
        'full_functional_parity': False, 'results': results}
    # Private raw outputs never leave this host. The separate proof has digests only.
    raw_path = output.with_suffix('.private-raw.json')
    raw_path.write_text(json.dumps(raw_results, indent=2, sort_keys=True) + '\n'); raw_path.chmod(0o600)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n'); output.chmod(0o600)
    print(json.dumps({k: v for k, v in proof.items() if k != 'results'}, sort_keys=True))


if __name__ == '__main__': main()
