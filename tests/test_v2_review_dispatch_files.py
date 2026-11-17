"""Explicit original file paths and minimal observations, without any native write."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from lib import review_dispatch as logic
from lib import review_dispatch_application as application
from lib.providers import review_dispatch_files as native

AT = '2026-11-17T17:00:00Z'; PROFILE = 'legacy-local-dispatch-files-v1'
STATE = 'generated/agent-usage/recording-state.json'


class DispatchNativeFileInputs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.repo = self.root / 'repository'; self.repo.mkdir()

    def write(self, label, raw):
        path = self.repo / label; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return path

    def capture(self, action, **options):
        return native.capture(self.repo, STATE, logic.request(action, AT, **options), PROFILE)

    def test_missing_defaults_are_observed_without_creating_directories_or_files(self):
        before = list(self.repo.iterdir()); snapshot, state, log = self.capture('record-window', count=2)
        self.assertEqual(list(self.repo.iterdir()), before); self.assertIsNone(state); self.assertIsNone(log)
        self.assertTrue(snapshot['state']['observed']); self.assertFalse(snapshot['state']['present'])
        self.assertFalse(snapshot['log']['observed']); self.assertIsNone(snapshot['log']['present'])

    def test_lexical_labels_preserve_original_relative_and_explicit_external_paths(self):
        self.assertEqual(native.legacy_label(self.repo, 'logs/../usage.jsonl'), 'logs/../usage.jsonl')
        self.assertEqual(native.legacy_label(self.repo, str(self.repo / 'logs/usage.jsonl')), 'logs/usage.jsonl')
        outside = self.root / 'external.jsonl'
        self.assertEqual(native.legacy_label(self.repo, str(outside)), str(outside))
        snapshot, _, _ = self.capture('dispatch', log_usage=True, usage_log=str(outside))
        self.assertEqual(snapshot['log']['path'], str(outside)); self.assertTrue(snapshot['log']['observed'])

    def test_status_ignores_bad_unused_log_and_summary_ignores_bad_unused_state(self):
        self.write(STATE, b'{}'); self.write(logic.DEFAULT_LOG, b'not-json')
        original = native.read; reads = []
        def observed(path, limit): reads.append(path); return original(path, limit)
        with patch.object(native, 'read', side_effect=observed): snapshot, _, _ = self.capture('recording-status')
        self.assertEqual(reads, [self.repo / STATE]); self.assertFalse(snapshot['log']['observed'])
        self.write(STATE, b'not-json'); self.write(logic.DEFAULT_LOG, b'{}\n'); reads.clear()
        with patch.object(native, 'read', side_effect=observed): snapshot, _, log = self.capture('usage-summary')
        self.assertEqual(reads, [self.repo / logic.DEFAULT_LOG]); self.assertFalse(snapshot['state']['observed'])
        self.assertEqual(log, b'{}\n')

    def test_active_recording_selects_original_log_and_external_pointer_needs_explicit_scope(self):
        state = logic.activate({}, 'window', AT, count=2, usage_log='logs/recorded.jsonl')
        self.write(STATE, logic.wire(state)); actual = self.write('logs/recorded.jsonl', b'{}\n')
        snapshot, _, raw = self.capture('dispatch', log_usage=True, usage_log='ignored.jsonl')
        self.assertEqual(snapshot['log']['path'], str(actual)); self.assertEqual(raw, b'{}\n')
        outside = self.root / 'external.jsonl'; outside.write_bytes(b'{}\n'); state['usage_log'] = str(outside)
        self.write(STATE, logic.wire(state))
        with self.assertRaisesRegex(ValueError, 'dispatch_recording_log_outside_declared_scope'): self.capture('dispatch')
        snapshot, _, raw = self.capture('dispatch', usage_log=str(outside))
        self.assertEqual(snapshot['log']['path'], str(outside)); self.assertEqual(raw, b'{}\n')

    def test_symlinks_hardlink_aliases_and_protected_write_targets_are_rejected(self):
        state = logic.activate({}, 'window', AT, count=2); path = self.write(STATE, logic.wire(state))
        log = self.repo / logic.DEFAULT_LOG; log.hardlink_to(path)
        with self.assertRaisesRegex(ValueError, 'dispatch_native_state_log_alias'): self.capture('dispatch')
        log.unlink(); outside = self.root / 'outside'; outside.write_bytes(b'private'); log.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'dispatch_native_file_read_failed'): self.capture('dispatch')
        log.unlink()
        with self.assertRaisesRegex(ValueError, 'dispatch_protected_file_target'):
            native.capture(self.repo, STATE, logic.request('record-window', AT, count=1), PROFILE, forbidden_roots=[self.repo])
        with self.assertRaisesRegex(ValueError, 'dispatch_git_metadata_file_forbidden'):
            native.capture(self.repo, '.git/config', logic.request('recording-status', AT), PROFILE)

    def test_retained_validation_never_reads_live_files_and_rejects_forged_observations(self):
        self.write(STATE, b'{}'); self.write(logic.DEFAULT_LOG, b'{}\n')
        request = logic.request('usage-summary', AT); snapshot, state, log = native.capture(self.repo, STATE, request, PROFILE)
        shutil.rmtree(self.repo)
        with patch.object(native, 'read', side_effect=AssertionError('retained validation must be pure')):
            native.validate(snapshot, request, state, log)
        for mutate in [lambda s:s.update(profile='other'), lambda s:s.update(extra='private'),
                lambda s:s['log'].update(observed=False), lambda s:s['log'].update(bytes=True),
                lambda s:s['log'].update(sha256='0' * 64), lambda s:s['state'].update(present=True)]:
            bad = deepcopy(snapshot); mutate(bad)
            with self.assertRaises(ValueError): native.validate(bad, request, state, log)

    def test_file_limits_and_unknown_profile_fail_without_native_mutation(self):
        self.write(STATE, b'{}')
        with patch.object(logic, 'MAX_STATE', 1), self.assertRaisesRegex(ValueError, 'dispatch_native_file_budget_or_type'):
            self.capture('recording-status')
        with self.assertRaisesRegex(ValueError, 'unsupported_dispatch_file_profile'):
            native.capture(self.repo, STATE, logic.request('recording-status', AT), 'other')
        self.assertEqual((self.repo / STATE).read_bytes(), b'{}')

    def rows(self):
        self.write(STATE, logic.wire(logic.activate({}, 'window', AT, count=2)))
        request = logic.request('dispatch', AT)
        snapshot, before_state, before_log = native.capture(self.repo, STATE, request, PROFILE)
        selection = {'changed_files': [], 'selected_agents': [], 'release_impact': 'none',
                     'required_validations': [], 'warnings': [], 'selection_reasons': {}}
        derived = application.derive(request, before_state, before_log, dispatch=selection, roles={})
        return [{'kind': kind, 'before': snapshot[kind], 'before_raw': before,
                 'after_raw': derived[kind + '_bytes']} for kind, before in [('log', before_log), ('state', before_state)]]

    def test_actual_native_outputs_are_written_log_first_after_recovery_record(self):
        rows = self.rows(); calls = []
        def before_write():
            calls.append('recovery_record'); self.assertFalse((self.repo / logic.DEFAULT_LOG).exists())
            self.assertEqual((self.repo / STATE).read_bytes(), rows[1]['before_raw'])
        replace = native.replace
        def effect(path, raw, mode): calls.append(path.name); return replace(path, raw, mode)
        with patch.object(native, 'replace', side_effect=effect):
            result = native.write_rows(rows, PROFILE, before_write=before_write)
        self.assertEqual(calls, ['recovery_record', 'agent-usage.jsonl', 'recording-state.json'])
        self.assertEqual(result['written'], ['log', 'state'])
        for row in rows: self.assertEqual(Path(row['before']['path']).read_bytes(), row['after_raw'])
        self.assertEqual((self.repo / logic.DEFAULT_LOG).stat().st_mode & 0o777, 0o600)

    def test_partial_native_effect_is_detectable_and_resume_never_appends_twice(self):
        rows = self.rows(); replace = native.replace; journal = []
        def fail_second(path, raw, mode):
            if path.name == 'recording-state.json': raise OSError('synthetic interrupted second file')
            return replace(path, raw, mode)
        with patch.object(native, 'replace', side_effect=fail_second):
            with self.assertRaises(OSError): native.write_rows(rows, PROFILE, before_write=lambda: journal.append('applying'))
        self.assertEqual(journal, ['applying'])
        self.assertEqual((self.repo / STATE).read_bytes(), rows[1]['before_raw'])
        self.assertEqual((self.repo / logic.DEFAULT_LOG).read_bytes(), rows[0]['after_raw'])
        result = native.write_rows(rows, PROFILE, allow_after=True)
        self.assertEqual(result, {'written': ['state'], 'already_desired': ['log']})
        self.assertEqual(len(logic.events((self.repo / logic.DEFAULT_LOG).read_bytes())), 1)
        result = native.write_rows(rows, PROFILE, allow_after=True)
        self.assertEqual(result, {'written': [], 'already_desired': ['log', 'state']})

    def test_native_conflicts_are_rejected_before_any_effect_or_journal_callback(self):
        rows = self.rows(); self.write(STATE, b'changed by another writer'); journal = []
        with self.assertRaisesRegex(ValueError, 'dispatch_native_file_conflict'):
            native.write_rows(rows, PROFILE, before_write=lambda: journal.append('started'))
        self.assertEqual(journal, []); self.assertFalse((self.repo / logic.DEFAULT_LOG).exists())

    def test_global_file_locks_cover_two_instances_without_creating_consumer_lock_files(self):
        rows = self.rows(); before = {p.relative_to(self.repo).as_posix() for p in self.repo.rglob('*')}
        with native.locks([row['before']['path'] for row in rows]):
            with self.assertRaisesRegex(ValueError, 'dispatch_native_files_busy'): native.write_rows(rows, PROFILE)
        self.assertEqual({p.relative_to(self.repo).as_posix() for p in self.repo.rglob('*')}, before)

    def test_write_set_scope_types_and_symlinks_cannot_bypass_input_validation(self):
        rows = self.rows()
        with self.assertRaisesRegex(ValueError, 'dispatch_protected_file_target'):
            native.write_rows(rows, PROFILE, forbidden_roots=[self.repo])
        bad = deepcopy(rows); bad[0]['before']['bytes'] = True
        with self.assertRaises(ValueError): native.write_rows(bad, PROFILE)
        with self.assertRaisesRegex(ValueError, 'invalid_dispatch_native_write'):
            native.write_rows([rows[0], rows[0]], PROFILE)
        outside = self.root / 'outside'; outside.write_bytes(b'private'); log = self.repo / logic.DEFAULT_LOG
        log.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'dispatch_native_file_read_failed'): native.write_rows(rows, PROFILE)
        self.assertEqual(outside.read_bytes(), b'private')

    def test_completed_operation_checks_outputs_without_reapplying_a_later_rollback(self):
        rows = self.rows(); native.write_rows(rows, PROFILE)
        with patch.object(native, 'replace', side_effect=AssertionError('verification must not write')):
            self.assertEqual(native.verify_outputs(rows, PROFILE), {'verified': ['log', 'state']})
            self.write(STATE, rows[1]['before_raw'])
            with self.assertRaisesRegex(ValueError, 'dispatch_native_output_verification_failed'):
                native.verify_outputs(rows, PROFILE)
        self.assertEqual((self.repo / STATE).read_bytes(), rows[1]['before_raw'])


if __name__ == '__main__': unittest.main()
