"""Installed read-only report parity against original V1 output bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path); parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path); parser.add_argument('--expected-source', required=True)
    args = parser.parse_args(); prefix = args.prefix.resolve()
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    path = args.fixtures / 'reporting-cases.json'
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == bindings[path.name]
    fixture = json.loads(path.read_text()); assert fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    def command(*arguments, expected=0):
        value = subprocess.run([str(prefix / 'axiom-v2'), 'reports', *arguments],
                               capture_output=True, text=True, timeout=180)
        assert value.returncode == expected, value.stderr
        return json.loads(value.stdout if expected == 0 else value.stderr)
    at = '2026-11-15T12:00:00Z'; results = {}
    kinds = {**fixture['expected_outputs'], 'all': {name: raw for files in fixture['expected_outputs'].values()
                                                 for name, raw in files.items()}}
    for kind, files in kinds.items():
        receipt = command('build', '--kind', kind, '--at', at)
        assert not receipt['published'] and not receipt['official_acceptance']
        assert command('build', '--kind', kind, '--at', at)['assessment_id'] == receipt['assessment_id']
        inspected = command('inspect', '--id', receipt['assessment_id'])
        assert inspected['original_sources_and_complete_outputs_reverified']
        value = inspected['assessment']
        assert value['source_revision'] == args.expected_source and value['source_worktree_clean']
        assert value['node_id'] == settings['node_id'] and not value['working_tree_used']
        assert not value['operating_acceptance_inherited'] and not value['authority_transferred']
        directory = Path(receipt['artifact_directory']); actual = {}
        for name, text in files.items():
            raw = (directory / name).read_bytes(); assert raw == text.encode()
            assert hashlib.sha256(raw).hexdigest() == value['files'][name]['sha256']
            actual[name] = raw.decode()
        results[kind] = {'complete_v1_output_bytes_equal': True, 'files': actual,
                         'source_scope': value['source_scope'], 'official_acceptance': False}
        if kind == 'all':
            name = next(iter(files)); path = directory / name; original = path.read_bytes(); path.write_bytes(b'changed')
            assert command('inspect', '--id', receipt['assessment_id'], expected=2)['diagnostics'] == ['derived_report_output_changed']
            path.write_bytes(original)
            assert command('inspect', '--id', receipt['assessment_id'])['original_sources_and_complete_outputs_reverified']
    raw = json.dumps(results, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    value = {'schema_version': 1, 'source_revision': settings['source_revision'], 'node_id': settings['node_id'],
        'runtime_source_digest': settings['runtime_source_digest'], 'source_scope': 'committed-governance-data-v1',
        'provider_invoked': False, 'official_acceptance': False, 'full_functional_parity': False,
        'results': results, 'business_digest': hashlib.sha256(raw).hexdigest()}
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n'); args.output.chmod(0o600)
    print(json.dumps({k: v for k, v in value.items() if k != 'results'}, sort_keys=True))


if __name__ == '__main__': main()
