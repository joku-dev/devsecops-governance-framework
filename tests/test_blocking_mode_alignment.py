from pathlib import Path
import json
import sys
import unittest

from jsonschema import Draft202012Validator
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_blocking_mode_alignment import assess


def readiness(repository_id: str, *, technical_ready: bool = False, approval: str = "pending") -> dict:
    criteria = [
        {"id": "minimum_trust_level", "required": True, "status": "pass" if technical_ready else "fail"},
        {"id": "accountable_approval", "required": True, "status": "pass" if approval == "approved" else "manual_review"},
    ]
    return {
        "generated_at": "2026-07-18T00:00:00Z",
        "repositories": [{
            "repository_id": repository_id,
            "technical_ready": technical_ready,
            "manual_approval": approval,
            "criteria": criteria,
        }],
    }


def model(records=None) -> dict:
    return {
        "model_introduced_at": "2026-07-18T00:00:00Z",
        "legacy_risk_records": records or [],
    }


class BlockingModeAlignmentTests(unittest.TestCase):
    def test_current_projection_and_model_validate(self):
        report = json.loads((ROOT / "generated/reports/blocking-mode-alignment.json").read_text())
        report_schema = json.loads((ROOT / "schemas/blocking-mode-alignment.schema.json").read_text())
        Draft202012Validator(report_schema).validate(report)
        registry = yaml.safe_load((ROOT / "model/enforcement/blocking-mode-alignment.yaml").read_text())
        model_schema = json.loads((ROOT / "schemas/blocking-mode-alignment-model.schema.json").read_text())
        Draft202012Validator(model_schema).validate(registry)
        self.assertEqual(report["alignment_status"], "controlled")
        self.assertEqual(report["summary"]["legacy_risk_active"], 1)
        self.assertEqual(report["summary"]["unsafe_blocking"], 0)
        legacy = next(item for item in report["repositories"] if item["repository_id"] == "joku-dev/ha-CPsWMS")
        self.assertFalse(legacy["blocking_activation_valid"])
        self.assertEqual(legacy["alignment"], "legacy_risk_active")

    def test_new_blocking_without_readiness_or_record_requires_review(self):
        repo = "owner/new-repo"
        result = assess(
            integrations={"integrations": [{"repository": repo, "governance_mode": "block-on-error"}]},
            readiness=readiness(repo), alignment_model=model(), as_of="2026-07-18T00:00:00Z",
        )
        self.assertEqual(result["alignment_status"], "review_required")
        self.assertEqual(result["summary"]["unsafe_blocking"], 1)
        self.assertEqual(result["repositories"][0]["alignment"], "unapproved_blocking")

    def test_record_created_after_cutoff_cannot_disguise_new_blocking(self):
        repo = "owner/new-repo"
        record = {
            "repository_id": repo, "current_mode": "block-on-error",
            "mode_observed_at": "2026-07-18T00:00:00Z", "review_due": "2026-08-18T00:00:00Z",
            "required_gap_ids": ["minimum_trust_level", "accountable_approval"],
            "disposition": "preserve_without_new_approval", "enforcement_change_authorized": False,
        }
        result = assess(
            integrations={"integrations": [{"repository": repo, "governance_mode": "block-on-error"}]},
            readiness=readiness(repo), alignment_model=model([record]), as_of="2026-07-18T00:00:00Z",
        )
        self.assertEqual(result["repositories"][0]["alignment"], "legacy_risk_incomplete")
        self.assertEqual(result["alignment_status"], "review_required")

    def test_expired_legacy_review_requires_action(self):
        repo = "owner/legacy-repo"
        record = {
            "repository_id": repo, "current_mode": "block-on-error",
            "mode_observed_at": "2026-07-01T00:00:00Z", "review_due": "2026-07-17T00:00:00Z",
            "required_gap_ids": ["minimum_trust_level", "accountable_approval"],
            "disposition": "preserve_without_new_approval", "enforcement_change_authorized": False,
        }
        result = assess(
            integrations={"integrations": [{"repository": repo, "governance_mode": "block-on-error"}]},
            readiness=readiness(repo), alignment_model=model([record]), as_of="2026-07-18T00:00:00Z",
        )
        self.assertEqual(result["repositories"][0]["alignment"], "legacy_risk_expired")
        self.assertEqual(result["alignment_status"], "review_required")

    def test_ready_and_approved_blocking_is_aligned_without_legacy_record(self):
        repo = "owner/ready-repo"
        result = assess(
            integrations={"integrations": [{"repository": repo, "governance_mode": "waiver-required"}]},
            readiness=readiness(repo, technical_ready=True, approval="approved"), alignment_model=model(),
            as_of="2026-07-18T00:00:00Z",
        )
        row = result["repositories"][0]
        self.assertEqual(row["alignment"], "aligned_blocking")
        self.assertTrue(row["blocking_activation_valid"])
        self.assertEqual(result["alignment_status"], "controlled")

    def test_orphaned_legacy_record_requires_review(self):
        result = assess(
            integrations={"integrations": []},
            readiness={"generated_at": "2026-07-18T00:00:00Z", "repositories": []},
            alignment_model=model([{"repository_id": "owner/removed-repo"}]),
            as_of="2026-07-18T00:00:00Z",
        )
        self.assertEqual(result["alignment_status"], "review_required")
        self.assertEqual(result["summary"]["orphaned_legacy_records"], 1)
        self.assertEqual(result["orphaned_legacy_records"], ["owner/removed-repo"])


if __name__ == "__main__":
    unittest.main()
