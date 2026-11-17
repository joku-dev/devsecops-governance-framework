"""Installed full V1 result mappings/indices and private declared intake."""
import argparse
from copy import deepcopy
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
    from lib.portable.contracts import canonical_digest
    from lib.provider_ports import result_index_profile
    from lib import results_projection
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    verify_source(source); instance(prefix / 'instance')
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    fixture_path = args.fixtures / 'general-result-cases.json'
    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == bindings[fixture_path.name]
    fixture = json.loads(fixture_path.read_text())
    assert fixture['synthetic'] and fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    cases = prefix / 'general-result-cases'; cases.mkdir(mode=0o700)
    results = {}

    def command(*arguments, expected=0):
        result = subprocess.run([str(prefix / 'axiom-v2'), *arguments], capture_output=True, text=True, timeout=120)
        assert result.returncode == expected, result.stderr
        return json.loads(result.stdout if expected == 0 else result.stderr)
    def cli(*arguments, expected=0): return command('results', *arguments, expected=expected)

    at = '2026-11-15T12:00:00Z'
    for index, case in enumerate([*fixture['bundle_cases'], *fixture['manual_cases']]):
        root = cases / case['id']; root.mkdir(mode=0o700)
        domain = case.get('domain', 'devsecops'); kind = 'bundle' if 'files' in case else 'manual'
        service = f'https://case-{index}.scm.example'
        metadata = {'schema_version': 1, 'input_kind': kind, 'domain': domain,
            'repository': {'provider': 'synthetic', 'instance': service, 'native_id': 'synthetic-1',
                'path': case['expected_snapshot']['repository_id'], 'url': service + '/' + case['expected_snapshot']['repository_id']},
            'governance_repository': case['governance_repository'], 'parameters': case['metadata']}
        metadata_path = root / 'metadata.json'; metadata_path.write_text(json.dumps(metadata)); metadata_path.chmod(0o600)
        if kind == 'bundle':
            bundle = root / 'bundle'; bundle.mkdir(mode=0o700)
            for name, value in case['files'].items():
                path = bundle / name; path.write_text(json.dumps(value)); path.chmod(0o600)
            sha = cli('describe', '--bundle', str(bundle))['input_sha256']
            assert cli('validate-bundle', '--bundle', str(bundle), '--sha256', sha, '--domain', domain)['validation'] == 'pass'
            receipt = cli('verify-bundle', '--bundle', str(bundle), '--sha256', sha,
                          '--metadata', str(metadata_path), '--at', at)
        else:
            summary = root / 'summary.json'; summary.write_text(json.dumps(case['control_summary'])); summary.chmod(0o600)
            receipt = cli('manual', '--metadata', str(metadata_path), '--summary', str(summary), '--at', at)
        inspected = cli('inspect', '--id', receipt['assessment_id'])
        assert inspected['raw_sources_reverified'] and not inspected['native_metadata_rechecked_now']
        snapshot = inspected['assessment']['snapshots'][domain]
        assert snapshot == case['expected_snapshot']
        admitted = cli('intake', '--id', receipt['assessment_id'])
        assert admitted['results'][domain]['status'] == 'recorded'
        assert admitted['results'][domain]['effective_trust'] == 'unverified'
        assert cli('intake', '--id', receipt['assessment_id'])['results'][domain]['status'] == 'idempotent'
        project = cli('project', '--domain', domain, '--origin', 'operator_bundle', '--scm', 'synthetic',
                      '--service', service, '--event-profile', 'legacy-v1', '--main-branch', 'main', '--at', at)
        value = cli('inspect-project', '--id', project['projection_id'])['projection']
        assert not value['published'] and not value['official_acceptance']
        assert value['reported_index'] == value['effective_index']
        assert value['reported_index']['summary']['result_count'] == 1
        results[case['id']] = {'snapshot': snapshot, 'reported_index': value['reported_index'],
                              'effective_index': value['effective_index']}

    # These complete multi-context report objects were produced in frozen V1,
    # including independent pass/finding and Trust/freshness/replay dimensions.
    data = cases / 'frozen-indices'; data.mkdir(mode=0o700)
    for domain, records in fixture['index_records'].items():
        for row in records:
            path = data / row['path']; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row['payload']))
        expected = fixture['expected_indices'][domain]
        actual = getattr(results_projection, domain + '_index')(data, expected['generated_at'],
            **result_index_profile('legacy-v1', 'main'))
        assert actual == expected
        results['full-v1-index-' + domain] = actual

    # Run after the separately retained typed harness on this same fresh node.
    typed = command('typed', 'index', '--limit', '1')
    assert typed['record_count'] == 2
    descriptor = typed['records'][0]['repository']
    project = cli('project', '--domain', 'typed', '--origin', 'operator_bundle', '--scm', descriptor['provider'],
                  '--service', descriptor['instance'], '--event-profile', 'legacy-v1', '--main-branch', 'main', '--at', at)
    typed_view = cli('inspect-project', '--id', project['projection_id'])['projection']
    assert typed_view['reported_index']['summary']['trust_level_counts'] == {'provenance_verified': 2}
    assert typed_view['effective_index']['summary']['trust_level_counts'] == {'unverified': 2}
    results['typed-reported-index'] = typed_view['reported_index']
    results['typed-effective-index'] = typed_view['effective_index']
    results['boundaries'] = {'origin': 'operator_bundle', 'official_acceptance': False, 'published': False,
                            'raw_sources_reverified': True, 'native_metadata_rechecked_now': False}
    verify_source(source); instance(prefix / 'instance')
    receipt = {'source_revision': args.expected_source, 'runtime_source_digest': settings['runtime_source_digest'],
        'node_id': settings['node_id'], 'synthetic': True, 'provider_invoked': False,
        'official_acceptance': False, 'full_functional_parity': False,
        'results': results, 'business_digest': canonical_digest(results)}
    args.output.write_text(json.dumps(receipt, indent=2) + '\n'); args.output.chmod(0o600)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'results'}))


if __name__ == '__main__': main()
