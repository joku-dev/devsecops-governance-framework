from pathlib import Path
import json
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SourceDocumentIntakeStatusTests(unittest.TestCase):
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

    def test_source_document_intake_status_is_generated(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_source_document_intake_status.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        output_json = ROOT / "generated" / "reports" / "source-document-intake-status.json"
        output_md = ROOT / "generated" / "reports" / "source-document-intake-status.md"
        self.assertTrue(output_json.exists())
        self.assertTrue(output_md.exists())

        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["registered_source_documents"], 20)
        self.assertEqual(payload["summary"]["status_counts"]["candidate"], 5)
        self.assertEqual(payload["summary"]["status_counts"]["intake"], 10)
        self.assertEqual(payload["summary"]["status_counts"]["review"], 3)
        self.assertEqual(payload["summary"]["replacement_review_items"], 1)
        self.assertEqual(payload["decision"]["runtime_governance_changed"], False)
        self.assertEqual(payload["decision"]["stricter_rules_enabled"], False)

        document_ids = {item["id"] for item in payload["documents"]}
        self.assertIn("ARCH-GOV-SRC-002", document_ids)
        open_ids = {item["id"] for item in payload["open_items"]}
        self.assertIn("ARCH-GOV-SRC-002", open_ids)
        self.assertIn("Source Document Intake Status", output_md.read_text(encoding="utf-8"))
