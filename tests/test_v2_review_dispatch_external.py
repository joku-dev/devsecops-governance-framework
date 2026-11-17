"""Complete original external-file effects and durable, explicit recovery."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests/acceptance')]
from lib import review_dispatch as logic, review_dispatch_external as app, review_planning
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import canonical_digest
from lib.provider_ports import (capture_dispatch_source, validate_dispatch_source, review_dispatch_profile, dispatch_file_label)
from lib.providers import review_dispatch_files as native
import v1_review_dispatch_oracle as oracle
import v1_review_planning_oracle as planning_oracle

FIXTURE = ROOT / 'tests/fixtures/v2-review-planning'
AT = '2026-11-17T17:00:00Z'; STATE = 'generated/agent-usage/recording-state.json'


class ExternalDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.node = self.base / 'node'; self.node.mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-native-dispatch-node'}; self.app = app.ExternalDispatchContext(self.node, self.settings)
        self.repo = self.base / 'repository'; self.repo.mkdir()
        for name, row in planning_oracle.target_files(FIXTURE).items():
            if not name.startswith(('.agents/roles/', '.agents/skills/', '.agents/routing/')): continue
            path = self.repo / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(row['bytes']); path.chmod(row['mode'])
        facts, raw = capture_dispatch_source(self.repo, None, ['docs/example.md'], app.PROFILE)
        self.roles, routing = validate_dispatch_source(facts, raw, app.PROFILE)
        self.dispatch = review_planning.dispatch(facts['changed_paths'], self.roles, routing, review_dispatch_profile(app.PROFILE))

    def prepare(self, action='dispatch', *, usage_state=STATE, **options):
        request = logic.request(action, AT, **options)
        return self.app.prepare(self.repo, usage_state, request,
                                paths=['docs/example.md'] if action == 'dispatch' else [])

    def compare_original(self, action, arguments, *, usage_state=STATE, **options):
        request = logic.request(action, AT, **options)
        snapshot, _, _ = native.capture(self.repo, usage_state, request, app.FILE_PROFILE)
        paths = [Path(snapshot[key]['path']) for key in ('state', 'log')]
        before = {p: (p.read_bytes(), p.stat().st_mode & 0o777) if p.exists() else None for p in paths}
        code, expected_stdout, errors = oracle.main(FIXTURE, self.repo, self.roles, AT, arguments, self.dispatch)
        self.assertEqual(code, 0); self.assertEqual(errors, b'')
        expected = {p: p.read_bytes() if p.exists() else None for p in paths}
        for path, previous in before.items():
            if previous is None: path.unlink(missing_ok=True)
            else: path.write_bytes(previous[0]); path.chmod(previous[1])
        plan = self.app.prepare(self.repo, usage_state, request, paths=['docs/example.md'] if action == 'dispatch' else [])
        self.assertEqual(self.app.stdout(plan['assessment_id']), expected_stdout)
        result = self.app.apply(plan['assessment_id']); self.assertEqual(result['execution_state'], 'applied')
        for path, raw in expected.items(): self.assertEqual(path.read_bytes() if path.exists() else None, raw)
        self.assertFalse(result['provider_invoked']); self.assertFalse(result['official_acceptance'])
        return result

    def test_complete_original_default_file_stdout_state_log_and_summary_sequence(self):
        self.compare_original('record-window', ['--record-next', '2', '--json'], count=2, json_output=True)
        self.compare_original('dispatch', ['docs/example.md', '--json'], json_output=True)
        self.compare_original('dispatch', ['docs/example.md', '--provider-review', 'codex'], provider_review='codex')
        self.compare_original('dispatch', ['docs/example.md'])
        self.compare_original('recording-status', ['--recording-status', '--json'], json_output=True)
        self.compare_original('record-continuous', ['--record-continuous'])
        self.compare_original('dispatch', ['docs/example.md', '--provider-review', 'mistral'], provider_review='mistral')
        self.compare_original('usage-summary', ['--usage-summary', '--json'], json_output=True)
        self.compare_original('usage-summary', ['--usage-summary'])

    def test_original_existing_custom_external_files_and_lexical_labels(self):
        outside = self.base / 'custom-log.jsonl'; outside.write_bytes(b'{}\n')
        state = self.base / 'custom-state.json'; state.write_bytes(b'{invalid previous state')
        label = dispatch_file_label(self.repo, str(outside))
        self.compare_original('record-window', ['--record-next', '10001', '--usage-state', str(state), '--usage-log', str(outside)],
                              usage_state=str(state), count=10001, usage_log=label)
        self.compare_original('dispatch', ['docs/example.md', '--usage-state', str(state), '--usage-log', str(outside), '--provider-review', 'codex'],
                              usage_state=str(state), usage_log=label, provider_review='codex')
        self.assertEqual(len(logic.events(outside.read_bytes())), 2)
        self.compare_original('record-window', ['--record-next', '2', '--usage-log', 'logs/../lexical.jsonl'], count=2, usage_log='logs/../lexical.jsonl')
        self.assertEqual(logic.state((self.repo / STATE).read_bytes())['usage_log'], 'logs/../lexical.jsonl')

    def test_prepare_only_changes_private_material_and_inspection_never_reads_live_targets(self):
        before = {p.relative_to(self.repo).as_posix() for p in self.repo.rglob('*')}
        plan = self.prepare('record-window', count=2)
        self.assertEqual({p.relative_to(self.repo).as_posix() for p in self.repo.rglob('*')}, before)
        self.assertEqual(plan['execution_state'], 'prepared'); self.assertIsNone(self.app.execution(plan['assessment_id']))
        self.app.apply(plan['assessment_id']); shutil.rmtree(self.repo)
        with patch.object(app, 'capture_dispatch_files', side_effect=AssertionError('no live files on inspect')), \
                patch.object(app, 'observe_dispatch_source', side_effect=AssertionError('no live source on inspect')):
            receipt = self.app.inspect(plan['assessment_id'])
        self.assertTrue(receipt['retained_complete_outputs_reverified']); self.assertFalse(receipt['native_outputs_rechecked'])

    def partial(self):
        self.app.apply(self.prepare('record-window', count=2)['assessment_id'])
        plan = self.prepare('dispatch'); identifier = plan['assessment_id']; replace = native.replace
        def interrupted(path, raw, mode):
            if path.name == 'recording-state.json': raise OSError('synthetic interruption after first file')
            return replace(path, raw, mode)
        with patch.object(native, 'replace', side_effect=interrupted):
            with self.assertRaises(OSError): self.app.apply(identifier)
        self.assertEqual(self.app.execution(identifier)['state'], 'applying')
        self.assertEqual(self.app.pending(), [identifier]); return identifier

    def test_durable_partial_recovery_after_process_context_recreation_never_duplicates(self):
        identifier = self.partial(); restarted = app.ExternalDispatchContext(self.node, self.settings)
        result = restarted.apply(identifier)
        self.assertEqual(result['execution_state'], 'applied'); self.assertTrue(result['resumed_partial_operation'])
        self.assertEqual(restarted.pending(), []); self.assertEqual(len(logic.events((self.repo / logic.DEFAULT_LOG).read_bytes())), 1)
        self.assertEqual(logic.state((self.repo / STATE).read_bytes())['remaining'], 1)
        with patch.object(native, 'replace', side_effect=AssertionError('applied retry must only verify')):
            result = restarted.apply(identifier)
        self.assertTrue(result['idempotent_apply'])

    def test_complete_intent_sync_barrier_precedes_journal_and_first_native_effect(self):
        self.app.apply(self.prepare('record-window', count=2)['assessment_id'])
        plan = self.prepare('dispatch'); identifier = plan['assessment_id']
        root = self.app.plans / identifier
        paths = [root / 'record.json', *list((root / 'blobs').iterdir()), root / 'blobs', root,
                 self.app.plans, self.app.executions, self.app.root, self.app.root.parent, self.app.instance]
        identities = {(p.stat().st_dev, p.stat().st_ino) for p in paths}
        blob = next((root / 'blobs').iterdir()); blocked = (blob.stat().st_dev, blob.stat().st_ino)
        fsync = os.fsync
        def fail_blob(fd):
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) == blocked: raise OSError('synthetic intent sync failure')
            return fsync(fd)
        with patch.object(app.os, 'fsync', side_effect=fail_blob), \
                patch.object(native, 'replace', side_effect=AssertionError('no native effect before durable intent')):
            with self.assertRaises(OSError): self.app.apply(identifier)
        self.assertEqual(self.app.pending(), []); self.assertIsNone(self.app.execution(identifier))
        self.assertFalse((self.repo / logic.DEFAULT_LOG).exists())
        synced = set(); replace = native.replace
        def observed_sync(fd):
            info = os.fstat(fd); result = fsync(fd); synced.add((info.st_dev, info.st_ino)); return result
        def first_effect(path, raw, mode):
            self.assertTrue(identities <= synced)
            for metadata in (self.app.root / 'pending.json', self.app.executions / (identifier + '.json')):
                info = metadata.stat(); self.assertIn((info.st_dev, info.st_ino), synced)
            return replace(path, raw, mode)
        with patch.object(app.os, 'fsync', side_effect=observed_sync), patch.object(native, 'replace', side_effect=first_effect):
            self.assertEqual(self.app.apply(identifier)['execution_state'], 'applied')

    def test_unresolved_partial_operation_fences_a_different_operation(self):
        identifier = self.partial(); other = self.prepare('usage-summary')
        with self.assertRaisesRegex(ValueError, 'external_dispatch_pending_operation_requires_recovery'):
            self.app.apply(other['assessment_id'])
        self.assertIsNone(self.app.execution(other['assessment_id'])); self.assertEqual(self.app.pending(), [identifier])

    def test_lost_completion_receipt_is_recovered_from_already_desired_outputs(self):
        self.app.apply(self.prepare('record-window', count=1)['assessment_id']); plan = self.prepare('dispatch')
        real = app.atomic_json
        def fail_completion(path, value):
            if value.get('state') == 'applied': raise OSError('synthetic lost completion receipt')
            return real(path, value)
        with patch.object(app, 'atomic_json', side_effect=fail_completion):
            with self.assertRaises(OSError): self.app.apply(plan['assessment_id'])
        with patch.object(native, 'replace', side_effect=AssertionError('fully written outputs must not repeat')):
            receipt = self.app.apply(plan['assessment_id'])
        self.assertEqual(receipt['execution_state'], 'applied')
        self.assertEqual(len(logic.events((self.repo / logic.DEFAULT_LOG).read_bytes())), 1)

    def test_stale_native_or_source_inputs_conflict_before_any_native_effect(self):
        plan = self.prepare('record-window', count=2); state = self.repo / STATE
        state.parent.mkdir(parents=True); state.write_bytes(b'operator changed this')
        with self.assertRaisesRegex(ValueError, 'external_dispatch_native_inputs_changed'): self.app.apply(plan['assessment_id'])
        self.assertEqual(state.read_bytes(), b'operator changed this'); self.assertIsNone(self.app.execution(plan['assessment_id']))
        state.unlink(); plan = self.prepare('dispatch', log_usage=True)
        with patch.object(app, 'observe_dispatch_source', return_value=({}, {})):
            with self.assertRaisesRegex(ValueError, 'external_dispatch_source_changed_before_apply'): self.app.apply(plan['assessment_id'])
        self.assertFalse((self.repo / logic.DEFAULT_LOG).exists()); self.assertIsNone(self.app.execution(plan['assessment_id']))

    def test_applied_operation_does_not_undo_a_later_operator_change(self):
        plan = self.prepare('record-window', count=2); self.app.apply(plan['assessment_id']); state = self.repo / STATE
        state.write_bytes(b'operator changed this')
        with patch.object(native, 'replace', side_effect=AssertionError('must not restore rolled-back state')):
            with self.assertRaisesRegex(ValueError, 'dispatch_native_output_verification_failed'): self.app.apply(plan['assessment_id'])
        self.assertEqual(state.read_bytes(), b'operator changed this')

    def test_closed_plan_members_output_resealing_and_foreign_node_are_rejected(self):
        plan = self.prepare('dispatch', log_usage=True); identifier = plan['assessment_id']
        value, files = self.app.material(identifier); value['effects']['event_appended'] = False
        changed = canonical_digest(value); shutil.copytree(self.app.plans / identifier, self.app.plans / changed)
        atomic_json(self.app.plans / changed / 'record.json', value)
        with self.assertRaisesRegex(ValueError, 'external_dispatch_effects_changed'): self.app.inspect(changed)
        other = app.ExternalDispatchContext(self.node, {'node_id': 'foreign-node'})
        with self.assertRaisesRegex(ValueError, 'external_dispatch_node_runtime_or_source_changed'): other.inspect(identifier)
        blob = next((self.app.plans / identifier / 'blobs').iterdir()); blob.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'external_dispatch_material_changed'): self.app.inspect(identifier)

    def test_budgets_reserved_paths_and_global_busy_do_not_create_a_recovery_state(self):
        with patch.object(app, 'reserve', side_effect=ValueError('synthetic_reserve')), \
                patch.object(app, 'capture_dispatch_files', side_effect=AssertionError('reserve first')):
            with self.assertRaisesRegex(ValueError, 'synthetic_reserve'): self.prepare('record-window', count=1)
        with self.assertRaisesRegex(ValueError, 'dispatch_protected_file_target'):
            self.prepare('record-window', usage_state=str(self.node / 'instance.json'), count=1)
        plan = self.prepare('record-window', count=1); identifier = plan['assessment_id']
        with native.locks([self.repo / STATE]):
            with self.assertRaisesRegex(ValueError, 'dispatch_native_files_busy'): self.app.apply(identifier)
        self.assertIsNone(self.app.execution(identifier)); self.assertFalse((self.repo / STATE).exists())

    def test_pending_marker_survives_failure_before_execution_journal_without_file_effects(self):
        plan = self.prepare('record-window', count=1); identifier = plan['assessment_id']; real = app.atomic_json
        def fail_journal(path, value):
            if value.get('kind') == 'external-review-dispatch-execution': raise OSError('synthetic journal admission failure')
            return real(path, value)
        with patch.object(app, 'atomic_json', side_effect=fail_journal):
            with self.assertRaises(OSError): self.app.apply(identifier)
        self.assertEqual(self.app.pending(), [identifier]); self.assertIsNone(self.app.execution(identifier))
        self.assertFalse((self.repo / STATE).exists())
        restarted = app.ExternalDispatchContext(self.node, self.settings); restarted.apply(identifier)
        self.assertEqual(restarted.pending(), []); self.assertTrue((self.repo / STATE).exists())

    def test_pending_check_ignores_unrelated_completed_history(self):
        identifier = self.partial()
        unrelated = self.app.executions / ('e' * 64 + '.json')
        unrelated.write_bytes(b'unrelated historical material is not a live recovery marker')
        unrelated.chmod(0o600)
        self.assertEqual(self.app.pending(), [identifier])
        self.app.apply(identifier); self.assertEqual(self.app.pending(), [])

    def test_explicit_abandonment_releases_intent_without_reverting_or_certifying_partial_files(self):
        identifier = self.partial(); before_state = (self.repo / STATE).read_bytes()
        before_log = (self.repo / logic.DEFAULT_LOG).read_bytes()
        receipt = self.app.abandon(identifier, 'Operator will reconcile the separate files')
        self.assertEqual(receipt['execution_state'], 'abandoned'); self.assertTrue(receipt['abandoned_without_native_revert'])
        self.assertFalse(receipt['abandonment']['native_outputs_certified']); self.assertFalse(receipt['risk_acceptance'])
        self.assertEqual((self.repo / STATE).read_bytes(), before_state)
        self.assertEqual((self.repo / logic.DEFAULT_LOG).read_bytes(), before_log)
        self.assertEqual(self.app.pending(), [])
        with self.assertRaisesRegex(ValueError, 'external_dispatch_abandoned_operation'): self.app.apply(identifier)
        other = self.prepare('usage-summary'); self.app.apply(other['assessment_id'])

    def test_success_cannot_be_relabelled_as_abandoned_and_prepared_cancellation_keeps_other_fence(self):
        initial = self.prepare('record-window', count=1); self.app.apply(initial['assessment_id'])
        with self.assertRaisesRegex(ValueError, 'external_dispatch_completed_cannot_abandon'):
            self.app.abandon(initial['assessment_id'], 'must not rewrite success')
        identifier = self.partial(); unused = self.prepare('usage-summary')
        self.app.abandon(unused['assessment_id'], 'Unused prepared intent')
        self.assertEqual(self.app.pending(), [identifier])


if __name__ == '__main__': unittest.main()
