"""Installed original native wire replay; synthetic inputs confer no provenance."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path); parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path); parser.add_argument('--expected-source', required=True)
    args = parser.parse_args(); prefix = args.prefix.resolve(); source = prefix / 'package/source'
    sys.path.insert(0, str(source / 'scripts'))
    from lib.v2_application import instance
    from lib.v2_distribution import verify_source
    from lib.ci_bundle_storage import DEFAULT_BUDGET, hash_file
    from lib.consumer_intake_store import atomic_json
    from lib.portable.contracts import canonical_digest
    from lib.provider_ports import general_result_verify
    settings = instance(prefix / 'instance')[1]
    assert settings['source_revision'] == args.expected_source and not settings['development']
    verify_source(source)
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    fixture_path = args.fixtures / 'native-result-cases.json'
    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == bindings[fixture_path.name]
    fixture = json.loads(fixture_path.read_text())
    assert fixture['synthetic'] and fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    def audit(event, values):
        if event == 'socket.connect': raise AssertionError('network forbidden in native wire replay')
    sys.addaudithook(audit)
    cases = prefix / 'native-result-replay-cases'; cases.mkdir(mode=0o700)
    results = {}
    for case in fixture['cases']:
        root = cases / case['id']; root.mkdir(mode=0o700)
        artifact = root / 'artifact.zip'; artifact.write_bytes(base64.b64decode(case['zip_base64'])); artifact.chmod(0o600)
        manifest = {'schema_version': 1, 'kind': 'native-general-result-capture', 'provider': 'github-actions',
            'repository_id': 'synthetic/native', 'domain': case['domain'], 'parameters': case['parameters'],
            'run': case['run'], 'jobs': case['jobs'], 'artifacts': [case['artifact']],
            'branch_protected': case['branch_protected'], 'branch_protection_lookup': case['branch_protection_lookup'],
            'archives': {'primary': {**hash_file(artifact, 1024**3), 'path': 'artifact.zip', 'artifact': case['artifact']}},
            'verified_at': case['at']}
        if 'companion' in case:
            companion = case['companion']; artifact = root / 'governance-run-input.zip'
            artifact.write_bytes(base64.b64decode(companion['zip_base64'])); artifact.chmod(0o600)
            manifest['artifacts'].append(companion['artifact'])
            manifest['archives']['companion'] = {**hash_file(artifact, 1024**3),
                'path': 'governance-run-input.zip', 'artifact': companion['artifact']}
        atomic_json(root / 'capture.json', manifest)
        sha = hash_file(root / 'capture.json', 16 * 1024**2)['sha256']
        verification = general_result_verify('github-actions', root, sha, budget=DEFAULT_BUDGET)
        snapshot = verification['snapshots'][case['domain']]
        assert snapshot == case['expected_snapshot']
        results[case['id']] = {'full_native_v1_wire_equal': True, 'snapshot': snapshot,
            'reported_trust': snapshot['trust']['effective_level'], 'effective_replay_trust': 'unverified',
            'native_metadata_rechecked_now': False}
        original = (root / 'artifact.zip').read_bytes(); (root / 'artifact.zip').write_bytes(original + b'changed')
        try:
            general_result_verify('github-actions', root, sha, budget=DEFAULT_BUDGET)
        except ValueError as error:
            assert str(error) == 'native_result_archive_bytes_changed'
        else: raise AssertionError('changed native archive accepted')
        (root / 'artifact.zip').write_bytes(original)

    # Exercise the real installed command's credential gate without making a
    # native request or manufacturing a successful native-origin assessment.
    credential = cases / 'mismatched-synthetic-reader.json'
    atomic_json(credential, {'schema_version': 1, 'provider': 'github-actions',
        'instance': 'https://api.github.com', 'repository': 'other/repository',
        'token': 'synthetic-unused-not-a-real-token'})
    completed = subprocess.run([str(prefix / 'axiom-v2'), 'results', 'capture-native',
        '--provider', 'github-actions', '--repository', 'synthetic/native', '--run-id', '8100',
        '--attempt', '1', '--credential-file', str(credential), '--domain', 'devsecops',
        '--artifact-name', 'devsecops-pipeline-evidence', '--governance-repository', 'synthetic/governance'],
        capture_output=True, text=True, timeout=120)
    assert completed.returncode == 2
    assert json.loads(completed.stderr)['diagnostics'] == ['native_result_reader_binding_mismatch']
    assert 'synthetic-unused-not-a-real-token' not in completed.stdout + completed.stderr
    assert not list((prefix / 'instance/state/results-native/assessments').iterdir())
    credential.unlink()
    verify_source(source); instance(prefix / 'instance')
    value = {'schema_version': 1, 'source_revision': settings['source_revision'], 'node_id': settings['node_id'],
        'runtime_source_digest': settings['runtime_source_digest'], 'synthetic': True, 'provider_invoked': False,
        'official_acceptance': False, 'full_functional_parity': False, 'results': results,
        'business_digest': canonical_digest(results)}
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n'); args.output.chmod(0o600)
    print(json.dumps({key: val for key, val in value.items() if key != 'results'}, sort_keys=True))


if __name__ == '__main__': main()
