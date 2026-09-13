"""Executable CLG-01 contracts; no claimed ledger or live approval acceptance."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.governance_lifecycle.contracts import (
    ContractError, KINDS, acceptance_statement, approval_target,
    canonical_digest, check_closure_prerequisites, check_event_references,
    finding_id, observation_identity, record_ref, schema_validator,
    validate_record, validate_test_profile, validate_test_record, versioned_ref,
)
from validate_governance_lifecycle_contracts import load_examples


class LifecycleContractTests(unittest.TestCase):
    def setUp(self):
        self.profile, self.records, self.resources = load_examples()
        self.closure = self.records["closure:synthetic-001"]
        self.passing = self.records["observation:synthetic-pass"]
        self.failing = self.records["observation:synthetic-fail"]
        self.decision = self.records["decision:synthetic-001"]
        self.remediation = self.records["remediation:synthetic-001"]
        self.event = self.records["event:synthetic-opened"]

    def fixture(self, name, payload):
        data = (json.dumps(payload, indent=2) + "\n").encode()
        uri = "fixture://test-" + name + ".json"
        self.resources[uri] = data
        return {"uri": uri, "digest": hashlib.sha256(data).hexdigest()}

    def approve_fixture(self, record):
        """Simulate a NEW synthetic proof to isolate checks beyond content binding."""
        approval = record["approval"]
        approval["target_digest"] = approval_target(record)
        proof = {k: v for k, v in approval.items() if k != "proof_ref"}
        approval["proof_ref"] = self.fixture(record["record_id"], {"environment": "synthetic", "approval": proof})

    def accept_fixture(self, record):
        record["body"]["acceptance"]["proof_ref"] = self.fixture(record["record_id"], acceptance_statement(record))

    def refresh_packet(self):
        """Rebind fixture references after a deliberate semantic mutation."""
        self.decision["body"]["observation_ref"] = record_ref(self.failing)
        self.approve_fixture(self.decision)
        self.remediation["body"]["decision_ref"] = record_ref(self.decision)
        self.closure["body"].update(
            remediation_ref=record_ref(self.remediation),
            failing_observation_ref=record_ref(self.failing),
            passing_observation_ref=record_ref(self.passing),
        )
        self.approve_fixture(self.closure)

    def check_closure(self):
        check_closure_prerequisites(self.closure, self.records, self.profile, self.resources,
                                    as_of=self.closure["body"]["as_of"])

    def test_p01_complete_packet_has_valid_contracts_and_prerequisites(self):
        validate_test_profile(self.profile)
        self.assertEqual(set(KINDS), {r["record_type"] for r in self.records.values()})
        for record in self.records.values():
            with self.subTest(record=record["record_id"]):
                validate_test_record(record, self.profile, self.resources)
        check_event_references(self.event, self.records)
        self.check_closure()

    def test_invalid_examples_fail_for_documented_missing_fields(self):
        directory = ROOT / "tests/fixtures/governance-lifecycle/invalid"
        cases = json.loads((directory / "manifest.json").read_text())
        self.assertEqual(set(KINDS), {c["kind"] for c in cases})
        for case in cases:
            with self.subTest(case=case["file"]):
                value = json.loads((directory / case["file"]).read_text())
                parent, field = case["missing_path"].split("/")
                errors = list(schema_validator(case["kind"]).iter_errors(value))
                self.assertTrue(any(e.validator == case["expected_validator"] and list(e.path) == [parent]
                                    and field in e.message for e in errors))

    def test_strict_record_fields_and_utc_dates(self):
        for field, value in (("recorded_at", "not-a-date"), ("recorded_at", "2026-02-30T10:00:00Z"),
                             ("recorded_at", "2026-09-13T12:00:00+02:00"), ("unrecognized", True)):
            with self.subTest(field=field, value=value):
                record = deepcopy(self.event)
                record[field] = value
                with self.assertRaises(ValidationError):
                    validate_record(record)

    def test_p02_delivery_identity_stable_on_redelivery_not_content_conflicts(self):
        again = deepcopy(self.failing)
        again["recorded_at"] = "2026-09-13T10:02:00Z"
        self.assertEqual(observation_identity(again), observation_identity(self.failing))
        self.assertNotEqual(canonical_digest(again), canonical_digest(self.failing))
        # Identity equality requires comparing content; it does not authorize replacement.
        again["body"]["result"] = "pass"
        self.assertEqual(observation_identity(again), observation_identity(self.failing))
        again["body"]["source_context"]["run_id"] = "independent-observation"
        self.assertNotEqual(observation_identity(again), observation_identity(self.failing))

    def test_fingerprint_is_versioned_stable_and_scope_sensitive(self):
        key = self.failing["finding"]["key"]
        self.assertEqual(finding_id(key), finding_id(dict(reversed(list(key.items())))))
        self.assertNotEqual(finding_id(key), finding_id({**key, "repository_id": "synthetic/other"}))
        self.assertNotEqual(finding_id(key), finding_id({**key, "resource": "refs/heads/other"}))
        # Fixed interoperability vector; uses the repository's existing canonical serializer.
        self.assertEqual(canonical_digest({"b": 2, "a": 1}),
                         "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777")

    def test_fingerprint_tampering_rejected(self):
        self.event["finding"]["finding_id"] = "finding:" + "0" * 64
        with self.assertRaisesRegex(ContractError, "fingerprint"):
            validate_record(self.event)

    def test_p03_revision_edges_and_predecessor_binding(self):
        event = deepcopy(self.event)
        event["record_id"] = "event:next"
        event["body"].update(event_type="observation_added", revision=2, expected_revision=1,
                             previous_event_ref=record_ref(self.event))
        check_event_references(event, self.records)
        event["body"].update(revision=3, expected_revision=2)
        with self.assertRaisesRegex(ContractError, "predecessor revision"):
            check_event_references(event, self.records)
        event["body"]["revision"] = 4
        with self.assertRaisesRegex(ContractError, "advance by one"):
            validate_record(event)

    def test_event_cannot_open_from_pass_or_missing_source(self):
        self.event["recorded_at"] = self.passing["recorded_at"]
        self.event["body"]["source_refs"] = [record_ref(self.passing)]
        with self.assertRaisesRegex(ContractError, "accepted criterion FAIL"):
            check_event_references(self.event, self.records)
        self.event["body"]["source_refs"][0]["id"] = "observation:missing"
        with self.assertRaisesRegex(ContractError, "Missing referenced"):
            check_event_references(self.event, self.records)

    def test_p04_p05_observation_and_recording_time_are_distinct(self):
        late = deepcopy(self.failing)
        late["recorded_at"] = "2026-09-13T12:00:00Z"
        validate_record(late)
        self.assertLess(late["body"]["observed_at"], self.passing["body"]["observed_at"])
        self.assertGreater(late["recorded_at"], self.closure["recorded_at"])
        # This proves the inputs preserve ordering, not that a reducer reopens correctly.
        later = deepcopy(self.failing)
        later["body"]["observed_at"] = "2026-09-13T12:00:00Z"
        later["body"]["acceptance"]["evaluated_at"] = "2026-09-13T12:00:00Z"
        later["recorded_at"] = "2026-09-13T12:01:00Z"
        validate_record(later)
        self.assertGreater(later["body"]["observed_at"], self.closure["recorded_at"])

    def test_p06_granularity_and_unchecked_criterion_cannot_close(self):
        self.passing["body"]["granularity"] = "gate_summary"
        with self.assertRaises(ValidationError):
            validate_record(self.passing)
        self.passing["body"]["granularity"] = "criterion"
        for result in ("unknown", "not_evaluated", "fail"):
            with self.subTest(result=result):
                self.passing["body"]["result"] = result
                self.accept_fixture(self.passing)
                self.refresh_packet()
                with self.assertRaisesRegex(ContractError, "criterion mismatch"):
                    self.check_closure()

    def test_p06_other_repository_cannot_close(self):
        self.passing["finding"] = deepcopy(self.passing["finding"])
        self.passing["finding"]["key"]["repository_id"] = "synthetic/other"
        self.passing["finding"]["finding_id"] = finding_id(self.passing["finding"]["key"])
        self.accept_fixture(self.passing)
        self.refresh_packet()
        with self.assertRaisesRegex(ContractError, "repository mismatch"):
            self.check_closure()

    def test_p06_policy_version_mismatch_cannot_close(self):
        self.passing["body"]["policy_version"] = "0.2.0"
        self.accept_fixture(self.passing)
        self.refresh_packet()
        with self.assertRaisesRegex(ContractError, "Incompatible evidence versions"):
            self.check_closure()

    def test_p07_required_checks_cannot_be_replaced_by_high_level(self):
        original = deepcopy(self.passing)
        for name in self.profile["required_checks"]:
            for result in (None, "fail", "unknown", "not_evaluated"):
                with self.subTest(check=name, result=result):
                    self.passing.clear()
                    self.passing.update(deepcopy(original))
                    checks = self.passing["body"]["trust"]["checks"]
                    if result is None:
                        checks[:] = [c for c in checks if c["id"] != name]
                    else:
                        next(c for c in checks if c["id"] == name)["result"] = result
                    self.passing["body"]["trust"]["effective_level"] = "attested"
                    self.accept_fixture(self.passing)
                    self.refresh_packet()
                    with self.assertRaisesRegex(ContractError, "Required trust check"):
                        self.check_closure()

    def test_p07_duplicate_trust_check_ids_rejected(self):
        check = deepcopy(self.passing["body"]["trust"]["checks"][0])
        check["result"] = "fail"
        self.passing["body"]["trust"]["checks"].append(check)
        self.accept_fixture(self.passing)
        self.refresh_packet()
        with self.assertRaisesRegex(ContractError, "Duplicate trust check"):
            self.check_closure()

    def test_p07_freshness_boundary_is_explicit_and_reproducible(self):
        self.closure["body"]["as_of"] = "2026-09-14T11:00:00Z"
        self.approve_fixture(self.closure)
        self.check_closure()
        self.closure["body"]["as_of"] = "2026-09-14T11:00:01Z"
        self.approve_fixture(self.closure)
        with self.assertRaisesRegex(ContractError, "stale or from the future"):
            self.check_closure()

    def test_p07_snapshot_tampering_and_missing_resources_rejected(self):
        reference = self.passing["body"]["snapshot_ref"]
        self.resources[reference["uri"]] += b" "
        with self.assertRaisesRegex(ContractError, "Fixture digest mismatch"):
            self.check_closure()
        del self.resources[reference["uri"]]
        with self.assertRaisesRegex(ContractError, "Missing fixture resource"):
            self.check_closure()

    def test_p08_content_revision_and_scope_tampering_rejected(self):
        for edit, expected in ((lambda r: r["body"].update(rationale="changed"), "content binding"),
                               (lambda r: r["approval"].update(expected_revision=7), "revision mismatch"),
                               (lambda r: r["approval"].update(finding_id="finding:" + "0" * 64), "scope mismatch")):
            with self.subTest(expected=expected):
                record = deepcopy(self.decision)
                edit(record)
                with self.assertRaisesRegex(ContractError, expected):
                    validate_record(record)

    def test_p08_bot_or_wrong_role_cannot_supply_test_approval(self):
        self.decision["approval"]["subject_type"] = "bot"
        with self.assertRaises(ValidationError):
            validate_record(self.decision)
        self.decision["approval"]["subject_type"] = "human"
        self.decision["approval"]["subject_id"] = "test-human:unassigned"
        self.approve_fixture(self.decision)
        with self.assertRaisesRegex(ContractError, "not assigned"):
            validate_test_record(self.decision, self.profile, self.resources)

    def test_p08_proof_and_role_binding_must_match(self):
        self.decision["approval"]["issued_at"] = "2026-09-13T10:09:00Z"
        with self.assertRaisesRegex(ContractError, "approval proof mismatch"):
            validate_test_record(self.decision, self.profile, self.resources)
        self.approve_fixture(self.decision)
        self.decision["approval"]["role_binding_ref"]["version"] = "0.2.0"
        with self.assertRaisesRegex(ContractError, "Role binding mismatch"):
            validate_test_record(self.decision, self.profile, self.resources)

    def test_p08_rejected_or_withdrawn_decision_cannot_close(self):
        for disposition in ("reject", "revoke"):
            with self.subTest(disposition=disposition):
                self.decision["approval"]["disposition"] = disposition
                if disposition == "revoke":
                    self.decision["body"]["supersedes_ref"] = {"id":"decision:prior", "digest":"0"*64}
                self.refresh_packet()
                with self.assertRaisesRegex(ContractError, "decision not approved"):
                    self.check_closure()

    def test_p08_withdrawal_requires_a_predecessor(self):
        for record in (self.decision, self.closure):
            with self.subTest(kind=record["record_type"]):
                record["approval"]["disposition"] = "revoke"
                self.approve_fixture(record)
                with self.assertRaises(ValidationError):
                    validate_record(record)

    def test_p09_synthetic_proofs_never_validate_as_live(self):
        self.decision["environment"] = "live"
        with self.assertRaises(ValidationError):
            validate_record(self.decision)
        self.decision["approval"].update(channel="external_review", subject_id="human:someone")
        self.approve_fixture(self.decision)
        validate_record(self.decision)
        with self.assertRaisesRegex(ContractError, "Live records"):
            validate_test_record(self.decision, self.profile, self.resources)
        self.profile["live_intake_enabled"] = True
        with self.assertRaises(ValidationError):
            validate_test_profile(self.profile)

    def test_p09_branch_pr_manual_and_real_repository_not_test_context(self):
        for kind in ("branch", "pull_request", "manual", "mainline", "release"):
            with self.subTest(kind=kind):
                self.passing["body"]["source_context"]["kind"] = kind
                self.accept_fixture(self.passing)
                with self.assertRaisesRegex(ContractError, "Context not accepted"):
                    validate_test_record(self.passing, self.profile, self.resources)

    def test_reference_digest_mismatch_rejected(self):
        self.closure["body"]["passing_observation_ref"]["digest"] = "0" * 64
        self.approve_fixture(self.closure)
        with self.assertRaisesRegex(ContractError, "reference binding"):
            self.check_closure()

    def test_accepted_failure_also_requires_profile_trust(self):
        self.failing["body"]["trust"]["effective_level"] = "unverified"
        self.accept_fixture(self.failing)
        self.refresh_packet()
        with self.assertRaisesRegex(ContractError, "Insufficient observation trust"):
            self.check_closure()

    def test_planned_work_or_changed_action_does_not_close(self):
        self.remediation["body"]["progress"] = "planned"
        self.refresh_packet()
        with self.assertRaisesRegex(ContractError, "not completed"):
            self.check_closure()
        self.remediation["body"]["progress"] = "completed"
        self.remediation["body"]["action"] = "An unrelated change"
        self.refresh_packet()
        with self.assertRaisesRegex(ContractError, "authorized action"):
            self.check_closure()

    def test_schema_rejects_waiver_closure_and_real_owner_in_synthetic_remediation(self):
        self.closure["body"]["reason"] = "risk_accepted"
        with self.assertRaises(ValidationError):
            validate_record(self.closure)
        self.remediation["body"]["owner_id"] = "human:real-person"
        with self.assertRaises(ValidationError):
            validate_record(self.remediation)

    def test_p10_contract_checks_do_not_mutate_or_read_current_time(self):
        before = deepcopy((self.records, self.profile, self.resources))
        self.check_closure()
        self.check_closure()
        self.assertEqual(before, (self.records, self.profile, self.resources))
        with self.assertRaisesRegex(ContractError, "Explicit as_of"):
            check_closure_prerequisites(self.closure, self.records, self.profile, self.resources,
                                        as_of="2026-09-13T11:11:00Z")


if __name__ == "__main__":
    unittest.main()
