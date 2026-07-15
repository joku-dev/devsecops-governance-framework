from pathlib import Path
import json
import tempfile
import unittest

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "model" / "evidence" / "evidence-collector-contract.yaml"
MODEL_SCHEMA_PATH = ROOT / "schemas" / "evidence-collector-contract.schema.json"
RECORD_SCHEMA_PATH = ROOT / "schemas" / "evidence-collector-record.schema.json"
TRUST_SCHEMA_PATH = ROOT / "schemas" / "evidence-trust-record.schema.json"
EXAMPLE_PATH = ROOT / "docs" / "examples" / "evidence-collector-record.example.json"

import sys

sys.path.insert(0, str(ROOT / "scripts"))
from lib.evidence_trust import build_trust_capture, digest_subject


class EvidenceCollectorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))
        cls.model_schema = json.loads(MODEL_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.record_schema = json.loads(RECORD_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.trust_schema = json.loads(TRUST_SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_contract_model_is_provisional_report_only_and_compatible(self):
        jsonschema.Draft202012Validator(self.model_schema).validate(self.model)
        self.assertEqual(self.model["status"], "provisional")
        self.assertEqual(self.model["enforcement"], "report_only")
        self.assertTrue(self.model["adoption"]["existing_records_remain_valid"])
        self.assertFalse(self.model["adoption"]["existing_records_reclassified"])
        self.assertFalse(self.model["adoption"]["latest_result_selection_changed"])
        self.assertFalse(self.model["adoption"]["downstream_producer_contract_changed"])
        self.assertFalse(self.model["adoption"]["baseline_release_required"])

    def test_governance_result_profile_covers_both_intake_paths(self):
        profile = self.model["profiles"][0]
        self.assertEqual(profile["evidence_type"], "governance_result")
        self.assertEqual(set(profile["governance_domains"]), {"devsecops", "architecture"})
        self.assertEqual(profile["freshness_policy"], "freshness-governance-result-24h")
        for implementation_path in profile["implementation_paths"]:
            self.assertTrue((ROOT / implementation_path).is_file())

        freshness = yaml.safe_load(
            (ROOT / "model" / "evidence" / "evidence-freshness-policies.yaml").read_text(encoding="utf-8")
        )
        freshness_ids = {policy["id"] for policy in freshness["policies"]}
        self.assertIn(profile["freshness_policy"], freshness_ids)
        self.assertTrue((ROOT / self.model["source_document"]).is_file())

    def test_vulnerability_scan_pilot_has_input_subject_and_freshness_contracts(self):
        profile = next(item for item in self.model["profiles"] if item["evidence_type"] == "vulnerability_scan")
        self.assertEqual(profile["state"], "pilot")
        self.assertEqual(profile["governance_domains"], ["devsecops"])
        self.assertEqual(profile["subject_binding_mode"], "co_collected")
        self.assertTrue(profile["rejects_placeholders"])
        self.assertTrue((ROOT / profile["input_schema"]).is_file())
        for implementation_path in profile["implementation_paths"]:
            self.assertTrue((ROOT / implementation_path).is_file())

        freshness = yaml.safe_load(
            (ROOT / "model" / "evidence" / "evidence-freshness-policies.yaml").read_text(encoding="utf-8")
        )
        freshness_ids = {policy["id"] for policy in freshness["policies"]}
        self.assertIn(profile["freshness_policy"], freshness_ids)

    def test_documented_collector_record_validates(self):
        example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(self.record_schema).validate(example)

    def test_new_trust_capture_is_a_valid_collector_record(self):
        with tempfile.TemporaryDirectory() as tempdir:
            report = Path(tempdir) / "report.json"
            report.write_text('{"status":"pass"}\n', encoding="utf-8")
            capture = build_trust_capture(
                governance_domain="architecture",
                repository_id="owner/repo",
                commit_id="abc123",
                workflow_name="Architecture Runtime Governance",
                run_id="42",
                run_attempt=1,
                artifact_name="architecture-governance-evidence",
                source_uri="https://api.github.test/artifacts/7/zip",
                produced_at="2026-07-15T13:59:00Z",
                captured_at="2026-07-15T14:00:00Z",
                subjects=[digest_subject("architecture_report", report, "artifact_metadata.report_sha256")],
            )

        jsonschema.Draft202012Validator(self.record_schema).validate(capture["capture"])
        jsonschema.Draft202012Validator(self.trust_schema).validate(capture)
        self.assertEqual(capture["capture"]["governance_domain"], "architecture")
        self.assertEqual(capture["capture"]["status"], "collected")
        self.assertEqual(capture["capture"]["errors"], [])

    def test_collected_record_rejects_missing_run_attempt_or_subjects(self):
        common = {
            "governance_domain": "devsecops",
            "repository_id": "owner/repo",
            "commit_id": "abc123",
            "workflow_name": "DevSecOps Baseline",
            "run_id": "42",
            "artifact_name": "governance-control-evaluation",
            "source_uri": "https://api.github.test/artifacts/7/zip",
            "produced_at": "2026-07-15T13:59:00Z",
            "captured_at": "2026-07-15T14:00:00Z",
        }
        with self.assertRaises(ValueError):
            build_trust_capture(run_attempt=None, subjects=[], **common)
        with self.assertRaises(ValueError):
            build_trust_capture(run_attempt=1, subjects=[], **common)
        common["captured_at"] = "2026-07-15T14:00:00"
        with self.assertRaises(ValueError):
            build_trust_capture(run_attempt=1, subjects=[{"evidence_ref": "ref"}], **common)
        common["captured_at"] = "2026-07-15T14:00:00Z"
        common["commit_id"] = "unknown"
        with self.assertRaises(ValueError):
            build_trust_capture(run_attempt=1, subjects=[{"evidence_ref": "ref"}], **common)

    def test_failed_record_shape_requires_error_and_no_subject(self):
        record = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
        record["status"] = "failed"
        record["subjects"] = []
        record["custody"] = record["custody"][:1]
        record["errors"] = [
            {
                "code": "artifact_download_failed",
                "message": "The authoritative artifact could not be downloaded.",
                "retryable": True,
            }
        ]
        jsonschema.Draft202012Validator(self.record_schema).validate(record)


if __name__ == "__main__":
    unittest.main()
