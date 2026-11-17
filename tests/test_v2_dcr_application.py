from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_document_consistency_review_model import generate_model
from lib.candidate_workspace import CandidateWorkspace
from lib.dcr_application import run
from lib.dcr_manifest import build_manifest
from lib.dcr_structure import validate_model
from lib.dcr_semantics import validate_semantic_response
from lib.dcr_response import adapt_provider_response

FIXTURES = ROOT / 'tests/fixtures/document-consistency-review-semantic'


def data_fixture(root, source):
    sources = root / 'docs/governance/source-documents'
    sources.mkdir(parents=True, mode=0o700)
    register = root / 'model/documents'
    register.mkdir(parents=True, mode=0o700)
    shutil.copyfile(FIXTURES / 'source-a.md', sources / 'SYN-SRC-A-001.md')
    shutil.copyfile(FIXTURES / 'source-b.md', sources / 'SYN-SRC-B-001.md')
    shutil.copyfile(FIXTURES / 'source-document-register.yaml', register / 'source-document-register.yaml')


class DcrApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.instance = Path(self.temporary.name) / 'instance'
        self.instance.mkdir(mode=0o700)
        (self.instance / 'state').mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-dcr-node'}
        self.workspace = CandidateWorkspace(self.instance, 'dcr', node_id=self.settings['node_id'])
        with patch('lib.candidate_workspace.seed', data_fixture):
            self.workspace.initialize(ROOT)

    def call(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(run(['--workspace', 'dcr', *arguments], self.instance, self.settings), 0)
        value = json.loads(output.getvalue())
        self.assertEqual(value['authority_scope'], 'candidate_only')
        self.assertIs(value['official_acceptance'], False)
        return value

    def structural(self):
        return self.call('structural', '--review-id', 'dcr-parity', '--source-id', 'SYN-SRC-A-001',
                         '--source-id', 'SYN-SRC-B-001')

    def response_file(self, name, *, matching=True):
        value = json.loads((FIXTURES / name).read_text())
        current, _ = self.workspace.current()
        if matching:
            value['review_id'] = 'dcr-parity'
            value['source_manifest_sha256'] = hashlib.sha256(
                (current / 'dcr/reviews/dcr-parity/manifest.json').read_bytes()).hexdigest()
        path = Path(self.temporary.name) / name
        path.write_text(json.dumps(value))
        return path

    def test_structure_retains_missing_git_snapshot_finding(self):
        result = self.structural()
        current, _ = self.workspace.current()
        manifest = json.loads((current / 'dcr/reviews/dcr-parity/manifest.json').read_text())
        self.assertIsNone(manifest['reviewed_commit'])
        self.assertEqual(manifest['repository'], 'axiom-v2:candidate:synthetic-dcr-node:dcr')
        rule = next(row for row in result['report']['rules'] if row['rule_id'] == 'DCR-009')
        self.assertEqual(rule['status'], 'fail')
        self.assertIn('manifest/model commit is missing or differs', rule['details'])

    def test_valid_semantic_response_remains_unconfirmed(self):
        self.structural()
        path = self.response_file('valid-response.json')
        result = self.call('semantic', '--review-id', 'dcr-parity', '--response', str(path))
        self.assertEqual(result['report']['formal_validation']['status'], 'pass')
        self.assertTrue(result['report']['findings'])
        self.assertTrue(all(row['disposition'] == 'unconfirmed' for row in result['report']['findings']))

    def test_fabricated_quote_is_quarantined(self):
        self.structural()
        path = self.response_file('fabricated-quote-response.json')
        result = self.call('semantic', '--review-id', 'dcr-parity', '--response', str(path))
        self.assertTrue(any(row['disposition'] == 'quarantined' for row in result['report']['findings']))

    def test_wrong_review_and_invalid_json_do_not_change_generation(self):
        self.structural()
        _, before = self.workspace.current()
        path = self.response_file('valid-response.json', matching=False)
        with self.assertRaisesRegex(ValueError, 'review_mismatch'):
            self.call('semantic', '--review-id', 'dcr-parity', '--response', str(path))
        self.assertEqual(self.workspace.current()[1], before)
        path.write_text('{"review_id":"dcr-parity","review_id":"dcr-parity"}')
        with self.assertRaises(ValueError):
            self.call('semantic', '--review-id', 'dcr-parity', '--response', str(path))
        self.assertEqual(self.workspace.current()[1], before)

    def test_repeat_review_does_not_replace_existing_evidence(self):
        self.structural()
        _, before = self.workspace.current()
        with self.assertRaisesRegex(ValueError, 'fresh_dcr_review_required'):
            self.structural()
        self.assertEqual(self.workspace.current()[1], before)

    def test_adapter_never_calls_a_provider_or_approves_findings(self):
        self.structural()
        result = self.call('adapt', '--review-id', 'dcr-parity', '--input', str(FIXTURES / 'provider-projection.json'),
                           '--provider', 'declared-provider', '--model', 'declared-model', '--prompt-version', 'test-1')
        self.assertIn('no provider was invoked', result['limitations'][0])
        self.assertEqual(result['adapted_response']['execution']['provider'], 'declared-provider')
        self.assertTrue(all(row['semantic_state'] != 'confirmed' for row in result['adapted_response']['findings']))

    def test_domain_outputs_match_independently_executed_frozen_v1(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/dcr-domain-cases.json').read_text())
        self.assertTrue(fixture['synthetic'])
        self.assertEqual(fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        current, _ = self.workspace.current()
        manifest = json.loads((FIXTURES / 'manifest.json').read_text())
        digest = hashlib.sha256((FIXTURES / 'manifest.json').read_bytes()).hexdigest()
        model = generate_model(current, manifest, schema_root=ROOT)
        self.assertEqual(model, fixture['expected']['model'])
        self.assertEqual(validate_model(current, manifest, model), fixture['expected']['structure'])
        for name, expected in fixture['expected']['semantics'].items():
            response = json.loads((FIXTURES / name).read_text())
            self.assertEqual(validate_semantic_response(current, manifest, response, digest), expected)
        config = json.loads((ROOT / 'model/governance/document-consistency/provider-adapter-config-v1.json').read_text())
        projection = json.loads((FIXTURES / 'provider-projection.json').read_text())
        adapted = adapt_provider_response(projection, config, review_id='provider-adapter-regression',
            source_manifest_sha256=digest, provider='provider-under-test', model='model-under-test',
            prompt_version='phase2-provider-neutral-1')
        self.assertEqual(adapted, fixture['expected']['adapted'])

    def test_manifest_rejects_duplicate_scope_and_source_escape(self):
        current, _ = self.workspace.current()
        with self.assertRaisesRegex(ValueError, 'unique'):
            build_manifest(current, ['SYN-SRC-A-001', 'SYN-SRC-A-001'], repository='synthetic')
        def corrupt(root):
            path = root / 'model/documents/source-document-register.yaml'
            text = path.read_text().replace('docs/governance/source-documents/SYN-SRC-A-001.md', '../../outside.md')
            path.write_text(text)
        self.workspace.execute(corrupt, write=True)
        _, before = self.workspace.current()
        with self.assertRaisesRegex(ValueError, 'outside the source directory'):
            self.structural()
        self.assertEqual(self.workspace.current()[1], before)


if __name__ == '__main__':
    unittest.main()
