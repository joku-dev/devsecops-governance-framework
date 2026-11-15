from contextlib import redirect_stdout
from copy import deepcopy
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
from lib.source_collection import collect, persist, snapshot
from lib.functional_parity import git_read
from lib.providers.source_inspection import local_source_signals


SOURCE_FILES = {
    '.github/workflows/ci.yml': 'name: Synthetic CI\njobs: {}\n',
    '.github/workflows/security-audit.yml': 'name: Synthetic security\njobs: {}\n',
    '.governance/devsecops/release-evidence.json': json.dumps({'status': 'approved', 'evidence_refs': ['synthetic-only']}),
    'docs/ARCHITECTURE.md': '# Synthetic\nneo4j ha-sync semantic-enrichment query-api HTTP API owner decision recovery\n',
    'docs/DEPLOYMENT.md': '# Synthetic\nsecret token health-check rollback restart logs\n',
    'docker-compose.yml': 'services:\n  query-api:\n    image: synthetic\n  neo4j:\n    image: synthetic\n',
    'query-api/requirements.txt': 'example==1.0\n',
    'tests/test_security.py': '# Synthetic source, never executed.\n',
    'api/schemas/contract.json': '{}\n',
}


def make_repository(root):
    root.mkdir(mode=0o700)
    for name, text in SOURCE_FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git_read(root, 'init', '--template=', '-q')
    git_read(root, 'add', '.')
    with patch.dict(os.environ, {'GIT_AUTHOR_DATE': '2026-11-15T12:00:00Z', 'GIT_COMMITTER_DATE': '2026-11-15T12:00:00Z'}):
        git_read(root, '-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@localhost',
                 'commit', '-qm', 'Frozen source collection fixture')
    return git_read(root, 'rev-parse', 'HEAD').decode().strip()


class SourceCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repository = self.base / 'repository'
        self.revision = make_repository(self.repository)

    def collect(self, domain='controls'):
        return collect(domain, self.repository, self.revision, ci_profile='github-actions',
                       release_id='synthetic-parity', baseline='synthetic-baseline')

    def test_frozen_v1_inputs_match_both_domains_exactly(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/source-collection.json').read_text())
        self.assertEqual(self.revision, fixture['consumer_fixture_revision'])
        self.assertTrue(fixture['synthetic'])
        for domain in ('controls', 'architecture'):
            value = self.collect(domain)
            self.assertEqual(value['input']['target_repository']['path'], str(self.repository.resolve()))
            payload = deepcopy(value['input'])
            payload['target_repository']['path'] = '<fixture-repository>'
            self.assertEqual(payload, fixture['expected'][domain])
            self.assertFalse(value['working_tree_used'])
            self.assertFalse(value['provider_invoked'])
            self.assertFalse(value['official_acceptance'])
            self.assertEqual(value['evidence_trust'], 'unverified')
            self.assertEqual(set(value['source_files']), set(SOURCE_FILES))

    def test_uncommitted_changes_and_untracked_scripts_are_not_used(self):
        expected = self.collect()
        (self.repository / '.governance/devsecops/release-evidence.json').write_text('{"status":"draft"}')
        (self.repository / 'untracked.py').write_text('raise RuntimeError("never execute inspected code")')
        self.assertEqual(self.collect(), expected)

    def test_revision_must_be_immutable_and_exist(self):
        for revision in ('main', 'HEAD', self.revision[:7], '0' * 40):
            with self.assertRaises(ValueError):
                collect('controls', self.repository, revision, ci_profile='github-actions', release_id='test', baseline='test')

    def test_ambiguous_source_approval_json_is_rejected(self):
        path = self.repository / '.governance/devsecops/release-evidence.json'
        path.write_text('{"status":"candidate","status":"approved"}')
        git_read(self.repository, 'add', '.')
        git_read(self.repository, '-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@localhost',
                 'commit', '-qm', 'Ambiguous JSON rejection fixture')
        revision = git_read(self.repository, 'rev-parse', 'HEAD').decode().strip()
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
            collect('controls', self.repository, revision, ci_profile='github-actions', release_id='test', baseline='test')

    def test_committed_symlink_is_rejected_before_reading_source(self):
        (self.repository / 'escape').symlink_to(self.base / 'external')
        git_read(self.repository, 'add', 'escape')
        git_read(self.repository, '-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@localhost',
                 'commit', '-qm', 'Synthetic symlink rejection fixture')
        revision = git_read(self.repository, 'rev-parse', 'HEAD').decode().strip()
        with self.assertRaisesRegex(ValueError, 'unsafe_collection_source'):
            collect('controls', self.repository, revision, ci_profile='github-actions', release_id='test', baseline='test')

    def test_git_replace_cannot_reinterpret_a_pinned_commit(self):
        before = self.collect()
        (self.repository / '.governance/devsecops/release-evidence.json').write_text('{"status":"draft"}')
        git_read(self.repository, 'add', '.')
        git_read(self.repository, '-c', 'user.name=Synthetic fixture', '-c', 'user.email=fixture@localhost',
                 'commit', '-qm', 'Replacement fixture')
        other = git_read(self.repository, 'rev-parse', 'HEAD').decode().strip()
        git_read(self.repository, 'replace', self.revision, other)
        self.assertEqual(self.collect(), before)

    def test_ci_layouts_are_observed_by_adapters(self):
        self.assertEqual(local_source_signals('github-actions', self.repository),
                         {'ci_definition_present': True, 'security_workflow_present': True})
        (self.repository / '.gitlab-ci.yml').write_text('include: []\n')
        (self.repository / '.gitlab').mkdir()
        (self.repository / '.gitlab/security.yml').write_text('synthetic')
        self.assertEqual(local_source_signals('gitlab-ci', self.repository),
                         {'ci_definition_present': True, 'security_workflow_present': True})
        (self.repository / 'bamboo-specs').mkdir()
        (self.repository / 'bamboo-specs/bamboo.yaml').write_text('synthetic')
        self.assertTrue(local_source_signals('bamboo', self.repository)['ci_definition_present'])
        with self.assertRaisesRegex(ValueError, 'unsupported_source_ci_profile'):
            local_source_signals('unreviewed-provider', self.repository)

    def test_collection_store_is_private_immutable_and_idempotent(self):
        node = self.base / 'node'
        node.mkdir(mode=0o700)
        (node / 'state').mkdir(mode=0o700)
        value = self.collect()
        first = persist(value, node)
        self.assertEqual(persist(value, node), first)
        path = Path(first['input_path'])
        self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(json.loads(path.read_text()), value['input'])
        path.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'immutable_collection_conflict'):
            persist(value, node)

    def test_snapshot_requires_an_empty_destination(self):
        with self.assertRaisesRegex(ValueError, 'fresh_collection_snapshot_required'):
            snapshot(self.repository, self.revision, self.repository)

    def test_collection_store_rejects_symlink_targets(self):
        node = self.base / 'node'
        node.mkdir(mode=0o700)
        (node / 'state').mkdir(mode=0o700)
        (node / 'state/collections').symlink_to(self.repository)
        with self.assertRaisesRegex(ValueError, 'unsafe_collection_state'):
            persist(self.collect(), node)

    def test_instance_collection_can_feed_full_evaluation(self):
        import shutil
        from lib.v2_application import initialize, run
        opa = shutil.which('opa')
        if not opa:
            self.skipTest('Pinned OPA not available')
        node = self.base / 'application-node'
        initialize(node, opa=opa, development=True)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run('collect-source', ['--domain', 'controls', '--repo', str(self.repository),
                '--revision', self.revision, '--ci-profile', 'github-actions'], instance_path=node), 0)
        receipt = json.loads(output.getvalue())
        self.assertFalse(receipt['official_acceptance'])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run('evaluate', ['--domain', 'controls', '--input', receipt['input_path'],
                '--at', '2026-11-15T12:00:00Z'], instance_path=node), 0)
        assessment = json.loads(output.getvalue())
        self.assertEqual(assessment['summary']['total_controls'], 46)
        self.assertFalse(assessment['official_compliance_result'])


if __name__ == '__main__':
    unittest.main()
