from pathlib import Path
import json
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SourceDocumentRequirementDeltaTests(unittest.TestCase):
    @staticmethod
    def run_command(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def test_source_document_requirement_delta_is_generated(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_source_document_requirement_delta.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        output_json = ROOT / "generated" / "reports" / "source-document-requirement-delta.json"
        output_md = ROOT / "generated" / "reports" / "source-document-requirement-delta.md"
        self.assertTrue(output_json.exists())
        self.assertTrue(output_md.exists())

        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["decision"]["current_state"], "review_support_only")
        self.assertEqual(payload["decision"]["runtime_governance_changed"], False)
        self.assertEqual(payload["decision"]["candidate_promoted"], False)
        self.assertEqual(payload["decision"]["stricter_rules_enabled"], False)
        self.assertEqual(payload["summary"]["replacement_pairs"], 2)

        intake_inventory = payload["requirement_intake_inventory"]
        inventory_summary = intake_inventory["summary"]
        self.assertEqual(inventory_summary["registered_source_documents"], 15)
        self.assertEqual(inventory_summary["scanned_source_documents"], 14)
        self.assertEqual(inventory_summary["skipped_source_documents"], 1)
        self.assertEqual(
            inventory_summary["identification_counts"]["author_identified"],
            0,
        )
        self.assertEqual(
            inventory_summary["identification_counts"]["extraction_row_id"],
            sum(
                source["identification_counts"]["extraction_row_id"]
                for source in intake_inventory["sources"]
            ),
        )
        self.assertEqual(
            inventory_summary["identification_counts"]["inferred_candidate"],
            len(intake_inventory["inferred_candidates"]),
        )
        self.assertEqual(inventory_summary["inferred_candidate_count"], 0)
        self.assertEqual(intake_inventory["inferred_candidates"], [])
        self.assertEqual(inventory_summary["extraction_mode"], "explicit_identifiers_only")
        self.assertEqual(inventory_summary["extraction_row_id_count"], 0)
        self.assertEqual(inventory_summary["explicit_identifier_count"], 46)
        sources = {source["source_id"]: source for source in intake_inventory["sources"]}
        self.assertEqual(sources["DSCB-STD-REQ-001"]["identification_counts"]["explicit_identifier"], 46)
        self.assertEqual(sources["PRA-STD-REQ-001"]["identification_counts"]["explicit_identifier"], 0)
        self.assertEqual(len(payload["requirement_delta_pairs"]), 2)
        for pair in payload["requirement_delta_pairs"]:
            # Neither replacement pair contains explicit declarations. An empty
            # comparison must not revive the former keyword-based extraction.
            self.assertEqual(pair["summary"]["candidate_requirements"], 0)
            self.assertEqual(pair["summary"]["target_requirements"], 0)
            self.assertEqual(pair["deltas"], [])
        markdown = output_md.read_text(encoding="utf-8")
        self.assertIn("Source Document Requirement Delta", markdown)
        self.assertNotIn("inferred_candidate (P2)", markdown)
        self.assertIn("## Requirement Intake Identification", markdown)
        self.assertIn("explicit_identifiers_only", markdown)
        self.assertIn("Confirmed source-author identifiers (P1): `0`", markdown)
        self.assertIn("Explicit requirement identifiers with unverified origin: `46`", markdown)
