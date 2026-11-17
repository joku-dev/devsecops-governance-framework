"""Installed full typed verification/intake against independent synthetic V1 bytes."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    source = prefix / 'package/source'
    sys.path.insert(0, str(source / 'scripts'))
    from lib.portable.contracts import canonical_digest
    from lib.consumer_intake_store import atomic_json
    from lib.v2_application import instance
    from lib.v2_distribution import verify_source
    verify_source(source)
    _, settings = instance(prefix / 'instance')
    assert settings['source_revision'] == args.expected_source and not settings['development']
    assert not (source / 'scripts/lib/evidence_trust.py').exists()
    raw = (args.fixtures / 'typed-container-cases.json').read_bytes()
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == bindings['typed-container-cases.json']
    fixture = json.loads(raw)
    assert fixture['synthetic'] and fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    bundle = prefix / 'acceptance-typed-import'
    bundle.mkdir(mode=0o700)
    (bundle / 'archives').mkdir(mode=0o700)
    for name, content in fixture['archive_bytes_base64'].items():
        path = bundle / 'archives' / (name + '.zip')
        path.write_bytes(base64.b64decode(content, validate=True))
        path.chmod(0o600)
    atomic_json(bundle / 'capture.json', fixture['manifest'])
    sha = hashlib.sha256((bundle / 'capture.json').read_bytes()).hexdigest()
    def command(*arguments, fail=False):
        completed = subprocess.run([str(prefix / 'axiom-v2'), 'typed', *arguments],
                                   capture_output=True, text=True, timeout=180)
        if fail:
            assert completed.returncode == 2
            return json.loads(completed.stderr)
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)
    receipt = command('verify-local', '--provider', 'github-actions', '--bundle', str(bundle),
                      '--sha256', sha, '--at', fixture['at'])
    inspected = command('inspect', '--id', receipt['assessment_id'])
    value = inspected['assessment']
    assert value['source_revision'] == args.expected_source and value['source_worktree_clean']
    assert value['node_id'] == settings['node_id'] and value['input_origin'] == 'operator_bundle'
    assert value['verification']['snapshots'] == fixture['expected_initial_snapshots']
    assert value['verification']['measured_containers'] == fixture['expected_measured_containers']
    assert value['evidence_trust'] == 'unverified' and not value['capture']['native_metadata_rechecked']
    assert not value['official_acceptance'] and not inspected['native_metadata_rechecked_now']
    assert command('index')['record_count'] == 0
    first = command('intake', '--id', receipt['assessment_id'])
    assert all(row['status'] == 'recorded' and row['effective_trust'] == 'unverified' for row in first['results'].values())
    again = command('intake', '--id', receipt['assessment_id'])
    assert all(row['status'] == 'idempotent' for row in again['results'].values())
    projection = command('index', '--limit', '1')
    assert projection['record_count'] == 2 and projection['conflict_count'] == 0
    other = command('index', '--limit', '1', '--offset', '1')
    results = {}
    for row in [*projection['records'], *other['records']]:
        assert row['assessment_id'] == receipt['assessment_id']
        assert row['payload'] == fixture['expected_replay_snapshots'][row['evidence_type']]
        assert row['effective_trust'] == 'unverified'
        results[row['evidence_type']] = row['payload']
    assert set(results) == {'sbom', 'vulnerability_scan'}
    archive = prefix / 'instance/state/typed/raw' / sha / 'archives/coverage.zip'
    original = archive.read_bytes()
    archive.write_bytes(original + b'x')
    try:
        results['tamper_rejection'] = command('inspect', '--id', receipt['assessment_id'], fail=True)
        assert results['tamper_rejection']['diagnostics'] == ['typed_archive_bytes_changed']
    finally:
        archive.write_bytes(original)
    verify_source(source)
    instance(prefix / 'instance')
    output = {'schema_version': 1, 'kind': 'installed-typed-intake-partial-parity',
        'source_revision': args.expected_source, 'runtime_source_digest': settings['runtime_source_digest'],
        'node_id': settings['node_id'], 'synthetic': True, 'provider_invoked': False,
        'official_acceptance': False, 'full_functional_parity': False,
        'business_digest': canonical_digest(results), 'results': results}
    args.output.write_text(json.dumps(output, sort_keys=True, indent=2) + '\n')
    args.output.chmod(0o600)
    print(json.dumps({key: value for key, value in output.items() if key != 'results'}, sort_keys=True))


if __name__ == '__main__':
    main()
