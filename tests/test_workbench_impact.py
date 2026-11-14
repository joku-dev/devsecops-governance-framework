"""Regression tests for exact, read-only private impact hints."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib.workbench_impact import ImpactProjection


class ImpactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = {'id': 'TEST-SRC-001', 'status': 'approved', 'source_path': 'docs/source.md'}
        self.write('docs/source.md', '[TEST-REQ-001] Evidence shall be retained.')
        self.source_hash = self.hash('docs/source.md')
        self.write('docs/decision.md', 'Recorded human approval')
        self.write('docs/equivalence.json', '{}')
        self.write('policies/check.rego', 'package test')
        self.row = {'id': 'row-one', 'source_requirement_id': 'TEST-REQ-001',
                    'statement': 'Evidence shall be retained.', 'identification_class': 'explicit_identifier'}
        self.proposal = {'source_requirement_id': 'TEST-REQ-001', 'statement': '[TEST-REQ-001] Evidence shall be retained.',
                         'decision': {'disposition': 'approve', 'decision_ref': 'docs/decision.md'},
                         'activation': {'requirement_id': 'GRQ-000001', 'revision': 1}}
        self.case = {'source': {'source_id': self.source['id'], 'source_path': self.source['source_path'],
                               'source_sha256': self.source_hash}, 'proposals': [self.proposal]}
        self.canonical = {'revision': 1, 'status': 'effective', 'source_refs': ['TEST-REQ-001'],
                          'statement': self.proposal['statement'], 'authorized_derivations': ['policies'],
                          'decision_ref': 'docs/decision.md'}
        self.catalog = {'requirements': [{'id': 'GRQ-000001', 'active_revision': 1, 'revisions': [self.canonical]}]}
        self.mapping = {'id': 'RTA-000001', 'requirement_ref': 'GRQ-000001@rev1',
                        'source_requirement_refs': ['TEST-REQ-001'],
                        'artifact': {'path': 'policies/check.rego', 'type': 'policies', 'sha256': self.hash('policies/check.rego')},
                        'decision': {'status': 'effective', 'equivalence': 'equivalent',
                                     'decision_ref': 'docs/decision.md', 'equivalence_evidence': ['docs/equivalence.json']},
                        'enforcement': 'blocking'}
        self.mappings = [self.mapping]

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)

    def hash(self, path):
        return hashlib.sha256((self.root / path).read_bytes()).hexdigest()

    def project(self):
        self.write('model/requirements/lifecycle-cases/case.json', json.dumps(self.case))
        self.write('model/requirements/governance-requirement-catalog.yaml', yaml.safe_dump(self.catalog))
        self.write('model/requirements/requirement-to-artifact-register.yaml', yaml.safe_dump({'entries': self.mappings}))
        return ImpactProjection(self.root).project(self.source, self.source_hash, [self.row], [self.source])['row-one']

    def test_exact_confirmed_mapping_is_review_need_not_execution_or_low_risk(self):
        result = self.project()
        self.assertEqual(result['risk'], 'review_required')
        self.assertEqual(result['requirement_ref'], 'GRQ-000001@rev1')
        self.assertTrue(result['mappings'][0]['confirmed'])
        self.assertEqual(result['mappings'][0]['enforcement_authorization'], 'blocking')
        self.assertIn('Kein anforderungsbezogener', result['runtime'])
        self.assertNotIn('high', json.dumps(result))
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.project()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_missing_mapping_is_unknown(self):
        self.mappings = []
        result = self.project()
        self.assertEqual(result['risk'], 'unknown')
        self.assertEqual(result['requirement_ref'], 'GRQ-000001@rev1')

    def test_partial_mapping_never_claims_complete_coverage(self):
        self.mapping['decision']['equivalence'] = 'partial'
        result = self.project()
        self.assertEqual(result['risk'], 'review_required')
        self.assertEqual(result['mappings'][0]['coverage'], 'partial')
        self.assertTrue(any('teilweise' in r for r in result['reasons']))

    def test_source_hash_status_and_statement_each_gate_approval(self):
        original = copy.deepcopy((self.source, self.case, self.row))
        for change in ('source_hash', 'candidate', 'statement', 'activation', 'rejected', 'case_path'):
            with self.subTest(change=change):
                self.source, self.case, self.row = copy.deepcopy(original)
                if change == 'source_hash': self.case['source']['source_sha256'] = '0' * 64
                if change == 'candidate': self.source['status'] = 'candidate'
                if change == 'statement': self.row['statement'] = 'Another requirement shall apply.'
                if change == 'activation': self.case['proposals'][0]['activation'] = None
                if change == 'rejected': self.case['proposals'][0]['decision']['disposition'] = 'reject'
                if change == 'case_path': self.case['source']['source_path'] = 'another.md'
                result = self.project()
                self.assertEqual(result['risk'], 'unknown')
                self.assertIsNone(result['requirement_ref'])

    def test_wrong_revision_duplicate_catalog_and_duplicate_lifecycle_fail_closed(self):
        self.canonical['revision'] = 2
        self.assertIsNone(self.project()['requirement_ref'])
        self.canonical['revision'] = 1
        self.catalog['requirements'].append(copy.deepcopy(self.catalog['requirements'][0]))
        self.assertIsNone(self.project()['requirement_ref'])
        self.catalog['requirements'].pop()
        self.case['proposals'].append(copy.deepcopy(self.proposal))
        self.assertIsNone(self.project()['requirement_ref'])

    def test_tampered_artifact_missing_evidence_and_unauthorized_type_are_unknown(self):
        original = copy.deepcopy(self.mapping)
        for change in ('hash', 'path', 'symlink', 'decision', 'evidence', 'scope', 'type', 'equivalence', 'duplicate'):
            with self.subTest(change=change):
                self.mapping = copy.deepcopy(original); self.mappings = [self.mapping]
                if change == 'hash': self.mapping['artifact']['sha256'] = '0' * 64
                if change == 'path': self.mapping['artifact']['path'] = '../outside'
                if change == 'symlink':
                    (self.root / 'escape').symlink_to('/etc/hosts')
                    self.mapping['artifact']['path'] = 'escape'
                if change == 'decision': self.mapping['decision']['status'] = 'superseded'
                if change == 'evidence': self.mapping['decision']['equivalence_evidence'] = ['missing.json']
                if change == 'scope': self.mapping['source_requirement_refs'] = ['ANOTHER-REQ-001']
                if change == 'type': self.mapping['artifact']['type'] = 'workflows'
                if change == 'equivalence': self.mapping['decision']['equivalence'] = 'not_equivalent'
                if change == 'duplicate': self.mappings.append(copy.deepcopy(self.mapping))
                result = self.project()
                self.assertEqual(result['risk'], 'unknown')
                self.assertTrue(all(not m['confirmed'] for m in result['mappings']))

    def test_multiple_mappings_remain_separate_and_one_invalid_keeps_unknown(self):
        second = copy.deepcopy(self.mapping); second['id'] = 'RTA-000002'
        self.mappings.append(second)
        self.assertEqual(len(self.project()['mappings']), 2)
        second['artifact']['sha256'] = '0' * 64
        result = self.project()
        self.assertEqual(result['risk'], 'unknown')
        self.assertEqual(sum(m['confirmed'] for m in result['mappings']), 1)

    def test_malformed_or_missing_authority_data_cannot_break_review(self):
        self.mapping['source_requirement_refs'] = [None, {}]
        self.assertEqual(self.project()['risk'], 'unknown')
        projection = ImpactProjection(self.root)
        projection.catalog = [{'id': 'GRQ-000001', 'revisions': None}]
        self.assertEqual(projection.project(self.source, self.source_hash, [self.row], [self.source])['row-one']['risk'], 'unknown')
        (self.root / 'model/requirements/governance-requirement-catalog.yaml').unlink()
        result = ImpactProjection(self.root).project(self.source, self.source_hash, [self.row], [self.source])
        self.assertEqual(result['row-one']['risk'], 'unknown')
