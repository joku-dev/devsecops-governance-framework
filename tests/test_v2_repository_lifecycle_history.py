"""Whole frozen V1 default ledger validation and adversarial capture comparisons."""
import ast
import base64
import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.providers.repository_data_io import RepositoryDataIO
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.repository_memory import RepositoryMemoryIO
from lib.repository_paths import RepositoryPaths
from lib.v2_boundary import violations

FIXTURES = ROOT / 'tests/fixtures/v2-repository-validation'
CONTRACT = json.loads((FIXTURES / 'contract.json').read_bytes())


class LifecycleHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        self.root.mkdir(mode=0o700)
        for name in ('model', 'schemas', 'governance', 'status', 'docs', 'scripts', 'generated', '.github'):
            shutil.copytree(ROOT / name, self.root / name,
                            ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        shutil.copyfile(ROOT / 'requirements-validation.txt', self.root / 'requirements-validation.txt')
        self.modules = patch.dict(sys.modules, {})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.original = {}
        sources = {**CONTRACT['lifecycle_helpers'], **CONTRACT['lifecycle_history'],
                   **CONTRACT['lifecycle_capture_adapter'], **CONTRACT['lifecycle_history_support']}
        order = ['contracts', 'adapter', 'kernel', 'store', 'decisions', 'closure', 'exceptions',
                 'live_preparation', 'live_evidence', 'live_admission', 'personal_probe', 'pilot_actions',
                 'operating_acceptance', 'generate_governance_lifecycle_index',
                 *[n for n in CONTRACT['lifecycle_history'] if n.startswith('generate_')],
                 'validate_governance_lifecycle_ledger']
        for name in order:
            metadata = sources[name]
            raw = (FIXTURES / metadata['fixture']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata['source_sha256'])
            full = 'lib.governance_lifecycle.' + name if not name.startswith(('generate_', 'validate_')) else name
            module = ModuleType(full)
            module.__package__ = 'lib.governance_lifecycle' if full.startswith('lib.') else ''
            module.__file__ = str(self.root / metadata['source_path'])
            sys.modules[full] = module
            exec(compile(raw, str(FIXTURES / metadata['fixture']), 'exec'), module.__dict__)
            self.original[name] = module
        self.current = RepositoryLifecycle(self.root, validator_class=Draft202012Validator,
                                           provider_factory=LegacyRepositoryLifecycleCapture)

    @staticmethod
    def result(function, *args, **kwargs):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                result = {'value': function(*args, **kwargs)}
            except Exception as error:
                result = {'type': type(error).__name__, 'message': str(error)}
        return result | {'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()}

    def original_default(self):
        with patch.object(sys, 'argv', ['validate_governance_lifecycle_ledger.py']):
            return self.result(self.original['validate_governance_lifecycle_ledger'].main)

    def current_default(self, context=None):
        return self.result((context or self.current).validate_default_ledger, print_line=print)

    def receipt(self):
        return json.loads(next((self.root / 'governance/lifecycle/live-validation/transactions').glob('*.json')).read_bytes())

    def test_all_62_history_functions_retain_the_original_ast_after_declared_ports(self):
        def dump(node): return ast.dump(node, include_attributes=False)
        def expression(value): return ast.parse(value, mode='eval').body
        count = 0
        for module, metadata in CONTRACT['lifecycle_history'].items():
            original = ast.parse((FIXTURES / metadata['fixture']).read_bytes())
            expected = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
            actual_module = ast.parse((ROOT / 'scripts/lib/repository_lifecycle' / metadata['module']).read_bytes())
            cls = next(n for n in actual_module.body if isinstance(n, ast.ClassDef))
            actual = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
            mapping = {dump(expression('self.root')): expression('ROOT'),
                       dump(expression('self.path_factory')): expression('Path')}
            mapping.update({dump(expression('self.' + name)): expression(name) for name in metadata['functions']})
            mapping.update({dump(expression(value)): expression(name) for name, value in metadata['import_ports'].items()})
            mapping.update({dump(expression('self.input_' + name.lower())): expression(name) for name in metadata['root_constants']})
            mapping[dump(expression('self.context.provider.capture_method'))] = ast.Constant('github_api_get_via_gh')
            if module == 'personal_probe':
                for name in ('assess_bound_comments', 'comment_identity', 'replay_bound_snapshot'):
                    mapping[dump(expression('self.context.provider.' + name))] = expression(name)
            for old in ast.walk(original):
                if not isinstance(old, ast.JoinedStr): continue
                spelling = ast.unparse(old)
                if module == 'live_preparation' and spelling == 'f"github-user:{subject[\'provider_user_id\']}"':
                    mapping[dump(expression("self.context.provider.subject_id(subject['provider_user_id'])"))] = old
                if module == 'live_preparation' and spelling == 'f"https://github.com/{subject[\'login\']}"':
                    mapping[dump(expression("self.context.provider.profile_url(subject['login'])"))] = old
                if module in ('operating_acceptance', 'generate_personal_channel_probe') and 'Diskussion: https://github.com/' in spelling:
                    variable = 'request' if module == 'generate_personal_channel_probe' else 'value'
                    prefix = old.values[0].value.split('https://github.com/')[0]
                    suffix = old.values[-1].value
                    replacement = repr(prefix) + " + self.context.provider.discussion_url(" + variable + "['repository_id'], " + variable + "['discussion_number']) + " + repr(suffix)
                    mapping[dump(expression(replacement))] = old
            for name in metadata['functions']:
                count += 1
                with self.subTest(module=module, function=name):
                    value = copy.deepcopy(actual[name])
                    self.assertEqual(value.args.args.pop(0).arg, 'self')
                    omitted = metadata['omitted_defaults'][name]
                    for argument, old_default in omitted.items():
                        offset = 1 if isinstance(value.body[0], ast.Expr) and isinstance(value.body[0].value, ast.Constant) and isinstance(value.body[0].value.value, str) else 0
                        guard = value.body.pop(offset)
                        self.assertEqual(ast.unparse(guard.test), argument + ' is _OMITTED')
                        self.assertEqual(guard.body[0].targets[0].id, argument)
                        expected_value = metadata['import_ports'].get(old_default, 'self.root' if old_default == 'ROOT' else None)
                        self.assertEqual(dump(guard.body[0].value), dump(expression(expected_value)))
                        index = next(i for i, arg in enumerate(value.args.args) if arg.arg == argument)
                        position = index - (len(value.args.args) - len(value.args.defaults))
                        self.assertEqual(ast.unparse(value.args.defaults[position]), '_OMITTED')
                        value.args.defaults[position] = expression(old_default)
                    nested = {n.names[0].asname or n.names[0].name: n for n in ast.walk(expected[name]) if isinstance(n, ast.ImportFrom)}
                    class Undo(ast.NodeTransformer):
                        def visit(self, node):
                            if dump(node) in mapping:
                                return copy.deepcopy(mapping[dump(node)])
                            return super().visit(node)
                        def visit_Assign(self, node):
                            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in nested:
                                old_import = nested[node.targets[0].id]
                                expected_port = 'self.context.' + ('personal' if old_import.module == 'personal_probe' else metadata['context']) + '.' + old_import.names[0].name
                                if old_import.module.startswith('generate_'):
                                    expected_port = 'self.context.' + CONTRACT['lifecycle_history'][old_import.module]['context'] + '.' + old_import.names[0].name
                                if ast.unparse(node.value) == expected_port:
                                    return copy.deepcopy(old_import)
                            return self.generic_visit(node)
                    if module == 'live_admission' and name == 'replay_embedded':
                        self.assertEqual(ast.unparse(value.body[-1]), 'return self.context.provider.replay_embedded(files)')
                        value.body[-1] = copy.deepcopy(expected[name].body[-1])
                    self.assertEqual(dump(Undo().visit(value)), dump(expected[name]))
        self.assertEqual(count, 62)

    def test_all_seven_captured_provider_functions_retain_original_checks(self):
        actual_module = ast.parse((ROOT / 'scripts/lib/providers/repository_lifecycle_capture.py').read_bytes())
        cls = next(n for n in actual_module.body if isinstance(n, ast.ClassDef))
        actual = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
        count = 0
        for module, metadata in CONTRACT['lifecycle_capture_adapter'].items():
            original = ast.parse((FIXTURES / metadata['fixture']).read_bytes())
            expected = {n.name: n for n in original.body if isinstance(n, ast.FunctionDef)}
            mapping = {'self.path_factory': 'Path', 'self.context.contracts.validator_class': 'Draft202012Validator'}
            mapping.update({'self.' + name: name for name in metadata['functions']})
            mapping.update({value: name for name, value in metadata['import_ports'].items()})
            class Undo(ast.NodeTransformer):
                def visit_Attribute(self, node):
                    value = ast.unparse(node)
                    if value in mapping: return ast.Name(id=mapping[value], ctx=ast.Load())
                    return self.generic_visit(node)
                def visit_Assign(self, node):
                    if ast.unparse(node.value) == 'self.context.contracts.schema_validator':
                        return ast.ImportFrom(module='contracts', names=[ast.alias(name='schema_validator')], level=1)
                    return self.generic_visit(node)
            for name in metadata['functions']:
                count += 1
                with self.subTest(module=module, function=name):
                    value = copy.deepcopy(actual[name])
                    self.assertEqual(value.args.args.pop(0).arg, 'self')
                    self.assertEqual(ast.dump(Undo().visit(value), include_attributes=False),
                                     ast.dump(expected[name], include_attributes=False))
        self.assertEqual(count, 7)

    def test_complete_original_default_main_stdout_stderr_result_and_no_file_effect(self):
        def inventory():
            return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob('*') if p.is_file()}
        before = inventory()
        expected = self.original_default()
        self.assertEqual(expected['value'], None)
        self.assertIn('synthetic closure pilot', expected['stdout'])
        with patch('subprocess.run', side_effect=AssertionError('no native process allowed')), \
             patch('subprocess.check_output', side_effect=AssertionError('no native process allowed')), \
             patch('tempfile.TemporaryDirectory', side_effect=AssertionError('no temporary materialization allowed')):
            actual = self.current_default()
        self.assertEqual(actual, expected)
        self.assertEqual(inventory(), before)

    def test_all_historical_projections_and_report_and_viewer_bytes_equal_original(self):
        for name in ('generate_lifecycle_pilot_validation', 'generate_personal_channel_probe',
                     'generate_personal_channel_evidence', 'generate_lifecycle_pilot_actions'):
            with self.subTest(name=name):
                current = getattr(self.current, CONTRACT['lifecycle_history'][name]['context'])
                self.assertEqual(current.validate(), self.original[name].validate())
        old = self.original['operating_acceptance']
        for method in ('manifest', 'request', 'captures', 'effective', 'projection', 'validate'):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.current.operating, method)(), getattr(old, method)())
        index = old.projection()
        self.assertEqual(self.current.operating.render(index), old.render(index))
        request = old.request()
        self.assertEqual(self.current.operating.statement_template(request, self.current.personal.statement_body),
                         old.statement_template(request, self.original['personal_probe'].statement_body))
        overview = self.original['generate_governance_lifecycle_overview'].validate_overview()
        self.assertEqual(self.current.governance_lifecycle_overview.validate_overview(), overview)
        self.assertEqual(self.current.governance_lifecycle_viewer.validate_viewer(overview=overview),
                         self.original['generate_governance_lifecycle_viewer'].validate_viewer(overview=overview))

    def test_entire_default_validation_works_through_held_directory_namespace(self):
        namespace = RepositoryPaths(str(self.root), RepositoryDataIO(self.root))
        bound = RepositoryLifecycle(namespace.root, validator_class=Draft202012Validator,
                                    path_factory=namespace.path, provider_factory=LegacyRepositoryLifecycleCapture)
        self.assertEqual(self.current_default(bound), self.original_default())

    def test_capture_profile_must_be_explicit(self):
        context = RepositoryLifecycle(self.root, validator_class=Draft202012Validator)
        self.assertEqual(self.current_default(context)['message'], 'explicit_lifecycle_capture_profile_required')

    def test_all_complete_embedded_receipts_match_original_without_provider_authentication(self):
        for path in (self.root / 'governance/lifecycle/live-validation/transactions').glob('*.json'):
            record = json.loads(path.read_bytes())
            expected = self.original['live_admission'].replay_embedded(record['capture'])
            actual = self.current.admission.replay_embedded(record['capture'])
            self.assertEqual(actual, expected)
            self.assertEqual(actual['verification_scope'], 'captured_metadata_and_bytes')
            self.assertFalse(actual['official_state'])
            self.assertIn('captured_provider_metadata_is_not_independently_authenticated_by_offline_replay', actual['limits'])

    def test_unsafe_missing_extra_and_changed_capture_members_keep_original_errors(self):
        encoded = self.receipt()['capture']
        mutations = []
        missing = copy.deepcopy(encoded); missing.pop('repository.json'); mutations.append(missing)
        extra = copy.deepcopy(encoded); extra['unlisted.json'] = base64.b64encode(b'{}').decode(); mutations.append(extra)
        changed = copy.deepcopy(encoded); changed['repository.json'] = base64.b64encode(b'{}').decode(); mutations.append(changed)
        unsafe = copy.deepcopy(encoded); unsafe['../outside'] = base64.b64encode(b'{}').decode(); mutations.append(unsafe)
        malformed = copy.deepcopy(encoded); malformed['repository.json'] = '!'; mutations.append(malformed)
        for value in mutations:
            with self.subTest(keys=list(value)[-2:]):
                expected = self.result(self.original['live_admission'].replay_embedded, value)
                self.assertIn('type', expected)
                self.assertEqual(self.result(self.current.admission.replay_embedded, value), expected)

    def test_outer_manifest_rehash_cannot_hide_wrong_run_or_report(self):
        encoded = self.receipt()['capture']
        for name, key, value in [('run-after.json', 'head_sha', '0' * 40),
                                 ('repository.json', 'id', 1), ('preflight.json', 'captured_at', '2020-01-01T00:00:00Z')]:
            changed = copy.deepcopy(encoded)
            payload = json.loads(base64.b64decode(changed[name])); payload[key] = value
            raw = json.dumps(payload).encode(); changed[name] = base64.b64encode(raw).decode()
            if name != 'preflight.json':
                manifest = json.loads(base64.b64decode(changed['preflight.json']))
                manifest['capture']['snapshot_sha256'][name] = hashlib.sha256(raw).hexdigest()
                changed['preflight.json'] = base64.b64encode(json.dumps(manifest).encode()).decode()
            expected = self.result(self.original['live_admission'].replay_embedded, changed)
            self.assertIn('type', expected)
            self.assertEqual(self.result(self.current.admission.replay_embedded, changed), expected)

    def test_duplicate_preparation_and_wrong_provider_identity_keep_original_errors(self):
        prepared = self.current.preparation.validate_preparation()
        for key, value in [('subject_id', 'other-user:1'), ('profile_url', 'https://example.invalid/user')]:
            binding = copy.deepcopy(prepared['binding']); binding['subjects'][0][key] = value
            expected = self.result(self.original['live_preparation'].validate_bindings, [binding])
            self.assertIn('type', expected)
            self.assertEqual(self.result(self.current.preparation.validate_bindings, [binding]), expected)
        bindings = self.root / 'model/governance/lifecycle/live-pilot/role-bindings'
        shutil.copyfile(bindings / '00000001.json', bindings / '00000003.json')
        self.assertEqual(self.current_default(), self.original_default())
        self.assertIn('type', self.current_default())

    def test_tampered_channel_action_operating_and_overview_outputs_keep_full_default_error(self):
        for name in ('generated/reports/lifecycle-personal-channel-statement.md',
                     'generated/reports/governance-lifecycle-pilot-actions.md',
                     'generated/reports/governance-lifecycle-live.md',
                     'generated/reports/governance-lifecycle-overview.md',
                     'generated/viewer/governance-lifecycle-viewer.html'):
            with self.subTest(name=name):
                path = self.root / name; before = path.read_bytes()
                try:
                    path.write_bytes(before + b'changed')
                    expected = self.original_default()
                    self.assertIn('type', expected)
                    self.assertEqual(self.current_default(), expected)
                finally:
                    path.write_bytes(before)

    def test_implementation_changes_invalidate_historical_acceptance_without_repairing_it(self):
        path = self.root / 'scripts/lib/governance_lifecycle/adapter.py'
        path.write_bytes(path.read_bytes() + b'\n# controlled observed-data mutation\n')
        expected = self.original['operating_acceptance'].effective()
        self.assertFalse(expected['implementation_matches'])
        self.assertFalse(expected['effective'])
        self.assertEqual(self.current.operating.effective(), expected)
        self.assertEqual(self.current_default(), self.original_default())
        self.assertIn('type', self.current_default())

    def test_comment_identity_actor_edit_delete_wrong_discussion_and_app_metadata_equal_original(self):
        snapshot = json.loads(next((self.root / 'generated/reports/lifecycle-operating-acceptance').glob('*.json')).read_bytes())
        request = snapshot['request']
        comments = [c for page in snapshot['comment_pages_after'] for c in json.loads(page)]
        at = snapshot['result']['captured_at']
        self.assertTrue(comments)
        variants = [copy.deepcopy(comments), []]
        for key, value in [('html_url', 'https://example.invalid/wrong'), ('updated_at', at),
                           ('performed_via_github_app', {'id': 1})]:
            modified = copy.deepcopy(comments); modified[0][key] = value; variants.append(modified)
        modified = copy.deepcopy(comments); modified[0]['user']['type'] = 'Bot'; variants.append(modified)
        modified = copy.deepcopy(comments); modified.append(copy.deepcopy(modified[0])); variants.append(modified)
        modified = copy.deepcopy(comments); modified[0].pop('performed_via_github_app', None); variants.append(modified)
        for value in variants:
            expected = self.result(self.original['personal_probe'].assess_bound_comments,
                                   request, value, captured_at=at, previous_comments=comments)
            self.assertEqual(self.result(self.current.provider.assess_bound_comments,
                request, value, captured_at=at, previous_comments=comments), expected)

    def test_explicit_none_does_not_silently_select_the_default_root(self):
        for name, method in [('live_preparation', 'validate_preparation'), ('live_admission', 'load_operating'),
                             ('pilot_actions', 'project_actions'), ('operating_acceptance', 'effective'),
                             ('generate_governance_lifecycle_overview', 'validate_overview')]:
            target = getattr(self.current, CONTRACT['lifecycle_history'][name]['context'])
            self.assertEqual(self.result(getattr(target, method), None),
                             self.result(getattr(self.original[name], method), None))

    def test_neutral_history_has_no_provider_or_old_implementation_imports(self):
        for path in (ROOT / 'scripts/lib/repository_lifecycle').glob('*.py'):
            self.assertEqual(violations(path.relative_to(ROOT).as_posix(), path.read_text()), [], path.name)
        adapter = ast.parse((ROOT / 'scripts/lib/providers/repository_lifecycle_capture.py').read_bytes())
        imports = [n for n in ast.walk(adapter) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertNotIn('subprocess', '\n'.join(ast.unparse(n) for n in imports))
        self.assertNotIn('lib.governance_lifecycle', '\n'.join(ast.unparse(n) for n in imports))


class EmbeddedMemoryTests(unittest.TestCase):
    def test_memory_is_read_only_and_directory_order_matches_materialization(self):
        files = {'b/z': b'z', 'a': b'first', 'b/y': b'y'}
        memory = RepositoryMemoryIO(files)
        files['a'] = b'changed'
        self.assertEqual(memory.read('a'), b'first')
        self.assertEqual([r['name'] for r in memory.entries('')], ['b', 'a'])
        self.assertEqual([r['name'] for r in memory.entries('b')], ['z', 'y'])
        with self.assertRaises(TypeError): memory.files['a'] = b'mutation'
        with self.assertRaises(IsADirectoryError): memory.read('b')
        with self.assertRaises(NotADirectoryError): memory.entries('a')
        with self.assertRaises(FileNotFoundError): memory.read('missing')

    def test_path_collision_and_budgets_fail_before_any_native_write(self):
        for files in ({'a': b'', 'a/b': b''}, {'a/b': b'', 'a': b''}):
            with self.assertRaises(OSError): RepositoryMemoryIO(files)
        for name in ('../escape', '/outside', 'a/../b', 'a//b', '.'):
            with self.assertRaises(ValueError): RepositoryMemoryIO({name: b''})
        with self.assertRaises(ValueError): RepositoryMemoryIO({'a': b'xx'}, maximum_bytes=1)
        with self.assertRaises(ValueError): RepositoryMemoryIO({'a/b': b''}, maximum_members=2)


if __name__ == '__main__':
    unittest.main()
