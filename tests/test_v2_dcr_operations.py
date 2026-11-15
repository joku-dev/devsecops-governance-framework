"""Frozen V1 DCR operating flows and technical source/authority boundaries."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.candidate_workspace import CandidateWorkspace
from lib.dcr_application import run
from lib.dcr_catalog import prepare
from lib.dcr_manifest import build_manifest
from lib.dcr_operations import validate, plan_scope, classify_transition
from lib.dcr_projection import validate_decisions
from lib.dcr_source_context import git_head, repository_revision, require_committed_source
from lib.dcr_structure import validate_model
from lib.document_consistency_view import build_redacted_snapshot
from generate_document_consistency_review_model import generate_model


def source_fixture(root, fixture):
    root.mkdir(mode=0o700)
    for name, raw in fixture['source_files'].items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw)
    env = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_COUNT': '0', 'GIT_AUTHOR_NAME': 'AXIOM synthetic fixture',
           'GIT_AUTHOR_EMAIL': 'fixture@example.invalid', 'GIT_COMMITTER_NAME': 'AXIOM synthetic fixture',
           'GIT_COMMITTER_EMAIL': 'fixture@example.invalid', 'GIT_AUTHOR_DATE': '2026-11-15T12:00:00Z',
           'GIT_COMMITTER_DATE': '2026-11-15T12:00:00Z'}
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_CONFIG_PARAMETERS'):
        env.pop(key, None)
    def git(*args):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', *args],
            cwd=root, env=env, stderr=subprocess.DEVNULL).decode().strip()
    git('init', '-b', 'main'); git('add', '.'); git('commit', '-m', 'Frozen synthetic DCR source')
    assert git('rev-parse', 'HEAD') == fixture['source_revision']
    return git


class DcrOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/dcr-operations-cases.json').read_text())
        self.source = self.base / 'source'
        self.git = source_fixture(self.source, self.fixture)
        self.instance = self.base / 'instance'; self.instance.mkdir(mode=0o700)
        (self.instance / 'state').mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-dcr-operations-node'}
        self.workspace = CandidateWorkspace(self.instance, 'operations', node_id=self.settings['node_id'])
        self.workspace.initialize(self.source)

    def call(self, *args):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(run(['--workspace', 'operations', *args], self.instance, self.settings), 0)
        result = json.loads(stream.getvalue())
        self.assertEqual(result['authority_scope'], 'candidate_only')
        self.assertIs(result['official_acceptance'], False)
        return result

    def inputs(self):
        for name in ('manifest', 'report'):
            (self.base / (name + '.json')).write_text(json.dumps(self.fixture[name], ensure_ascii=False, indent=2) + '\n')
        paths = []
        for i, decision in enumerate(self.fixture['decisions']):
            path = self.base / f'decision-{i}.json'; path.write_text(json.dumps(decision)); paths.append(path)
        return self.base / 'manifest.json', self.base / 'report.json', paths

    def test_complete_operations_and_scope_outputs_equal_frozen_v1(self):
        self.assertTrue(self.fixture['synthetic'])
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        self.assertEqual(validate(), self.fixture['operations'])
        matrix = json.loads((ROOT / 'model/governance/document-consistency/trigger-scope-matrix-v1.json').read_text())
        for case in self.fixture['scopes']:
            self.assertEqual(plan_scope(matrix, case['change_types'], impact_known=case['impact_known']), case['expected'])
        before = self.workspace.current()[1]
        self.assertEqual(self.call('operations')['operations'], self.fixture['operations'])
        self.assertEqual(self.call('scope', '--change-type', 'unknown-change')['scope'], self.fixture['scopes'][-1]['expected'])
        self.assertEqual(self.workspace.current()[1], before)

    def test_catalog_package_and_all_provider_input_hashes_equal_v1(self):
        package_root = self.base / 'catalog'
        self.assertEqual(prepare(package_root), self.fixture['catalog'])
        actual = {p.relative_to(package_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in package_root.rglob('*') if p.is_file()}
        self.assertEqual(actual, self.fixture['catalog_files'])
        value = self.call('prepare-catalog', '--review-id', 'prepared-not-run')
        self.assertEqual(value['package'], self.fixture['catalog'])
        self.assertFalse(value['provider_invoked'])
        before = self.workspace.current()[1]
        with self.assertRaises(ValueError): self.call('prepare-catalog', '--review-id', 'prepared-not-run')
        self.assertEqual(self.workspace.current()[1], before)

    def test_manifest_structure_and_redacted_projection_equal_v1(self):
        manifest = build_manifest(self.source, ['SYN-SRC-A-001', 'SYN-SRC-B-001'],
                                  repository=self.fixture['manifest']['repository'])
        self.assertEqual(manifest, self.fixture['manifest'])
        model = generate_model(self.source, manifest)
        self.assertEqual(validate_model(self.source, manifest, model), self.fixture['structure'])
        mp, _, paths = self.inputs()
        validate_decisions(self.fixture['report'], manifest, mp, paths)
        actual = build_redacted_snapshot(self.source, self.fixture['report'], manifest, mp.read_bytes(), 3)
        self.assertEqual(actual, self.fixture['projection'])
        self.assertFalse(actual['documents']); self.assertFalse(actual['scope']['source_ids'])
        self.assertIsNone(actual['semantic_comparison_coverage']['population_count'])

    def test_committed_source_is_explicit_and_keeps_candidate_authority(self):
        with patch('lib.dcr_application.ROOT', self.source):
            result = self.call('structural', '--review-id', 'committed-source', '--context', 'committed-source',
                               '--source-id', 'SYN-SRC-A-001', '--source-id', 'SYN-SRC-B-001')
        self.assertEqual(result['report']['reviewed_commit'], self.fixture['source_revision'])
        self.assertEqual(next(r for r in result['report']['rules'] if r['rule_id'] == 'DCR-009')['status'], 'pass')
        current, _ = self.workspace.current()
        self.assertEqual(json.loads((current / 'dcr/reviews/committed-source/context.json').read_text()),
                         {'kind': 'committed-source', 'source_revision': self.fixture['source_revision']})
        # The next operation cannot silently switch to another source revision or changed bytes.
        source = self.source / 'docs/governance/source-documents/SYN-SRC-A-001.requirements.md'
        source.write_text(source.read_text() + '\nChanged\n')
        before = self.workspace.current()[1]
        with patch('lib.dcr_application.ROOT', self.source), self.assertRaisesRegex(ValueError, 'committed_dcr_source'):
            self.call('evaluate', '--review-id', 'committed-source', '--catalog-version', 'v1')
        self.assertEqual(self.workspace.current()[1], before)

    def test_candidate_cannot_inherit_an_enclosing_checkout_commit(self):
        child = self.source / 'private-candidate'; child.mkdir()
        self.assertIsNone(git_head(child)); self.assertIsNone(repository_revision(child))
        with self.assertRaises(ValueError): require_committed_source(child)

    def test_hidden_source_change_is_not_clean_even_with_index_skip_bit(self):
        self.assertEqual(repository_revision(self.source), self.fixture['source_revision'])
        name = 'docs/governance/source-documents/SYN-SRC-A-001.requirements.md'
        self.git('update-index', '--skip-worktree', name)
        (self.source / name).write_text('Changed behind skip-worktree\n')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertIsNone(repository_revision(self.source))

    def test_projection_is_private_exact_v1_and_does_not_publish_asserted_decisions(self):
        mp, report, paths = self.inputs()
        args = ['project', '--review-id', self.fixture['report']['review_id'], '--manifest', str(mp),
                '--report', str(report), '--comparison-count', '3']
        for path in paths: args.extend(['--decision', str(path)])
        with patch('lib.dcr_application.ROOT', self.source): result = self.call(*args)
        self.assertEqual(result['snapshot'], self.fixture['projection'])
        self.assertFalse(result['published']); self.assertFalse(result['decision_identity_authenticated'])
        self.assertFalse((self.source / 'status/document-consistency-public-projection.json').exists())
        current, _ = self.workspace.current()
        self.assertFalse(list((current / 'dcr').rglob('decision*.json')))
        self.assertFalse(list((current / 'dcr').rglob('report.json')))

    def test_missing_duplicate_changed_decisions_and_stale_sources_are_rejected(self):
        mp, _, paths = self.inputs()
        report = self.fixture['report']; manifest = self.fixture['manifest']
        for selected in ([], paths + paths):
            with self.assertRaises(ValueError): validate_decisions(report, manifest, mp, selected)
        decision = json.loads(paths[0].read_text()); decision['finding_sha256'] = '0' * 64
        paths[0].write_text(json.dumps(decision))
        with self.assertRaisesRegex(ValueError, 'finding hash'): validate_decisions(report, manifest, mp, paths)
        source = self.source / manifest['source_documents'][0]['source_path']; source.write_text('Changed\n')
        with self.assertRaisesRegex(ValueError, 'source bytes do not match|stale'):
            build_redacted_snapshot(self.source, report, manifest, mp.read_bytes(), 3)

    def test_non_reassessment_never_resolves_a_finding(self):
        previous = {'state': 'new', 'severity': 'low', 'source_ids': ['A']}
        self.assertEqual(classify_transition(previous, None, reassessed=False), 'not_reassessed')
        self.assertEqual(classify_transition(previous, None, reassessed=True), 'resolved')
        self.assertEqual(classify_transition(previous, {**previous, 'severity': 'high'}, reassessed=True), 'worsened')
        self.assertEqual(classify_transition({**previous, 'state': 'resolved'}, previous, reassessed=True), 'reopened')


if __name__ == '__main__': unittest.main()
