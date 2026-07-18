from pathlib import Path
import json
import sys
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.evidence_attestation import assess_attestation, load_trust_roots


class EvidenceAttestationTests(unittest.TestCase):
    def setUp(self):
        self.attestation = json.loads((ROOT / "docs/examples/evidence-attestation.example.json").read_text())
        self.registry = load_trust_roots(ROOT / "model/evidence/evidence-trust-roots.yaml")
        statement = self.attestation["statement"]
        self.context = {key: statement[key] for key in ("repository_id", "commit_id", "run_id", "run_attempt", "artifact_name")}
        self.subject = statement["subject"]

    def assess(self, attestation=None, context=None, subject=None):
        return assess_attestation(
            attestation=attestation or self.attestation, registry=self.registry,
            expected_context=context or self.context, expected_subject=subject or self.subject,
            evaluated_at="2026-07-17T10:01:00Z", attestation_ref="docs/examples/evidence-attestation.example.json",
        )

    def test_example_and_successful_assessment_validate(self):
        Draft202012Validator(json.loads((ROOT / "schemas/evidence-attestation.schema.json").read_text())).validate(self.attestation)
        assessment = self.assess()
        Draft202012Validator(json.loads((ROOT / "schemas/evidence-attestation-assessment.schema.json").read_text())).validate(assessment)
        self.assertEqual(assessment["status"], "pass")
        self.assertEqual(assessment["candidate_level"], "attested")
        self.assertEqual(assessment["effective_level"], "integrity_verified")
        self.assertEqual({check["result"] for check in assessment["checks"]}, {"pass"})

    def test_signed_statement_tampering_invalidates_signature_and_context(self):
        changed = json.loads(json.dumps(self.attestation))
        changed["statement"]["commit_id"] = "different"
        assessment = self.assess(attestation=changed)
        checks = {item["id"]: item["result"] for item in assessment["checks"]}
        self.assertEqual(checks["attestation_signature_valid"], "fail")
        self.assertEqual(checks["attestation_context_matches"], "fail")
        self.assertEqual(assessment["candidate_level"], "none")

    def test_collected_subject_mismatch_is_reported(self):
        changed_subject = {**self.subject, "digest": "b" * 64}
        assessment = self.assess(subject=changed_subject)
        self.assertEqual(assessment["status"], "fail")
        self.assertEqual(next(item for item in assessment["checks"] if item["id"] == "attestation_subject_matches")["result"], "fail")

    def test_unknown_trust_root_cannot_be_attested(self):
        changed = json.loads(json.dumps(self.attestation))
        changed["key_id"] = "unknown-key"
        assessment = self.assess(attestation=changed)
        checks = {item["id"]: item["result"] for item in assessment["checks"]}
        self.assertEqual(checks["trust_root_known"], "fail")
        self.assertEqual(checks["attestation_signature_valid"], "not_evaluated")


if __name__ == "__main__":
    unittest.main()
