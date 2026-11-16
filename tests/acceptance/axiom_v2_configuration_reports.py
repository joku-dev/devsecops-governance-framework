"""Installed explicit native-source signature profile; no live configuration claim."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path); parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path); parser.add_argument('--expected-source', required=True)
    parser.add_argument('--provider', required=True)
    args = parser.parse_args(); prefix = args.prefix.resolve()
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    path = args.fixtures / 'configuration-readiness-cases.json'; raw = path.read_bytes()
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == bindings[path.name]
    fixture = json.loads(raw); assert fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    profile = fixture['source_configuration_profile']; assert args.provider == profile['provider'] and profile['source_signature_only']
    at = '2026-11-15T12:00:00Z'
    def command(*arguments, expected=0):
        result = subprocess.run([str(prefix / 'axiom-v2'), 'reports', *arguments], capture_output=True, text=True, timeout=180)
        assert result.returncode == expected, result.stderr
        return json.loads(result.stderr if expected == 2 else result.stdout)
    arguments = ['configuration', '--kind', 'multi-consumer-readiness', '--provider', args.provider, '--at', at]
    receipt = command(*arguments); again = command(*arguments, '--fail-on-findings')
    assert receipt['assessment_id'] == again['assessment_id'] and receipt['configuration_ready']
    assert receipt['source_signature_only'] and not receipt['official_acceptance'] and not receipt['published']
    inspected = command('inspect', '--id', receipt['assessment_id'])
    assert inspected['original_sources_and_complete_outputs_reverified'] and not inspected['native_metadata_rechecked']
    value = inspected['assessment']; assert value['source_configuration_profile'] == profile
    assert value['source_revision'] == args.expected_source and value['source_worktree_clean']
    assert value['node_id'] == settings['node_id'] and not value['provider_invoked']
    for flag in ['official_acceptance', 'production_approval', 'risk_acceptance', 'authority_transferred', 'operating_acceptance_inherited']:
        assert value[flag] is False
    results = {}; actual = {}
    for name, text in fixture['cases'][-1]['expected_outputs']['multi-consumer-readiness'].items():
        raw = (Path(receipt['artifact_directory']) / name).read_bytes(); assert raw == text.encode()
        actual[name] = raw.decode(); assert hashlib.sha256(raw).hexdigest() == value['files'][name]['sha256']
    results['explicit-source-configuration'] = {'complete_original_file_bytes_equal': True, 'files': actual,
        'source_configuration_profile': profile, 'live_effective_configuration_verified': False, 'official_acceptance': False}
    path = Path(receipt['artifact_directory']) / 'generated/reports/multi-consumer-readiness.md'
    original = path.read_bytes(); path.write_bytes(b'changed')
    assert command('inspect', '--id', receipt['assessment_id'], expected=2)['diagnostics'] == ['derived_report_output_changed']
    path.write_bytes(original)
    assert command('inspect', '--id', receipt['assessment_id'])['original_sources_and_complete_outputs_reverified']
    # The generic all-profile must retain its provider-independent selection.
    generic = command('build', '--kind', 'all', '--at', at)
    generic_value = command('inspect', '--id', generic['assessment_id'])['assessment']
    assert generic_value['source_configuration_profile'] is None and len(generic_value['files']) == 35
    assert not any('multi-consumer-readiness' in name for name in generic_value['files'])
    results['generic-all-separate'] = {'files': sorted(generic_value['files']), 'source_configuration_profile': None}
    raw = json.dumps(results, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    value = {'schema_version': 1, 'source_revision': settings['source_revision'], 'runtime_source_digest': settings['runtime_source_digest'],
        'node_id': settings['node_id'], 'provider_invoked': False, 'official_acceptance': False,
        'full_functional_parity': False, 'results': results, 'business_digest': hashlib.sha256(raw).hexdigest()}
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n'); args.output.chmod(0o600)
    print(json.dumps({k: v for k, v in value.items() if k != 'results'}, sort_keys=True))


if __name__ == '__main__': main()
