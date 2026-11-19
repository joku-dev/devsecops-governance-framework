"""Core negative-path and interruption checks; native parity is separate."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.environment_bootstrap import BootstrapFailure, RecordedPorts, run, replay


class Journal:
    def __init__(self):
        self.events = []
    def before(self, action):
        token = len(self.events)
        self.events.append(('intent', action))
        return token
    def after(self, token, value):
        self.events.append(('returned', token, value))
    def failed(self, token, code):
        self.events.append(('failed', token, code))


class EnvironmentBootstrapCore(unittest.TestCase):
    def actions(self, profile, existing):
        result = ['preflight', 'environment_python_executable']
        if not existing:
            result.append('create_environment')
        result.append('install_dependencies')
        if profile == 'validation-environment-v1':
            result.extend(('ensure_policy_tool', 'verify_policy_tool_version', 'check_dependency_consistency'))
        result.append('render_ready_message')
        return result

    def observations(self, profile, existing):
        return [{'action': action, 'value': existing if action == 'environment_python_executable' else None}
                for action in self.actions(profile, existing)]

    def test_existing_environment_still_updates_dependencies_and_validation_repairs_tools(self):
        for profile in ('validation-environment-v1', 'source-intake-environment-v1'):
            for existing in (True, False):
                with self.subTest(profile=profile, existing=existing):
                    ports = RecordedPorts(self.observations(profile, existing)); journal = Journal()
                    result = run(profile, ports, journal); ports.complete()
                    actions = [e[1] for e in journal.events if e[0] == 'intent']
                    self.assertIn('install_dependencies', actions)
                    self.assertEqual('create_environment' in actions, not existing)
                    self.assertEqual('ensure_policy_tool' in actions, profile == 'validation-environment-v1')
                    self.assertEqual(result.state, 'complete')
                    self.assertEqual(result.existing_environment_used, existing)

    def test_every_declared_native_failure_stops_before_later_effects_and_has_matching_intent(self):
        for profile in ('validation-environment-v1', 'source-intake-environment-v1'):
            for existing in (True, False):
                original = self.observations(profile, existing)
                for position in range(len(original)):
                    with self.subTest(profile=profile, existing=existing, failed_action=position):
                        rows = original[:position] + [{'action': original[position]['action'], 'failure': 'declared_native_failure'}]
                        ports = RecordedPorts(rows); journal = Journal()
                        with self.assertRaisesRegex(BootstrapFailure, '^declared_native_failure$'):
                            run(profile, ports, journal)
                        ports.complete()
                        self.assertEqual(journal.events[-1][0], 'failed')
                        self.assertEqual(journal.events[-2], ('intent', original[position]['action']))
                        self.assertEqual([e[1] for e in journal.events if e[0] == 'intent'], self.actions(profile, existing)[:position+1])

    def test_unexpected_interruption_leaves_pending_intent_without_claimed_failure_or_retry(self):
        class Interrupted:
            calls = 0
            def perform(self, action):
                self.calls += 1
                raise KeyboardInterrupt()
        ports = Interrupted(); journal = Journal()
        with self.assertRaises(KeyboardInterrupt):run('validation-environment-v1', ports, journal)
        self.assertEqual(ports.calls, 1)
        self.assertEqual(journal.events, [('intent', 'preflight')])

    def test_forged_result_extra_missing_or_reordered_observations_never_gain_completion(self):
        profile = 'validation-environment-v1'
        rows = self.observations(profile, True)
        rows[1] = {'action': 'environment_python_executable', 'value': 1}
        with self.assertRaisesRegex(BootstrapFailure, 'invalid_bootstrap_adapter_result'):
            run(profile, RecordedPorts(rows), Journal())
        original = self.observations(profile, True)
        for changed in (original[:-1], original[1:], [original[1], original[0], *original[2:]]):
            with self.assertRaises(ValueError):run(profile, RecordedPorts(changed), Journal())
        ports = RecordedPorts([*original, {'action': 'render_ready_message', 'value': None}])
        run(profile, ports, Journal())
        with self.assertRaisesRegex(ValueError, 'bootstrap_observation_unused'):ports.complete()

    def test_complete_replay_rejects_trailing_or_invalid_profile_without_native_calls(self):
        profile = 'validation-environment-v1'
        original = self.observations(profile, True)
        self.assertEqual(replay(profile, original).state, 'complete')
        with self.assertRaisesRegex(ValueError, 'bootstrap_observation_unused'):
            replay(profile, [*original, {'action': 'render_ready_message', 'value': None}])
        for invalid in (None, [], {}, True, 'unknown-profile'):
            with self.assertRaisesRegex(ValueError, 'unsupported_environment_bootstrap_profile'):
                replay(invalid, original)

    def test_failure_replay_requires_exact_end_of_declared_observations(self):
        failure = {'action': 'preflight', 'failure': 'declared_native_failure'}
        with self.assertRaisesRegex(BootstrapFailure, '^declared_native_failure$'):
            replay('validation-environment-v1', [failure])
        with self.assertRaisesRegex(ValueError, 'bootstrap_observation_unused'):
            replay('validation-environment-v1', [failure, {'action': 'render_ready_message', 'value': None}])

    def test_failed_intent_write_never_starts_the_native_operation(self):
        class Ports:
            calls = 0
            def perform(self, action):
                self.calls += 1
        class BrokenJournal(Journal):
            def before(self, action):
                raise OSError('declared intent storage failure')
        ports = Ports(); journal = BrokenJournal()
        with self.assertRaisesRegex(OSError, 'declared intent storage failure'):
            run('validation-environment-v1', ports, journal)
        self.assertEqual(ports.calls, 0)
        self.assertEqual(journal.events, [])
