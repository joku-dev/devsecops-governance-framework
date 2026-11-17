"""Original state/log effects in atomic private generations, with offline replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests/acceptance')]
from lib import candidate_workspace, review_dispatch as logic, review_dispatch_application as app
from lib.candidate_workspace import inventory
from lib.portable.contracts import canonical_digest
from lib.provider_ports import capture_dispatch_source, validate_dispatch_source, review_dispatch_profile
from lib import review_planning
import v1_review_dispatch_oracle as oracle
import v1_review_planning_oracle as planning_oracle

AT = '2026-11-17T17:00:00Z'
FIXTURE = ROOT / 'tests/fixtures/v2-review-planning'


class DispatcherWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.node = self.base / 'node'; self.node.mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-dispatch-node'}
        self.app = app.DispatchWorkspace(self.node, 'recording', self.settings); self.app.initialize()
        self.target = self.base / 'target'; self.target.mkdir()
        for name, row in planning_oracle.target_files(FIXTURE).items():
            if not name.startswith(('.agents/roles/', '.agents/skills/', '.agents/routing/')): continue
            path = self.target / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(row['bytes']); path.chmod(row['mode'])
        facts, raw = capture_dispatch_source(self.target, None, ['docs/example.md'], app.PROFILE)
        self.roles, routing = validate_dispatch_source(facts, raw, app.PROFILE)
        self.dispatch = review_planning.dispatch(facts['changed_paths'], self.roles, routing, review_dispatch_profile(app.PROFILE))

    def current(self): return self.app.workspace.current()[1]['generation']

    def compare(self, action, arguments, **options):
        request = logic.request(action, AT, **options)
        old_code, old_stdout, old_stderr = oracle.main(FIXTURE, self.target, self.roles, AT, arguments, self.dispatch)
        self.assertEqual(old_code, 0); self.assertEqual(old_stderr, b'')
        source = {'repository': self.target, 'paths': ['docs/example.md']} if action == 'dispatch' else {}
        receipt = self.app.execute(request, **source); root = Path(receipt['data_directory'])
        self.assertEqual(Path(receipt['stdout_file']).read_bytes(), old_stdout)
        for name in (app.DEFAULT_STATE, logic.DEFAULT_LOG):
            old = self.target / name; new = root / name
            self.assertEqual(new.exists(), old.exists())
            if old.exists(): self.assertEqual(new.read_bytes(), old.read_bytes())
        self.assertTrue(receipt['retained_complete_outputs_reverified']); self.assertFalse(receipt['provider_invoked'])
        self.assertEqual(self.app.inspect(receipt['generation'])['effects'], receipt['effects'])
        return receipt

    def test_original_complete_json_text_state_log_and_summary_through_private_store(self):
        self.compare('record-window', ['--record-next', '2', '--json'], count=2, json_output=True)
        self.compare('dispatch', ['docs/example.md', '--json'], json_output=True)
        self.compare('dispatch', ['docs/example.md', '--provider-review', 'codex'], provider_review='codex')
        self.compare('dispatch', ['docs/example.md'])
        self.compare('recording-status', ['--recording-status', '--json'], json_output=True)
        self.compare('record-continuous', ['--record-continuous'])
        self.compare('dispatch', ['docs/example.md', '--provider-review', 'mistral'], provider_review='mistral')
        self.compare('usage-summary', ['--usage-summary', '--json'], json_output=True)
        self.compare('usage-summary', ['--usage-summary'])

    def test_each_generation_replays_after_target_deleted_without_source_observation(self):
        first = self.app.execute(logic.request('record-window', AT, count=1))
        second = self.app.execute(logic.request('dispatch', AT), repository=self.target, paths=['docs/example.md'])
        shutil.rmtree(self.target)
        with patch.object(app, 'observe_dispatch_source', side_effect=AssertionError('no live observation on replay')), \
                patch.object(app, 'capture_dispatch_source', side_effect=AssertionError('no live capture on replay')):
            for receipt in (first, second):
                result = self.app.inspect(receipt['generation'])
                self.assertTrue(result['retained_complete_outputs_reverified']); self.assertFalse(result['target_current_state_rechecked'])
        self.assertTrue(second['target_current_state_rechecked'])

    def test_status_and_summary_need_no_repository_and_original_empty_wires(self):
        with patch.object(app, 'capture_dispatch_source', side_effect=AssertionError('no consumer read')):
            self.compare('recording-status', ['--recording-status'])
            self.compare('usage-summary', ['--usage-summary'])
        with self.assertRaisesRegex(ValueError, 'unexpected_dispatch_repository'):
            self.app.execute(logic.request('recording-status', AT), repository=self.target)
        with self.assertRaisesRegex(ValueError, 'dispatch_repository_required'):
            self.app.execute(logic.request('dispatch', AT))

    def test_repeated_calls_remain_distinct_original_runs_and_all_history_is_retained(self):
        request = logic.request('dispatch', AT, log_usage=True)
        first = self.app.execute(request, repository=self.target, paths=['docs/example.md'])
        second = self.app.execute(request, repository=self.target, paths=['docs/example.md'])
        self.assertNotEqual(first['generation'], second['generation'])
        self.assertEqual(len(logic.events((Path(first['data_directory']) / logic.DEFAULT_LOG).read_bytes())), 1)
        self.assertEqual(len(logic.events((Path(second['data_directory']) / logic.DEFAULT_LOG).read_bytes())), 2)
        self.app.inspect(first['generation'])

    def test_failed_pointer_write_keeps_old_state_and_retry_publishes_once(self):
        self.app.execute(logic.request('record-window', AT, count=1)); previous = self.current()
        request = logic.request('dispatch', AT)
        with patch.object(candidate_workspace, 'atomic_json', side_effect=OSError('synthetic interrupted pointer publication')):
            with self.assertRaises(OSError): self.app.execute(request, repository=self.target, paths=['docs/example.md'])
        self.assertEqual(self.current(), previous)
        result = self.app.execute(request, repository=self.target, paths=['docs/example.md'])
        self.assertEqual(len(logic.events((Path(result['data_directory']) / logic.DEFAULT_LOG).read_bytes())), 1)
        self.assertEqual(logic.state((Path(result['data_directory']) / app.DEFAULT_STATE).read_bytes())['remaining'], 0)

    def test_source_recheck_failure_and_space_guard_preserve_current_generation(self):
        previous = self.current()
        with patch.object(app, 'observe_dispatch_source', return_value=({}, {})):
            with self.assertRaisesRegex(ValueError, 'dispatch_target_changed_before_commit'):
                self.app.execute(logic.request('dispatch', AT, log_usage=True), repository=self.target, paths=['docs/example.md'])
        self.assertEqual(self.current(), previous)
        with patch.object(app, 'reserve', side_effect=ValueError('synthetic_reserve')), \
                patch.object(app, 'capture_dispatch_source', side_effect=AssertionError('reserve before capture')):
            with self.assertRaisesRegex(ValueError, 'synthetic_reserve'):
                self.app.execute(logic.request('dispatch', AT), repository=self.target, paths=['docs/example.md'])
        self.assertEqual(self.current(), previous)

    def test_lock_and_private_namespace_reject_unsafe_or_aliased_paths(self):
        with self.app.workspace.lock():
            with self.assertRaisesRegex(ValueError, 'candidate_workspace_busy'):
                self.app.execute(logic.request('recording-status', AT))
        for name in ('.', '../outside', '/outside', '.axiom/context.json', 'a/../b', 'a\\b', 'a:b'):
            with self.subTest(name=name), self.assertRaises(ValueError): app.business_name(name)
        with self.assertRaisesRegex(ValueError, 'dispatch_state_log_alias'):
            self.app.execute(logic.request('recording-status', AT, usage_log=app.DEFAULT_STATE))

    def test_closed_context_and_resealed_business_or_metadata_tampering_rejected(self):
        result = self.app.execute(logic.request('recording-status', AT)); original = Path(result['data_directory'])
        for name, raw, error in [('unexpected.json', b'{}', 'dispatch_business_outputs_changed'),
                ('.axiom/extra.json', b'{}', 'dispatch_metadata_members_changed')]:
            with tempfile.TemporaryDirectory(dir=self.app.workspace.root) as temporary:
                staged = Path(temporary) / 'data'; shutil.copytree(original, staged); app.write(staged, name, raw)
                identifier = canonical_digest(inventory(staged)); saved = self.app.workspace.generations / identifier
                staged.rename(saved)
                with self.assertRaisesRegex(ValueError, error): self.app.inspect(identifier)
        with tempfile.TemporaryDirectory(dir=self.app.workspace.root) as temporary:
            staged = Path(temporary) / 'data'; shutil.copytree(original, staged)
            value = app.strict_json((staged / app.CONTEXT).read_bytes()); value['provider_invoked'] = True
            app.write(staged, app.CONTEXT, logic.wire(value)); identifier = canonical_digest(inventory(staged))
            staged.rename(self.app.workspace.generations / identifier)
            with self.assertRaisesRegex(ValueError, 'invalid_dispatch_context'): self.app.inspect(identifier)

    def test_unchanged_hash_does_not_hide_extra_empty_directories_and_output_mutations(self):
        result = self.app.execute(logic.request('recording-status', AT)); root = Path(result['data_directory'])
        extra = root / 'extra'; extra.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'dispatch_directory_members_changed'): self.app.inspect(result['generation'])
        extra.rmdir(); stdout = root / app.STDOUT; original = stdout.read_bytes(); stdout.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'dispatch_generation_changed'): self.app.inspect(result['generation'])
        stdout.write_bytes(original)
        stdout.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private_candidate_file_required'): self.app.inspect(result['generation'])

    def test_initialization_foreign_node_and_program_drift_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'fresh_dispatch_workspace_required'): self.app.initialize()
        other = app.DispatchWorkspace(self.node, 'recording', {'node_id': 'different-node'})
        with self.assertRaisesRegex(ValueError, 'dispatch_node_runtime_or_source_changed'): other.inspect(self.current())
        with patch.object(app, 'source_digest', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'dispatch_product_changed'): self.app.inspect(self.current())

    def test_compact_input_cannot_publish_a_state_larger_than_the_reader_accepts(self):
        raw = json.dumps({str(n): 0 for n in range(5500)}, separators=(',', ':')).encode()
        self.assertLess(len(raw), logic.MAX_STATE)
        request = logic.request('record-continuous', AT)
        self.assertGreater(len(logic.transition(request, raw, None)['state_bytes']), logic.MAX_STATE)
        with self.assertRaisesRegex(ValueError, 'dispatch_state_output_budget'): app.derive(request, raw, None)


if __name__ == '__main__': unittest.main()
