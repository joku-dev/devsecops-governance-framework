"""Frozen original decisions; complete application/orchestration proof is separate."""
from pathlib import Path
import ast
import copy
import hashlib
import io
import json
import sys
import tempfile
from types import SimpleNamespace
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_validation import RepositoryValidation

FIXTURE = ROOT / 'tests/fixtures/v2-repository-validation'
RAW = (FIXTURE / 'validate_governance_repo.py.txt').read_bytes()
EXPECTED = '0cc28beae8174773982d9effa8ce655b28264253aa69ff5ce8bba65b6144f0e1'
assert hashlib.sha256(RAW).hexdigest() == EXPECTED

HELPERS = {
    'verify_release_integrity': ('lib.release_integrity', 'verify_release_integrity'),
    'load_measured_security_snapshots': ('lib.measured_security', 'load_snapshots'),
    'load_measured_l1_snapshots': ('lib.measured_l1', 'load_snapshots'),
    'load_assurance_profile': ('lib.control_evidence_assurance', 'load_profile'),
    'load_assurance_snapshots': ('lib.control_evidence_assurance', 'load_snapshots'),
    'validate_assurance_source': ('lib.control_evidence_assurance', 'validate_assurance_source'),
    'load_staging_deployment_snapshots': ('lib.staging_deployment', 'load_snapshots'),
    'load_consolidated_l1_snapshots': ('lib.consolidated_l1', 'load_snapshots'),
    'validate_consolidated_l1_sources': ('lib.consolidated_l1', 'validate_sources'),
}


class OriginalNames(ast.NodeTransformer):
    """Undo only declared environment substitutions; retain every decision."""
    def visit_Attribute(self, node):
        spelling = ast.unparse(node)
        fixed = {
            'self.root': 'ROOT', 'self.model': 'MODEL',
            'self.source_document_root': 'SOURCE_DOCUMENT_ROOT',
            'self.app_architecture_evidence_template_dir': 'APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR',
            'self.environment.validator_class': 'Draft202012Validator',
            'self.environment.print': 'print', 'self.environment.python': 'sys.executable',
            'self.environment.stderr': 'sys.stderr', 'self.environment.run': 'subprocess.run',
            'self.environment.which': 'shutil.which',
        }
        if spelling in fixed:
            return ast.parse(fixed[spelling], mode='eval').body
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            return ast.Name(id=node.attr, ctx=ast.Load())
        return self.generic_visit(node)

    def visit_Assign(self, node):
        spelling = ast.unparse(node.value)
        if spelling.startswith('self.environment.') and spelling.split('.')[-1] in HELPERS:
            module, name = HELPERS[spelling.split('.')[-1]]
            assert len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            local = node.targets[0].id
            return ast.ImportFrom(module=module, names=[ast.alias(name=name, asname=local if local != name else None)], level=0)
        return self.generic_visit(node)

    def visit_ImportFrom(self, node):
        return [ast.ImportFrom(module=node.module, names=[copy.deepcopy(alias)], level=node.level) for alias in node.names]


class RepositoryDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.errors = io.StringIO()
        self.output = io.StringIO()
        self.environment = SimpleNamespace(root=self.root, validator_class=Draft202012Validator,
            stderr=self.errors, print=lambda *a, **k: print(*a, file=k.pop('file', self.output), **k))
        self.current = RepositoryValidation(self.environment)
        self.original = {'__name__': 'controlled_frozen_v1_repository_validator',
                         '__file__': str(ROOT / 'scripts/validate_governance_repo.py')}
        # The controlled test harness executes the hash-bound reference only.
        # It never invokes its main or a subprocess as an import side effect.
        exec(compile(RAW, str(FIXTURE / 'validate_governance_repo.py.txt'), 'exec'), self.original)
        self.original.update(ROOT=self.root, MODEL=self.root / 'model',
            SOURCE_DOCUMENT_ROOT=self.root / 'docs/governance/source-documents',
            APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR=self.current.app_architecture_evidence_template_dir)

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value if isinstance(value, str) else json.dumps(value))

    def equal_errors(self, name, *args):
        before, after = [], []
        self.original[name](before, *copy.deepcopy(args))
        getattr(self.current, name)(after, *copy.deepcopy(args))
        self.assertEqual(after, before)
        return after

    def test_all_29_original_functions_are_retained_after_declared_substitutions(self):
        old = {n.name: n for n in ast.parse(RAW).body if isinstance(n, ast.FunctionDef)}
        core = ast.parse((ROOT / 'scripts/lib/repository_validation.py').read_bytes())
        cls = next(n for n in core.body if isinstance(n, ast.ClassDef))
        new = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name != '__init__'}
        self.assertEqual(len(old), 29)
        self.assertEqual(set(new), set(old))
        for name, original in old.items():
            with self.subTest(function=name):
                actual = copy.deepcopy(new[name])
                self.assertEqual(actual.args.args.pop(0).arg, 'self')
                expected = OriginalNames().visit(copy.deepcopy(original))
                actual = OriginalNames().visit(actual)
                self.assertEqual(ast.dump(actual, include_attributes=False), ast.dump(expected, include_attributes=False))

    def test_core_cannot_import_or_launch_native_programs(self):
        tree = ast.parse((ROOT / 'scripts/lib/repository_validation.py').read_bytes())
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertFalse(imports & {'subprocess', 'os', 'shutil', 'tempfile', 'importlib'})
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {'exec', 'eval', 'compile', '__import__'})

    def test_missing_environment_does_not_supply_successful_subvalidators(self):
        with self.assertRaises(AttributeError):
            self.current.main()

    def test_source_path_findings_are_whole_original_decisions(self):
        for name in ('docs/governance/source-documents/good.md', 'docs/elsewhere.md'):
            self.write(name, 'controlled source fixture')
        for name in ('', 'missing.md', 'docs/elsewhere.md', 'docs/governance/source-documents/good.md'):
            with self.subTest(path=name):
                self.equal_errors('validate_source_document_path', name, 'fixture')

    def test_waiver_authority_findings_preserve_missing_and_mismatched_cases(self):
        authorities = {'high': {'approval_authority': 'owner'}}
        for waiver in ({}, {'risk_classification': 'high'},
                       {'risk_classification': 'high', 'approval_authority': 'owner'},
                       {'risk_classification': 'high', 'approval_authority': 'different'}):
            with self.subTest(waiver=waiver):
                self.equal_errors('validate_waiver_authority', waiver, authorities, 'fixture')

    def test_schema_errors_match_whole_original_messages_and_order(self):
        self.write('schemas/control.json', {'type': 'object', 'required': ['id'], 'properties': {'id': {'type': 'integer'}}})
        for value in ({}, {'id': 'invalid'}, {'id': 1}):
            with self.subTest(value=value):
                self.write('model/input.json', value)
                self.equal_errors('validate_schema', self.root / 'schemas/control.json', self.root / 'model/input.json')

    def test_missing_empty_and_invalid_architecture_templates_match_original(self):
        self.equal_errors('validate_app_architecture_evidence_templates')
        self.current.app_architecture_evidence_template_dir.mkdir(parents=True)
        self.equal_errors('validate_app_architecture_evidence_templates')
        self.write('schemas/app-architecture-evidence.schema.json', {'type': 'object', 'required': ['id']})
        self.write('pipeline-baseline/templates/app-architecture-evidence/.governance/architecture/test.json', {})
        self.equal_errors('validate_app_architecture_evidence_templates')

    def test_absent_optional_intake_and_typed_directories_match_original(self):
        for name in ('validate_intake_conflicts', 'validate_intake_events', 'validate_intake_health', 'validate_typed_evidence_results'):
            with self.subTest(function=name):
                self.assertEqual(self.equal_errors(name), [])


if __name__ == '__main__':
    unittest.main()
