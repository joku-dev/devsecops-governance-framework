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
        cls.report = json.loads((ROOT / "docs/examples/document-consistency-review-phase2-live-pilot-report.json").read_text())
        cls.manifest = json.loads((ROOT / "docs/examples/document-consistency-review-phase1-source-manifest.json").read_text())

    def test_one_time_public_snapshot_is_redacted_and_fresh(self):
        result = project_public(ROOT)
        self.assertEqual("partial", result["overall_status"])
        self.assertEqual("dcr-codex-once-2026-10-09", result["review_id"])
        self.assertEqual("completed", result["execution"]["status"])
        self.assertEqual("recorded_locally_details_withheld", result["sections"]["human_decisions"])
        self.assertEqual("not_assessed", result["sections"]["implementation_coverage"])
        self.assertEqual("current", result["freshness"]["status"])
        self.assertEqual(10, result["scope"]["source_count"])
        self.assertEqual([], result["scope"]["source_ids"])
        self.assertEqual([], result["documents"])
        self.assertEqual(10, result["coverage"]["source_population_count"])
        self.assertEqual(10, result["coverage"]["in_scope_source_count"])
        self.assertEqual(0, result["coverage"]["omitted_source_count"])
        self.assertEqual("complete", result["coverage"]["source_scope_status"])
        self.assertEqual(310, result["coverage"]["section_count"])
        self.assertEqual(310, result["coverage"]["structurally_inventoried_section_count"])
        self.assertIsNone(result["coverage"]["semantically_assessed_section_count"])
        self.assertEqual("not_measured", result["coverage"]["semantic_section_coverage_status"])
        self.assertEqual(2138, result["coverage"]["requirement_count"])
        self.assertEqual(2138, result["coverage"]["structurally_inventoried_requirement_count"])
        self.assertIsNone(result["coverage"]["semantically_assessed_requirement_count"])
        self.assertEqual("not_measured", result["coverage"]["semantic_item_coverage_status"])
        self.assertEqual("partial", result["coverage"]["semantic_review_status"])
        self.assertEqual(3, result["semantic_comparison_coverage"]["assessed_count"])
        self.assertIsNone(result["semantic_comparison_coverage"]["population_count"])
        self.assertEqual("recorded_locally_details_withheld", result["sections"]["human_decisions"])
        self.assertEqual(3, len(result["findings"]))
        self.assertTrue(result["limitations"]["no_consistency_claim"])

    def test_checked_in_pilot_report_projects_completed_review_state(self):
        result = project_public(ROOT, report=self.report, manifest=self.manifest)
        self.assertEqual("dcr-semantic-pilot-20261007-run2", result["review_id"])
        self.assertEqual("partial", result["overall_status"])
        self.assertEqual("completed", result["execution"]["status"])
        self.assertEqual("partial", result["sections"]["semantic_review"])
        self.assertEqual("not_run", result["sections"]["human_decisions"])
        self.assertEqual("not_assessed", result["sections"]["implementation_coverage"])

    def test_checked_in_example_remains_available_as_explicit_projection(self):
        example = json.loads((ROOT / "docs/examples/document-consistency-review-phase2-report.json").read_text())
        result = project_public(ROOT, report=example, manifest=self.manifest)
        self.assertEqual("not_run", result["overall_status"])
        self.assertEqual(2, result["scope"]["source_count"])

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

    def test_report_scope_outside_registered_requirements_population_fails_closed(self):
        report = deepcopy(self.report)
        manifest = deepcopy(self.manifest)
        source = deepcopy(manifest["source_documents"][0])
        source["id"] = "UNREGISTERED-SRC-001"
        report["scope"]["source_ids"][0] = source["id"]
        manifest["source_documents"].append(source)
        manifest["source_count"] += 1
        with self.assertRaisesRegex(ValueError, "outside the tracked requirements population"):
            project_public(ROOT, report=report, manifest=manifest)

    def test_viewer_escapes_values_and_exposes_document_review_route(self):
        source = (ROOT / "apps/governance-viewer/app.js").read_text()
        self.assertIn("function documentReview()", source)
        self.assertIn("esc(item.id)", source)
        self.assertIn("view==='document-review'", source)


if __name__ == "__main__":
    unittest.main()
