from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

import yaml


ROOT = Path(__file__).resolve().parents[1]


class HarmonizedRequirementsCandidateTests(unittest.TestCase):
    def setUp(self):
        self.model = yaml.safe_load(
            (ROOT / "model" / "requirements" / "harmonized-devsecops-requirements.yaml").read_text(encoding="utf-8")
        )
        self.mapping = yaml.safe_load(
            (ROOT / "model" / "traceability" / "standards-to-harmonized-requirements.yaml").read_text(encoding="utf-8")
        )
        self.report = json.loads(
            (ROOT / "generated" / "reports" / "harmonized-requirements-coverage.json").read_text(encoding="utf-8")
        )
        self.maturity_mapping = yaml.safe_load(
            (ROOT / "model" / "traceability" / "harmonized-requirements-to-maturity-levels.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.maturity_report = json.loads(
            (ROOT / "generated" / "reports" / "harmonized-requirements-maturity.json").read_text(encoding="utf-8")
        )

    def test_candidate_cannot_authorize_runtime_governance(self):
        self.assertEqual(self.model["status"], "candidate")
        self.assertFalse(self.model["normative"])
        self.assertEqual(self.model["enforcement"], "none")
        self.assertEqual(self.model["derivation_policy"], "review_only")
        self.assertFalse(any(self.report["decision_boundary"].values()))

    def test_every_source_and_harmonized_requirement_is_mapped(self):
        mappings = self.mapping["mappings"]
        self.assertEqual(self.mapping["summary"]["mapped_source_requirements"], len(mappings))
        self.assertEqual(self.mapping["summary"]["unmapped_source_requirements"], 0)
        known = {item["id"] for item in self.model["requirements"]}
        referenced = {target for item in mappings for target in item["harmonized_requirement_ids"]}
        self.assertEqual(referenced, known)
        self.assertTrue(all(item["review_status"] == "human_review_required" for item in mappings))

    def test_public_mapping_contains_no_source_requirement_text(self):
        self.assertFalse(self.mapping["public_source_text_included"])
        forbidden_keys = {"source_text", "original_text", "description", "title"}
        for item in self.mapping["mappings"]:
            self.assertFalse(forbidden_keys & set(item))

    def test_coverage_summary_is_derived_from_candidate_model(self):
        requirements = self.model["requirements"]
        for status in ("covered", "partial", "gap"):
            expected = sum(item["coverage"]["status"] == status for item in requirements)
            self.assertEqual(self.report["summary"][status], expected)
        source_total = self.report["summary"]["source_requirements"]
        classified = sum(self.report["summary"][f"source_{status}"] for status in ("covered", "partial", "gap"))
        self.assertEqual(classified, source_total)
        self.assertGreaterEqual(self.report["summary"]["weighted_design_coverage_pct"], 0)
        self.assertLessEqual(self.report["summary"]["weighted_design_coverage_pct"], 100)

    def test_hygiene_scanner_checks_text_and_office_metadata(self):
        scanner = ROOT / "scripts" / "check_public_artifact_hygiene.py"
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            clean = temp / "clean.md"
            clean.write_text("Public neutral content\n", encoding="utf-8")
            clean_result = subprocess.run(
                ["python3", str(scanner), "--forbidden-term", "PrivateCorp", str(clean)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(clean_result.returncode, 0, clean_result.stdout + clean_result.stderr)

            office = temp / "metadata.xlsx"
            with ZipFile(office, "w") as archive:
                archive.writestr("xl/worksheets/sheet1.xml", "<worksheet>Public neutral</worksheet>")
                archive.writestr("xl/tables/table1.xml", "<table displayName='PrivateCorpRequirements'/>")
            failed_result = subprocess.run(
                ["python3", str(scanner), "--forbidden-term", "PrivateCorp", str(office)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed_result.returncode, 1)
            self.assertIn("xl/tables/table1.xml", failed_result.stdout)

    def test_registered_source_uses_related_source_review_state(self):
        intake = json.loads(
            (ROOT / "generated" / "reports" / "source-document-intake-status.json").read_text(encoding="utf-8")
        )
        item = next(entry for entry in intake["documents"] if entry["id"] == "CISO-REQ-SRC-001")
        self.assertEqual(item["review_state"], "candidate_related_source_review_required")
        self.assertEqual(item["similarity_assessment"], "related_source")
        self.assertEqual(item["candidate_replacement_for"], [])

        impact = json.loads(
            (ROOT / "generated" / "reports" / "governance-change-impact.json").read_text(encoding="utf-8")
        )
        impact_item = next(entry for entry in impact["source_impacts"] if entry["id"] == "CISO-REQ-SRC-001")
        self.assertEqual(impact_item["source_state"], "candidate_related_source_review")

    def test_every_harmonized_requirement_has_a_candidate_maturity_assignment(self):
        known = {item["id"] for item in self.model["requirements"]}
        assignments = self.maturity_mapping["mappings"]
        assigned = {item["requirement_id"] for item in assignments}
        self.assertEqual(assigned, known)
        self.assertEqual(len(assignments), len(assigned))
        self.assertTrue(all(item["review_status"] == "human_review_required" for item in assignments))

    def test_maturity_paths_are_cumulative_and_governance_is_separate(self):
        expected_paths = {
            "L1": ["L1", "L2", "L3"],
            "L2": ["L2", "L3"],
            "L3": ["L3"],
            "GOV": ["GOV"],
        }
        for item in self.maturity_mapping["mappings"]:
            self.assertEqual(item["maturity_path"], expected_paths[item["minimum_level"]])
            self.assertEqual(item["governance_overlay"], item["minimum_level"] == "GOV")

    def test_maturity_report_is_derived_and_non_authorizing(self):
        assignments = self.maturity_mapping["mappings"]
        summary = self.maturity_report["summary"]
        self.assertEqual(summary["harmonized_requirements"], len(assignments))
        for level in ("L1", "L2", "L3", "GOV"):
            self.assertEqual(
                summary["minimum_level_counts"][level],
                sum(item["minimum_level"] == level for item in assignments),
            )
            self.assertEqual(
                summary["cumulative_level_counts"][level],
                sum(level in item["maturity_path"] for item in assignments),
            )
        self.assertEqual(summary["human_review_required"], len(assignments))
        self.assertFalse(any(self.maturity_report["decision_boundary"].values()))


if __name__ == "__main__":
    unittest.main()
