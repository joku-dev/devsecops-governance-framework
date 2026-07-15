from pathlib import Path
import json
import tempfile
import unittest

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "model" / "evidence" / "evidence-freshness-policies.yaml"
SCHEMA_PATH = ROOT / "schemas" / "evidence-freshness-policies.schema.json"

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from lib.evidence_trust import (
    build_trust_capture,
    digest_subject,
    evaluate_freshness,
    load_freshness_policy,
    verify_trust_capture,
)


class EvidenceFreshnessPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy_set = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.governance_result_policy = load_freshness_policy(
            POLICY_PATH,
            "freshness-governance-result-24h",
        )

    def test_policy_set_validates_and_is_provisional_report_only(self):
        Draft202012Validator(self.schema).validate(self.policy_set)
        self.assertEqual(self.policy_set["status"], "provisional")
        self.assertEqual(self.policy_set["enforcement"], "report_only")
        self.assertEqual(self.policy_set["policy_set_id"], "evidence-freshness-policies")
        self.assertFalse(self.policy_set["change_control"]["retrospective_reclassification"])
        self.assertTrue(self.policy_set["change_control"]["requires_gcr"])

    def test_provisional_windows_match_the_recorded_decision(self):
        policies = {item["id"]: item for item in self.policy_set["policies"]}
        self.assertEqual(policies["freshness-governance-result-24h"]["maximum_age_seconds"], 86400)
        self.assertEqual(policies["freshness-vulnerability-scan-24h"]["maximum_age_seconds"], 86400)
        self.assertEqual(policies["freshness-runtime-evidence-30m"]["maximum_age_seconds"], 1800)
        self.assertEqual(policies["freshness-architecture-review-180d"]["maximum_age_seconds"], 15552000)
        self.assertEqual(policies["freshness-sbom-subject-bound"]["evaluation_mode"], "subject_bound")
        self.assertEqual(
            policies["freshness-release-approval-candidate-bound"]["evaluation_mode"],
            "release_candidate_bound",
        )

    def test_max_age_evaluation_passes_within_window(self):
        check = evaluate_freshness(
            self.governance_result_policy,
            produced_at="2026-07-15T12:00:00Z",
            evaluated_at="2026-07-15T14:00:00Z",
        )
        self.assertEqual(check["result"], "pass")
        self.assertEqual(check["age_seconds"], 7200)
        self.assertEqual(check["maximum_age_seconds"], 86400)
        self.assertEqual(check["evidence_refs"], ["generated_at", "trust.verified_at"])
        self.assertEqual(check["finding_effect"], "report_only")

    def test_expired_future_and_missing_metadata_are_explicit(self):
        expired = evaluate_freshness(
            self.governance_result_policy,
            produced_at="2026-07-14T12:00:00Z",
            evaluated_at="2026-07-15T14:00:01Z",
        )
        future = evaluate_freshness(
            self.governance_result_policy,
            produced_at="2026-07-15T15:00:00Z",
            evaluated_at="2026-07-15T14:00:00Z",
        )
        missing = evaluate_freshness(
            self.governance_result_policy,
            produced_at=None,
            evaluated_at="2026-07-15T14:00:00Z",
        )
        self.assertEqual(expired["result"], "fail")
        self.assertEqual(future["result"], "fail")
        self.assertEqual(missing["result"], "not_evaluated")

    def test_freshness_check_is_recorded_without_changing_governance_outcome(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            report = directory / "report.json"
            report.write_text('{"overall_status":"pass"}\n', encoding="utf-8")
            subject = digest_subject("governance_report", report, "artifact_metadata.report_sha256")
            trust = build_trust_capture(
                repository_id="owner/repo",
                commit_id="abc123",
                workflow_name="Governance",
                run_id="42",
                run_attempt=1,
                artifact_name="governance-evidence",
                source_uri="https://example.test/artifact/42",
                captured_at="2026-07-15T14:00:00Z",
                subjects=[subject],
            )
            verified = verify_trust_capture(
                trust,
                repository_id="owner/repo",
                commit_id="abc123",
                run_id="42",
                artifact_name="governance-evidence",
                subject_paths={"governance_report": report},
                verified_at="2026-07-15T14:00:00Z",
                freshness_policy=self.governance_result_policy,
                produced_at="2026-07-14T12:00:00Z",
            )

        checks = {check["id"]: check for check in verified["checks"]}
        self.assertEqual(checks["freshness_evaluated"]["result"], "fail")
        self.assertEqual(verified["effective_level"], "integrity_verified")
        governance_snapshot = {"overall_status": "pass", "trust": verified}
        self.assertEqual(governance_snapshot["overall_status"], "pass")


if __name__ == "__main__":
    unittest.main()
