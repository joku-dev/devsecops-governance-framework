from contextlib import redirect_stdout
from copy import deepcopy
import fcntl
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.candidate_workspace import CandidateWorkspace
from lib.requirement_application import run
from lib.requirement_workspace import RequirementWorkspace
from lib.requirement_lifecycle import load_yaml, write_yaml


NATIVE = '''---
id: NATIVE-PARITY-001
title: Retain candidate audit history
normative_strength: MUST
domain: devsecops
owner: synthetic-owner
decision_ref: docs/governance/change-requests/GCR-PARITY.md
---
Candidate changes shall retain their audit history.
'''


def seed_fixture(root, source):
    for relative in ('model/requirements/lifecycle-cases', 'model/documents',
                     'docs/governance/requirements/native-sources', 'docs/governance/change-requests'):
        (root / relative).mkdir(parents=True, mode=0o700, exist_ok=True)
    catalog = {'schema_version': '1.0.0', 'catalog_id': 'GOVERNANCE-REQUIREMENT-CATALOG',
               'version': '0.1.0', 'next_sequence': 1, 'requirements': []}
    write_yaml(root / 'model/requirements/governance-requirement-catalog.yaml', catalog)
    write_yaml(root / 'model/requirements/requirement-authority-ledger.yaml', {'sources': []})
    write_yaml(root / 'model/documents/source-document-register.yaml', {'documents': []})
    (root / 'docs/governance/change-requests/GCR-PARITY.md').write_text('Synthetic decision fixture.\n')


class RequirementWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.instance = Path(self.temporary.name) / 'instance'
        self.instance.mkdir(mode=0o700)
        (self.instance / 'state').mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-node'}
        self.workspace = CandidateWorkspace(self.instance, 'parity', node_id='synthetic-node')
        with patch('lib.candidate_workspace.seed', seed_fixture):
            self.workspace.initialize(ROOT)
        self.native = Path(self.temporary.name) / 'native.md'
        self.native.write_text(NATIVE)

    def call(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run(['--workspace', 'parity', *arguments], self.instance, self.settings), 0)
        value = json.loads(output.getvalue())
        self.assertEqual(value['authority_scope'], 'candidate_only')
        self.assertIs(value['official_acceptance'], False)
        return value

    def start(self):
        self.call('put-native', '--file', str(self.native), '--name', 'parity.md')
        return self.call('start-native', '--case-id', 'RLC-PARITY', '--source-path',
                         'docs/governance/requirements/native-sources/parity.md')

    def decide(self, enforcement='none'):
        return self.call('decide', '--case-id', 'RLC-PARITY', '--proposal-id', 'RLC-PARITY-P0001',
                         '--decided-by', 'synthetic-owner', '--decision-role', 'owner',
                         '--rationale', 'Synthetic technical fixture', '--disposition', 'approve',
                         '--classification', 'new', '--runtime-enforcement', enforcement)

    def test_native_decision_activation_and_publication_preserve_generations(self):
        started = self.start()
        initial, _ = self.workspace.current()
        before = (initial / 'model/requirements/lifecycle-cases/RLC-PARITY.json').read_bytes()
        self.decide()
        self.call('activate', '--case-id', 'RLC-PARITY', '--effective-from', '2026-11-15', '--commit', 'synthetic')
        self.call('generate-publication')
        current, marker = self.workspace.current()
        catalog = load_yaml(current / 'model/requirements/governance-requirement-catalog.yaml')
        self.assertEqual(catalog['requirements'][0]['id'], 'GRQ-000001')
        self.assertEqual(catalog['requirements'][0]['active_revision'], 1)
        self.assertTrue((current / 'docs/governance/requirements/GRQ-000001/v0001.md').is_file())
        self.assertTrue((current / 'docs/publishing/governance-requirement-catalog/requirements/GRQ-000001.md').is_file())
        self.assertEqual((initial / 'model/requirements/lifecycle-cases/RLC-PARITY.json').read_bytes(), before)
        self.assertNotEqual(marker['generation'], started['generation'])

    def test_complete_native_flow_matches_frozen_v1_files_exactly(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/requirement-native-flow.json').read_text())
        self.assertTrue(fixture['synthetic'])
        self.assertEqual(fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        self.call('put-native', '--file', str(self.native), '--name', 'parity.md')
        with patch('lib.requirement_lifecycle.utc_now', return_value=fixture['at']):
            for operation in fixture['operations']:
                self.call(*operation)
        current, _ = self.workspace.current()
        actual = {p.relative_to(current).as_posix(): p.read_text()
                  for area in ('model/requirements', 'docs/governance/requirements',
                               'docs/publishing/governance-requirement-catalog')
                  for p in (current / area).rglob('*') if p.is_file()}
        self.assertEqual(actual, fixture['expected_files'])

    def test_undecided_and_blocking_operations_rollback(self):
        self.start()
        _, before = self.workspace.current()
        with self.assertRaisesRegex(ValueError, 'explicit decision'):
            self.call('activate', '--case-id', 'RLC-PARITY', '--effective-from', '2026-11-15', '--commit', 'test')
        self.assertEqual(self.workspace.current()[1], before)
        with self.assertRaisesRegex(ValueError, 'separate enforcement'):
            self.decide('blocking')
        self.assertEqual(self.workspace.current()[1], before)

    def test_partial_mutation_failure_does_not_change_visible_generation(self):
        root, before = self.workspace.current()
        original = (root / 'model/requirements/governance-requirement-catalog.yaml').read_bytes()
        def fail(staged):
            (staged / 'model/requirements/governance-requirement-catalog.yaml').write_text('partial mutation')
            raise ValueError('simulated_failure')
        with self.assertRaisesRegex(ValueError, 'simulated_failure'):
            self.workspace.execute(fail, write=True)
        self.assertEqual(self.workspace.current()[1], before)
        self.assertEqual((root / 'model/requirements/governance-requirement-catalog.yaml').read_bytes(), original)

    def test_symlink_and_tampered_generations_fail_closed(self):
        root, _ = self.workspace.current()
        target = root / 'escape'
        target.symlink_to(self.native)
        with self.assertRaisesRegex(ValueError, 'unsafe_candidate_file'):
            self.workspace.current()
        target.unlink()
        (root / 'docs/governance/change-requests/GCR-PARITY.md').write_text('tamper')
        with self.assertRaisesRegex(ValueError, 'candidate_generation_changed'):
            self.workspace.current()

    def test_node_and_runtime_binding_are_required(self):
        foreign = CandidateWorkspace(self.instance, 'parity', node_id='other-node')
        with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
            foreign.current()
        with patch('lib.candidate_workspace.source_digest', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'binding_mismatch'):
                self.workspace.current()

    def test_concurrent_writer_and_traversal_are_rejected(self):
        with self.workspace.lock():
            with self.assertRaisesRegex(ValueError, 'workspace_busy'):
                self.workspace.execute(lambda root: None, write=True)
        with self.assertRaisesRegex(ValueError, 'workspace_name'):
            CandidateWorkspace(self.instance, '../escape', node_id='synthetic-node')
        with self.assertRaisesRegex(ValueError, 'case_id'):
            self.call('next-decision', '--case-id', '../../escape')
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.call('put-native', '--file', str(self.native), '--name', '../../escape.md')

    def test_candidate_registered_source_cannot_be_derived(self):
        def add_candidate(root):
            write_yaml(root / 'model/documents/source-document-register.yaml', {'documents': [
                {'id': 'SRC-CANDIDATE', 'status': 'candidate', 'source_path': 'docs/source.md'}]})
        self.workspace.execute(add_candidate, write=True)
        _, before = self.workspace.current()
        with self.assertRaisesRegex(ValueError, 'source must be approved'):
            self.call('import-source', '--case-id', 'RLC-CANDIDATE', '--source-id', 'SRC-CANDIDATE')
        self.assertEqual(self.workspace.current()[1], before)

    def test_source_migration_keeps_decision_and_completion_gates(self):
        def add_approved_fixture(root):
            path = root / 'docs/governance/source-documents/synthetic.md'
            path.parent.mkdir(parents=True, mode=0o700)
            path.write_text('| ID | Strength | Context | Requirement |\n|---|---|---|---|\n'
                            '| `DSCB-L1-REQ-999` | MUST | Audit | Retain synthetic evidence. |\n')
            write_yaml(root / 'model/documents/source-document-register.yaml', {'documents': [{
                'id': 'SRC-APPROVED-001', 'status': 'approved', 'source_path': path.relative_to(root).as_posix(),
                'owner': 'synthetic-owner', 'version': '1.0', 'governance_domains': ['devsecops']}]})
        self.workspace.execute(add_approved_fixture, write=True)
        self.call('import-source', '--case-id', 'RLC-SOURCE', '--source-id', 'SRC-APPROVED-001')
        self.call('next-decision', '--case-id', 'RLC-SOURCE')
        _, before = self.workspace.current()
        with self.assertRaises(ValueError):
            self.call('complete-migration', '--case-id', 'RLC-SOURCE', '--catalog-release',
                      'requirement-catalog-v0.1.0', '--effective-from', '2026-11-15',
                      '--decision-ref', 'docs/governance/change-requests/GCR-PARITY.md')
        self.assertEqual(self.workspace.current()[1], before)
        self.call('decide', '--case-id', 'RLC-SOURCE', '--proposal-id', 'RLC-SOURCE-P0001',
                  '--decided-by', 'synthetic-owner', '--decision-role', 'owner', '--rationale', 'Synthetic fixture',
                  '--disposition', 'approve', '--classification', 'new')
        self.call('activate', '--case-id', 'RLC-SOURCE', '--effective-from', '2026-11-15',
                  '--commit', 'synthetic', '--proposal-id', 'RLC-SOURCE-P0001')
        completed = self.call('complete-migration', '--case-id', 'RLC-SOURCE', '--catalog-release',
                             'requirement-catalog-v0.1.0', '--effective-from', '2026-11-15',
                             '--decision-ref', 'docs/governance/change-requests/GCR-PARITY.md')
        current, _ = self.workspace.current()
        ledger = load_yaml(current / 'model/requirements/requirement-authority-ledger.yaml')
        self.assertEqual(ledger['sources'][0]['authority_mode'], 'git_authoritative')
        self.assertIs(completed['official_acceptance'], False)
        self.assertEqual(completed['authority_scope'], 'candidate_only')

    def test_full_application_binds_real_committed_data_without_source_mutation(self):
        import shutil
        from lib.v2_application import initialize, run as application_run
        opa = shutil.which('opa')
        if not opa:
            self.skipTest('Pinned OPA not available')
        node = Path(self.temporary.name) / 'application-node'
        initialize(node, opa=opa, development=True)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(application_run('requirements', ['--workspace', 'real-data', 'init'], instance_path=node), 0)
            self.assertEqual(application_run('requirements', ['--workspace', 'real-data', 'report'], instance_path=node), 0)
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertTrue(all(row['official_acceptance'] is False for row in rows))
        self.assertTrue(any(line.startswith('Canonical requirements: ') for line in rows[-1]['messages']))
        self.assertFalse((node / 'state/workspaces/real-data/.git').exists())

    def test_read_only_report_does_not_change_generation(self):
        _, marker = self.workspace.current()
        report = self.call('report')
        self.assertEqual(report['generation'], marker['generation'])
        self.assertIn('Canonical requirements: 0', report['messages'])

    def test_existing_workspace_is_never_reset(self):
        _, marker = self.workspace.current()
        with self.assertRaisesRegex(ValueError, 'fresh_candidate_workspace_required'):
            self.workspace.initialize(ROOT)
        self.assertEqual(self.workspace.current()[1], marker)


if __name__ == '__main__':
    unittest.main()
