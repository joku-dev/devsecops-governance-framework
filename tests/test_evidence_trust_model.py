from pathlib import Path
import json
import unittest

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "model" / "evidence" / "evidence-trust-model.yaml"
SCHEMA_PATH = ROOT / "schemas" / "evidence-trust-model.schema.json"


class EvidenceTrustModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_model_validates_against_schema(self):
        jsonschema.Draft202012Validator(self.schema).validate(self.model)

    def test_trust_levels_are_monotone_and_references_are_known(self):
        dimension_ids = {item["id"] for item in self.model["trust_dimensions"]}
        check_ids = {item["id"] for item in self.model["verification_checks"]}
        check_dimensions = {item["dimension"] for item in self.model["verification_checks"]}
        levels = sorted(self.model["trust_levels"], key=lambda item: item["rank"])

        self.assertEqual([item["rank"] for item in levels], list(range(len(levels))))
        self.assertTrue(check_dimensions.issubset(dimension_ids))

        prior_dimensions = set()
        prior_checks = set()
        for level in levels:
            required_dimensions = set(level["required_dimensions"])
            required_checks = set(level["required_checks"])
            self.assertTrue(required_dimensions.issubset(dimension_ids))
            self.assertTrue(required_checks.issubset(check_ids))
            self.assertTrue(prior_dimensions.issubset(required_dimensions))
            self.assertTrue(prior_checks.issubset(required_checks))
            prior_dimensions = required_dimensions
            prior_checks = required_checks

    def test_model_identifiers_and_migration_references_are_consistent(self):
        collections = (
            "principles",
            "trust_dimensions",
            "verification_checks",
            "trust_levels",
            "decision_rules",
            "migration_gaps",
            "migration_phases",
            "open_decisions",
        )
        for collection in collections:
            with self.subTest(collection=collection):
                identifiers = [item["id"] for item in self.model[collection]]
                self.assertEqual(len(identifiers), len(set(identifiers)))

        level_ids = {item["id"] for item in self.model["trust_levels"]}
        phase_ids = {item["id"] for item in self.model["migration_phases"]}
        for gap in self.model["migration_gaps"]:
            self.assertIn(gap["target_level"], level_ids)
            self.assertIn(gap["phase"], phase_ids)
        for decision in self.model["open_decisions"]:
            self.assertIn(decision["blocking_for_phase"], phase_ids)

        source_document = ROOT / self.model["source_document"]
        self.assertTrue(source_document.is_file())

    def test_trust_is_report_only_and_independent_from_governance_outcome(self):
        adoption = self.model["adoption"]
        self.assertEqual(adoption["enforcement"], "report_only")
        self.assertEqual(adoption["existing_evidence_default"], "unverified")
        self.assertTrue(adoption["trust_does_not_imply_governance_pass"])
        self.assertTrue(adoption["governance_pass_does_not_imply_trust"])
        self.assertFalse(adoption["existing_snapshots_reclassified"])

    def test_gap_assessment_covers_both_intake_paths_and_shared_controls(self):
        scopes = {item["scope"] for item in self.model["migration_gaps"]}
        self.assertEqual(scopes, {"shared", "devsecops_intake", "architecture_intake"})

        gap_ids = {item["id"] for item in self.model["migration_gaps"]}
        self.assertIn("devsecops_custody_partial", gap_ids)
        self.assertIn("architecture_verification_projection_missing", gap_ids)
        self.assertIn("authenticity_not_evaluated", gap_ids)
        self.assertIn("freshness_policy_missing", gap_ids)
        self.assertIn("replay_detection_partial", gap_ids)

    def test_blocking_remains_gated_by_an_explicit_decision(self):
        phases = {item["id"]: item for item in self.model["migration_phases"]}
        enforcement = phases["enforcement_decision"]
        self.assertEqual(enforcement["state"], "gated")
        self.assertEqual(enforcement["enforcement"], "decision_required")

        rules = {item["id"] for item in self.model["decision_rules"]}
        self.assertIn("blocking_requires_release_review", rules)


if __name__ == "__main__":
    unittest.main()
