from pathlib import Path
import json
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SourceDocumentIntakeReviewBriefTests(unittest.TestCase):
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

    def test_source_document_intake_review_briefs_are_generated(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_source_document_intake_review_briefs.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        output_json = ROOT / "generated" / "reports" / "source-document-intake-review-briefs.json"
        output_md = ROOT / "generated" / "reports" / "source-document-intake-review-briefs.md"
        self.assertTrue(output_json.exists())
        self.assertTrue(output_md.exists())

        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["decision"]["current_state"], "decision_support_only")
        self.assertEqual(payload["decision"]["autonomous_decisions_enabled"], False)
        self.assertEqual(payload["decision"]["runtime_governance_changed"], False)
        self.assertEqual(payload["summary"]["review_briefs"], 7)
        self.assertEqual(payload["summary"]["human_decision_required"], 7)

        briefs_by_source = {
            brief["source_document"]["id"]: brief
            for brief in payload["review_briefs"]
        }
        replacement_brief = briefs_by_source["ARCH-GOV-SRC-002"]
        self.assertEqual(replacement_brief["prepared_by_agent"], "source-document-intake")
        self.assertEqual(replacement_brief["autonomous_decision"], False)
        self.assertEqual(replacement_brief["review_focus"], "replacement decision")

        option_ids = {option["option"] for option in replacement_brief["decision_options"]}
        self.assertIn("replacement_confirmed", option_ids)
        self.assertIn("related_source_keep_candidate", option_ids)
        self.assertIn("duplicate_or_not_relevant_retire", option_ids)
        self.assertIn("Source Document Intake Review Briefs", output_md.read_text(encoding="utf-8"))
