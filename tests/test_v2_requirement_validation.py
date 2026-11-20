"""Whole immutable V1 requirement validator decisions, outputs and error order."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from importlib.machinery import SourceFileLoader
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.requirement_validation_context import validate
from lib.requirement_validation import RequirementValidation
from lib.v2_boundary import violations

REFERENCE = ROOT / 'tests/fixtures/v2-requirement-validation-original/validate_requirement_lifecycle.py.txt'
ORIGINAL_SHA = '0ec1602133b3a0c481963d8c862c35e99ffd426cc5953d166bea072adaadaa6f'
assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == ORIGINAL_SHA
loader = SourceFileLoader('immutable_V1_requirement_validator', str(REFERENCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
ORIGINAL = importlib.util.module_from_spec(spec)
loader.exec_module(ORIGINAL)
PATHS = {'CATALOG': 'model/requirements/governance-requirement-catalog.yaml',
         'LEDGER': 'model/requirements/requirement-authority-ledger.yaml',
         'CASES': 'model/requirements/lifecycle-cases',
         'PUBLICATION': 'docs/publishing/governance-requirement-catalog/publication.yaml',
         'ARTIFACT_REGISTER': 'model/requirements/requirement-to-artifact-register.yaml',
         'POLICY_REVIEW_ROOT': 'docs/governance/review-packets'}
OPA = PATHS['POLICY_REVIEW_ROOT'] + '/OPA-DSCB-2026-001/review.json'
PRA = PATHS['POLICY_REVIEW_ROOT'] + '/PRA-2026-001/review.json'
CASES = []


class OrdinaryData:
    """Test-only data adapter; production implementation must be separately tested."""
    def __init__(self, root): self.root, self.files, self.directories = root, {}, {''}
    def stat(self, name):
        p = self.root / name
        if p.is_file():
            self.files[name] = p.read_bytes()
            return {'kind': 'file', 'bytes': p.stat().st_size, 'mode': p.stat().st_mode}
        if p.is_dir():
            self.directories.add(name)
            return {'kind': 'directory', 'bytes': 0, 'mode': p.stat().st_mode}
        return None
    def entries(self, name):
        return [{'name': p.name, **self.stat(p.relative_to(self.root).as_posix())}
                for p in (self.root / name).iterdir()]
    def read(self, name):
        raw = (self.root / name).read_bytes()
        self.files[name] = raw
        return raw


class History:
    def __init__(self, files=None, changes=(), existing=()):
        self.files, self.changes, self.existing = dict(files or {}), set(changes), set(existing)
        self.calls = []
    def previous(self, base, name):
        self.calls.append(('previous', base, name))
        raw = self.files.get(name)
        return None if raw is None else raw.decode('utf-8')
    def changed(self, base):
        self.calls.append(('changed', base))
        return self.changes.copy()
    def existed(self, base, name):
        self.calls.append(('existed', base, name))
        return name in self.existing


class WholeRequirementValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = OrdinaryData(ROOT)
        result = validate(str(ROOT), source, History())
        assert result['exit_code'] == 0 and result['kernel_exception'] is None
        cls.baseline, cls.directories = source.files, source.directories
        cls.baseline['schemas/native-requirement-source.schema.json'] = (ROOT/'schemas/native-requirement-source.schema.json').read_bytes()
        cls.case_names = sorted(n for n in source.files if n.startswith(PATHS['CASES'] + '/') and n.endswith('.json'))
        cls.native_case = cls.case_names[0]
        cls.decided_case = next(n for n in cls.case_names if any(p['decision'] for p in json.loads(cls.baseline[n])['proposals']))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'data'
        self.root.mkdir()
        for name in self.directories: (self.root / name).mkdir(parents=True, exist_ok=True)
        for name, raw in self.baseline.items():
            p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)

    def read(self, name):
        raw = (self.root / name).read_text()
        return json.loads(raw) if name.endswith('.json') else yaml.safe_load(raw)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if name.endswith('.json') else yaml.safe_dump(value, sort_keys=False, allow_unicode=True))

    def change(self, name, fn):
        value = self.read(name); fn(value); self.put(name, value)

    def compare(self, *, base=None, history=None):
        previous = history or History()
        def value(base, path):
            raw = previous.previous(base, path.relative_to(self.root).as_posix())
            return None if raw is None else json.loads(raw) if path.suffix == '.json' else yaml.safe_load(raw)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(ORIGINAL, 'ROOT', self.root), patch.multiple(ORIGINAL, **{k: self.root / n for k, n in PATHS.items()}), \
             patch.object(ORIGINAL, 'git_value', side_effect=value), \
             patch.object(ORIGINAL, 'changed_paths', side_effect=previous.changed), \
             patch.object(ORIGINAL, 'git_path_exists', side_effect=previous.existed), \
             patch.object(sys, 'argv', ['original'] + ([] if base is None else ['--base-ref', base])), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            try: code, error = ORIGINAL.main(), None
            except Exception as exc:
                code, error = 1, {'type': type(exc).__name__, 'message': str(exc)}
        expected_calls = previous.calls.copy(); previous.calls.clear()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        actual = validate(str(self.root), OrdinaryData(self.root), previous, base_ref=base)
        expected = {'exit_code': code, 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue(), 'kernel_exception': error}
        self.assertEqual(actual, expected)
        self.assertEqual(previous.calls, expected_calls)
        self.assertEqual({str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)
        CASES.append({'exit': code, 'kernel_exception': None if error is None else error['type'],
                      'whole_streams_and_exception_equal': True, 'whole_history_call_order_equal': True,
                      'result_sha256': hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()})
        return actual

    def test_whole_real_default_data_and_no_history_call(self):
        result = self.compare()
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('- canonical requirements: 54\n', result['stdout'])

    def test_all_catalog_allocation_revision_relationship_and_blocking_failures(self):
        mutations = [lambda v: v['requirements'].append(deepcopy(v['requirements'][0])),
                     lambda v: v.update(next_sequence=9999),
                     lambda v: v['requirements'][0]['revisions'][0].update(revision=2),
                     lambda v: v['requirements'][0].update(active_revision=99),
                     lambda v: v['requirements'][0]['revisions'][0].update(status='retired'),
                     lambda v: v['requirements'][0]['revisions'][0]['relationships'].append({'type': 'duplicates', 'target': 'GRQ-999999@rev1'}),
                     lambda v: v['requirements'][0]['revisions'][0].update(runtime_enforcement='blocking')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.put(PATHS['CATALOG'], yaml.safe_load(self.baseline[PATHS['CATALOG']]))
                self.change(PATHS['CATALOG'], mutate)
                self.assertEqual(self.compare()['exit_code'], 1)

    def test_ledger_source_hash_arithmetic_order_authority_and_duplicate_errors(self):
        mutations = [lambda v: v['sources'].append(deepcopy(v['sources'][0])),
                     lambda v: v['sources'][0].update(source_path='docs/missing.md'),
                     lambda v: v['sources'][0].update(document_sha256='0' * 64),
                     lambda v: v['sources'][0]['coverage'].update(unresolved=123),
                     lambda v: v['sources'][0]['coverage'].update(effective=999),
                     lambda v: v['sources'][0].update(authority_mode='git_authoritative')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.put(PATHS['LEDGER'], yaml.safe_load(self.baseline[PATHS['LEDGER']]))
                self.change(PATHS['LEDGER'], mutate)
                self.assertEqual(self.compare()['exit_code'], 1)

    def test_artifact_register_duplicate_inactive_derivation_enforcement_file_hash_decision_equivalence(self):
        changes = [lambda v: v['entries'].append(deepcopy(v['entries'][0])),
                   lambda v: v['entries'][0].update(requirement_ref='GRQ-999999@rev1'),
                   lambda v: v['entries'][0]['artifact'].update(type='controls'),
                   lambda v: v['entries'][0].update(enforcement='blocking'),
                   lambda v: v['entries'][0]['artifact'].update(path='policies/opa/missing.rego'),
                   lambda v: v['entries'][0]['artifact'].update(sha256='0' * 64),
                   lambda v: v['entries'][0]['decision'].update(decision_ref='docs/missing.md'),
                   lambda v: v['entries'][0]['decision'].update(equivalence='not_equivalent')]
        for mutate in changes:
            with self.subTest(mutation=mutate):
                self.put(PATHS['ARTIFACT_REGISTER'], yaml.safe_load(self.baseline[PATHS['ARTIFACT_REGISTER']]))
                self.change(PATHS['ARTIFACT_REGISTER'], mutate)
                self.assertEqual(self.compare()['exit_code'], 1)

    def test_all_policy_review_mapping_counts_decision_and_effective_register_errors(self):
        changes = [lambda v: v['mappings'].append(deepcopy(v['mappings'][0])),
                   lambda v: v['mappings'][0].update(requirement_ref='GRQ-999999@rev1'),
                   lambda v: v['mappings'][0].update(policy_path='policies/opa/missing.rego'),
                   lambda v: v['mappings'][0].update(policy_sha256='0' * 64),
                   lambda v: v['summary'].update(mapping_count=999),
                   lambda v: v['summary'].update(equivalent=999),
                   lambda v: v['summary'].update(policy_file_count=999),
                   lambda v: v['decision'].update(decision_ref='docs/missing.md'),
                   lambda v: v['decision']['approved'].append(v['decision']['approved'][0]),
                   lambda v: v['decision']['approved'].append(v['decision']['withheld'].pop()),
                   lambda v: v['summary'].update(effective_register_entries=999)]
        for mutate in changes:
            with self.subTest(mutation=mutate):
                self.put(OPA, json.loads(self.baseline[OPA])); self.change(OPA, mutate)
                self.assertEqual(self.compare()['exit_code'], 1)

    def test_platform_review_source_hash_duplicates_and_undecided_decisions(self):
        changes = [lambda v: v['source'].update(source_path='docs/missing.md'),
                   lambda v: v['source'].update(source_sha256='0' * 64),
                   lambda v: v['requirements'].append(deepcopy(v['requirements'][0])),
                   lambda v: v.update(status='review_required')]
        for mutate in changes:
            with self.subTest(mutation=mutate):
                self.put(PRA, json.loads(self.baseline[PRA])); self.change(PRA, mutate)
                self.assertEqual(self.compare()['exit_code'], 1)

    def test_case_source_hash_reference_activation_open_and_unknown_requirement(self):
        changes = [lambda v: v['source'].update(source_path='docs/missing.md'),
                   lambda v: v['source'].update(source_sha256='0' * 64),
                   lambda v: v['source'].update(decision_ref='docs/missing.md'),
                   lambda v: v['source'].update(decision_ref='README.md'),
                   lambda v: v.update(status='activated'),
                   lambda v: v['proposals'][0].update(activation={'requirement_id':'GRQ-999999','requirement_revision':1,'activated_at':'2026-11-15T12:00:00Z','effective_from':'2026-11-15','commit':'a'*40})]
        case = next(n for n in self.case_names if any(p['decision'] is None for p in json.loads(self.baseline[n])['proposals']))
        for mutate in changes:
            with self.subTest(mutation=mutate):
                self.put(case, json.loads(self.baseline[case])); self.change(case, mutate)
                self.assertEqual(self.compare()['exit_code'], 1)

    def test_native_frontmatter_invalid_metadata_and_missing_statement(self):
        case = self.read(self.native_case)
        case['intake_type'] = 'native_git'
        case['source']['source_path'] = 'docs/governance/requirements/native-sources/TEST-VALIDATION.md'
        path = self.root / case['source']['source_path']; path.parent.mkdir(parents=True, exist_ok=True)
        original = ('---\nid: NATIVE-REQ-2026-TEST\ntitle: Explicit test\nnormative_strength: MUST\ndomain: devsecops\nowner: Test owner\ndecision_ref: ' + case['source']['decision_ref'] + '\n---\nThe explicit test statement.\n').encode()
        path.write_bytes(original); case['source']['source_sha256'] = hashlib.sha256(original).hexdigest(); self.put(self.native_case, case)
        self.assertEqual(self.compare()['exit_code'], 0)
        for raw in (b'not frontmatter', b'---\nid: NATIVE-1\n---\nbody', b'---\nid: NATIVE-1\n---\n'):
            with self.subTest(raw=raw):
                path.write_bytes(raw); case['source']['source_sha256'] = hashlib.sha256(raw).hexdigest(); self.put(self.native_case, case)
                self.assertEqual(self.compare()['exit_code'], 1)
        path.write_bytes(original)

    def test_missing_and_different_publication_and_absent_review_directories(self):
        publication = self.root / PATHS['PUBLICATION']; saved = publication.read_bytes(); publication.unlink()
        self.assertEqual(self.compare()['exit_code'], 1)
        publication.write_bytes(saved); self.change(PATHS['PUBLICATION'], lambda v: v.update(sections=[]))
        self.assertEqual(self.compare()['exit_code'], 1)
        publication.write_bytes(saved); shutil.rmtree(self.root / PATHS['POLICY_REVIEW_ROOT'])
        # The original tolerates absent review directories; missing decision
        # reference files within them remain ordinary explicit failures.
        self.compare()

    def test_malformed_and_schema_invalid_inputs_preserve_first_exception_and_whole_errors(self):
        for name, raw in [(PATHS['CATALOG'], b'null'), (PATHS['CATALOG'], b'{}'),
                          (PATHS['LEDGER'], b'not: [valid'), (OPA, b'not JSON'),
                          ('schemas/governance-requirement-catalog.schema.json', b'not JSON')]:
            with self.subTest(name=name):
                original = (self.root / name).read_bytes(); (self.root / name).write_bytes(raw)
                self.assertEqual(self.compare()['exit_code'], 1); (self.root / name).write_bytes(original)

    def test_full_base_history_matches_original_and_changes_preserve_registered_release_rules(self):
        base = 'stable-reference'
        h = History(self.baseline)
        self.assertEqual(self.compare(base=base, history=h)['exit_code'], 0)
        for changes, existed in [(['releases/test/file.json'], ['releases/test/file.json']),
                                 (['policies/opa/missing.rego'], []),
                                 (['policies/opa/branch_protection.rego'], []),
                                 (['model/platform/unmapped.yaml'], [])]:
            with self.subTest(changes=changes):
                if changes[0].startswith('model/platform/'):
                    p = self.root / changes[0]; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('new: model')
                self.compare(base=base, history=History(self.baseline, changes, existed))

    def test_immutable_catalog_deletion_and_revision_rewrite(self):
        for mutate in (lambda v: v['requirements'].pop(), lambda v: v['requirements'][0]['revisions'][0].update(title='changed')):
            self.put(PATHS['CATALOG'], yaml.safe_load(self.baseline[PATHS['CATALOG']]))
            self.change(PATHS['CATALOG'], mutate)
            result = self.compare(base='base', history=History(self.baseline))
            self.assertIn('immutable requirement revision changed' if len(self.read(PATHS['CATALOG'])['requirements'])==54 else 'previous requirement deleted', result['stderr'])

    def test_every_immutable_intake_proposal_decision_analysis_and_activation_field(self):
        case = self.decided_case
        source = json.loads(self.baseline[case]); index = next(i for i,p in enumerate(source['proposals']) if p['decision'])
        changes = [lambda v: v['source'].update(owner='different'), lambda v: v['proposals'].pop()]
        changes += [lambda v, field=field: v['proposals'][index].update({field:'changed'}) for field in ('proposal_id','source_requirement_id','title','statement','normative_strength','domain')]
        changes += [lambda v: v['proposals'][index]['decision'].update(rationale='changed'),
                    lambda v: v['proposals'][index].update(analysis=None),
                    lambda v: v['proposals'][index].update(activation=None)]
        for mutate in changes:
            with self.subTest(mutation=mutate):
                self.put(case, source); self.change(case, mutate)
                self.compare(base='base', history=History(self.baseline))

    def test_core_has_no_provider_access_or_dynamic_execution(self):
        for name in ('requirement_validation.py','requirement_validation_context.py'):
            self.assertEqual(violations('scripts/lib/'+name,(ROOT/'scripts/lib'/name).read_text()), [])
        original = {n.name for n in ast.parse(REFERENCE.read_bytes()).body if isinstance(n,ast.FunctionDef)}
        converted = {n.name for n in ast.parse((ROOT/'scripts/lib/requirement_validation.py').read_bytes()).body[-1].body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(original-{'main'}|{'validate','__init__'},converted)




class WholeOriginalStructure(unittest.TestCase):
    def test_every_decision_function_and_main_prefix_preserve_complete_original_AST(self):
        original={n.name:n for n in ast.parse(REFERENCE.read_bytes()).body if isinstance(n,ast.FunctionDef)}
        current={n.name:n for n in ast.parse((ROOT/'scripts/lib/requirement_validation.py').read_bytes()).body[-1].body if isinstance(n,ast.FunctionDef)}
        constants={'root':'ROOT','catalog':'CATALOG','ledger':'LEDGER','cases':'CASES','publication':'PUBLICATION',
                   'artifact_register':'ARTIFACT_REGISTER','policy_review_root':'POLICY_REVIEW_ROOT','derived_prefixes':'DERIVED_PREFIXES'}
        class OriginalNames(ast.NodeTransformer):
            def visit_Attribute(self,node):
                if isinstance(node.value,ast.Name) and node.value.id=='self':
                    if node.attr=='validator':return ast.Name('Draft202012Validator',node.ctx)
                    if node.attr=='review_paths':return ast.Attribute(ast.Name('POLICY_REVIEW_ROOT',ast.Load()),'glob',node.ctx)
                    return ast.Name(constants.get(node.attr,node.attr),node.ctx)
                return self.generic_visit(node)
            def visit_Name(self,node):
                if node.id=='PurePosixPath':return ast.Name('Path',node.ctx)
                if node.id=='local_validator':return ast.Name('Draft202012Validator',node.ctx)
                if node.id=='bounded_native_requirement':return ast.Name('parse_native_requirement',node.ctx)
                if node.id=='yaml_text':return ast.Attribute(ast.Name('yaml',ast.Load()),'safe_load',node.ctx)
                if node.id=='base_ref' and self.main:return ast.Attribute(ast.Name('args',ast.Load()),'base_ref',node.ctx)
                return node
        for name,fn in original.items():
            if name in ('git_value','git_path_exists','changed_paths'):continue
            with self.subTest(function=name):
                normalized=deepcopy(current['validate' if name=='main' else name]);normalized.args.args.pop(0)
                mapper=OriginalNames();mapper.main=name=='main'
                if name=='main':
                    self.assertEqual(len(normalized.body[:-2]),len(fn.body[3:-6]))
                    for a,b in zip(normalized.body[:-2],fn.body[3:-6]):
                        self.assertEqual(ast.dump(mapper.visit(a),include_attributes=False),ast.dump(b,include_attributes=False))
                else:
                    self.assertEqual(ast.dump(mapper.visit(normalized),include_attributes=False),ast.dump(fn,include_attributes=False))


if __name__ == '__main__': unittest.main()
