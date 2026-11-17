"""Installed original domain JSON/Markdown files and guarded combination parity."""
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
    path = args.fixtures / 'domain-reporting-cases.json'; raw = path.read_bytes()
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == bindings[path.name]
    fixture = json.loads(raw); assert fixture['synthetic'] and fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    at = '2026-11-15T12:00:00Z'; results = {}; root = prefix / 'domain-report-inputs'; root.mkdir(mode=0o700)
    def command(*arguments, expected=0):
        value = subprocess.run([str(prefix / 'axiom-v2'), *arguments], capture_output=True, text=True, timeout=180)
        assert value.returncode == expected, value.stderr
        return json.loads(value.stderr if expected == 2 else value.stdout)
    for case in fixture['cases']:
        ids = {}; files = {}; exits = {}
        for domain, payload in case['inputs'].items():
            path = root / (case['id'] + '-' + domain + '.json'); path.write_text(json.dumps(payload, indent=2) + '\n'); path.chmod(0o600)
            receipt = command('evaluate', '--domain', domain, '--input', str(path), '--at', at)
            ids[domain] = receipt['assessment_id']; assert receipt['mode'] == 'report-only'
            assert not receipt['official_compliance_result'] and receipt['execution'] == 'complete'
            if domain == 'devsecops-release':
                exit_code = case['exits']['fail_on_findings']
                assert command('evaluate', '--domain', domain, '--input', str(path), '--at', at,
                               '--fail-on-findings', expected=exit_code)['assessment_id'] == ids[domain]
                exits = case['exits']
            generated = command('reports', 'domain', '--id', ids[domain], '--at', at)
            value = command('reports', 'inspect-domain', '--id', generated['report_id'])
            assert value['input_records_and_complete_outputs_reverified']
            assert not value['original_input_bytes_reverified'] and not value['native_metadata_rechecked']
            for name, expected in case['outputs'][domain].items():
                raw = (Path(generated['artifact_directory']) / name).read_bytes(); assert raw == expected.encode()
                files[name] = raw.decode()
        generated = command('reports', 'combine', '--architecture-id', ids['architecture'],
                            '--devsecops-id', ids['devsecops-release'], '--at', at)
        value = command('reports', 'inspect-domain', '--id', generated['report_id'])['report']
        assert value['evidence_trust'] == 'unverified' and not value['authority_transferred']
        assert not value['official_acceptance'] and not value['published']
        for name, expected in case['outputs']['combined'].items():
            raw = (Path(generated['artifact_directory']) / name).read_bytes(); assert raw == expected.encode(); files[name] = raw.decode()
        if case['id'] == 'red':
            name = 'combined.md'; path = Path(generated['artifact_directory']) / name; raw = path.read_bytes(); path.write_bytes(b'changed')
            assert command('reports', 'inspect-domain', '--id', generated['report_id'], expected=2)['diagnostics'] == ['domain_report_output_changed']
            path.write_bytes(raw)
        results[case['id']] = {'complete_original_files_equal': True, 'files': files, 'original_exit_codes': exits}
    raw = json.dumps(results, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    value = {'schema_version': 1, 'source_revision': settings['source_revision'], 'node_id': settings['node_id'],
        'runtime_source_digest': settings['runtime_source_digest'], 'synthetic': True, 'full_functional_parity': False,
        'official_acceptance': False, 'provider_invoked': False, 'results': results,
        'business_digest': hashlib.sha256(raw).hexdigest()}
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n'); args.output.chmod(0o600)
    print(json.dumps({k: v for k, v in value.items() if k != 'results'}, sort_keys=True))


if __name__ == '__main__': main()
