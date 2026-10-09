from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.requirement_lifecycle import analyze_statement, activate_case, record_decision


def catalog_with(statement="Existing requirement"):
    return {
        "schema_version": "1.0.0", "catalog_id": "GOVERNANCE-REQUIREMENT-CATALOG",
        "version": "0.1.0", "next_sequence": 2,
        "requirements": [{"id": "GRQ-000001", "active_revision": 1, "revisions": [{
            "revision": 1, "status": "effective", "title": "Existing", "statement": statement,
            "normative_strength": "MUST", "domain": "devsecops", "owner": "owner",
            "approved_at": "2026-10-09T00:00:00Z", "effective_from": "2026-10-09",
            "effective_until": None, "source_refs": ["SRC-REQ-001"], "relationships": [],
            "decision_ref": "GCR-1", "authorized_derivations": [], "runtime_enforcement": "none"
        }]}],
    }


def lifecycle_case(statement="New requirement"):
    return {
        "schema_version": "1.0.0", "case_id": "RLC-TEST", "intake_type": "native_git",
        "status": "decision_required", "created_at": "2026-10-09T00:00:00Z",
        "source": {"source_id": "NATIVE-1", "source_path": "docs/native.md", "source_sha256": "0" * 64, "owner": "owner", "decision_ref": "GCR-2"},
        "proposals": [{"proposal_id": "RLC-TEST-P0001", "source_requirement_id": "NATIVE-1",
                       "title": "New", "statement": statement, "normative_strength": "MUST",
                       "domain": "devsecops", "analysis": analyze_statement(statement, catalog_with()),
                       "decision": None, "activation": None}],
    }


class RequirementLifecycleTests(unittest.TestCase):
    def test_exact_match_is_duplicate(self):
        analysis = analyze_statement("Existing requirement", catalog_with())
        self.assertEqual(analysis["suggested_classification"], "duplicate")
        self.assertEqual(analysis["confidence"], 1.0)

    def test_cross_case_exact_match_is_duplicate(self):
        analysis = analyze_statement("Same obligation", {"requirements": []}, [("RLC-OTHER-P0001", "Same obligation")])
        self.assertEqual(analysis["suggested_classification"], "duplicate")
        self.assertEqual(analysis["candidate_matches"][0]["requirement_id"], "RLC-OTHER-P0001")

    def test_decision_requires_target_for_non_new_classification(self):
        with self.assertRaisesRegex(ValueError, "requires a target"):
            record_decision(lifecycle_case(), proposal_id="RLC-TEST-P0001", disposition="approve",
                            classification="extend", target_requirement_id=None, decided_by="user",
                            decision_role="owner", rationale="approved", authorized_derivations=[],
                            runtime_enforcement="none")

    def test_blocking_requires_separate_authorization(self):
        with self.assertRaisesRegex(ValueError, "separate enforcement"):
            record_decision(lifecycle_case(), proposal_id="RLC-TEST-P0001", disposition="approve",
                            classification="new", target_requirement_id=None, decided_by="user",
                            decision_role="owner", rationale="approved", authorized_derivations=[],
                            runtime_enforcement="blocking")

    def test_activation_requires_all_decisions(self):
        with self.assertRaisesRegex(ValueError, "explicit decision"):
            activate_case(lifecycle_case(), catalog_with(), effective_from="2026-10-10", commit="abc")

    def test_approved_new_requirement_activates_immutable_revision(self):
        case = lifecycle_case()
        catalog = catalog_with()
        record_decision(case, proposal_id="RLC-TEST-P0001", disposition="approve", classification="new",
                        target_requirement_id=None, decided_by="user", decision_role="owner",
                        rationale="approved", authorized_derivations=["documentation"], runtime_enforcement="report_only")
        activate_case(case, catalog, effective_from="2026-10-10", commit="abc")
        created = catalog["requirements"][-1]
        self.assertEqual(created["id"], "GRQ-000002")
        self.assertEqual(created["active_revision"], 1)
        self.assertEqual(created["revisions"][0]["status"], "effective")
        self.assertEqual(case["status"], "activated")

    def test_change_supersedes_previous_revision(self):
        case = lifecycle_case("Changed requirement")
        catalog = catalog_with()
        record_decision(case, proposal_id="RLC-TEST-P0001", disposition="approve", classification="change",
                        target_requirement_id="GRQ-000001", decided_by="user", decision_role="owner",
                        rationale="change approved", authorized_derivations=[], runtime_enforcement="none")
        activate_case(case, catalog, effective_from="2026-10-10", commit="abc")
        revisions = catalog["requirements"][0]["revisions"]
        self.assertEqual([item["status"] for item in revisions], ["superseded", "effective"])
        self.assertEqual(catalog["requirements"][0]["active_revision"], 2)


if __name__ == "__main__":
    unittest.main()
