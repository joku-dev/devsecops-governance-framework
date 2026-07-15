from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dispatch_governance_agents.py"

spec = importlib.util.spec_from_file_location("dispatch_governance_agents", SCRIPT)
dispatch_cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["dispatch_governance_agents"] = dispatch_cli
spec.loader.exec_module(dispatch_cli)


class DispatchGovernanceAgentsTests(unittest.TestCase):
    def test_build_dispatch_selects_policy_and_release_agents(self):
        dispatch = dispatch_cli.build_dispatch(["policies/opa/vulnerability_gate.rego"])

        self.assertEqual(dispatch["release_impact"], "candidate")
        self.assertIn("policy-as-code", dispatch["selected_agents"])
        self.assertIn("release-manager", dispatch["selected_agents"])
        self.assertIn("repo-steward", dispatch["selected_agents"])
        self.assertIn("opa check policies/opa", dispatch["required_validations"])

    def test_build_dispatch_warns_for_released_baselines(self):
        dispatch = dispatch_cli.build_dispatch(["releases/l1/v1.1.3/checksums.txt"])

        self.assertEqual(dispatch["release_impact"], "released_baseline")
        self.assertIn("release-manager", dispatch["selected_agents"])
        self.assertEqual(dispatch["warnings"], ["Released baseline path changed; release-manager review is mandatory."])

    def test_build_dispatch_warns_for_source_candidate_derivation_risk(self):
        dispatch = dispatch_cli.build_dispatch(
            [
                "docs/governance/source-documents/new-standard.md",
                "policies/opa/vulnerability_gate.rego",
            ]
        )

        self.assertIn("Derived governance artifact path changed", dispatch["warnings"][0])

    def test_json_output_is_machine_readable(self):
        dispatch = dispatch_cli.build_dispatch(["status/repository-results-index.json"])
        payload = json.loads(json.dumps(dispatch))

        self.assertIn("evidence-and-intake", payload["selected_agents"])
        self.assertEqual(payload["release_impact"], "none")

    def test_text_output_contains_agents_and_validations(self):
        dispatch = dispatch_cli.build_dispatch(["docs/governance/source-documents/new.md"])
        output = dispatch_cli.render_text(dispatch)

        self.assertIn("source-document-intake", output)
        self.assertIn("python3 scripts/validate_governance_repo.py", output)

    def test_build_dispatch_keeps_company_ci_adapters_on_neutral_roles(self):
        dispatch = dispatch_cli.build_dispatch(["pipeline-baseline/templates/bamboo/bamboo-specs.yml"])

        self.assertIn("devsecops-baseline", dispatch["selected_agents"])
        self.assertIn("release-manager", dispatch["selected_agents"])
        self.assertIn("repo-steward", dispatch["selected_agents"])

    def test_build_usage_event_maps_agents_to_skills(self):
        dispatch = dispatch_cli.build_dispatch(["pipeline-baseline/templates/bitbucket/README.md"])

        event = dispatch_cli.build_usage_event(
            dispatch,
            run_type="provider_review",
            provider="codex",
            platform="github-actions",
            source="reference-run",
        )

        self.assertEqual(event["run_type"], "provider_review")
        self.assertEqual(event["provider"], "codex")
        self.assertEqual(event["platform"], "github-actions")
        self.assertIn("release-manager", event["selected_agents"])
        self.assertIn("release-management", event["skills"])
        self.assertEqual(event["release_impact"], "none")

    def test_usage_log_round_trip_and_summary(self):
        dispatch = dispatch_cli.build_dispatch(["policies/opa/vulnerability_gate.rego"])
        event = dispatch_cli.build_usage_event(
            dispatch,
            run_type="dispatch",
            provider="none",
            platform="local",
            source="unit-test",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "agent-usage.jsonl"
            dispatch_cli.append_usage_event(path, event)
            events = dispatch_cli.load_usage_events(path)
            summary = dispatch_cli.summarize_usage(events)

        self.assertEqual(len(events), 1)
        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["agent_counts"]["policy-as-code"], 1)
        self.assertEqual(summary["skill_counts"]["policy-as-code"], 1)
        self.assertEqual(summary["provider_counts"]["none"], 1)
        self.assertEqual(summary["platform_counts"]["local"], 1)

    def test_provider_review_shortcut_logs_provider_review_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "agent-usage.jsonl"
            state_path = Path(tmpdir) / "recording-state.json"

            result = dispatch_cli.main(
                [
                    "--provider-review",
                    "codex",
                    "--platform",
                    "local",
                    "--source",
                    "unit-test",
                    "--usage-log",
                    str(log_path),
                    "--usage-state",
                    str(state_path),
                    "docs/operations/agents/agent-usage-tracking.md",
                ]
            )
            events = dispatch_cli.load_usage_events(log_path)

        self.assertEqual(result, 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["run_type"], "provider_review")
        self.assertEqual(events[0]["provider"], "codex")
        self.assertEqual(events[0]["platform"], "local")

    def test_provider_review_shortcut_rejects_none_provider(self):
        result = dispatch_cli.main(["--provider-review", "none", "docs/operations/agents/agent-usage-tracking.md"])

        self.assertEqual(result, 2)

    def test_recording_state_consumes_configured_number_of_events(self):
        dispatch = dispatch_cli.build_dispatch(["policies/opa/vulnerability_gate.rego"])
        event = dispatch_cli.build_usage_event(
            dispatch,
            run_type="dispatch",
            provider="none",
            platform="local",
            source="unit-test",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "recording-state.json"
            log_path = Path(tmpdir) / "agent-usage.jsonl"

            state = dispatch_cli.activate_recording(state_path, count=2, usage_log=log_path)
            recorded, remaining = dispatch_cli.consume_recording_event(state_path, state, event)
            self.assertTrue(recorded)
            self.assertEqual(remaining, 1)
            self.assertEqual(len(dispatch_cli.load_usage_events(log_path)), 1)

            state = dispatch_cli.load_recording_state(state_path)
            recorded, remaining = dispatch_cli.consume_recording_event(state_path, state, event)
            self.assertTrue(recorded)
            self.assertEqual(remaining, 0)
            self.assertEqual(len(dispatch_cli.load_usage_events(log_path)), 2)

            state = dispatch_cli.load_recording_state(state_path)

        self.assertFalse(state["active"])
        self.assertEqual(state["remaining"], 0)
        self.assertIn("completed_at", state)

    def test_continuous_recording_state_keeps_recording_events(self):
        dispatch = dispatch_cli.build_dispatch(["policies/opa/vulnerability_gate.rego"])
        event = dispatch_cli.build_usage_event(
            dispatch,
            run_type="dispatch",
            provider="none",
            platform="local",
            source="unit-test",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "recording-state.json"
            log_path = Path(tmpdir) / "agent-usage.jsonl"

            state = dispatch_cli.activate_continuous_recording(state_path, usage_log=log_path)
            recorded, remaining = dispatch_cli.consume_recording_event(state_path, state, event)
            self.assertTrue(recorded)
            self.assertIsNone(remaining)

            state = dispatch_cli.load_recording_state(state_path)
            recorded, remaining = dispatch_cli.consume_recording_event(state_path, state, event)
            self.assertTrue(recorded)
            self.assertIsNone(remaining)

            state = dispatch_cli.load_recording_state(state_path)
            events = dispatch_cli.load_usage_events(log_path)

        self.assertTrue(state["active"])
        self.assertEqual(state["mode"], "continuous")
        self.assertIsNone(state["remaining"])
        self.assertEqual(len(events), 2)

    def test_render_usage_summary_orders_counts(self):
        summary = {
            "event_count": 2,
            "agent_counts": {"repo-steward": 2, "release-manager": 1},
            "skill_counts": {"repo-steward": 2, "release-management": 1},
            "provider_counts": {"none": 1, "codex": 1},
            "platform_counts": {"local": 2},
            "run_type_counts": {"dispatch": 1, "provider_review": 1},
        }

        output = dispatch_cli.render_usage_summary(summary)

        self.assertIn("Events: 2", output)
        self.assertIn("- repo-steward: 2", output)
        self.assertIn("- release-manager: 1", output)
