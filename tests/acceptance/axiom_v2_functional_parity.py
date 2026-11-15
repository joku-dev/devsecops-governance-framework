"""Installed partial V1 parity acceptance; synthetic fixtures, no provider or authority."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    source = prefix / 'package/source'
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source
    assert not settings['development']
    sys.path.insert(0, str(source / 'scripts'))
    from lib.portable.contracts import canonical_digest
    from lib.v2_distribution import verify_source
    from lib.v2_application import instance
    verify_source(source)
    instance(prefix / 'instance')
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    for name, expected in bindings.items():
        assert digest(args.fixtures / name) == expected
    manifest = json.loads((args.fixtures / 'manifest.json').read_text())
    assert manifest['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    assert manifest['evidence_kind'] == 'frozen_v1_synthetic_golden_reports'

    def command(*arguments, expected=0):
        result = subprocess.run([str(prefix / 'axiom-v2'), *arguments], capture_output=True, text=True, timeout=120)
        assert result.returncode == expected, result.stderr
        value = json.loads(result.stdout if expected == 0 else result.stderr)
        return value

    results = {}
    for case in manifest['cases']:
        path = (args.fixtures / 'inputs' / (case['id'] + '.json')).resolve()
        assert digest(path) == case['input_sha256']
        expected_path = args.fixtures / 'expected' / case['report']
        assert digest(expected_path) == case['report_sha256']
        receipt = command('evaluate', '--domain', case['domain'], '--input', str(path), '--at', '2026-11-15T12:00:00Z')
        assessment_path = prefix / 'instance/state/assessments' / (receipt['assessment_id'] + '.json')
        assessment = json.loads(assessment_path.read_text())
        assert canonical_digest(assessment) == receipt['assessment_id']
        assert assessment['source_revision'] == args.expected_source and assessment['source_worktree_clean']
        assert assessment['mode'] == 'report-only' and assessment['official_compliance_result'] is False
        assert assessment['evidence_trust'] == 'unverified' and assessment['input_sha256'] == case['input_sha256']
        expected_report = json.loads(expected_path.read_text())
        if case['domain'] == 'controls':
            assert assessment['report']['input_file'] == str(path)
            # Only this descriptive path differs from frozen V1's fixture location.
            expected_report['input_file'] = str(path)
        assert assessment['report'] == expected_report
        results[case['id']] = {'v1_report_equal': True, 'summary': assessment['report']['summary'],
                               'input_sha256': case['input_sha256']}

    def requirements(*arguments, expected=0):
        value = command('requirements', '--workspace', 'host-parity', *arguments, expected=expected)
        if expected == 0:
            assert value['authority_scope'] == 'candidate_only' and value['official_acceptance'] is False
        return value

    requirements('init')
    from lib.candidate_workspace import CandidateWorkspace
    workspace = CandidateWorkspace(prefix / 'instance', 'host-parity', node_id=settings['node_id'])
    current, marker = workspace.current()
    import yaml
    catalog_path = 'model/requirements/governance-requirement-catalog.yaml'
    initial_catalog = yaml.safe_load((current / catalog_path).read_text())
    next_id = 'GRQ-' + str(initial_catalog['next_sequence']).zfill(6)
    native = prefix / 'host-parity-native.md'
    native.write_text('---\nid: NATIVE-HOST-PARITY-001\ntitle: Synthetic host parity\n'
                      'normative_strength: MUST\ndomain: devsecops\nowner: synthetic-host-fixture\n'
                      'decision_ref: docs/governance/change-requests/GCR-2026-186-axiom-v2-functional-parity.md\n'
                      '---\nSynthetic candidate changes shall preserve their history.\n')
    native.chmod(0o600)
    requirements('put-native', '--file', str(native), '--name', 'host-parity.md')
    requirements('start-native', '--case-id', 'RLC-HOST-PARITY', '--source-path',
                 'docs/governance/requirements/native-sources/host-parity.md')
    _, before = workspace.current()
    requirements('activate', '--case-id', 'RLC-HOST-PARITY', '--effective-from', '2026-11-15',
                 '--commit', 'synthetic-host-fixture', expected=2)
    assert workspace.current()[1] == before
    requirements('decide', '--case-id', 'RLC-HOST-PARITY', '--proposal-id', 'RLC-HOST-PARITY-P0001',
                 '--disposition', 'approve', '--classification', 'new', '--decided-by', 'synthetic-host-fixture',
                 '--decision-role', 'synthetic-fixture', '--rationale', 'Synthetic test only; no real approval.',
                 '--runtime-enforcement', 'none')
    requirements('activate', '--case-id', 'RLC-HOST-PARITY', '--effective-from', '2026-11-15',
                 '--commit', 'synthetic-host-fixture')
    requirements('generate-publication')
    current, _ = workspace.current()
    catalog = yaml.safe_load((current / catalog_path).read_text())
    created = catalog['requirements'][-1]
    assert created['id'] == next_id and created['active_revision'] == 1
    assert len(catalog['requirements']) == len(initial_catalog['requirements']) + 1
    assert (current / ('docs/governance/requirements/' + next_id + '/v0001.md')).is_file()
    assert (current / ('docs/publishing/governance-requirement-catalog/requirements/' + next_id + '.md')).is_file()
    results['requirements'] = {'created_id': next_id, 'revision': 1, 'undecided_activation_rejected': True,
                               'publication_prepared': True, 'authority_scope': 'candidate_only',
                               'statement': created['revisions'][0]['statement']}

    def dcr(*arguments):
        value = command('dcr', '--workspace', 'host-parity', *arguments)
        assert value['authority_scope'] == 'candidate_only' and value['official_acceptance'] is False
        return value
    structural = dcr('structural', '--review-id', 'host-parity', '--source-id', 'DSCB-STD-REQ-001')
    report = structural['report']
    assert report['reviewed_commit'] is None and report['semantic_review'] == 'not_run'
    assert next(r for r in report['rules'] if r['rule_id'] == 'DCR-009')['status'] == 'fail'
    results['dcr-structure'] = report
    current, _ = workspace.current()
    response = json.loads((args.fixtures / 'not-run-response.json').read_text())
    response['review_id'] = 'host-parity'
    response['source_manifest_sha256'] = digest(current / 'dcr/reviews/host-parity/manifest.json')
    response_path = prefix / 'host-parity-not-run-response.json'
    response_path.write_text(json.dumps(response))
    response_path.chmod(0o600)
    semantic = dcr('semantic', '--review-id', 'host-parity', '--response', str(response_path))['report']
    assert semantic['execution']['status'] == 'not_run' and semantic['human_decisions']['status'] == 'not_run'
    assert not semantic['findings']
    # The manifest contains the explicit node ID; its digest is intentionally host-specific.
    semantic = deepcopy(semantic)
    assert semantic['scope']['source_manifest_sha256'] == response['source_manifest_sha256']
    del semantic['scope']['source_manifest_sha256']
    results['dcr-semantic-not-run'] = semantic
    verify_source(source)
    instance(prefix / 'instance')
    source_status = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True)
    assert not source_status.strip()
    collector = command('collector', 'status')
    assert collector['paused'] and not collector['publisher_active'] and collector['counts'] == {}
    output = {'schema_version': 1, 'kind': 'installed-partial-v1-parity', 'synthetic': True,
              'source_revision': settings['source_revision'], 'runtime_source_digest': settings['runtime_source_digest'],
              'node_id': settings['node_id'], 'opa_sha256': settings['opa_sha256'],
              'full_functional_parity': False, 'official_acceptance': False, 'provider_invoked': False,
              'normalization': ['validated descriptive control input path', 'validated node-bound semantic manifest digest'],
              'business_digest': canonical_digest(results), 'results': results}
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    args.output.chmod(0o600)
    print(json.dumps({k: v for k, v in output.items() if k != 'results'}, sort_keys=True))


if __name__ == '__main__':
    main()
