from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from jsonschema import Draft202012Validator

from scripts.evaluate_document_consistency_semantic_report import evaluate
from scripts.adapt_document_consistency_provider_response import adapt_provider_response
from scripts.validate_document_consistency_semantic_review import validate_semantic_response


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/document-consistency-review-semantic-v2"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
MANIFEST_SHA256 = hashlib.sha256((FIXTURES / "manifest.json").read_bytes()).hexdigest()
CATALOG = json.loads((ROOT / "model/governance/document-consistency/semantic-evaluation-catalog-v2.json").read_text(encoding="utf-8"))
ADAPTER_CONFIG = json.loads((ROOT / "model/governance/document-consistency/provider-adapter-config-v1.json").read_text(encoding="utf-8"))


def evidence(evidence_id: str, source_id: str, locator: str, excerpt: str) -> dict:
    source = next(item for item in MANIFEST["source_documents"] if item["id"] == source_id)
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "content_sha256": source["content_sha256"],
        "locator": {"type": "requirement_id", "value": locator},
        "excerpt": excerpt,
    }


def finding(finding_id: str, state: str, applicability: str, evidence_items: list[dict]) -> dict:
    return {
        "finding_id": finding_id,
        "category": "conflict",
        "statement": "Synthetic case output only.",
        "interpretation": "Synthetic fixture interpretation only.",
        "recommendation": "Synthetic fixture recommendation.",
        "semantic_state": state,
        "confidence": 0.5,
        "applicability": {"status": applicability, "rationale": "Synthetic test rationale."},
        "evidence": evidence_items,
        "search_scope": None,
    }


class DocumentConsistencySemanticCatalogV2Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for name in (
            "document-consistency-review-manifest.schema.json",
            "document-consistency-semantic-response.schema.json",
            "document-consistency-semantic-report.schema.json",
            "document-consistency-semantic-evaluation-report.schema.json",
            "document-consistency-semantic-evaluation-catalog.schema.json",
        ):
            target = self.root / "schemas" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "schemas" / name, target)
        source_root = self.root / "docs/governance/source-documents"
        source_root.mkdir(parents=True)
        for source in MANIFEST["source_documents"]:
            shutil.copy2(FIXTURES / source["source_path"], self.root / source["source_path"])
        register_path = self.root / MANIFEST["source_register_path"]
        register_path.parent.mkdir(parents=True)
        shutil.copy2(FIXTURES / "model/documents/source-document-register.yaml", register_path)

    def tearDown(self):
        self.temporary.cleanup()

    def response(self, findings: list[dict]) -> dict:
        projection_findings = deepcopy(findings)
        for item in projection_findings:
            item["search_scope"] = {"status": "not_applicable", "source_ids": [], "method": "", "limitations": []}
        projection = {
            "schema_version": "1.0.0",
            "response_type": "document_consistency_provider_projection",
            "findings": projection_findings,
            "limitations": ["Synthetic provider-projection fixture; no provider was called."],
        }
        response = adapt_provider_response(
            projection,
            ADAPTER_CONFIG,
            review_id="dcr-catalog-v2-local-simulation",
            source_manifest_sha256=MANIFEST_SHA256,
            provider="synthetic-fixture-only",
            model="synthetic-fixture-only",
            prompt_version="synthetic-catalog-v2",
        )
        # The adapter normally binds a live provider. This test-only projection
        # fixture is explicitly rebound to synthetic mode before validation.
        response["execution"].update(mode="synthetic_fixture", provider=None, model=None)
        response["limitations"].append("Local synthetic simulation; no provider was called.")
        return response

    def validated_and_evaluated(self, response: dict) -> tuple[dict, dict]:
        report = validate_semantic_response(self.root, MANIFEST, response, MANIFEST_SHA256)
        report_schema = json.loads((self.root / "schemas/document-consistency-semantic-report.schema.json").read_text())
        Draft202012Validator(report_schema).validate(report)
        result = evaluate(CATALOG, report)
        evaluation_schema = json.loads((self.root / "schemas/document-consistency-semantic-evaluation-report.schema.json").read_text())
        Draft202012Validator(evaluation_schema).validate(result)
        return report, result

    def test_expected_conflict_and_context_missing_case_pass_offline(self):
        clear_conflict = finding("DCR-SEM-101", "proposed", "same_context", [
            evidence("EVID-001", "SYN-SRC-C-001", "SYN-C-REQ-004", "Release records SHALL be retained for at least 90 days."),
            evidence("EVID-002", "SYN-SRC-D-001", "SYN-D-REQ-004", "Release records MUST be deleted after 30 days."),
        ])
        context_missing = finding("DCR-SEM-103", "context_missing", "unknown", [
            evidence("EVID-003", "SYN-SRC-C-001", "SYN-C-REQ-002", "Emergency deployments MAY proceed before a second approval when an incident commander authorizes the action."),
            evidence("EVID-004", "SYN-SRC-D-001", "SYN-D-REQ-002", "Urgent operations MAY proceed before approval during an active incident."),
        ])
        report, result = self.validated_and_evaluated(self.response([clear_conflict, context_missing]))

        self.assertEqual("pass", report["formal_validation"]["status"])
        self.assertEqual(["unconfirmed", "context_missing"], [item["disposition"] for item in report["findings"]])
        self.assertEqual("pass", result["status"])
        self.assertEqual({"case_count": 4, "passed": 4, "failed": 0, "required_detected": 1, "required_total": 1, "prohibited_triggered": 0, "eligible_finding_count": 2}, result["summary"])

    def test_missing_conflict_evidence_is_quarantined_and_does_not_pass_positive_case(self):
        incomplete_conflict = finding("DCR-SEM-101", "proposed", "same_context", [
            evidence("EVID-001", "SYN-SRC-C-001", "SYN-C-REQ-004", "Release records SHALL be retained for at least 90 days."),
        ])
        report, result = self.validated_and_evaluated(self.response([incomplete_conflict]))

        self.assertEqual("quarantined", report["findings"][0]["disposition"])
        positive = next(item for item in result["cases"] if item["case_id"] == "DCR-EVAL-101")
        self.assertEqual("fail", positive["result"])
        self.assertEqual("fail", result["status"])


if __name__ == "__main__":
    unittest.main()
