"""Whole frozen original provenance/DCR subvalidator outcomes, including failures."""
from pathlib import Path
import ast
import copy
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import math
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.exceptions import NoSuchResource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import dcr_operations
from lib.repository_provenance_validation import RepositoryProvenanceValidation

FIXTURE = ROOT / 'tests/fixtures/v2-repository-validation'


class SubvalidatorOriginalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'data'
        self.root.mkdir()
        for name in ('model', 'schemas', 'status', 'docs', 'tests', 'generated'):
            shutil.copytree(ROOT / name, self.root / name,
                            ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        self.originals = {}
        contract = json.loads((FIXTURE / 'contract.json').read_bytes())['subvalidators']
        for name in ('provenance', 'dcr'):
            metadata = contract[name]
            raw = (FIXTURE / (metadata['source_path'].split('/')[-1] + '.txt')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata['source_sha256'])
            module = types.ModuleType('controlled_original_' + name)
            module.__file__ = str(ROOT / metadata['source_path'])
            exec(compile(raw, str(FIXTURE / (metadata['source_path'].split('/')[-1] + '.txt')), 'exec'), module.__dict__)
            module.ROOT = self.root
            if name == 'provenance':
                module.SCHEMA_PATH = self.root / 'schemas/evidence-agent-provenance.schema.json'
                module.RECORD_ROOT = self.root / 'status/evidence-agent-provenance'
            self.originals[name] = module
        self.provenance = RepositoryProvenanceValidation(self.root, validator_class=Draft202012Validator)
        # The repository intentionally has no official association records.
        # Use its checked-in example as explicitly synthetic controlled input.
        record = json.loads((self.root / 'docs/examples/evidence-agent-provenance.example.json').read_bytes())
        directory = self.root / 'status/evidence-agent-provenance'
        directory.mkdir(parents=True, exist_ok=True)
        self.record = directory / 'controlled-example.json'
        self.record.write_text(json.dumps(record, indent=2) + '\n')
        source = self.root / record['evidence']['source_file']
        self.assertFalse(source.exists())
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(json.dumps({'subjects': [{'id': record['evidence']['subject_id'],
                                                  'digest': record['evidence']['subject_digest']}]}))

    def outcome(self, function, *args, **kwargs):
        try:
            return {'value': function(*args, **kwargs)}
        except Exception as error:
            return {'type': type(error).__name__, 'message': str(error)}

    def original_command(self, name):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', ['trusted-original-validator']), redirect_stdout(stdout), redirect_stderr(stderr):
            code = self.originals[name].main()
        return {'returncode': code, 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()}

    def test_provenance_whole_original_command_and_checked_in_example_record(self):
        self.assertEqual(self.provenance.run(), self.original_command('provenance'))
        schema = json.loads((self.root / 'schemas/evidence-agent-provenance.schema.json').read_bytes())
        paths = sorted((self.root / 'status/evidence-agent-provenance').rglob('*.json'))
        self.assertGreater(len(paths), 0)
        for path in paths:
            self.assertEqual(self.provenance.validate_record(path, schema),
                             self.originals['provenance'].validate_record(path, schema))

    def test_provenance_invalid_record_and_source_json_keep_original_json_errors(self):
        path = next((self.root / 'status/evidence-agent-provenance').rglob('*.json'))
        record = path.read_bytes()
        path.write_text('{')
        self.assertEqual(self.provenance.run(), self.original_command('provenance'))
        path.write_bytes(record)
        source = self.root / json.loads(record)['evidence']['source_file']
        source.write_text('{')
        self.assertEqual(self.provenance.run(), self.original_command('provenance'))

    def test_provenance_missing_subject_and_changed_digest_match_original_wires(self):
        path = next((self.root / 'status/evidence-agent-provenance').rglob('*.json'))
        original = json.loads(path.read_bytes())
        for changes in ({'subject_id': 'unknown'}, {'subject_digest': '0' * 64}, {'source_file': 'missing.json'}):
            value = copy.deepcopy(original)
            value['evidence'].update(changes)
            path.write_text(json.dumps(value))
            result = self.provenance.run()
            self.assertEqual(result, self.original_command('provenance'))
            self.assertEqual(result['returncode'], 1)

    def test_provenance_permissive_original_json_parse_is_not_silently_replaced(self):
        path = next((self.root / 'status/evidence-agent-provenance').rglob('*.json'))
        raw = path.read_text()
        path.write_text(raw[:-2] + ', "unrecognized_field": NaN}\n')
        self.assertTrue(math.isnan(json.loads(path.read_text())['unrecognized_field']))
        self.assertEqual(self.provenance.run(), self.original_command('provenance'))

    def test_provenance_empty_optional_record_directory_keeps_original_success(self):
        self.record.unlink()
        self.assertEqual(self.provenance.run(), self.original_command('provenance'))
        shutil.rmtree(self.record.parent)
        self.assertEqual(self.provenance.run(), self.original_command('provenance'))

    def test_all_three_provenance_decision_functions_preserve_the_original_ast(self):
        raw = (FIXTURE / 'validate_evidence_agent_provenance.py.txt').read_bytes()
        old = {n.name: n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
        tree = ast.parse((ROOT / 'scripts/lib/repository_provenance_validation.py').read_bytes())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
        class Undo(ast.NodeTransformer):
            def visit_Attribute(self, node):
                mapping = {'self.root': 'ROOT', 'self.schema_path': 'SCHEMA_PATH',
                           'self.record_root': 'RECORD_ROOT', 'self.validator_class': 'Draft202012Validator',
                           'self.load_subject_digest': 'load_subject_digest', 'self.validate_record': 'validate_record'}
                if ast.unparse(node) in mapping:
                    return ast.Name(id=mapping[ast.unparse(node)], ctx=ast.Load())
                return self.generic_visit(node)
        for name in ('load_subject_digest', 'validate_record', 'validate_records'):
            with self.subTest(function=name):
                current = copy.deepcopy(methods[name])
                current.decorator_list = []
                if name != 'load_subject_digest':
                    self.assertEqual(current.args.args.pop(0).arg, 'self')
                if name == 'validate_records':
                    self.assertEqual(current.args.defaults[0].id, '_DEFAULT_RECORDS')
                    current.args.defaults[0] = ast.Name(id='RECORD_ROOT', ctx=ast.Load())
                    self.assertIsInstance(current.body.pop(0), ast.If)
                self.assertEqual(ast.dump(Undo().visit(current), include_attributes=False),
                                 ast.dump(old[name], include_attributes=False))

    def test_provenance_explicit_none_root_keeps_original_failure(self):
        self.assertEqual(self.outcome(self.provenance.validate_records, None),
                         self.outcome(self.originals['provenance'].validate_records, None))

    def test_dcr_whole_original_result_and_command_projection(self):
        result = dcr_operations.validate(self.root)
        self.assertEqual(result, self.originals['dcr'].validate(self.root))
        self.assertEqual({'returncode': 0, 'stdout': json.dumps(result, sort_keys=True) + '\n', 'stderr': ''},
                         self.original_command('dcr'))

    def test_dcr_original_missing_file_and_tampered_artifact_errors(self):
        package = json.loads((self.root / 'docs/examples/document-consistency-review-phase4-candidate-package.json').read_bytes())
        artifact = self.root / package['artifacts'][0]['path']
        artifact.write_bytes(artifact.read_bytes() + b'\ncontrolled mutation\n')
        expected = self.outcome(self.originals['dcr'].validate, self.root)
        self.assertEqual(self.outcome(dcr_operations.validate, self.root), expected)
        self.assertIn('type', expected)
        artifact.unlink()
        self.assertEqual(self.outcome(dcr_operations.validate, self.root),
                         self.outcome(self.originals['dcr'].validate, self.root))

    def test_dcr_supplied_validator_controls_every_contract_without_ambient_retrieval(self):
        seen = []
        def retrieve(uri):
            self.fail('No external resource should be retrieved for the original contracts: ' + uri)
        def guarded(schema, **kwargs):
            seen.append(schema)
            return Draft202012Validator(schema, registry=Registry(retrieve=retrieve), **kwargs)
        self.assertEqual(dcr_operations.validate(self.root, validator_class=guarded),
                         self.originals['dcr'].validate(self.root))
        self.assertEqual(len(seen), len(dcr_operations.FILES) + len(dcr_operations.CATALOG_MANIFESTS))

    def test_dcr_external_reference_cannot_bypass_the_supplied_registry(self):
        path = self.root / dcr_operations.FILES['operating'][1]
        schema = json.loads(path.read_bytes())
        schema['$ref'] = 'file:///controlled-test-never-read.json'
        path.write_text(json.dumps(schema))
        seen = []
        def reject(uri):
            seen.append(uri)
            raise NoSuchResource(ref=uri)
        def guarded(schema, **kwargs):
            return Draft202012Validator(schema, registry=Registry(retrieve=reject), **kwargs)
        result = self.outcome(dcr_operations.validate, self.root, validator_class=guarded)
        self.assertIn('type', result)
        self.assertEqual(seen, ['file:///controlled-test-never-read.json'])


if __name__ == '__main__':
    unittest.main()
