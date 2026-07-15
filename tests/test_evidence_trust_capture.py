from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "evidence-trust-record.schema.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


architecture_intake = load_script("intake_architecture_github_actions_run")
from lib.evidence_trust import build_trust_capture, digest_subject, project_trust, verify_trust_capture


class EvidenceTrustCaptureTests(unittest.TestCase):
    def build_capture(self, directory: Path) -> dict:
        report = directory / "report.json"
        report.write_text('{"status":"pass"}\n', encoding="utf-8")
        subject = digest_subject("governance_report", report, "artifact_metadata.governance_report_sha256")
        return build_trust_capture(
            governance_domain="devsecops",
            repository_id="owner/repo",
            commit_id="abc123",
            workflow_name="Governance",
            run_id="42",
            run_attempt=2,
            artifact_name="governance-evidence",
            source_uri="https://api.github.test/artifacts/7/zip",
            produced_at="2026-07-15T13:59:00Z",
            captured_at="2026-07-15T14:00:00Z",
            subjects=[subject],
        )

    def test_capture_record_validates_and_does_not_claim_verification(self):
        with tempfile.TemporaryDirectory() as tempdir:
            trust = self.build_capture(Path(tempdir))

        Draft202012Validator(SCHEMA).validate(trust)
        self.assertEqual(trust["effective_level"], "unverified")
        self.assertEqual(trust["assessment_status"], "not_evaluated")
        self.assertIsNone(trust["verifier"])
        self.assertIsNone(trust["verified_at"])
        self.assertEqual(trust["checks"], [])
        self.assertEqual(trust["capture"]["source"]["run_attempt"], 2)
        self.assertEqual(trust["capture"]["contract_id"], "evidence-collector-contract")
        self.assertEqual(trust["capture"]["collector"]["version"], "0.1.0")
        self.assertEqual([step["action"] for step in trust["capture"]["custody"]], ["download", "extract_and_hash"])

    def test_documented_capture_example_validates(self):
        example = json.loads(
            (ROOT / "docs" / "examples" / "evidence-trust-record.example.json").read_text(encoding="utf-8")
        )
        Draft202012Validator(SCHEMA).validate(example)

    def test_not_evaluated_record_cannot_claim_a_higher_level(self):
        with tempfile.TemporaryDirectory() as tempdir:
            trust = self.build_capture(Path(tempdir))
        trust["effective_level"] = "integrity_verified"

        errors = list(Draft202012Validator(SCHEMA).iter_errors(trust))
        self.assertTrue(errors)

    def test_verifier_derives_integrity_level_and_leaves_later_checks_pending(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            trust = self.build_capture(directory)
            verified = verify_trust_capture(
                trust,
                repository_id="owner/repo",
                commit_id="abc123",
                run_id="42",
                artifact_name="governance-evidence",
                subject_paths={"governance_report": directory / "report.json"},
                verified_at="2026-07-15T14:01:00Z",
            )

        Draft202012Validator(SCHEMA).validate(verified)
        projection = project_trust({"overall_status": "fail", "trust": verified})
        self.assertEqual(projection["effective_level"], "integrity_verified")
        self.assertEqual(projection["assessment_status"], "evaluated")
        self.assertEqual(projection["check_summary"], {"pass": 5, "fail": 0, "not_evaluated": 7})

    def test_digest_mismatch_prevents_integrity_level(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            trust = self.build_capture(directory)
            (directory / "report.json").write_text('{"status":"changed"}\n', encoding="utf-8")
            verified = verify_trust_capture(
                trust,
                repository_id="owner/repo",
                commit_id="abc123",
                run_id="42",
                artifact_name="governance-evidence",
                subject_paths={"governance_report": directory / "report.json"},
                verified_at="2026-07-15T14:01:00Z",
            )

        self.assertEqual(verified["effective_level"], "unverified")
        checks = {check["id"]: check["result"] for check in verified["checks"]}
        self.assertEqual(checks["content_digest_verified"], "fail")

    def test_historical_snapshot_projects_as_unverified_without_reclassification(self):
        projection = project_trust({"overall_status": "pass"})
        self.assertEqual(projection["effective_level"], "unverified")
        self.assertEqual(projection["assessment_status"], "not_available")

    def test_architecture_snapshot_captures_digests_without_changing_outcome(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            old_status_results = architecture_intake.STATUS_RESULTS
            architecture_intake.STATUS_RESULTS = directory / "status" / "architecture-results"
            try:
                trust = self.build_capture(directory)
                artifact_metadata = {
                    "artifact_name": "architecture-governance-evidence",
                    "artifact_size_bytes": 123,
                    "architecture_governance_report_sha256": "a" * 64,
                    "architecture_release_input_sha256": "b" * 64,
                    "artifact_archive_sha256": "c" * 64,
                }
                output = architecture_intake.write_snapshot(
                    repository_id="owner/repo",
                    architecture_baseline_ref="architecture-baseline-l1-v0.1.0",
                    run={
                        "id": 42,
                        "conclusion": "success",
                        "updated_at": "2026-07-15T14:00:00Z",
                        "head_branch": "main",
                        "head_sha": "abc123",
                        "html_url": "https://example.com/runs/42",
                        "name": "Architecture Runtime Governance",
                        "event": "push",
                    },
                    report={"summary": {"finding_count": 0}},
                    release_input={"architecture": {}},
                    branch_protected=True,
                    artifact_metadata=artifact_metadata,
                    trust=trust,
                    notes="test",
                )
                snapshot = json.loads(output.read_text(encoding="utf-8"))
                Draft202012Validator(SCHEMA).validate(snapshot["trust"])
                self.assertEqual(snapshot["overall_status"], "pass")
                self.assertEqual(snapshot["trust"]["effective_level"], "unverified")
                self.assertEqual(snapshot["artifact_metadata"], artifact_metadata)
            finally:
                architecture_intake.STATUS_RESULTS = old_status_results


if __name__ == "__main__":
    unittest.main()
