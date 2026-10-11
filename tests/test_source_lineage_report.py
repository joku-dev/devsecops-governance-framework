import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_source_lineage_report.py"
SPEC = importlib.util.spec_from_file_location("generate_source_lineage_report", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_governance_repo", ROOT / "scripts" / "validate_governance_repo.py"
)
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


class SourceLineageReportTests(unittest.TestCase):
    def test_inventory_comes_from_register_and_all_registered_files_exist(self):
        report = MODULE.build_report()

        register = MODULE.load_yaml(ROOT / "model" / "documents" / "source-document-register.yaml")
        self.assertEqual(report["summary"]["source_document_count"], len(register["documents"]))
        self.assertEqual(report["summary"]["missing_registered_source_count"], 0)
        self.assertEqual(report["summary"]["unregistered_source_file_count"], 0)
        self.assertTrue(all(item["exists"] for item in report["source_documents"]))

    def test_shared_intake_outputs_are_not_counted_as_source_derivations(self):
        report = MODULE.build_report()
        shared_paths = {item["path"] for item in report["shared_intake_outputs"]}
        linked_paths = {
            artifact["artifact_path"]
            for source in report["lineage"]
            for artifact in source["derived_artifacts"]
        }

        self.assertTrue(shared_paths)
        self.assertTrue(shared_paths.isdisjoint(linked_paths))

    def test_unregistered_historical_source_reference_is_explicit(self):
        report = MODULE.build_report()
        references = {item["path"]: item for item in report["unresolved_source_references"]}
        historical_path = "docs/governance/source-documents/ARCH-SDD-SRC-001.public.md"

        self.assertIn(historical_path, references)
        self.assertFalse(references[historical_path]["exists"])
        self.assertEqual(len(references[historical_path]["referenced_by"]), 5)

    def test_source_inventory_discrepancies_are_report_only_for_validator(self):
        report = {
            "summary": {
                "missing_derived_artifacts": 0,
                "missing_registered_source_count": 1,
                "unregistered_source_file_count": 1,
            }
        }
        errors = []
        completed = SimpleNamespace(returncode=0, stderr="", stdout="")

        with (
            patch.object(VALIDATOR.subprocess, "run", return_value=completed),
            patch.object(VALIDATOR, "load_json", return_value=report),
        ):
            result = VALIDATOR.validate_source_lineage_report(errors)

        self.assertEqual(result, report)
        self.assertEqual(errors, [])

    def test_missing_derived_artifacts_remain_a_validator_error(self):
        report = {"summary": {"missing_derived_artifacts": 1}}
        errors = []
        completed = SimpleNamespace(returncode=0, stderr="", stdout="")

        with (
            patch.object(VALIDATOR.subprocess, "run", return_value=completed),
            patch.object(VALIDATOR, "load_json", return_value=report),
        ):
            VALIDATOR.validate_source_lineage_report(errors)

        self.assertEqual(errors, ["Source lineage report contains missing derived artifacts"])


if __name__ == "__main__":
    unittest.main()
