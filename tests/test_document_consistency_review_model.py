from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from jsonschema import Draft202012Validator

from scripts.generate_document_consistency_review_model import generate_model
from scripts.generate_document_consistency_review_model import extract_requirement_rows
from scripts.validate_document_consistency_review import validate_model


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "docs/examples/document-consistency-review-phase1-source-manifest.json").read_text())
BASE_MODEL = json.loads((ROOT / "docs/examples/document-consistency-review-phase1-model.json").read_text())
MODEL_SCHEMA = json.loads((ROOT / "schemas/document-consistency-review-model.schema.json").read_text())


class DocumentConsistencyReviewModelTests(unittest.TestCase):
    def run_model(self, model: dict, manifest: dict | None = None) -> dict:
        Draft202012Validator(MODEL_SCHEMA).validate(model)
        return validate_model(ROOT, deepcopy(manifest or MANIFEST), model)

    @staticmethod
    def rule(report: dict, rule_id: str) -> dict:
        return next(item for item in report["rules"] if item["rule_id"] == rule_id)

    def test_bounded_source_inventory_reports_stale_register_snapshot(self):
        report = self.run_model(deepcopy(BASE_MODEL))
        self.assertEqual(report["overall_status"], "fail")
        self.assertEqual(report["semantic_review"], "not_run")
        for rule_id in ("DCR-001", "DCR-007"):
            self.assertEqual(self.rule(report, rule_id)["status"], "pass")
        self.assertEqual(self.rule(report, "DCR-002")["status"], "fail")
        self.assertIn("source register bytes differ", self.rule(report, "DCR-002")["details"][0])
        self.assertEqual(self.rule(report, "DCR-009")["status"], "fail")
        self.assertIn("source register snapshot is stale", self.rule(report, "DCR-009")["details"])
        for rule_id in ("DCR-003", "DCR-005", "DCR-006", "DCR-008"):
            self.assertEqual(self.rule(report, rule_id)["status"], "not_in_scope")
        self.assertEqual(self.rule(report, "DCR-004")["status"], "pass")
        self.assertIn("explicit scope gap", self.rule(report, "DCR-004")["details"][0])

    def test_generator_extracts_requirement_structure_without_prose(self):
        model = generate_model(ROOT, deepcopy(MANIFEST))
        self.assertEqual(len(model["requirements"]), 111)
        mandatory = [item for item in model["requirements"] if item["mandatory"]]
        self.assertTrue(mandatory)
        self.assertTrue(all(item["open_gap"] for item in mandatory))
        self.assertTrue(model["relationships"])
        self.assertTrue(all(item["status"] == "candidate" for item in model["relationships"]))
        all_ids = {item["id"] for source in model["sources"] for item in source["identifiers"]}
        all_ids.update(item["id"] for item in model["requirements"])
        self.assertTrue(all(item["target_entity_id"] in all_ids for item in model["relationships"]))
        serialized = json.dumps(model)
        self.assertNotIn("controlled and repeatable software delivery", serialized)
        self.assertNotIn("All software components SHALL be traceable", serialized)

    def test_generator_covers_should_rows_and_opaque_sections(self):
        source = ROOT / "docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md"
        requirements, _ = extract_requirement_rows("ARCH-SDD-REQ-001", source)
        self.assertEqual(938, len(requirements))
        should_rows = [item for item in requirements if item["strength"] == "SHOULD"]
        self.assertEqual(345, len(should_rows))
        self.assertTrue(all(item["section_ref"].startswith("SEC-") for item in requirements))
        self.assertTrue(all(item["mandatory"] for item in requirements if item["strength"] in {"MUST", "SHALL"}))
        self.assertTrue(all(not item["mandatory"] for item in should_rows))

    def test_duplicate_stable_identifier_fails_dcr_001(self):
        model = deepcopy(BASE_MODEL)
        duplicate = deepcopy(model["sources"][0]["identifiers"][0])
        model["sources"][1]["identifiers"].append(duplicate)
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-001")["status"], "fail")

    def test_unresolved_source_reference_fails_dcr_001(self):
        model = deepcopy(BASE_MODEL)
        model["derivation_relationships"].append(
            {"source_id": "UNKNOWN-SRC-001", "target_id": "MODEL-ITEM-001", "status": "candidate"}
        )
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-001")["status"], "fail")

    def test_reference_mention_does_not_define_its_own_target(self):
        model = deepcopy(BASE_MODEL)
        model["relationships"].append(
            {
                "type": "references",
                "source_entity_id": model["requirements"][0]["id"],
                "target_entity_id": "UNKNOWN-REQ-999",
                "source_document_id": MANIFEST["source_documents"][0]["id"],
                "status": "candidate",
            }
        )
        model["sources"][0]["identifiers"].append(
            {"id": "UNKNOWN-REQ-999", "line": 99, "kind": "reference"}
        )
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-001")["status"], "fail")

    def test_unresolved_role_reference_fails_dcr_003(self):
        model = deepcopy(BASE_MODEL)
        model["requirements"].append(
            {
                "id": "REQ-TEST-001",
                "source_id": MANIFEST["source_documents"][0]["id"],
                "mandatory": False,
                "owner_role_id": "MISSING-ROLE",
                "verification_artifact_id": None,
                "open_gap": "Owner mapping remains to be decided.",
            }
        )
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-003")["status"], "fail")

    def test_mandatory_requirement_needs_verification_or_explicit_gap(self):
        model = deepcopy(BASE_MODEL)
        model["requirements"].append(
            {
                "id": "REQ-TEST-002",
                "source_id": MANIFEST["source_documents"][0]["id"],
                "mandatory": True,
                "owner_role_id": None,
                "verification_artifact_id": None,
                "open_gap": None,
            }
        )
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-004")["status"], "fail")

    def test_gate_requires_inputs_outputs_and_owner_or_open_gap(self):
        model = deepcopy(BASE_MODEL)
        model["gates"].append(
            {
                "id": "GATE-TEST-001",
                "source_id": MANIFEST["source_documents"][0]["id"],
                "input_artifact_ids": [],
                "output_artifact_ids": [],
                "decision_owner_role_id": None,
                "open_gap": None,
            }
        )
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-005")["status"], "fail")

    def test_evidence_links_must_resolve(self):
        model = deepcopy(BASE_MODEL)
        model["evidence_links"].append({"requirement_id": "REQ-MISSING-001", "artifact_id": "ART-MISSING-001"})
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-006")["status"], "fail")

    def test_candidate_source_cannot_have_accepted_derivation(self):
        manifest = deepcopy(MANIFEST)
        candidate_id = manifest["source_documents"][0]["id"]
        manifest["source_documents"][0]["status"] = "candidate"
        model = deepcopy(BASE_MODEL)
        model["sources"][0]["status"] = "candidate"
        model["derivation_relationships"].append(
            {"source_id": candidate_id, "target_id": "GOVERNANCE-ARTIFACT-001", "status": "accepted"}
        )
        report = self.run_model(model, manifest)
        self.assertEqual(self.rule(report, "DCR-007")["status"], "fail")

    def test_candidate_source_cannot_have_confirmed_relationship(self):
        manifest = deepcopy(MANIFEST)
        source = manifest["source_documents"][0]
        source["status"] = "candidate"
        model = deepcopy(BASE_MODEL)
        model["sources"][0]["status"] = "candidate"
        artifact_id = "ART-TEST-001"
        model["artifacts"].append({"id": artifact_id, "source_id": source["id"], "kind": "synthetic"})
        model["relationships"].append(
            {
                "type": "implements",
                "source_entity_id": model["sources"][0]["identifiers"][0]["id"],
                "target_entity_id": artifact_id,
                "source_document_id": source["id"],
                "status": "confirmed",
            }
        )
        report = self.run_model(model, manifest)
        self.assertEqual(self.rule(report, "DCR-007")["status"], "fail")

    def test_ambiguous_topic_authority_requires_open_decision(self):
        model = deepcopy(BASE_MODEL)
        model["topic_authorities"].append(
            {
                "topic": "synthetic-topic",
                "source_ids": [item["id"] for item in MANIFEST["source_documents"]],
                "decision_open": False,
            }
        )
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-008")["status"], "fail")

    def test_changed_source_hash_is_stale(self):
        model = deepcopy(BASE_MODEL)
        model["sources"][0]["sha256"] = "0" * 64
        report = self.run_model(model)
        self.assertEqual(self.rule(report, "DCR-002")["status"], "fail")
        self.assertEqual(self.rule(report, "DCR-009")["status"], "fail")

    def test_newer_repository_commit_does_not_stale_unchanged_source_snapshot(self):
        manifest = deepcopy(MANIFEST)
        register_path = ROOT / manifest["source_register_path"]
        manifest["source_register_sha256"] = hashlib.sha256(register_path.read_bytes()).hexdigest()
        report = self.run_model(deepcopy(BASE_MODEL), manifest)
        self.assertEqual(self.rule(report, "DCR-009")["status"], "pass")
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if MANIFEST["reviewed_commit"] != head:
            self.assertIn("newer than the recorded source snapshot", self.rule(report, "DCR-009")["details"][0])


if __name__ == "__main__":
    unittest.main()
