from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "collect_architecture_release_input.py"

spec = importlib.util.spec_from_file_location("collect_architecture_release_input", SCRIPT)
collector = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["collect_architecture_release_input"] = collector
spec.loader.exec_module(collector)


class CollectArchitectureReleaseInputTests(unittest.TestCase):
    def test_app_architecture_evidence_templates_validate_against_schema(self):
        schema = json.loads((ROOT / "schemas" / "app-architecture-evidence.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        template_dir = (
            ROOT
            / "pipeline-baseline"
            / "templates"
            / "app-architecture-evidence"
            / ".governance"
            / "architecture"
        )
        template_paths = sorted(template_dir.glob("*.json"))

        self.assertGreaterEqual(len(template_paths), 10)
        for path in template_paths:
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                errors = list(validator.iter_errors(payload))
                self.assertEqual(errors, [])

    def test_collects_neutral_detailed_evidence_report_only(self):
        with tempfile.TemporaryDirectory() as tempdir:
            repo = Path(tempdir)
            (repo / "docs").mkdir()
            (repo / ".governance" / "architecture").mkdir(parents=True)
            (repo / "docs" / "ARCHITECTURE.md").write_text(
                "Architecture exposes a REST API endpoint with explicit ownership.",
                encoding="utf-8",
            )
            (repo / ".governance" / "architecture" / "threat-model.json").write_text(
                json.dumps(
                    {
                        "evidence_type": "threat_model",
                        "status": "approved",
                        "owner": "Security Architect",
                        "evidence_refs": ["docs/ARCHITECTURE.md"],
                    }
                ),
                encoding="utf-8",
            )
            (repo / ".governance" / "architecture" / "interface-contract.json").write_text(
                json.dumps(
                    {
                        "evidence_type": "interface_contract",
                        "status": "reviewed",
                        "owner": "Product Architect",
                        "evidence_refs": ["docs/ARCHITECTURE.md"],
                    }
                ),
                encoding="utf-8",
            )
            (repo / ".governance" / "architecture" / "deployment-manifest.json").write_text(
                json.dumps(
                    {
                        "evidence_type": "deployment_manifest",
                        "status": "reviewed",
                        "owner": "Platform Architect",
                        "evidence_refs": ["docs/DEPLOYMENT.md"],
                    }
                ),
                encoding="utf-8",
            )
            (repo / ".governance" / "architecture" / "model-based-architecture.json").write_text(
                json.dumps(
                    {
                        "evidence_type": "model_based_architecture",
                        "status": "draft",
                        "owner": "Solution Architect",
                        "model_export": "docs/architecture/model-export.pdf",
                        "evidence_refs": ["docs/ARCHITECTURE.md"],
                    }
                ),
                encoding="utf-8",
            )
            (repo / ".governance" / "architecture" / "architecture-review-record.json").write_text(
                json.dumps(
                    {
                        "evidence_type": "architecture_review_record",
                        "status": "reviewed",
                        "owner": "Enterprise Architect",
                        "evidence_refs": ["docs/ARCHITECTURE.md"],
                    }
                ),
                encoding="utf-8",
            )
            (repo / ".governance" / "architecture" / "architecture-exception.json").write_text(
                json.dumps(
                    {
                        "evidence_type": "architecture_exception",
                        "status": "reviewed",
                        "owner": "Architecture Board",
                        "evidence_refs": ["docs/ARCHITECTURE.md"],
                    }
                ),
                encoding="utf-8",
            )

            payload = collector.collect(repo, "test-release", "test-baseline")

        architecture = payload["architecture"]
        detailed = architecture["detailed_evidence"]

        self.assertTrue(detailed["report_only"])
        self.assertEqual(detailed["by_type"]["threat_model"]["coarse_type"], "security_evidence")
        self.assertEqual(
            detailed["by_type"]["interface_contract"]["coarse_type"],
            "release_compatibility_declaration",
        )
        self.assertEqual(detailed["by_type"]["deployment_manifest"]["coarse_type"], "deployment_evidence")
        self.assertEqual(detailed["by_type"]["model_based_architecture"]["coarse_type"], "solution_baseline")
        self.assertEqual(detailed["by_type"]["architecture_review_record"]["coarse_type"], "review_evidence")
        self.assertEqual(detailed["by_type"]["architecture_exception"]["coarse_type"], "exception_evidence")
        self.assertTrue(architecture["security_evidence"]["exists"])
        self.assertTrue(architecture["compatibility_evidence"]["exists"])
        self.assertTrue(architecture["deployment_evidence"]["exists"])
        self.assertTrue(architecture["review_evidence"]["exists"])
        self.assertTrue(architecture["exception_evidence"]["exists"])

        marker_scores = {item["id"]: item["score"] for item in architecture["marker_assessments"]}
        self.assertEqual(marker_scores["E6"], 4)
        self.assertEqual(marker_scores["S5"], 4)
        self.assertEqual(marker_scores["P8"], 4)


if __name__ == "__main__":
    unittest.main()
