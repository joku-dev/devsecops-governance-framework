"""Whole frozen V1 current-file comparisons and separately labelled offline guards."""
import base64
import ast
from copy import deepcopy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(os.environ.get('AXIOM_TEST_PRODUCT_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.validation_application import ValidationContext, execute
from lib.validation_files import ValidationFiles, WORKING_PROFILE
from lib.validation_operations import RuntimeValidationEnvironment
from lib.providers.validation_tools import ValidationOPA
from lib.providers.validation_worktree import ValidationWorktree
from lib.providers import validation_worktree
from lib import validation_sources

OPA = Path(shutil.which('opa')) if shutil.which('opa') else ROOT / '.venv-validation/bin/opa'
DIRECTORY = ROOT / 'tests/fixtures/v2-runtime-validation'
spec = importlib.util.spec_from_file_location('working_original_runtime', ROOT / 'tests/acceptance/v1_runtime_validation_oracle.py')
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)


class RuntimeWorkingTree(unittest.TestCase):
    def setUp(self):
        previous = os.umask(0o077); self.addCleanup(os.umask, previous)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve(); product = self.base / 'product'; product.mkdir(mode=0o700)
        self.original = oracle.Original(DIRECTORY, product); self.original.write_data(self.original.contract['data'])
        self.git_environment = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_AUTHOR_NAME': 'Synthetic fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Synthetic fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
        for args in [('init', '-q'), ('add', '.'), ('commit', '-qm', 'Trusted immutable original fixture')]: self.git(product, *args)
        self.source = self.base / 'current'; shutil.copytree(product, self.source)
        self.reference = oracle.Original(DIRECTORY, self.source)
        self.revision = self.git(product, 'rev-parse', 'HEAD').decode().strip()
        self.instance = self.base / 'instance'; self.instance.mkdir(mode=0o700)
        self.context = ValidationContext(self.instance, {'node_id': 'synthetic-working-tree-node', 'opa': str(OPA)}, product_root=product)

    def git(self, root, *args):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgSign=false', '-C', str(root), *args], env=self.git_environment, stderr=subprocess.STDOUT)

    def edit(self, name, transform):
        p = self.source / name; value = yaml.safe_load(p.read_bytes()); transform(value)
        p.write_text(yaml.safe_dump(value, sort_keys=False))

    def compare(self, expected_code=0):
        data, manifest = ValidationWorktree(self.source, self.revision).capture()
        files = ValidationFiles(data, manifest['membership'], label=str(self.source), native_profile=WORKING_PROFILE)
        port = ValidationOPA(OPA, product_root=self.original.root)
        value, environment = execute(files, port)
        code, stdout, stderr, output = self.reference.run(opa=OPA)
        self.assertEqual(value['execution'], 'complete')
        self.assertEqual((value['exit_code'], base64.b64decode(value['stdout_base64']), base64.b64decode(value['stderr_base64'])), (code, stdout, stderr))
        self.assertEqual(files.files, output)
        self.assertEqual(code, expected_code)
        self.assertTrue(all(not x['process_started'] for x in environment.commands))
        self.assertTrue(all(x['request']['execution_profile'] == WORKING_PROFILE for x in port.observations))
        self.assertFalse(any(name.startswith('scripts/') for name in data))
        return value, files, port

    def test_pristine_whole_original_stdout_stderr_exit_and_every_file(self):
        self.compare()

    def test_all_nine_original_functions_preserved_with_explicit_environment_operations(self):
        original = ast.parse(self.original.contract['sources']['scripts/validate_runtime_governance.py'])
        functions = {node.name for node in original.body if isinstance(node, ast.FunctionDef)}
        class Ports(ast.NodeTransformer):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load) and node.id == 'ROOT':
                    return ast.Attribute(ast.Name('self', ast.Load()), 'root', ast.Load())
                if isinstance(node.ctx, ast.Load) and node.id in functions:
                    return ast.Attribute(ast.Name('self', ast.Load()), node.id, ast.Load())
                return node
            def visit_Attribute(self, node):
                node = self.generic_visit(node)
                mapping = {('sys', 'executable'): 'python', ('shutil', 'which'): 'which',
                           ('subprocess', 'run'): 'run', ('jsonschema', 'validate'): 'validate'}
                if isinstance(node.value, ast.Name) and (node.value.id, node.attr) in mapping:
                    return ast.Attribute(ast.Attribute(ast.Name('self', ast.Load()), 'environment', ast.Load()), mapping[(node.value.id, node.attr)], ast.Load())
                return node
            def visit_Call(self, node):
                node = self.generic_visit(node)
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    node.func = ast.Attribute(ast.Attribute(ast.Name('self', ast.Load()), 'environment', ast.Load()), 'print', ast.Load())
                return node
        implementation = ast.parse((ROOT / 'scripts/lib/runtime_validation.py').read_bytes())
        actual = next(node for node in implementation.body if isinstance(node, ast.ClassDef) and node.name == 'RuntimeValidation')
        methods = {node.name: node for node in actual.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(methods), functions | {'__init__'}); self.assertEqual(len(functions), 9)
        for node in original.body:
            if not isinstance(node, ast.FunctionDef): continue
            node.args.args.insert(0, ast.arg(arg='self'))
            with self.subTest(function=node.name):
                self.assertEqual(ast.dump(Ports().visit(node)), ast.dump(methods[node.name]))

    def test_dirty_marker_counterexample_now_matches_whole_original(self):
        self.edit('architecture/quality-markers.yaml', lambda d: d['markers'][0].update(id='UNKNOWN-DIRTY'))
        self.compare(1)

    def test_working_bytes_win_over_different_staged_bytes(self):
        self.git(self.source, 'add', 'architecture/quality-markers.yaml')
        self.edit('architecture/quality-markers.yaml', lambda d: d['markers'][0].update(id='AFTER-STAGING'))
        self.compare(1)

    def test_untracked_architecture_level_is_included_in_original_glob(self):
        shutil.copyfile(self.source / 'architecture/arch-l1.yaml', self.source / 'architecture/arch-extra.yaml')
        self.compare(1)

    def test_deleted_demo_input_matches_original_schema_failure_and_skipped_generator(self):
        (self.source / 'generated/demo/ha-cpswms-architecture-release-input.json').unlink()
        self.compare(1)

    def test_deleted_optional_devsecops_report_matches_original_effects(self):
        (self.source / 'generated/demo/ha-cpswms-devsecops-governance-report.json').unlink()
        self.compare()

    def test_dirty_schema_uses_actual_current_validation_contract(self):
        p = self.source / 'schemas/quality-marker.schema.json'; data = json.loads(p.read_text()); data['maxProperties'] = 0; p.write_text(json.dumps(data))
        self.compare(1)

    def test_invalid_nonpath_rule_preserves_original_exception_class_as_incomplete(self):
        self.edit('architecture/arch-l1.yaml', lambda d: d['requirements'][0]['policy_as_code'].update(rule=17))
        operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        old_code, _, old_stderr, _ = self.reference.run(opa=OPA)
        self.assertEqual(old_code, 1); self.assertIn(b'TypeError', old_stderr)
        self.assertEqual(value['execution'], 'incomplete'); self.assertEqual(value['exception_type'], 'TypeError')
        self.assertEqual(value['exit_code'], 2)
        with self.assertRaisesRegex(ValueError, 'incomplete_execution_cannot_replay'): self.context.inspect(operation)

    def test_uncommitted_rego_policy_is_actually_evaluated_and_matches_original(self):
        (self.source / 'policies/opa/architecture_release_readiness.rego').write_text('package architecture.release_readiness\nimport rego.v1\ndeny contains "working-policy-finding" if { true }\n')
        value, _, port = self.compare(1)
        self.assertIn(b'working-policy-finding', base64.b64decode(value['stdout_base64']))
        self.assertTrue(any(x['process_started'] for x in port.observations))

    def test_missing_policy_and_example_input_keep_native_failure_semantics(self):
        for name in ['policies/opa/architecture_release_readiness.rego', 'policies/example-input.architecture-release-candidate.json']:
            with self.subTest(name=name):
                path = self.source / name; raw = path.read_bytes(); path.unlink()
                operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
                old_code, _, _, _ = self.reference.run(opa=OPA)
                self.assertEqual(value['execution'], 'complete')
                self.assertEqual(value['exit_code'], old_code)
                self.assertEqual(old_code, 1)
                self.assertTrue(any(x['process_started'] and x['returncode'] != 0 for x in value['native_observations']))
                self.assertEqual(self.context.inspect(operation), value)
                # Native missing-file diagnostics contain actual private tool
                # paths; their raw cross-context identity is not asserted.
                path.write_bytes(raw)

    def test_deleted_and_untracked_policy_rule_existence_matches_original(self):
        (self.source / 'scripts/validate_runtime_governance.py').rename(self.source / 'scripts/saved.py')
        # The frozen reference program itself is restored only for its actual
        # execution; a different missing policy operand is checked by both.
        self.edit('architecture/arch-l1.yaml', lambda d: d['requirements'][0]['policy_as_code'].update(candidate=True, rule='new/validate_runtime_governance.py'))
        (self.source / 'scripts/saved.py').rename(self.source / 'scripts/validate_runtime_governance.py')
        self.compare(1)
        (self.source / 'new').mkdir(); (self.source / 'new/validate_runtime_governance.py').write_text('never execute this source')
        self.compare()

    def test_caller_python_is_membership_only_and_never_executed(self):
        marker = self.base / 'caller-code-executed'
        for name in oracle.PROGRAMS:
            (self.source / name).write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\nraise RuntimeError("caller code")\n')
        operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        self.assertEqual(value['exit_code'], 0); self.assertFalse(marker.exists())
        self.assertTrue(value['working_tree_used']); self.assertFalse(value['source_worktree_clean'])
        self.assertTrue(operation)

    def test_retained_replay_survives_deleted_caller_without_native_or_source_access(self):
        operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        shutil.rmtree(self.source)
        with patch('lib.validation_application.ValidationOPA', side_effect=AssertionError('native replay')), patch('lib.validation_application.ValidationWorktree', side_effect=AssertionError('caller replay')):
            self.assertEqual(self.context.inspect(operation), value)
        self.assertEqual(self.context.status()[0]['state'], 'retained_declared_replay_consistent')
        self.assertFalse(value['authority_transferred']); self.assertFalse(value['independent_execution_attested'])

    def test_foreign_base_and_installed_source_root_are_rejected_before_native_execution(self):
        with self.assertRaisesRegex(ValueError, 'separate_validation'):
            self.context.create('2026-11-18T13:00:00Z', source_worktree=self.original.root)
        (self.source / 'extra').write_text('other commit'); self.git(self.source, 'add', 'extra'); self.git(self.source, 'commit', '-qm', 'Different product revision')
        with self.assertRaisesRegex(ValueError, 'revision_mismatch'):
            self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        self.assertEqual(list(self.context.operations.iterdir()), [])

    def test_symlinks_hardlinks_and_fifos_are_explicit_pre_execution_guards(self):
        p = self.source / 'schemas/foreign.json'; outside = self.base / 'private.json'; outside.write_text('{}')
        for kind in ('symlink', 'hardlink', 'fifo'):
            with self.subTest(kind=kind):
                if kind == 'symlink': p.symlink_to(outside)
                elif kind == 'hardlink': os.link(outside, p)
                else: os.mkfifo(p)
                with self.assertRaises(ValueError): ValidationWorktree(self.source, self.revision).capture()
                p.unlink()
        self.assertEqual(list(self.context.operations.iterdir()), [])

    def test_evaluated_external_schema_reference_fails_without_fetching_live_local_server(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path); self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        def stop(): server.shutdown(); thread.join(timeout=2); server.server_close()
        self.addCleanup(stop)
        p = self.source / 'schemas/quality-marker.schema.json'; p.write_text(json.dumps({'$ref': f'http://127.0.0.1:{server.server_port}/private-schema'}))
        operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        self.assertEqual(value['execution'], 'complete'); self.assertEqual(value['exit_code'], 1)
        self.assertEqual(requests, []); self.assertTrue(value['native_observations'])
        self.assertEqual(self.context.inspect(operation), value)

    def test_unused_schema_reference_is_inert_and_does_not_reject_original_input(self):
        (self.source / 'schemas/unused.operator.schema.json').write_text('{"$ref":"http://127.0.0.1:1/never-evaluated"}')
        self.compare()

    def test_core_schema_registry_rejects_external_resolution_without_network(self):
        files = ValidationFiles({}, native_profile=WORKING_PROFILE)
        environment = RuntimeValidationEnvironment(files, None)
        with self.assertRaises(Exception) as error:
            environment.validate({}, {'$ref': 'http://127.0.0.1:1/never-fetched'})
        self.assertIn('Unresolvable', str(error.exception))

    def test_mutable_network_and_runtime_builtins_are_explicit_native_guards(self):
        local_schema = self.base / 'never-read-schema.json'; local_schema.write_text('{"type":"object"}')
        for expression in ['http.send({"method":"get","url":"http://127.0.0.1:1/never-called"})', 'net.lookup_ip_addr("never-called.invalid")', 'opa.runtime()',
                           'json.match_schema({}, ' + json.dumps({'$ref': local_schema.as_uri()}) + ')',
                           'json.verify_schema(' + json.dumps({'$ref': local_schema.as_uri()}) + ')']:
            with self.subTest(expression=expression):
                (self.source / 'policies/opa/architecture_release_readiness.rego').write_text('package architecture.release_readiness\nimport rego.v1\ndeny contains "unsafe" if { x := ' + expression + '; x != null }\n')
                operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
                self.assertEqual(value['execution'], 'complete'); self.assertEqual(value['exit_code'], 1)
                self.assertTrue(any(x['returncode'] != 0 for x in value['native_observations']))
                errors = b'\n'.join(base64.b64decode(x[name + '_base64'])
                    for x in value['native_observations'] for name in ('stdout', 'stderr'))
                self.assertIn(b'undefined function', errors)
                self.assertEqual(self.context.inspect(operation), value)

    def test_file_budget_rejects_before_native_and_keeps_caller_files(self):
        with patch.object(validation_worktree, 'MAX_FILE', 10):
            with self.assertRaisesRegex(ValueError, 'oversize'):
                self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        self.assertEqual(list(self.context.operations.iterdir()), [])
        self.assertTrue((self.source / 'architecture/quality-markers.yaml').is_file())

    def test_concurrent_input_change_preserves_pending_and_never_retries(self):
        original_execute = execute
        def changed(files, port):
            value = original_execute(files, port)
            self.edit('architecture/quality-markers.yaml', lambda d: d['markers'][0].update(id='CONCURRENT'))
            return value
        with patch('lib.validation_application.execute', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'product_inputs_changed'):
                self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        operation = next(self.context.operations.iterdir()).name
        with self.assertRaisesRegex(ValueError, 'pending_requires_review'): self.context.inspect(operation)
        self.assertEqual(self.context.status()[0]['state'], 'pending_incomplete_or_invalid')

    def test_closed_manifest_record_authority_and_profile_cannot_be_reinterpreted(self):
        operation, _ = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        target = self.context.operations / operation; report = target / 'assessment.json'; pending = target / 'pending.json'; manifest = target / 'input-manifest.json'
        originals = {p: p.read_bytes() for p in [report, pending, manifest]}
        for kind in ['authority', 'profile', 'membership', 'manifest-extra']:
            with self.subTest(kind=kind):
                if kind in ['authority', 'profile']:
                    for p in [report, pending]:
                        value = json.loads(p.read_text()); value['authority_transferred' if kind == 'authority' else 'working_tree_used'] = True if kind == 'authority' else False; p.write_text(json.dumps(value))
                else:
                    value = json.loads(manifest.read_text()); value['membership' if kind == 'membership' else 'invented'] = ['private/undeclared'] if kind == 'membership' else False; manifest.write_text(json.dumps(value))
                with self.assertRaises(ValueError): self.context.inspect(operation)
                for p, raw in originals.items(): p.write_bytes(raw)
        self.assertEqual(self.context.inspect(operation)['exit_code'], 0)


    def test_compiler_schema_file_reference_stops_after_parse_and_replays_the_guard(self):
        schema = self.base / 'compiler-private-schema.json'
        schema.write_text('{"type":"object","properties":{"foo":{"type":"string"}}}')
        policy = self.source / 'policies/opa/architecture_release_readiness.rego'
        operations = []
        definitions = [{'$ref': schema.as_uri()},
            {'$ref': '#/$defs/escape', '$defs': {'escape': {'$ref': schema.as_uri()}}},
            {'$ref': '#/const/escape', 'const': {'escape': {'$ref': schema.as_uri()}}}]
        for definition in definitions:
            with self.subTest(definition=definition):
                policy.write_text('package architecture.release_readiness\nimport rego.v1\n# METADATA\n# schemas:\n# - input: ' + json.dumps(definition) + '\ndeny contains x if { x := input.foo + 1 }\n')
                operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
                operations.append((operation, value))
                self.assertEqual(value['execution'], 'complete'); self.assertEqual(value['exit_code'], 1)
                related = [row for row in value['native_observations'] if row['request']['policy'].endswith('architecture_release_readiness.rego')]
                self.assertTrue(related)
                self.assertTrue(all(row['request'].get('native_action') == 'parse-policy' and row['returncode'] == 0 for row in related))
                self.assertIn(b'validation_policy_schema_reference_forbidden', base64.b64decode(value['stdout_base64']))
        # No evaluation was invoked. Offline replay uses the retained AST and
        # locally resolves pointers, including references into otherwise inert data.
        schema.unlink(); shutil.rmtree(self.source)
        for operation, value in operations: self.assertEqual(self.context.inspect(operation), value)

    def test_local_annotation_schemas_and_literal_ref_data_preserve_whole_original(self):
        for schema in [{'type': 'object'}, {'type': 'object', 'const': {'$ref': 'file:///axiom-synthetic-inert-literal'}}]:
            with self.subTest(schema=schema):
                policy = self.source / 'policies/opa/architecture_release_readiness.rego'
                policy.write_text('package architecture.release_readiness\nimport rego.v1\n# METADATA\n# schemas:\n# - input: ' + json.dumps(schema) + '\ndeny := set()\n')
                self.compare()

    def test_retained_parse_ast_and_parse_eval_order_cannot_change_replay(self):
        operation, value = self.context.create('2026-11-18T13:00:00Z', source_worktree=self.source)
        self.assertEqual(len(value['native_observations']), 16)
        target = self.context.operations / operation / 'assessment.json'; original = target.read_bytes()
        changed = json.loads(original); row = changed['native_observations'][0]
        self.assertEqual(row['request']['native_action'], 'parse-policy')
        parsed = json.loads(base64.b64decode(row['stdout_base64']))
        parsed['annotations'] = [{'schemas': [{'definition': {'$ref': 'file:///axiom-synthetic-forged-reference'}}]}]
        row['stdout_base64'] = base64.b64encode(json.dumps(parsed).encode()).decode()
        target.write_text(json.dumps(changed))
        with self.assertRaises(ValueError): self.context.inspect(operation)
        changed = json.loads(original); changed['native_observations'][0:2] = list(reversed(changed['native_observations'][0:2]))
        target.write_text(json.dumps(changed))
        with self.assertRaises(ValueError): self.context.inspect(operation)
        target.write_bytes(original); self.assertEqual(self.context.inspect(operation), value)



if __name__ == '__main__': unittest.main()
