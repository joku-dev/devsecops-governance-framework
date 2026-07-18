from pathlib import Path
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_blocking_readiness import assess


class BlockingReadinessTests(unittest.TestCase):
    def model(self):
        return {"thresholds": {"minimum_mainline_successes": 3, "minimum_intake_events": 10,
                               "minimum_intake_success_rate_pct": 99.0, "minimum_trust_level": "provenance_verified"},
                "manual_approvals": {}}

    def test_current_report_is_schema_valid_and_does_not_authorize_enforcement(self):
        report = json.loads((ROOT / "generated/reports/blocking-readiness.json").read_text())
        schema = json.loads((ROOT / "schemas/blocking-readiness.schema.json").read_text())
        Draft202012Validator(schema).validate(report)
        self.assertFalse(report["enforcement_change_authorized"])
        self.assertEqual(report["summary"]["repositories"], 3)
        self.assertEqual(report["summary"]["ready"], 0)
        self.assertGreaterEqual(report["summary"]["already_blocking_but_not_ready"], 1)

    def test_complete_technical_fixture_is_only_ready_for_human_approval(self):
        repo = "owner/repo"
        latest = {"status": "pass", "commit_id": "abc", "governance_baseline_ref": "l1-baseline-v1.1.3",
                  "trust": {"effective_level": "provenance_verified", "replay": "pass", "check_summary": {"fail": 0}}}
        history = [{"pipeline_event": "push", "branch": "main", "status": "pass"} for _ in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            result = assess(
                integrations={"integrations": [{"repository": repo, "governance_mode": "report-only"}]},
                devsecops={"generated_at": "2026-07-17T00:00:00Z", "repositories": [{"repository_id": repo, "latest_result": latest, "history": history}]},
                architecture={"generated_at": "2026-07-17T00:00:00Z", "repositories": []},
                typed={"generated_at": "2026-07-17T00:00:00Z", "repositories": [{"repository_id": repo, "latest_result": {"commit_id": "abc", "collector_status": "collected", "freshness": "pass", "content_integrity": "pass", "replay": "pass"}}]},
                health={"dimensions": [{"dimension": "repository_id", "value": repo, "metrics": {"total": 10, "success_rate_pct": 100.0}}]},
                model=self.model(), conflict_root=Path(directory) / "conflicts",
            )
        assessment = result["repositories"][0]
        self.assertTrue(assessment["technical_ready"])
        self.assertEqual(assessment["decision"], "ready_for_approval")
        self.assertEqual(assessment["manual_approval"], "pending")
        self.assertFalse(result["enforcement_change_authorized"])

    def test_conflict_or_architecture_findings_prevent_readiness(self):
        repo = "owner/repo"
        latest = {"status": "pass", "commit_id": "abc", "governance_baseline_ref": "l1-baseline-v1.1.3",
                  "trust": {"effective_level": "provenance_verified", "replay": "pass", "check_summary": {"fail": 0}}}
        history = [{"pipeline_event": "push", "branch": "main", "status": "pass"} for _ in range(3)]
        with tempfile.TemporaryDirectory() as directory:
            conflicts = Path(directory) / "conflicts"
            conflicts.mkdir()
            (conflicts / "owner__repo-conflict.json").write_text("{}")
            result = assess(
                integrations={"integrations": [{"repository": repo, "governance_mode": "block-on-error"}]},
                devsecops={"generated_at": "2026-07-17T00:00:00Z", "repositories": [{"repository_id": repo, "latest_result": latest, "history": history}]},
                architecture={"generated_at": "2026-07-17T00:00:00Z", "repositories": [{"repository_id": repo, "latest_result": {"status": "findings"}}]},
                typed={"generated_at": "2026-07-17T00:00:00Z", "repositories": [{"repository_id": repo, "latest_result": {"commit_id": "abc", "collector_status": "collected", "freshness": "pass", "content_integrity": "pass", "replay": "pass"}}]},
                health={"dimensions": [{"dimension": "repository_id", "value": repo, "metrics": {"total": 10, "success_rate_pct": 100.0}}]},
                model=self.model(), conflict_root=conflicts,
            )
        assessment = result["repositories"][0]
        self.assertFalse(assessment["technical_ready"])
        self.assertEqual(assessment["mode_alignment"], "already_blocking_but_not_ready")


if __name__ == "__main__":
    unittest.main()
