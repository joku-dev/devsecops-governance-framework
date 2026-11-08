"""Keep source decisions, artifact adoption, and runtime evidence distinct."""
import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lib.governance_requirement_lifecycle_view import project


class RequirementLifecycleViewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sources = {'documents': [
            {'id': 'DSCB-STD-REQ-001', 'status': 'approved'},
            {'id': 'TOOLCHAIN-CAND-001', 'status': 'candidate'},
        ]}
        self.case = {'source': {'source_id': 'DSCB-STD-REQ-001'},
                     'status': 'review', 'proposals': [
                         {'decision': {'disposition': 'approve'}, 'activation': {'id': 'GRQ-1'}},
                         {'decision': None},
                     ]}
        self.migration = {'sources': {'DSCB-STD-REQ-001': {
            'total': 2, 'open': 1, 'with_candidates': 1,
        }}}
        self.artifacts = {'entries': [
            {'source_requirement_refs': ['DSCB-STD-SRC-001-REQ-001',
                                         'DSCB-STD-SRC-001-REQ-002'],
             'decision': {'status': 'effective'},
             'artifact': {'type': 'policies', 'path': 'policies/opa/example.rego'},
             'enforcement': 'none'},
            {'source_requirement_refs': ['DSCB-STD-SRC-001-REQ-002'],
             'decision': {'status': 'proposed'},
             'artifact': {'type': 'platform'}},
        ]}

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data))

    def prepare(self):
        self.write('model/documents/source-document-register.yaml', self.sources)
        self.write('model/requirements/requirement-to-artifact-register.yaml', self.artifacts)
        self.write('model/requirements/lifecycle-cases/example.json', self.case)
        self.write('generated/reports/implemented-requirement-migration.json', self.migration)
        target = self.root / 'policies/opa/example.rego'
        target.parent.mkdir(parents=True)
        target.write_text('package example\n')

    def test_missing_inputs_are_unavailable_instead_of_complete(self):
        self.assertEqual({'available': False,
                          'unavailable_reason': 'lifecycle_source_data_unavailable'},
                         project(self.root))

    def test_decisions_mappings_and_runtime_remain_separate(self):
        self.prepare()
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        data = project(self.root)
        self.assertEqual(1, data['requirement_summary']['decided'])
        self.assertEqual(1, data['requirement_summary']['open'])
        self.assertEqual(1, data['requirement_summary']['activated'])
        self.assertEqual(1, data['implementation_summary']['effective_register_entries'])
        self.assertEqual(1, data['opa_summary']['effective_mapping_entries'])
        self.assertEqual({'none': 1}, data['opa_summary']['enforcement_counts'])
        self.assertEqual('not_recorded_in_viewer_data', data['opa_summary']['latest_validation'])
        source, candidate = data['sources']
        self.assertEqual(1, source['effective_mappings'])
        self.assertEqual(1, source['opa_mappings'])
        self.assertEqual('candidate', candidate['intake_status'])
        self.assertFalse(candidate['case_available'])
        self.assertEqual(0, candidate['effective_mappings'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_inconsistent_migration_is_rejected(self):
        self.migration['sources']['DSCB-STD-REQ-001']['open'] = 0
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'disagree'):
            project(self.root)


if __name__ == '__main__':
    unittest.main()
