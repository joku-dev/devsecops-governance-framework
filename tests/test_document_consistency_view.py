"""Public Document Consistency Review projection boundaries."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.document_consistency_view import project_public


class DocumentConsistencyViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / "docs/examples/document-consistency-review-phase2-report.json").read_text())
        cls.manifest = json.loads((ROOT / "docs/examples/document-consistency-review-phase1-source-manifest.json").read_text())

    def test_checked_in_report_projects_current_not_run_state(self):
        result = project_public(ROOT)
        self.assertEqual("not_run", result["overall_status"])
        self.assertEqual("current", result["freshness"]["status"])
        self.assertEqual(2, result["scope"]["source_count"])
        self.assertEqual([], result["findings"])
        self.assertTrue(result["limitations"]["no_consistency_claim"])

    def test_projection_is_an_explicit_allowlist(self):
        report = deepcopy(self.report)
        report["limitations"] = ["CONFIDENTIAL-CANARY-LIMITATION"]
        report["execution"]["provider"] = "CONFIDENTIAL-CANARY-PROVIDER"
        report["execution"]["model"] = "CONFIDENTIAL-CANARY-MODEL"
        result = project_public(ROOT, report=report, manifest=self.manifest)
        rendered = json.dumps(result)
        self.assertNotIn("CONFIDENTIAL-CANARY", rendered)
        self.assertNotIn("provider", result["execution"])
        self.assertNotIn("model", result["execution"])

    def test_semantic_prose_and_evidence_never_enter_public_projection(self):
        report = deepcopy(self.report)
        report["overall_status"] = "synthetic_only"
        report["execution"].update(mode="synthetic_fixture", status="completed")
        report["semantic_review"].update(status="synthetic_only", finding_count=1, validated_count=1)
        report["findings"] = [{
            "finding_id":"DCR-SEM-001", "category":"conflict",
            "statement":"CONFIDENTIAL-CANARY-STATEMENT", "interpretation":"CONFIDENTIAL-CANARY-INTERPRETATION",
            "recommendation":"CONFIDENTIAL-CANARY-RECOMMENDATION", "semantic_state":"proposed", "confidence":0.8,
            "applicability":{"status":"same_context","rationale":"CONFIDENTIAL-CANARY-RATIONALE"},
            "evidence":[{"excerpt":"CONFIDENTIAL-CANARY-EXCERPT"}], "search_scope":None,
            "evidence_status":"valid", "disposition":"unconfirmed", "validation_errors":[]
        }]
        result = project_public(ROOT, report=report, manifest=self.manifest)
        rendered = json.dumps(result)
        self.assertNotIn("CONFIDENTIAL-CANARY", rendered)
        self.assertEqual({"id","category","semantic_state","evidence_status","disposition"}, set(result["findings"][0]))

    def test_manifest_or_source_change_marks_projection_stale(self):
        report = deepcopy(self.report)
        report["scope"]["source_manifest_sha256"] = "f" * 64
        result = project_public(ROOT, report=report, manifest=self.manifest)
        self.assertEqual("stale", result["freshness"]["status"])

    def test_report_source_missing_from_manifest_fails_closed(self):
        manifest = deepcopy(self.manifest)
        manifest["source_documents"] = manifest["source_documents"][:1]
        manifest["source_count"] = 1
        with self.assertRaisesRegex(ValueError, "absent from manifest"):
            project_public(ROOT, report=self.report, manifest=manifest)

    def test_viewer_escapes_values_and_exposes_document_review_route(self):
        source = (ROOT / "apps/governance-viewer/app.js").read_text()
        self.assertIn("function documentReview()", source)
        self.assertIn("esc(item.id)", source)
        self.assertIn("view==='document-review'", source)


if __name__ == "__main__":
    unittest.main()
