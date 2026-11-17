"""Original main's whole output and concrete state/log effects on each path."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests/acceptance')]
from lib import review_dispatch as logic
import v1_review_dispatch_oracle as oracle

AT = '2026-11-17T18:00:00.123456+01:00'
FIXTURE = ROOT / 'tests/fixtures/v2-review-planning'


class DispatchMainTransitions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.state = self.base / 'generated/agent-usage/recording-state.json'
        self.log = self.base / logic.DEFAULT_LOG
        self.roles = {'repo-steward': {'skill': 'repo-steward'}}
        self.dispatch = {'changed_files': ['docs/test.md'], 'selected_agents': ['repo-steward'],
            'release_impact': 'none', 'required_validations': ['git diff --check'], 'warnings': [],
            'selection_reasons': {'repo-steward': ['always_select']}}

    def optional(self, path): return path.read_bytes() if path.exists() else None

    def write(self, path, raw):
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)

    def compare(self, request, arguments):
        before_state = self.optional(self.state)
        if request['action'] == 'dispatch':
            previous = logic.state(before_state)
            label = previous.get('usage_log', logic.DEFAULT_LOG) if logic.active(previous) else request['usage_log']
        else: label = request['usage_log']
        log = self.base / label; before_log = self.optional(log)
        old_code, old_out, old_err = oracle.main(FIXTURE, self.base, self.roles, AT, arguments, self.dispatch)
        self.assertEqual(old_code, 0); self.assertEqual(old_err, b'')
        new = logic.transition(request, before_state, before_log, dispatch=self.dispatch, roles=self.roles)
        self.assertEqual(new['stdout'], old_out)
        self.assertEqual(new['state_bytes'], self.optional(self.state))
        self.assertEqual(new['log_bytes'], self.optional(log)); self.assertFalse(new['provider_invoked'])
        return new

    def test_whole_default_dispatch_text_and_json_without_logging(self):
        for json_output in (False, True):
            new = self.compare(logic.request('dispatch', AT, json_output=json_output), ['docs/test.md', *(['--json'] if json_output else [])])
            self.assertFalse(new['state_changed']); self.assertFalse(new['log_changed']); self.assertIsNone(new['event'])

    def test_explicit_usage_and_provider_shortcut_are_declarations_only(self):
        for options, extra in [({'log_usage': True}, ['--log-usage']),
                ({'provider_review': 'codex', 'platform': 'ci', 'source': 'pull-request'}, ['--provider-review', 'codex', '--platform', 'ci', '--source', 'pull-request']),
                ({'log_usage': True, 'run_type': 'provider_review'}, ['--log-usage', '--run-type', 'provider_review'])]:
            new = self.compare(logic.request('dispatch', AT, json_output=True, **options), ['docs/test.md', '--json', *extra])
            self.assertTrue(new['log_changed']); self.assertFalse(new['state_changed'])
            self.assertFalse(new['provider_invoked'])
        self.assertEqual(len(logic.events(self.log.read_bytes())), 3)

    def test_finite_window_exhaustion_and_continuous_transition_whole_wires(self):
        self.compare(logic.request('record-window', AT, count=2, json_output=True), ['--record-next', '2', '--json'])
        for _ in range(3): self.compare(logic.request('dispatch', AT), ['docs/test.md'])
        self.assertEqual(len(logic.events(self.log.read_bytes())), 2)
        self.compare(logic.request('recording-status', AT), ['--recording-status'])
        self.compare(logic.request('record-continuous', AT), ['--record-continuous'])
        for _ in range(2): self.compare(logic.request('dispatch', AT, provider_review='mistral'), ['docs/test.md', '--provider-review', 'mistral'])
        self.compare(logic.request('usage-summary', AT, json_output=True), ['--usage-summary', '--json'])
        self.compare(logic.request('usage-summary', AT), ['--usage-summary'])

    def test_finite_window_replaces_corrupt_state_without_reading_it(self):
        self.write(self.state, b'{invalid previous state')
        self.write(self.log, b'invalid unrelated log')
        self.compare(logic.request('record-window', AT, count=1), ['--record-next', '1'])
        self.assertEqual(self.log.read_bytes(), b'invalid unrelated log')

    def test_summary_ignores_invalid_state_and_status_ignores_invalid_log(self):
        self.write(self.state, b'invalid unused state')
        self.compare(logic.request('usage-summary', AT), ['--usage-summary'])
        self.write(self.state, b'{}'); self.write(self.log, b'invalid unused log')
        self.compare(logic.request('recording-status', AT, json_output=True, log_usage=True), ['--recording-status', '--json', '--log-usage'])
        self.assertEqual(self.log.read_bytes(), b'invalid unused log')

    def test_active_recording_uses_its_own_log_instead_of_explicit_dispatch_log(self):
        self.compare(logic.request('record-window', AT, count=2, usage_log='logs/recorded.jsonl'),
                     ['--record-next', '2', '--usage-log', 'logs/recorded.jsonl'])
        ignored = self.base / 'logs/requested.jsonl'; self.write(ignored, b'SYNTHETIC_UNUSED')
        new = self.compare(logic.request('dispatch', AT, log_usage=True, usage_log='logs/requested.jsonl'),
                           ['docs/test.md', '--log-usage', '--usage-log', 'logs/requested.jsonl'])
        self.assertEqual(new['selected_usage_log'], 'logs/recorded.jsonl')
        self.assertEqual(ignored.read_bytes(), b'SYNTHETIC_UNUSED')

    def test_inactive_exhausted_state_stays_byte_exact_without_implicit_repair(self):
        raw = b'{"active":true,"remaining":0}\n'; self.write(self.state, raw)
        new = self.compare(logic.request('dispatch', AT), ['docs/test.md'])
        self.assertFalse(new['state_changed']); self.assertEqual(self.state.read_bytes(), raw)
        self.assertIsNone(self.optional(self.log))

    def test_action_priority_and_json_status_have_no_usage_side_effect(self):
        self.compare(logic.request('record-continuous', AT, json_output=True, provider_review='codex'),
                     ['--record-continuous', '--json', '--provider-review', 'codex'])
        self.compare(logic.request('recording-status', AT, json_output=True, provider_review='mistral'),
                     ['--recording-status', '--json', '--provider-review', 'mistral'])
        self.assertIsNone(self.optional(self.log))

    def test_closed_requests_reject_invalid_types_and_never_echo_private_input(self):
        base = logic.request('dispatch', AT)
        for key, value in [('action', 'SYNTHETIC_PRIVATE'), ('json', 1), ('log_usage', 'true'),
                ('provider_review', 'none'), ('count', 1), ('source', 'bad\nprivate')]:
            bad = deepcopy(base); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError) as error: logic.checked_request(bad)
            self.assertNotIn('SYNTHETIC_PRIVATE', str(error.exception))
        bad = deepcopy(base); bad['extra'] = 'private'
        with self.assertRaisesRegex(ValueError, '^invalid_dispatch_request$'): logic.checked_request(bad)


if __name__ == '__main__': unittest.main()
