"""Installed full measured/supplement parity against frozen synthetic V1 cases.

Run with the installed environment and prepared trusted fixtures in a fresh node.
No provider request, deployment or source approval occurs.
"""
import argparse
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
    from lib.provider_ports import measured_export
    from lib.v2_application import instance
    from lib.v2_distribution import verify_source
    verify_source(source)
    _, settings = instance(prefix / 'instance')
    assert settings['source_revision'] == args.expected_source and not settings['development']
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    values = {}
    for name in ('measured-native-cases.json', 'supplement-cases.json'):
        raw = (args.fixtures / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == bindings[name]
        values[name] = json.loads(raw)
        assert values[name]['synthetic']
        assert values[name]['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    raw = values['measured-native-cases.json']['input']
    captured = (raw['run'], raw['report'].encode(), raw['report_artifact'],
        {name: ({key: value.encode() for key, value in item['files'].items()}, item['artifact'])
         for name, item in raw['bundles'].items()}, raw['traceability'].encode())
    def command(*arguments, fail=False):
        completed = subprocess.run([str(prefix / 'axiom-v2'), *arguments], capture_output=True, text=True, timeout=180)
        if fail:
            assert completed.returncode == 2, (completed.returncode, completed.stderr)
            return json.loads(completed.stderr)
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)
    results = {}
    for kind, key in [('l1', 'expected_l1'), ('containers', 'expected_containers')]:
        bundle = prefix / ('acceptance-measured-' + kind)
        sha = measured_export('github-actions', captured, bundle, kind)
        receipt = command('measured', 'verify-local', '--provider', 'github-actions', '--kind', kind,
            '--bundle', str(bundle), '--sha256', sha, '--at', '2026-09-16T11:00:00Z')
        value = json.loads((prefix / 'instance/state/measured/assessments' / (receipt['assessment_id'] + '.json')).read_text())
        assert value['report'] == values['measured-native-cases.json'][key]
        assert value['evidence_trust'] == 'unverified' and not value['capture']['native_metadata_rechecked']
        results['measured-' + kind] = value['report']
        if kind == 'l1':
            measured_id = receipt['assessment_id']
    fixture = values['supplement-cases.json']
    raw = fixture['input']
    bundle = prefix / raw['bundle_name']
    bundle.mkdir(mode=0o700)
    for name, contents in raw['files'].items():
        target = bundle / name
        target.write_text(contents)
        target.chmod(0o600)
    common = ['--measured', measured_id, '--at', raw['at']]
    assurance = command('supplement', 'assurance', *common)
    staging = command('supplement', 'staging', *common, '--bundle', str(bundle),
        '--evidence-repository-commit', raw['evidence_repository_commit'])
    consolidated = command('supplement', 'consolidate', *common, '--staging', staging['supplement_id'])
    for kind, receipt in [('assurance', assurance), ('staging', staging), ('consolidated', consolidated)]:
        value = command('supplement', 'inspect', '--id', receipt['supplement_id'])
        assert value['node_id'] == settings['node_id'] and value['source_worktree_clean']
        assert value['report'] == fixture['expected_' + kind]
        assert value['reported_trust_only'] and value['evidence_trust'] == 'unverified'
        for flag in ('official_acceptance', 'authority_transferred', 'production_approval', 'risk_acceptance'):
            assert value[flag] is False
        results[kind] = value['report']
    before = sorted(p.name for p in (prefix / 'instance/state/supplements/assessments').iterdir())
    results['negative-wrong-source'] = command('supplement', 'consolidate', *common,
        '--staging', assurance['supplement_id'], fail=True)
    results['negative-stale'] = command('supplement', 'staging', '--measured', measured_id,
        '--at', '2026-10-01T11:00:00Z', '--bundle', str(bundle),
        '--evidence-repository-commit', raw['evidence_repository_commit'], fail=True)
    assert before == sorted(p.name for p in (prefix / 'instance/state/supplements/assessments').iterdir())
    verify_source(source)
    instance(prefix / 'instance')
    output = {'schema_version': 1, 'kind': 'installed-measured-supplement-partial-parity',
        'source_revision': args.expected_source, 'runtime_source_digest': settings['runtime_source_digest'],
        'node_id': settings['node_id'], 'synthetic': True, 'provider_invoked': False,
        'full_functional_parity': False, 'official_acceptance': False,
        'business_digest': canonical_digest(results), 'results': results}
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    args.output.chmod(0o600)
    print(json.dumps({key: value for key, value in output.items() if key != 'results'}, sort_keys=True))


if __name__ == '__main__':
    main()
