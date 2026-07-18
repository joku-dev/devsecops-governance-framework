from pathlib import Path
import copy
import json
import sys
import unittest

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from assess_governance_repository_security import assess


class GovernanceRepositorySecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = yaml.safe_load(
            (ROOT / "model/controls/governance-repository-security.yaml").read_text(encoding="utf-8")
        )
        cls.observation = json.loads(
            (ROOT / "docs/examples/governance-repository-security-observation.example.json").read_text(
                encoding="utf-8"
            )
        )

    def test_model_is_schema_valid_and_report_only(self):
        schema = json.loads(
            (ROOT / "schemas/governance-repository-security-model.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(self.model)
        self.assertEqual(self.model["enforcement"], "report_only")
        self.assertFalse(self.model["enforcement_change_authorized"])

    def test_secure_observation_passes_without_authorizing_enforcement(self):
        report = assess(self.model, self.observation)
        schema = json.loads(
            (ROOT / "schemas/governance-repository-security-report.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator(schema).validate(report)
        self.assertEqual(report["overall_status"], "pass")
        self.assertEqual(report["summary"]["fail"], 0)
        self.assertFalse(report["enforcement_change_authorized"])

    def test_missing_root_controls_are_visible_findings(self):
        observation = copy.deepcopy(self.observation)
        observation["repository"]["branch_protected"] = False
        observation["repository"]["required_approving_reviews"] = 0
        observation["repository"]["required_status_checks"] = []
        observation["actions"]["direct_main_write_workflows"] = [
            ".github/workflows/intake-governance-result.yml"
        ]
        observation["security_features"]["secret_scanning"] = "disabled"
        report = assess(self.model, observation)
        failures = {item["key"] for item in report["criteria"] if item["status"] == "fail"}
        self.assertIn("default_branch_protected", failures)
        self.assertIn("pull_request_review_required", failures)
        self.assertIn("governance_ci_required", failures)
        self.assertIn("automated_main_writes_absent", failures)
        self.assertIn("secret_scanning_enabled", failures)
        self.assertEqual(report["overall_status"], "findings")
        self.assertFalse(report["decision_boundary"]["blocks_pull_requests"])


if __name__ == "__main__":
    unittest.main()
