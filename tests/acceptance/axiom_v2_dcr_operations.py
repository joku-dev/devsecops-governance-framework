"""Installed DCR operating contracts and frozen V1 redaction; no provider invocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    prefix = args.prefix.resolve(); source = prefix / 'package/source'
    sys.path.insert(0, str(source / 'scripts'))
    from lib.v2_application import instance
    from lib.v2_distribution import verify_source
    from lib.portable.contracts import canonical_digest
    from lib.dcr_catalog import prepare
    from lib.dcr_projection import validate_decisions
    from lib.document_consistency_view import build_redacted_snapshot
    from lib.dcr_source_context import repository_revision
    settings = json.loads((prefix / 'instance/instance.json').read_text())
    assert settings['source_revision'] == args.expected_source and not settings['development']
    verify_source(source); instance(prefix / 'instance')
    bindings = json.loads((args.fixtures / 'bindings.json').read_text())
    path = args.fixtures / 'dcr-operations-cases.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == bindings[path.name]
    fixture = json.loads(path.read_text())
    assert fixture['synthetic'] and fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'

    def command(*arguments, expected=0):
        result = subprocess.run([str(prefix / 'axiom-v2'), *arguments], capture_output=True, text=True, timeout=120)
        assert result.returncode == expected, result.stderr
        return json.loads(result.stdout if expected == 0 else result.stderr)

    command('requirements', '--workspace', 'host-dcr-operations', 'init')
    def dcr(*arguments, expected=0):
        result = command('dcr', '--workspace', 'host-dcr-operations', *arguments, expected=expected)
        if expected == 0:
            assert result['authority_scope'] == 'candidate_only' and not result['official_acceptance']
        return result
    operations = dcr('operations')
    assert operations['operations'] == fixture['operations'] and not operations['provider_invoked']
    for case in fixture['scopes']:
        arguments = ['scope']
        for kind in case['change_types']: arguments += ['--change-type', kind]
        if not case['impact_known']: arguments += ['--impact-unknown']
        assert dcr(*arguments)['scope'] == case['expected']
    prepared = dcr('prepare-catalog', '--review-id', 'host-catalog')
    assert prepared['package'] == fixture['catalog'] and not prepared['provider_invoked']
    from lib.candidate_workspace import CandidateWorkspace
    workspace = CandidateWorkspace(prefix / 'instance', 'host-dcr-operations', node_id=settings['node_id'])
    current, before = workspace.current()
    prepared_root = current / 'dcr/catalog-runs/host-catalog'
    assert {p.relative_to(prepared_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in prepared_root.rglob('*') if p.is_file()} == fixture['catalog_files']
    dcr('prepare-catalog', '--review-id', 'host-catalog', expected=2)
    assert workspace.current()[1] == before
    committed = dcr('structural', '--review-id', 'host-committed-source', '--context', 'committed-source',
                    '--source-id', 'DSCB-STD-REQ-001')['report']
    assert committed['reviewed_commit'] == args.expected_source and committed['semantic_review'] == 'not_run'
    assert next(r for r in committed['rules'] if r['rule_id'] == 'DCR-009')['status'] == 'pass'
    # Synthetic source and expected public redaction were independently generated
    # in frozen V1; this tests the installed domain, not a live human review.
    with tempfile.TemporaryDirectory(prefix='dcr-v1-golden-', dir=prefix) as temporary:
        base = Path(temporary); root = base / 'source'; root.mkdir()
        for name, raw in fixture['source_files'].items():
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(raw)
        env = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_COUNT': '0', 'GIT_AUTHOR_NAME': 'AXIOM synthetic fixture',
               'GIT_AUTHOR_EMAIL': 'fixture@example.invalid', 'GIT_COMMITTER_NAME': 'AXIOM synthetic fixture',
               'GIT_COMMITTER_EMAIL': 'fixture@example.invalid', 'GIT_AUTHOR_DATE': '2026-11-15T12:00:00Z',
               'GIT_COMMITTER_DATE': '2026-11-15T12:00:00Z'}
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_CONFIG_PARAMETERS'): env.pop(key, None)
        for arguments in (('init', '-b', 'main'), ('add', '.'), ('commit', '-m', 'Frozen synthetic DCR source')):
            subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *arguments], cwd=root, env=env,
                           capture_output=True, check=True, timeout=30)
        assert repository_revision(root) == fixture['source_revision']
        manifest_path = base / 'manifest.json'
        manifest_path.write_text(json.dumps(fixture['manifest'], ensure_ascii=False, indent=2) + '\n')
        decisions = []
        for index, decision in enumerate(fixture['decisions']):
            target = base / f'decision-{index}.json'; target.write_text(json.dumps(decision)); decisions.append(target)
        validate_decisions(fixture['report'], fixture['manifest'], manifest_path, decisions)
        projection = build_redacted_snapshot(root, fixture['report'], fixture['manifest'], manifest_path.read_bytes(), 3)
        assert projection == fixture['projection']
        changed = root / fixture['manifest']['source_documents'][0]['source_path']; changed.write_text('Changed source\n')
        assert repository_revision(root) is None
        try: build_redacted_snapshot(root, fixture['report'], fixture['manifest'], manifest_path.read_bytes(), 3)
        except ValueError: pass
        else: raise AssertionError('stale source was accepted')
    verify_source(source); instance(prefix / 'instance')
    results = {'operations': operations['operations'], 'catalog': prepared['package'], 'scopes': fixture['scopes'],
               'projection': projection, 'committed_source': {'commit_bound': True, 'DCR-009': 'pass',
                   'source_commit_is_technical_provenance': True}, 'stale_source_rejected': True,
               'candidate_authority_only': True, 'provider_invoked': False}
    receipt = {'schema_version': 1, 'source_revision': args.expected_source, 'node_id': settings['node_id'],
               'results': results, 'results_digest': canonical_digest(results), 'public_files_written': False}
    args.output.write_text(json.dumps(receipt, indent=2) + '\n'); args.output.chmod(0o600)
    print(json.dumps({'results_digest': receipt['results_digest'], 'dcr_v1_equal': True, 'public_files_written': False}))


if __name__ == '__main__': main()
