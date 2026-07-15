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
        self.assertEqual(payload["summary"]["replacement_pairs"], 1)

        pair = payload["requirement_delta_pairs"][0]
        self.assertEqual(pair["candidate_id"], "ARCH-GOV-SRC-002")
        self.assertEqual(pair["target_id"], "ARCH-SDD-SRC-001")
        self.assertGreater(pair["summary"]["candidate_requirements"], 0)
        self.assertGreater(pair["summary"]["target_requirements"], 0)
        self.assertGreater(pair["summary"]["differences_requiring_review"], 0)
        self.assertIn("changed", pair["summary"]["status_counts"])
        self.assertIn("removed", pair["summary"]["status_counts"])
        self.assertIn("Source Document Requirement Delta", output_md.read_text(encoding="utf-8"))
