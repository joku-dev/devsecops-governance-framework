"""Whole V1 lifecycle examples and immutable synthetic projections, no live consent."""
from pathlib import Path
import ast
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import shutil
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.v2_boundary import violations
from lib.repository_paths import RepositoryPaths
from lib.providers.repository_data_io import RepositoryDataIO

FIXTURES = ROOT / 'tests/fixtures/v2-repository-validation'
CONTRACT = json.loads((FIXTURES / 'contract.json').read_bytes())['lifecycle_helpers']


class LifecycleOriginalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        self.root.mkdir(mode=0o700)
        for name in ('model', 'schemas', 'governance', 'status', 'docs', 'tests'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        self.original = {}
        self.modules = patch.dict(sys.modules, {})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        for name in ('contracts', 'adapter', 'kernel', 'store', 'decisions', 'closure', 'exceptions'):
            raw = (FIXTURES / CONTRACT[name]['fixture']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), CONTRACT[name]['source_sha256'])
            full = 'lib.governance_lifecycle.' + name
            module = ModuleType(full)
            module.__package__ = 'lib.governance_lifecycle'
            module.__file__ = str(self.root / CONTRACT[name]['source_path'])
            sys.modules[full] = module
            exec(compile(raw, str(FIXTURES / CONTRACT[name]['fixture']), 'exec'), module.__dict__)
            self.original[name] = module
        self.current = RepositoryLifecycle(self.root, validator_class=Draft202012Validator)

    def result(self, function, *args, **kwargs):
        try:
            return {'value': function(*args, **kwargs)}
        except Exception as error:
            return {'type': type(error).__name__, 'message': str(error)}

    def test_all_53_selected_functions_preserve_the_whole_original_ast(self):
        count = 0
        for name, metadata in CONTRACT.items():
            original = ast.parse((FIXTURES / metadata['fixture']).read_bytes())
            expected = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
            source = ast.parse((ROOT / 'scripts/lib/repository_lifecycle' / (name + '.py')).read_bytes())
            cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == metadata['class'])
            actual = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
            standalone = {n.name: n for n in source.body if isinstance(n, ast.FunctionDef)}
            class Undo(ast.NodeTransformer):
                def visit_Attribute(self, node):
                    spelling = ast.unparse(node)
                    mapping = {'self.root': 'ROOT', 'self.validator_class': 'Draft202012Validator', 'self.path_factory': 'Path'}
                    mapping.update({'self.' + key: key for key in metadata['functions']})
                    mapping.update({value: key for key, value in metadata['import_ports'].items()})
                    mapping.update({'self.input_' + key.lower(): key for key in metadata['root_constants']})
                    if spelling in mapping:
                        return ast.Name(id=mapping[spelling], ctx=ast.Load())
                    return self.generic_visit(node)
                def visit_Assign(self, node):
                    text = ast.unparse(node.value)
                    if isinstance(node.value, ast.Attribute) and text.startswith('self.context.'):
                        _, _, module, name = text.split('.')
                        target = node.targets[0].id
                        return ast.ImportFrom(module=module, names=[ast.alias(name=name,
                            asname=target if target != name else None)], level=1)
                    return self.generic_visit(node)
            for function in metadata['functions']:
                count += 1
                with self.subTest(module=name, function=function):
                    value = copy.deepcopy(actual[function])
                    self.assertEqual(value.args.args.pop(0).arg, 'self')
                    self.assertEqual(ast.dump(Undo().visit(value), include_attributes=False),
                                     ast.dump(expected[function], include_attributes=False))
            for function in metadata['standalone_functions']:
                count += 1
                self.assertEqual(ast.dump(standalone[function], include_attributes=False),
                                 ast.dump(expected[function], include_attributes=False))
        self.assertEqual(count, 53)

    def test_neutral_kernel_has_no_provider_import_or_literal(self):
        for path in (ROOT / 'scripts/lib/repository_lifecycle').glob('*.py'):
            self.assertEqual(violations(path.relative_to(ROOT).as_posix(), path.read_text()), [], path.name)

    def test_whole_original_example_validation_and_stdout(self):
        raw = (FIXTURES / 'validate_governance_lifecycle_contracts.py.txt').read_bytes()
        metadata = json.loads((FIXTURES / 'contract.json').read_bytes())['subvalidators']['lifecycle_contracts']
        self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata['source_sha256'])
        module = ModuleType('controlled_original_lifecycle_contracts')
        module.__file__ = str(self.root / metadata['source_path'])
        exec(compile(raw, '<frozen lifecycle example main>', 'exec'), module.__dict__)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertIsNone(module.main())
        self.assertEqual(self.current.load_examples(), module.load_examples())
        self.assertEqual(self.current.validate_examples(), {'returncode': 0, 'stdout': output.getvalue(), 'stderr': ''})

    def test_complete_original_ledger_transactions_states_and_projection_wires(self):
        for scenario, index in [('synthetic', 'governance-lifecycle-synthetic-index.json'),
                                ('synthetic-closure', 'governance-lifecycle-closure-index.json'),
                                ('synthetic-exceptions', 'governance-lifecycle-exception-index.json')]:
            with self.subTest(scenario=scenario):
                directory = self.root / 'governance/lifecycle' / scenario
                expected = self.original['store'].load_transactions(directory)
                actual = self.current.store.load_transactions(directory)
                self.assertEqual(actual, expected)
                profile = self.current.adapter.strict_json((self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json').read_bytes())
                self.assertEqual(self.current.kernel.replay(actual, profile), self.original['kernel'].replay(expected, profile))
                saved = self.current.adapter.strict_json((self.root / 'status' / index).read_bytes())
                projected = self.current.kernel.project(actual, profile, as_of=saved['as_of'])
                self.assertEqual(projected, self.original['kernel'].project(expected, profile, as_of=saved['as_of']))
                self.assertEqual(self.current.adapter.json_bytes(projected), self.original['adapter'].json_bytes(projected))
                self.assertEqual(projected, saved)
                self.assertEqual(self.current.validate_current(directory, self.root / 'status' / index,
                    self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json'), saved)

    def test_tampered_transaction_keeps_the_original_identity_error(self):
        directory = self.root / 'governance/lifecycle/synthetic/transactions'
        path = next(directory.glob('*.json'))
        value = json.loads(path.read_bytes())
        value['transaction_id'] = value['transaction_id'].split(':')[0] + ':' + '0' * 64
        path.write_text(json.dumps(value))
        expected = self.result(self.original['store'].load_transactions, directory.parent)
        self.assertEqual(self.result(self.current.store.load_transactions, directory.parent), expected)
        self.assertEqual(expected['type'], 'ContractError')

    def test_duplicate_json_and_nonfinite_numbers_keep_original_contract_errors(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            expected = self.result(self.original['adapter'].strict_json, raw)
            self.assertEqual(self.result(self.current.adapter.strict_json, raw), expected)
            self.assertIn('type', expected)

    def test_empty_ledger_and_unexpected_entry_keep_original_behavior(self):
        path = self.root / 'missing-ledger'
        self.assertEqual(self.current.store.load_transactions(path), self.original['store'].load_transactions(path))
        path.mkdir()
        (path / 'unexpected.json').write_text('{}')
        expected = self.result(self.original['store'].load_transactions, path)
        self.assertEqual(self.result(self.current.store.load_transactions, path), expected)
        self.assertEqual(expected['type'], 'ContractError')

    def test_replayed_duplicate_transaction_keeps_original_rejection(self):
        directory = self.root / 'governance/lifecycle/synthetic'
        records = self.current.store.load_transactions(directory)
        self.assertGreater(len(records), 0)
        profile = self.current.adapter.strict_json((self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json').read_bytes())
        duplicate = [*records, copy.deepcopy(records[-1])]
        expected = self.result(self.original['kernel'].replay, duplicate, profile)
        self.assertEqual(self.result(self.current.kernel.replay, duplicate, profile), expected)
        self.assertIn('type', expected)

    def test_invalid_live_profile_cannot_be_admitted_as_synthetic(self):
        profile, _, _ = self.current.load_examples()
        profile['environment'] = 'live'
        expected = self.result(self.original['contracts'].validate_test_profile, profile)
        self.assertEqual(self.result(self.current.contracts.validate_test_profile, profile), expected)
        self.assertIn('type', expected)

    def test_timestamp_contract_and_unknown_schema_kind_preserve_whole_original_errors(self):
        _, records, _ = self.current.load_examples()
        record = copy.deepcopy(next(iter(records.values())))
        record['recorded_at'] = '2026-11-15T12:00:00+00:00'
        expected = self.result(self.original['contracts'].validate_record, record)
        self.assertEqual(self.result(self.current.contracts.validate_record, record), expected)
        self.assertIn('type', expected)
        expected = self.result(self.original['contracts'].schema_validator, 'unregistered-kind')
        self.assertEqual(self.result(self.current.contracts.schema_validator, 'unregistered-kind'), expected)
        self.assertEqual(expected['type'], 'ContractError')

    def test_schema_resource_closure_never_fetches_an_unregistered_uri(self):
        path = self.root / 'schemas/governance-lifecycle-profile.schema.json'
        schema = json.loads(path.read_bytes())
        schema['$ref'] = 'urn:axiom:controlled-unregistered-resource'
        path.write_text(json.dumps(schema))
        profile = json.loads((self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json').read_bytes())
        expected = self.result(self.original['contracts'].validate_test_profile, profile)
        self.assertEqual(self.result(self.current.contracts.validate_test_profile, profile), expected)
        self.assertIn('type', expected)

    def test_whole_examples_and_all_ledgers_work_through_the_bounded_data_namespace(self):
        namespace = RepositoryPaths(str(self.root), RepositoryDataIO(self.root))
        bound = RepositoryLifecycle(namespace.root, validator_class=Draft202012Validator, path_factory=namespace.path)
        self.assertEqual(bound.validate_examples(), self.current.validate_examples())
        for scenario, index in [('synthetic', 'governance-lifecycle-synthetic-index.json'),
                                ('synthetic-closure', 'governance-lifecycle-closure-index.json'),
                                ('synthetic-exceptions', 'governance-lifecycle-exception-index.json')]:
            expected = self.current.validate_current(self.root / 'governance/lifecycle' / scenario,
                self.root / 'status' / index, self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json')
            actual = bound.validate_current(namespace.root / 'governance/lifecycle' / scenario,
                namespace.root / 'status' / index, namespace.root / 'model/governance/lifecycle/synthetic-grs002-profile.json')
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
