"""Actual V2 entrypoint, original stdout choices, mode priority and private effects."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests/acceptance')]
import axiom_v2
from lib import review_dispatch_application as app
from lib.provider_ports import capture_dispatch_source, validate_dispatch_source, review_dispatch_profile
from lib import review_planning
import v1_review_dispatch_oracle as oracle
import v1_review_planning_oracle as planning_oracle
from lib import review_dispatch as logic
from lib.providers import review_dispatch_files as native

AT = '2026-11-17T17:00:00Z'; FIXTURE = ROOT / 'tests/fixtures/v2-review-planning'


class DispatcherCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base = Path(self.temp.name).resolve()
        self.node = self.base / 'node'
        opa = shutil.which('opa')
        self.assertIsNotNone(opa, 'The repository-pinned OPA must be available on PATH')
        self.call('init', '--development', '--opa', opa, '--port', '18979')
        self.call('review-dispatch', 'init', '--workspace', 'cli', '--profile', app.PROFILE)
        self.target = self.base / 'target'; self.target.mkdir()
        for name, row in planning_oracle.target_files(FIXTURE).items():
            if not name.startswith(('.agents/roles/', '.agents/skills/', '.agents/routing/')): continue
            path = self.target / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(row['bytes']); path.chmod(row['mode'])
        facts, raw = capture_dispatch_source(self.target, None, ['docs/example.md'], app.PROFILE)
        self.roles, routing = validate_dispatch_source(facts, raw, app.PROFILE)
        self.dispatch = review_planning.dispatch(facts['changed_paths'], self.roles, routing, review_dispatch_profile(app.PROFILE))

    def call(self, *arguments, expected=0):
        output = io.StringIO(); errors = io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = axiom_v2.main(['--instance', str(self.node), *map(str, arguments)])
        self.assertEqual(code, expected, errors.getvalue())
        if expected == 0: self.assertEqual(errors.getvalue(), '')
        return output.getvalue(), errors.getvalue()

    def run_cli(self, *args, expected=0):
        return self.call('review-dispatch', 'run', '--workspace', 'cli', '--at', AT, *args, expected=expected)

    def test_original_full_stdout_and_json_for_window_dispatch_and_summary(self):
        cases = [(['--record-next', '1', '--json'], []),
                 (['--provider-review', 'codex', '--json'], ['docs/example.md']),
                 (['--recording-status'], []), (['--usage-summary', '--json'], [])]
        for options, paths in cases:
            code, expected, errors = oracle.main(FIXTURE, self.target, self.roles, AT, [*paths, *options], self.dispatch)
            self.assertEqual(code, 0); self.assertEqual(errors, b'')
            args = ['--repo', self.target, *paths, *options] if paths else options
            actual, _ = self.run_cli(*args); self.assertEqual(actual.encode(), expected)

    def test_receipt_inspection_does_not_reobserve_or_execute_target(self):
        out, _ = self.run_cli('--repo', self.target, 'docs/example.md', '--log-usage', '--format', 'receipt')
        receipt = json.loads(out); self.assertTrue(receipt['target_current_state_rechecked'])
        with patch.object(app, 'capture_dispatch_source', side_effect=AssertionError('no live capture')), \
                patch.object(app, 'observe_dispatch_source', side_effect=AssertionError('no live observation')):
            out, _ = self.call('review-dispatch', 'inspect', '--workspace', 'cli', '--generation', receipt['generation'])
        inspected = json.loads(out); self.assertFalse(inspected['target_current_state_rechecked'])
        self.assertTrue(inspected['retained_complete_outputs_reverified']); self.assertFalse(inspected['provider_invoked'])

    def test_original_mode_priority_ignores_dispatch_inputs_for_recording_operation(self):
        with patch.object(app, 'capture_dispatch_source', side_effect=AssertionError('recording takes priority')):
            out, _ = self.run_cli('--repo', self.base / 'absent', '--base-ref', 'not-a-ref',
                                  '--record-next', '2', '--record-continuous', '--log-usage', '--format', 'receipt')
        receipt = json.loads(out); self.assertEqual(receipt['operation'], 'record-window')
        self.assertFalse(receipt['effects']['event_appended']); self.assertFalse(receipt['provider_invoked'])

    def test_default_clock_is_actual_runtime_time_and_is_labelled(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return datetime(2026, 11, 17, 17, tzinfo=timezone.utc)
        with patch.object(app, 'datetime', Clock):
            out, _ = self.call('review-dispatch', 'run', '--workspace', 'cli', '--record-next', '1', '--format', 'receipt')
        receipt = json.loads(out)
        self.assertEqual(receipt['clock_provenance'], 'runtime_clock'); self.assertEqual(receipt['assessed_at'], AT)
        out, _ = self.run_cli('--recording-status', '--format', 'receipt')
        self.assertEqual(json.loads(out)['clock_provenance'], 'explicit_operator_time')

    def test_private_namespace_and_provider_declaration_errors_are_redacted(self):
        for args, code in [(['--provider-review', 'none', '--recording-status'], 'dispatch_provider_review_requires_provider'),
                (['--record-next', '1', '--usage-log', '../outside'], 'invalid_dispatch_business_path'),
                (['--record-next', '1', '--usage-state', '.axiom/context.json'], 'dispatch_metadata_path_reserved')]:
            out, errors = self.run_cli(*args, expected=2); self.assertEqual(out, '')
            self.assertEqual(json.loads(errors)['diagnostics'], [code])
        other = self.target / 'node'; other.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'dispatch_private_state_must_be_outside_target'):
            app.run(['run', '--workspace', 'wrong', '--repo', str(self.target), 'docs/example.md'], other,
                    {'node_id': 'synthetic-other-node'})
        self.assertFalse((other / 'state').exists())

    def external(self, *arguments, expected=0):
        return self.call('review-dispatch', 'run', '--external-files', '--file-profile', native.PROFILES[0],
                         '--repo', self.target, '--at', AT, *arguments, expected=expected)

    def test_external_cli_complete_original_stdout_and_actual_caller_files(self):
        code, expected, _ = oracle.main(FIXTURE, self.target, self.roles, AT, ['--record-next', '2', '--json'], self.dispatch)
        state = self.target / app.DEFAULT_STATE; expected_state = state.read_bytes(); state.unlink()
        out, _ = self.external('--record-next', '2', '--json')
        self.assertEqual(out.encode(), expected); self.assertEqual(state.read_bytes(), expected_state)
        before = state.read_bytes()
        code, expected, _ = oracle.main(FIXTURE, self.target, self.roles, AT,
                                        ['docs/example.md', '--provider-review', 'codex', '--json'], self.dispatch)
        log = self.target / logic.DEFAULT_LOG; expected_state = state.read_bytes(); expected_log = log.read_bytes()
        state.write_bytes(before); log.unlink()
        out, _ = self.external('docs/example.md', '--provider-review', 'codex', '--json')
        self.assertEqual(out.encode(), expected)
        self.assertEqual(state.read_bytes(), expected_state); self.assertEqual(log.read_bytes(), expected_log)

    def test_external_prepare_inspect_and_apply_are_separate_concrete_operations(self):
        out, _ = self.external('--record-next', '1', '--prepare-only')
        receipt = json.loads(out); self.assertEqual(receipt['execution_state'], 'prepared')
        self.assertTrue(receipt['native_file_targets']['state']['planned_write'])
        self.assertEqual(receipt['native_file_targets']['state']['path'], str(self.target / app.DEFAULT_STATE))
        state = self.target / app.DEFAULT_STATE; self.assertFalse(state.exists())
        out, _ = self.call('review-dispatch', 'external-inspect', '--id', receipt['assessment_id'])
        self.assertFalse(json.loads(out)['native_outputs_rechecked']); self.assertFalse(state.exists())
        out, _ = self.call('review-dispatch', 'external-apply', '--id', receipt['assessment_id'])
        self.assertEqual(json.loads(out)['execution_state'], 'applied'); self.assertTrue(state.exists())

    def test_external_cli_partial_failure_returns_private_recovery_id_without_payload(self):
        self.external('--record-next', '1'); replace = native.replace
        def fail_second(path, raw, mode):
            if path.name == 'recording-state.json': raise OSError('SYNTHETIC_PRIVATE_FAILURE')
            return replace(path, raw, mode)
        with patch.object(native, 'replace', side_effect=fail_second):
            out, errors = self.external('docs/example.md', '--provider-review', 'codex', expected=2)
        self.assertEqual(out, ''); self.assertNotIn('SYNTHETIC_PRIVATE_FAILURE', errors)
        error = json.loads(errors); self.assertEqual(error['diagnostics'], ['external_dispatch_apply_failed'])
        out, _ = self.call('review-dispatch', 'external-pending')
        self.assertEqual(json.loads(out)['pending_assessment_ids'], [error['assessment_id']])
        out, _ = self.call('review-dispatch', 'external-apply', '--id', error['assessment_id'])
        self.assertEqual(json.loads(out)['execution_state'], 'applied')
        self.assertEqual(len(logic.events((self.target / logic.DEFAULT_LOG).read_bytes())), 1)
        out, _ = self.call('review-dispatch', 'external-pending')
        self.assertEqual(json.loads(out)['pending_assessment_ids'], [])

    def test_external_cli_never_reapplies_a_completed_operation_after_operator_edit(self):
        out, _ = self.external('--record-next', '2', '--format', 'receipt'); identifier = json.loads(out)['assessment_id']
        state = self.target / app.DEFAULT_STATE; state.write_bytes(b'operator edit')
        out, errors = self.call('review-dispatch', 'external-apply', '--id', identifier, expected=2)
        self.assertEqual(json.loads(errors)['diagnostics'], ['dispatch_native_output_verification_failed'])
        self.assertEqual(state.read_bytes(), b'operator edit')

    def test_file_mode_requires_explicit_profile_and_cannot_implicitly_use_private_workspace(self):
        for arguments, code in [(['--external-files', '--recording-status'], 'external_dispatch_requires_file_profile_without_workspace'),
                (['--workspace', 'cli', '--file-profile', native.PROFILES[0], '--recording-status'], 'dispatch_file_options_require_external_mode'),
                (['--external-files', '--file-profile', native.PROFILES[0], '--workspace', 'cli', '--recording-status'], 'external_dispatch_requires_file_profile_without_workspace')]:
            out, errors = self.call('review-dispatch', 'run', *arguments, expected=2)
            self.assertEqual(out, ''); self.assertEqual(json.loads(errors)['diagnostics'], [code])

    def test_external_abandonment_is_explicit_and_does_not_claim_a_native_rollback(self):
        out, _ = self.external('--record-next', '1', '--prepare-only'); identifier = json.loads(out)['assessment_id']
        out, _ = self.call('review-dispatch', 'external-abandon', '--id', identifier, '--reason', 'Do not apply this prepared intent')
        receipt = json.loads(out); self.assertEqual(receipt['execution_state'], 'abandoned')
        self.assertFalse(receipt['abandonment']['native_files_reverted']); self.assertFalse((self.target / app.DEFAULT_STATE).exists())
        out, errors = self.call('review-dispatch', 'external-apply', '--id', identifier, expected=2)
        self.assertEqual(json.loads(errors)['diagnostics'], ['external_dispatch_abandoned_operation'])


if __name__ == '__main__': unittest.main()
