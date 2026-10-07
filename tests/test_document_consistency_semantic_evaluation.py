from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from scripts.evaluate_document_consistency_semantic_report import evaluate
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/document-consistency-review-semantic"
CATALOG = json.loads((ROOT / "model/governance/document-consistency/semantic-evaluation-catalog-v1.json").read_text())
RESPONSE = json.loads((FIXTURES / "valid-response.json").read_text())
EVALUATION_SCHEMA = json.loads((ROOT / "schemas/document-consistency-semantic-evaluation-report.schema.json").read_text())


class DocumentConsistencySemanticEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        finding = deepcopy(RESPONSE["findings"][0])
        finding.update(evidence_status="valid", disposition="unconfirmed", validation_errors=[])
        cls.report = {
            "report_version": "1.0.0",
            "report_type": "document_consistency_semantic_validation_report",
            "review_id": "synthetic-evaluation",
            "overall_status": "synthetic_only",
            "scope": {
                "source_manifest_sha256": CATALOG["source_manifest_sha256"],
                "source_ids": CATALOG["source_ids"],
            },
            "execution": RESPONSE["execution"],
            "formal_validation": {"status": "pass", "errors": []},
            "semantic_review": {
                "status": "synthetic_only", "finding_count": 1, "validated_count": 1,
                "quarantined_count": 0, "context_missing_count": 0, "not_assessable_count": 0,
            },
            "human_decisions": {"status": "not_run", "decisions": []},
            "implementation_coverage": {"status": "not_assessed", "details": []},
            "findings": [finding],
            "limitations": ["Synthetic evaluation fixture only."],
        }

    def evaluated(self, report=None):
        result = evaluate(CATALOG, deepcopy(report or self.report))
        Draft202012Validator(EVALUATION_SCHEMA).validate(result)
        return result

    def test_curated_positive_and_negative_cases_pass(self):
        result = self.evaluated()
        self.assertEqual("pass", result["status"])
        self.assertEqual(1, result["summary"]["required_detected"])
        self.assertEqual(0, result["summary"]["prohibited_triggered"])

    def test_missing_required_finding_fails_without_claiming_global_recall(self):
        report = deepcopy(self.report)
        report["findings"] = []
        result = self.evaluated(report)
        self.assertEqual("fail", result["status"])
        self.assertEqual(0, result["summary"]["required_detected"])
        self.assertIn("not population-level", result["limitations"][-1])

    def test_prohibited_conflict_is_counted(self):
        report = deepcopy(self.report)
        false_positive = deepcopy(report["findings"][0])
        false_positive["finding_id"] = "DCR-SEM-099"
        false_positive["evidence"][0]["locator"]["value"] = "SYN-A-REQ-002"
        false_positive["evidence"][1]["locator"]["value"] = "SYN-B-REQ-002"
        report["findings"].append(false_positive)
        result = self.evaluated(report)
        self.assertEqual("fail", result["status"])
        self.assertEqual(1, result["summary"]["prohibited_triggered"])

    def test_quarantined_finding_is_not_scored_as_detection(self):
        report = deepcopy(self.report)
        report["findings"][0]["disposition"] = "quarantined"
        report["findings"][0]["evidence_status"] = "invalid"
        result = self.evaluated(report)
        self.assertEqual("fail", result["status"])
        self.assertEqual(0, result["summary"]["eligible_finding_count"])

    def test_real_source_report_is_not_scored_against_synthetic_catalog(self):
        report = json.loads((ROOT / "docs/examples/document-consistency-review-phase2-live-pilot-report.json").read_text())
        result = self.evaluated(report)
        self.assertEqual("not_applicable", result["status"])
        self.assertFalse(result["scope_match"])


if __name__ == "__main__":
    unittest.main()
