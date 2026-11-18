"""Whole immutable V1 snapshot decisions and exact source-reference checks."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib
import json
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_snapshot_validation import RepositorySnapshotValidation

FIXTURES = ROOT / 'tests/fixtures/v2-repository-validation'
CONTRACT = json.loads((FIXTURES / 'contract.json').read_bytes())['snapshot_helpers']
ORIGINALS = {'security': 'measured_security', 'measured': 'measured_l1',
             'assurance': 'control_evidence_assurance', 'staging': 'staging_deployment',
             'consolidated': 'consolidated_l1'}
DIRECTORIES = {'security': 'measured-security-results', 'measured': 'measured-l1-results',
               'assurance': 'control-evidence-assurance', 'staging': 'staging-deployment-results',
               'consolidated': 'consolidated-l1-results'}


def original_module(key):
    raw = (FIXTURES / (ORIGINALS[key] + '.py.txt')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT[key]['source_sha256']
    module = types.ModuleType('lib.' + ORIGINALS[key])
    module.__file__ = str(ROOT / CONTRACT[key]['source_path'])
    exec(compile(raw, str(FIXTURES / (ORIGINALS[key] + '.py.txt')), 'exec'), module.__dict__)
    return module, ast.parse(raw)


class UndoPorts(ast.NodeTransformer):
    def __init__(self, metadata):
        self.metadata = metadata

    def visit_Attribute(self, node):
        spelling = ast.unparse(node)
        pairs = {'self.root': 'ROOT', 'self.validator_class': 'Draft202012Validator',
                 'self.peers.measured.validate_snapshot': 'validate_measured',
                 'self.peers.staging.validate_snapshot': 'validate_staging'}
        pairs.update({'self.' + key.lower(): key for key in self.metadata['root_constants']})
        pairs.update({'self.' + name: name for name in self.metadata['functions']})
        if spelling in pairs:
            return ast.Name(id=pairs[spelling], ctx=ast.Load())
        return self.generic_visit(node)

    def visit_Assign(self, node):
        if (ast.unparse(node.value) == 'self.peers.measured.validate_snapshot'
                and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == 'validate_snapshot'):
            return ast.ImportFrom(module='lib.measured_l1', names=[ast.alias(name='validate_snapshot')], level=0)
        return self.generic_visit(node)


class SnapshotOriginalDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'data'
        self.root.mkdir()
        for name in ('model', 'schemas', 'status'):
            shutil.copytree(ROOT / name, self.root / name)
        self.original = {}
        self.trees = {}
        self.mapping = {}
        self.modules = patch.dict(sys.modules, self.mapping)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        for key in ORIGINALS:
            module, tree = original_module(key)
            self.original[key] = module
            self.trees[key] = tree
            sys.modules['lib.' + ORIGINALS[key]] = module
            module.ROOT = self.root
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in CONTRACT[key]['root_constants'] for t in node.targets):
                    # Controlled immutable reference constants, rebased to the
                    # same retained data root used by the neutral validators.
                    exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(node)], type_ignores=[])), '<frozen root constants>', 'exec'), module.__dict__)
        self.current = RepositorySnapshotValidation(self.root, validator_class=Draft202012Validator)

    def outcomes(self, function, *arguments):
        try:
            return {'value': function(*arguments)}
        except Exception as error:
            return {'error_type': type(error).__name__, 'message': str(error)}

    def snapshots(self, key):
        directory = self.root / 'status' / DIRECTORIES[key]
        before = self.outcomes(self.original[key].load_snapshots, directory)
        after = self.outcomes(getattr(self.current, key).load_snapshots, directory)
        self.assertEqual(after, before)
        return before

    def test_every_selected_original_function_has_the_whole_original_ast(self):
        total = 0
        for key, metadata in CONTRACT.items():
            old = {node.name: node for node in self.trees[key].body if isinstance(node, ast.FunctionDef)}
            tree = ast.parse((ROOT / 'scripts/lib' / ('repository_snapshots_' + key + '.py')).read_bytes())
            cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
            current = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name != '__init__'}
            self.assertEqual(set(current), set(metadata['functions']))
            for name in metadata['functions']:
                total += 1
                with self.subTest(family=key, function=name):
                    expected = copy.deepcopy(old[name])
                    actual = copy.deepcopy(current[name])
                    self.assertEqual(actual.args.args.pop(0).arg, 'self')
                    for index, default in enumerate(expected.args.defaults):
                        if isinstance(default, ast.Name) and default.id == 'ROOT':
                            self.assertEqual(actual.args.defaults[index].id, '_DEFAULT_ROOT')
                            self.assertIsInstance(actual.body.pop(0), ast.If)
                            actual.args.defaults[index] = copy.deepcopy(default)
                    actual = UndoPorts(metadata).visit(actual)
                    self.assertEqual(ast.dump(actual, include_attributes=False), ast.dump(expected, include_attributes=False))
        self.assertEqual(total, 23)

    def test_all_original_module_tables_and_required_source_membership_are_preserved(self):
        for key, metadata in CONTRACT.items():
            current = importlib.import_module('lib.repository_snapshots_' + key)
            for node in self.trees[key].body:
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id != 'ROOT' and target.id not in metadata['root_constants']:
                        with self.subTest(family=key, constant=target.id):
                            self.assertEqual(getattr(current, target.id), getattr(self.original[key], target.id))

    def test_explicit_none_root_keeps_the_original_error(self):
        for key, function in [('assurance', 'validate_assurance_source'), ('consolidated', 'validate_sources')]:
            item = json.loads(next((self.root / 'status' / DIRECTORIES[key]).rglob('*.json')).read_bytes())
            expected = self.outcomes(getattr(self.original[key], function), item, None)
            actual = self.outcomes(getattr(getattr(self.current, key), function), item, None)
            self.assertEqual(actual, expected)
            self.assertEqual(expected['error_type'], 'TypeError')

    def test_all_five_families_load_whole_existing_original_snapshots(self):
        for key in CONTRACT:
            with self.subTest(family=key):
                result = self.snapshots(key)
                self.assertIn('value', result)
                self.assertGreater(len(result['value']), 0)

    def test_original_assurance_profile_and_exact_source_decisions(self):
        self.assertEqual(self.current.load_assurance_profile(), self.original['assurance'].load_profile())
        for item in self.current.load_assurance_snapshots(self.root / 'status/control-evidence-assurance'):
            self.assertEqual(self.outcomes(self.current.validate_assurance_source, item),
                             self.outcomes(self.original['assurance'].validate_assurance_source, item, self.root))

    def test_original_consolidated_sources_are_fully_recomputed(self):
        for item in self.current.load_consolidated_l1_snapshots(self.root / 'status/consolidated-l1-results'):
            expected = self.outcomes(self.original['consolidated'].validate_sources, item, self.root)
            self.assertEqual(self.outcomes(self.current.validate_consolidated_l1_sources, item), expected)
            self.assertEqual(expected, {'value': None})

    def test_each_family_retains_its_original_tampered_binding_or_count_error(self):
        for key in CONTRACT:
            with self.subTest(family=key):
                path = next((self.root / 'status' / DIRECTORIES[key]).rglob('*.json'))
                original = path.read_bytes()
                value = json.loads(original)
                if key == 'security':
                    value['counts']['LOW'] += 1
                else:
                    value['assurance_binding' if key == 'assurance' else 'evidence_binding'] = '0' * 64
                try:
                    path.write_text(json.dumps(value))
                    self.assertIn('error_type', self.snapshots(key))
                finally:
                    path.write_bytes(original)

    def test_original_source_escape_and_foreign_subject_findings(self):
        cases = [('assurance', 'source_assessment', 'validate_assurance_source'),
                 ('consolidated', 'source_assessments', 'validate_sources')]
        for key, field, function in cases:
            item = json.loads(next((self.root / 'status' / DIRECTORIES[key]).rglob('*.json')).read_bytes())
            if key == 'assurance':
                item[field]['source_file'] = '../outside.json'
            else:
                item[field]['measured']['source_file'] = '../outside.json'
            expected = self.outcomes(getattr(self.original[key], function), item, self.root)
            self.assertEqual(self.outcomes(getattr(getattr(self.current, key), function), item), expected)
            self.assertEqual(expected['error_type'], 'ValueError')

    def test_all_original_optional_snapshot_directories_can_be_absent(self):
        for key in CONTRACT:
            self.assertEqual(self.outcomes(getattr(self.current, key).load_snapshots, self.root / 'missing'),
                             self.outcomes(self.original[key].load_snapshots, self.root / 'missing'))


if __name__ == '__main__':
    unittest.main()
