"""Whole original dispatcher recording/log/state/summary wires and boundary checks."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'scripts'))
from lib import review_dispatch as logic
spec = importlib.util.spec_from_file_location('original_dispatch', ROOT/'tests/acceptance/v1_review_dispatch_oracle.py');oracle = importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
AT = '2026-11-17T18:00:00.123456+01:00'


class DispatchRecording(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base = Path(self.temp.name)
        self.roles = {'repo-steward': {'skill': 'repo-steward'}, 'evidence-and-intake': {'skill': 'evidence-and-intake'}}
        self.old = oracle.load(ROOT/'tests/fixtures/v2-review-planning', self.base, self.roles, AT)
        self.log = self.base/'generated/agent-usage/agent-usage.jsonl';self.statefile = self.base/'state.json'
        self.dispatch = {'changed_files': ['docs/test.md'], 'selected_agents': ['evidence-and-intake', 'repo-steward'], 'release_impact': 'none', 'required_validations': ['git diff --check'], 'warnings': [], 'selection_reasons': {}}
        self.event = logic.usage_event(self.dispatch, self.roles, AT)

    def assert_state(self, value):
        self.assertEqual(self.old['load_recording_state'](self.statefile), value)
        self.assertEqual(self.statefile.read_bytes(), (json.dumps(value, indent=2, sort_keys=True)+'\n').encode())
        self.assertEqual(self.old['render_recording_status'](value), logic.recording_text(value))

    def test_complete_default_state_and_status(self):
        for raw in (None, b'{}', b'{"custom":"retained"}', b'{"mode":"continuous"}'):
            if raw is not None:self.statefile.write_bytes(raw)
            old = self.old['load_recording_state'](self.statefile)
            self.assertEqual(logic.state(raw), old);self.assertEqual(logic.recording_text(logic.state(raw)), self.old['render_recording_status'](old))

    def test_complete_original_event_and_log_and_summary_wires(self):
        for kind, provider, platform, source in [('dispatch', 'none', 'local', 'manual'), ('provider_review', 'codex', 'github-actions', 'pull-request'), ('provider_review', 'mistral', 'bamboo', 'reference-run')]:
            old = self.old['build_usage_event'](self.dispatch, run_type=kind, provider=provider, platform=platform, source=source)
            new = logic.usage_event(self.dispatch, self.roles, AT, run_type=kind, provider=provider, platform=platform, source=source);self.assertEqual(old, new)
            before = self.log.read_bytes() if self.log.exists() else None;self.old['append_usage_event'](self.log, old);self.assertEqual(self.log.read_bytes(), logic.append(before, new))
            rows = self.old['load_usage_events'](self.log);summary = self.old['summarize_usage'](rows)
            self.assertEqual(logic.summary(self.log.read_bytes()), summary);self.assertEqual(logic.summary_text(summary), self.old['render_usage_summary'](summary))

    def test_finite_window_complete_state_file_and_effects(self):
        old = self.old['activate_recording'](self.statefile, count=2, usage_log=self.log);new = logic.activate(logic.state(None), 'window', AT, count=2)
        self.assertEqual(old, new);self.assert_state(new)
        raw = None
        for _ in range(3):
            result = self.old['consume_recording_event'](self.statefile, old, self.event)
            new, appended, remaining = logic.consume(new, self.event);self.assertEqual((appended, remaining), result)
            if appended:raw = logic.append(raw, self.event)
            self.assert_state(new);self.assertEqual(self.log.read_bytes(), raw)
        self.assertFalse(logic.active(new))

    def test_continuous_transition_retains_original_start_and_fields(self):
        old = self.old['activate_recording'](self.statefile, count=1, usage_log=self.log);self.old['consume_recording_event'](self.statefile, old, self.event)
        before = deepcopy(old);old = self.old['activate_continuous_recording'](self.statefile, usage_log=self.log)
        new = logic.activate(before, 'continuous', '2026-11-18T12:00:00Z');self.assertEqual(old, new);self.assert_state(new)
        # Original now_utc remains fixed; started_at must retain the earlier value.
        raw = self.log.read_bytes()
        for _ in range(2):
            result = self.old['consume_recording_event'](self.statefile, old, self.event);new, appended, remaining = logic.consume(new, self.event)
            self.assertEqual((appended, remaining), result);self.assert_state(new);raw = logic.append(raw, self.event);self.assertEqual(self.log.read_bytes(), raw)
        self.assertTrue(logic.active(new))

    def test_empty_summary_and_missing_usage_fields(self):
        for raw in (None, b'', b'\n \n', b'{}\n'):
            self.log.parent.mkdir(parents=True, exist_ok=True)
            if raw is not None:self.log.write_bytes(raw)
            old = self.old['summarize_usage'](self.old['load_usage_events'](self.log))
            self.assertEqual(logic.summary(raw), old);self.assertEqual(logic.summary_text(old), self.old['render_usage_summary'](old))

    def test_unterminated_log_separator_correction_preserves_prefix(self):
        raw = json.dumps(self.event).encode();after = logic.append(raw, self.event)
        self.assertTrue(after.startswith(raw+b'\n'));self.assertEqual(logic.events(after), [self.event, self.event])

    def test_clock_and_descriptor_diagnostics_do_not_include_private_input(self):
        for value in ('SYNTHETIC_PRIVATE', None, [], '2026-11-17T00:00:00'):
            with self.assertRaises(ValueError) as error:logic.utc_time(value)
            self.assertNotIn('SYNTHETIC_PRIVATE', str(error.exception))
        for value in ('private\nlabel', 'escape\x1b[31m', '', 'x'*4097):
            with self.assertRaisesRegex(ValueError, '^invalid_dispatch_usage_field$'):logic.text(value)

    def test_malformed_state_and_usage_reject_without_payload_diagnostics(self):
        for value in (b'[]', b'{', b'{"active":"SYNTHETIC_PRIVATE"}', b'{"remaining":true}', b'{"remaining":-1}', b'{"mode":"other"}', b'{"remaining":1.5}', b'{"active":true,"active":false}', b'{"usage_log":null}', b'{"started_at":"bad"}'):
            with self.assertRaises((ValueError, TypeError)):logic.state(value)
        for value in (b'[]', b'{', b'{"skills":true}', b'{"provider":{}}', b'{"selected_agents":[true]}', b'\xff'):
            with self.assertRaises(ValueError):logic.events(value)
        for count in (True, 0, -1, 1.5, '2'):
            with self.assertRaises(ValueError):logic.activate(logic.state(None), 'window', AT, count=count)

    def test_large_valid_window_is_a_counter_and_matches_original_without_eager_runs(self):
        count = 10**30
        old = self.old['activate_recording'](self.statefile, count=count, usage_log=self.log)
        new = logic.activate({}, 'window', AT, count=count)
        self.assertEqual(new, old); self.assert_state(new)
        appended, remaining = self.old['consume_recording_event'](self.statefile, old, self.event)
        new, recorded, value = logic.consume(new, self.event)
        self.assertEqual((recorded, value), (appended, remaining)); self.assert_state(new)
        self.assertEqual(value, count - 1); self.assertEqual(len(logic.events(self.log.read_bytes())), 1)


if __name__ == '__main__':unittest.main()
