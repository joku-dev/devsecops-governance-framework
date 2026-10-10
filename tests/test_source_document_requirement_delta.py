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
            sum(
                source["identification_counts"]["author_identified"]
                for source in intake_inventory["sources"]
            ),
        )
        self.assertEqual(
            inventory_summary["identification_counts"]["inferred_candidate"],
            len(intake_inventory["inferred_candidates"]),
        )
        self.assertGreater(inventory_summary["inferred_candidate_count"], 0)
        self.assertTrue(
            all(
                item["identification_class"] == "inferred_candidate"
                and item["intake_priority"] == "p2"
                and item["source_path"]
                and item["line"] > 0
                for item in intake_inventory["inferred_candidates"]
            )
        )

        pairs = {
            (pair["candidate_id"], pair["target_id"]): pair
            for pair in payload["requirement_delta_pairs"]
        }
        pair = pairs[("ARCH-GOV-REQ-001", "ARCH-SDD-REQ-001")]
        self.assertGreater(pair["summary"]["candidate_requirements"], 0)
        self.assertGreater(pair["summary"]["target_requirements"], 0)
        self.assertEqual(
            pair["summary"]["candidate_identification_counts"].get("author_identified"),
            pair["summary"]["candidate_requirements"],
        )
        self.assertEqual(
            pair["summary"]["target_identification_counts"].get("author_identified"),
            pair["summary"]["target_requirements"],
        )
        self.assertGreater(pair["summary"]["differences_requiring_review"], 0)
        self.assertIn("changed", pair["summary"]["status_counts"])
        self.assertIn("removed", pair["summary"]["status_counts"])
        policy_pair = pairs[("DEVSECOPS-POL-CAND-002", "DEVSECOPS-POL-REQ-001")]
        self.assertGreater(
            policy_pair["summary"]["candidate_identification_counts"].get("inferred_candidate", 0),
            0,
        )
        self.assertGreater(
            policy_pair["summary"]["target_identification_counts"].get("author_identified", 0),
            0,
        )
        inferred_delta = next(
            item
            for item in policy_pair["deltas"]
            if item.get("candidate_requirement")
            and item["candidate_requirement"]["identification_class"] == "inferred_candidate"
        )
        self.assertEqual(inferred_delta["candidate_requirement"]["intake_priority"], "p2")
        markdown = output_md.read_text(encoding="utf-8")
        self.assertIn("Source Document Requirement Delta", markdown)
        self.assertIn("inferred_candidate (P2)", markdown)
        self.assertIn("## Requirement Intake Identification", markdown)
        self.assertIn("### `inferred_candidate` Prose Findings", markdown)
