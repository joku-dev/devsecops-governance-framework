from pathlib import Path
import json
import unittest

from tests.agent_harness.routing import (
    EVIDENCE_CONTEXTS,
    REPO_STEWARD,
    evaluate_scenario,
)


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "tests" / "agent_harness" / "scenarios"
EXPECTED_DIR = ROOT / "tests" / "agent_harness" / "expected"


class AgentScenarioTests(unittest.TestCase):
    def load_pair(self, scenario_path: Path) -> tuple[dict, dict]:
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        expected_path = EXPECTED_DIR / f"{scenario_path.stem}.expected.json"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        return scenario, expected

    def test_scenarios_match_expected_agent_contracts(self):
        for scenario_path in sorted(SCENARIO_DIR.glob("*.json")):
            with self.subTest(scenario=scenario_path.name):
                scenario, expected = self.load_pair(scenario_path)
                actual = evaluate_scenario(scenario)

                self.assertEqual(actual["selected_agents"], expected["selected_agents"])
                self.assertEqual(actual["release_impact"], expected["release_impact"])
                self.assertFalse(set(scenario.get("forbidden_agents", [])) & set(actual["selected_agents"]))
                self.assertTrue(set(expected["required_validations"]).issubset(actual["required_validations"]))

    def test_repo_steward_is_required_for_every_scenario(self):
        for scenario_path in sorted(SCENARIO_DIR.glob("*.json")):
            with self.subTest(scenario=scenario_path.name):
                scenario, _ = self.load_pair(scenario_path)
                actual = evaluate_scenario(scenario)
                self.assertIn(REPO_STEWARD, actual["selected_agents"])

    def test_candidate_source_documents_do_not_derive_governance_artifacts(self):
        scenario_path = SCENARIO_DIR / "source-document-candidate.json"
        scenario, expected = self.load_pair(scenario_path)
        actual = evaluate_scenario(scenario)

        self.assertEqual(scenario["source_document_status"], "candidate")
        self.assertFalse(actual["candidate_derivation_detected"])
        self.assertIn("candidate_derivation_before_review", expected["forbidden_changes"])

    def test_released_baseline_changes_require_release_manager(self):
        scenario_path = SCENARIO_DIR / "release-package-change.json"
        scenario, expected = self.load_pair(scenario_path)
        actual = evaluate_scenario(scenario)

        self.assertEqual(actual["release_impact"], "released_baseline")
        self.assertIn("release-manager", actual["selected_agents"])
        self.assertIn("silent_released_baseline_mutation", expected["forbidden_changes"])

    def test_evidence_scenarios_use_explicit_run_contexts(self):
        scenario_path = SCENARIO_DIR / "evidence-viewer-change.json"
        scenario, _ = self.load_pair(scenario_path)

        self.assertIn(scenario["evidence_context"], EVIDENCE_CONTEXTS)
        self.assertNotEqual(scenario["evidence_context"], "mainline")
