"""CLG-03 consent binding, withdrawal, progress and mixed-history acceptance."""
from copy import deepcopy
import multiprocessing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_governance_lifecycle_index import DEFAULT_PROFILE
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, approval_target, record_ref
from lib.governance_lifecycle.decisions import progress_statement
from lib.governance_lifecycle.kernel import project, replay
from lib.governance_lifecycle.store import append_action, append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from lib.governance_lifecycle.synthetic_actions import decision_packet, remediation_packet, resource
from run_governance_lifecycle_action_demo import ACTION_AS_OF, run_action_demo


def racing_action(ledger, packet, profile, barrier, queue):
    try:
        barrier.wait(timeout=30)
        queue.put(append_action(ledger, *packet, profile, expected_revision=3)["outcome"])
    except Exception as error:
        queue.put(str(error))


class LifecycleDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        self.profile = strict_json(DEFAULT_PROFILE.read_bytes())
        self.observation, resources = synthetic_packet(self.profile, result="fail", observed_at="2026-09-13T10:00:00Z",
                                                      recorded_at="2026-09-13T10:00:00Z", run_id="action-test")
        append_observation(self.ledger, self.observation, resources, self.profile, expected_revision=0)

    def decision(self, revision=1, at="10:10", record_id="decision:approve", case_id="remediation-case:first", **kwargs):
        return decision_packet(self.profile, self.observation, revision=revision, at=f"2026-09-13T{at}:00Z",
                               record_id=record_id, case_id=case_id, **kwargs)

    def append(self, packet, expected=None):
        revision = packet[0]["body"]["expected_revision"] if expected is None else expected
        return append_action(self.ledger, *packet, self.profile, expected_revision=revision)

    def projection(self, as_of="2026-09-13T13:00:00Z"):
        return project(load_transactions(self.ledger), self.profile, as_of=as_of)

    def resign(self, packet):
        record, resources = packet
        approval = record["approval"]
        resources.pop(approval["proof_ref"]["uri"])
        approval["target_digest"] = approval_target(record)
        proof, values = resource({"environment": "synthetic", "approval": {k: v for k, v in approval.items() if k != "proof_ref"}})
        approval["proof_ref"] = proof
        resources.update(values)
        return packet

    def progress(self, decision, revision=2, at="10:20", record_id="remediation:planned", **kwargs):
        return remediation_packet(*decision, revision=revision, at=f"2026-09-13T{at}:00Z", record_id=record_id, **kwargs)

    def reprove(self, packet):
        record, resources = packet
        resources.pop(record["body"]["progress_evidence_ref"]["uri"])
        proof, values = resource(progress_statement(record))
        record["body"]["progress_evidence_ref"] = proof
        resources.update(values)
        return packet

    def test_bound_approval_and_planned_remediation_are_separate_from_finding_state(self):
        decision = self.decision()
        self.append(decision)
        self.append(self.progress(decision))
        finding = self.projection()["findings"][0]
        self.assertEqual(finding["active_decision_ref"], record_ref(decision[0]))
        self.assertEqual((finding["state"], finding["revision"], finding["occurrences"]), ("open", 3, 1))
        self.assertEqual(finding["remediation_cases"][0]["owner_id"], "test-human:remediation-owner")
        self.assertFalse(finding["closure_supported"])

    def test_each_plan_field_is_included_in_consent_digest(self):
        for field, value in (("owner_id", "test-human:other"), ("target_at", "2026-09-15T00:00:00Z"),
                             ("action", "Different work"), ("remediation_id", "remediation-case:other")):
            packet = self.decision()
            packet[0]["body"]["remediation_plan"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "content binding"):
                self.append(packet)
        self.assertEqual(len(load_transactions(self.ledger)), 1)

    def test_missing_proof_and_changed_proof_bytes_do_not_assert_consent(self):
        for missing in (True, False):
            packet = self.decision()
            uri = packet[0]["approval"]["proof_ref"]["uri"]
            if missing: packet[1].pop(uri)
            else: packet[1][uri] += b" "
            with self.subTest(missing=missing), self.assertRaises(ContractError):
                self.append(packet)

    def test_role_assignment_and_human_claim_are_not_sufficient_without_binding(self):
        for field, value in (("subject_id", "test-human:unassigned"), ("role", "closure_approver"),
                             ("subject_type", "bot"), ("channel", "external_review")):
            packet = self.decision()
            packet[0]["approval"][field] = value
            self.resign(packet)
            with self.subTest(field=field), self.assertRaises((ContractError, ValidationError)):
                self.append(packet)
        packet = self.decision()
        packet[0]["approval"]["role_binding_ref"]["digest"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "Role binding"):
            self.append(self.resign(packet))

    def test_live_and_old_contract_cannot_enter_action_intake(self):
        for field, value in (("environment", "live"), ("schema_version", "0.1.0")):
            packet = self.decision()
            packet[0][field] = value
            with self.subTest(field=field), self.assertRaises((ContractError, ValidationError)):
                self.append(self.resign(packet))

    def test_stale_revision_and_relabelled_old_consent_are_rejected(self):
        self.append(self.decision(disposition="reject", record_id="decision:rejected"))
        with self.assertRaisesRegex(ContractError, "Stale expected"):
            self.append(self.decision())
        packet = self.decision(revision=2, at="10:20")
        packet[0]["approval"]["issued_at"] = "2026-09-13T10:05:00Z"
        with self.assertRaisesRegex(ContractError, "Consent predates"):
            self.append(self.resign(packet))
        with self.assertRaisesRegex(ContractError, "Stale expected"):
            self.append(self.decision(revision=2, at="10:20"), expected=3)

    def test_approval_must_bind_an_accepted_failure(self):
        packet = self.decision()
        packet[0]["body"]["observation_ref"]["digest"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "reference binding"):
            self.append(self.resign(packet))
        passing, resources = synthetic_packet(self.profile, result="pass", observed_at="2026-09-13T10:05:00Z",
                                               recorded_at="2026-09-13T10:05:00Z", run_id="pass-test")
        append_observation(self.ledger, passing, resources, self.profile, expected_revision=1)
        packet = self.decision(revision=2)
        packet[0]["body"]["observation_ref"] = record_ref(passing)
        with self.assertRaisesRegex(ContractError, "accepted failure"):
            self.append(self.resign(packet))

    def test_expired_plan_cannot_be_approved(self):
        packet = self.decision()
        packet[0]["body"]["remediation_plan"]["target_at"] = "2026-09-13T10:00:00Z"
        with self.assertRaisesRegex(ContractError, "deadline predates"):
            self.append(self.resign(packet))

    def test_rejection_records_history_without_granting_or_removing_authority(self):
        decision = self.decision()
        self.append(decision)
        rejected = self.decision(revision=2, at="10:20", record_id="decision:reject", disposition="reject")
        self.append(rejected)
        self.assertEqual(self.projection()["findings"][0]["active_decision_ref"], record_ref(decision[0]))
        with self.assertRaisesRegex(ContractError, "not active"):
            self.append(self.progress(rejected, revision=3, at="10:30"))
        rejected = self.decision(revision=3, at="10:30", record_id="decision:bad-reject", disposition="reject", previous=decision[0])
        with self.assertRaisesRegex(ContractError, "cannot supersede"):
            self.append(rejected)

    def test_withdrawal_disables_progress_and_retry_never_reactivates(self):
        decision = self.decision()
        self.append(decision)
        planned = self.progress(decision)
        self.append(planned)
        self.append(self.decision(revision=3, at="10:30", record_id="decision:revoke", disposition="revoke", previous=decision[0]))
        self.assertEqual(self.append(decision)["outcome"], "duplicate")
        finding = self.projection()["findings"][0]
        self.assertIsNone(finding["active_decision_ref"])
        self.assertEqual(finding["remediation_cases"][0]["authorization_status"], "revoked")
        with self.assertRaisesRegex(ContractError, "not active"):
            self.append(self.progress(decision, revision=4, at="10:40", record_id="remediation:progress", progress="in_progress", previous=planned[0]))
        with self.assertRaisesRegex(ContractError, "currently active"):
            self.append(self.decision(revision=4, at="10:40", record_id="decision:again", disposition="revoke", previous=decision[0]))

    def test_withdrawal_after_deadline_remains_possible(self):
        decision = self.decision()
        self.append(decision)
        withdrawal = decision_packet(self.profile, self.observation, record_id="decision:late-revoke", revision=2,
                                    at="2026-09-15T00:00:00Z", case_id="remediation-case:first", disposition="revoke", previous=decision[0])
        self.append(withdrawal)
        self.assertIsNone(self.projection("2026-09-15T01:00:00Z")["findings"][0]["active_decision_ref"])

    def test_withdrawal_cannot_change_the_approved_plan(self):
        decision = self.decision()
        self.append(decision)
        withdrawal = self.decision(revision=2, at="10:20", record_id="decision:revoke", disposition="revoke", previous=decision[0])
        withdrawal[0]["body"]["remediation_plan"]["owner_id"] = "test-human:other"
        with self.assertRaisesRegex(ContractError, "unchanged approved plan"):
            self.append(self.resign(withdrawal))

    def test_replacement_requires_latest_predecessor_and_fresh_case(self):
        decision = self.decision()
        self.append(decision)
        with self.assertRaisesRegex(ContractError, "reference its predecessor"):
            self.append(self.decision(revision=2, at="10:20", record_id="decision:replacement", case_id="remediation-case:second"))
        with self.assertRaisesRegex(ContractError, "new remediation case"):
            self.append(self.decision(revision=2, at="10:20", record_id="decision:replacement", previous=decision[0]))
        second = self.decision(revision=2, at="10:20", record_id="decision:replacement", case_id="remediation-case:second", previous=decision[0])
        self.append(second)
        with self.assertRaisesRegex(ContractError, "latest approved"):
            self.append(self.decision(revision=3, at="10:30", record_id="decision:third", case_id="remediation-case:third", previous=decision[0]))
        self.assertEqual(self.projection()["findings"][0]["decision_records"][0]["effective_status"], "superseded")
        with self.assertRaisesRegex(ContractError, "not active"):
            self.append(self.progress(decision, revision=3, at="10:30"))

    def test_new_approval_after_revocation_leaves_old_case_revoked(self):
        decision = self.decision()
        self.append(decision)
        self.append(self.progress(decision))
        self.append(self.decision(revision=3, at="10:30", record_id="decision:revoke", disposition="revoke", previous=decision[0]))
        second = self.decision(revision=4, at="10:40", record_id="decision:second", case_id="remediation-case:second", previous=decision[0])
        self.append(second)
        self.append(self.progress(second, revision=5, at="10:50", record_id="remediation:second"))
        self.assertEqual([c["authorization_status"] for c in self.projection()["findings"][0]["remediation_cases"]], ["revoked", "approved"])

    def test_same_id_changed_content_rejected_even_with_new_proof(self):
        decision = self.decision()
        self.append(decision)
        changed = deepcopy(decision)
        changed[0]["body"]["rationale"] = "Another consent"
        with self.assertRaisesRegex(ContractError, "different immutable content"):
            self.append(self.resign(changed))

    def test_remediation_cannot_change_signed_owner_deadline_action_or_case(self):
        decision = self.decision()
        self.append(decision)
        for key, value in (("owner_id", "test-human:other"), ("target_at", "2026-09-15T00:00:00Z"),
                           ("action", "Other action"), ("remediation_id", "remediation-case:other")):
            packet = self.progress(decision)
            packet[0]["body"][key] = value
            with self.subTest(field=key), self.assertRaisesRegex(ContractError, "approved plan"):
                self.append(self.reprove(packet))

    def test_progress_requires_bound_proof_and_latest_predecessor(self):
        decision = self.decision()
        self.append(decision)
        with self.assertRaisesRegex(ContractError, "Initial remediation"):
            self.append(self.progress(decision, progress="completed"))
        planned = self.progress(decision)
        self.append(planned)
        packet = self.progress(decision, revision=3, at="10:30", record_id="remediation:progress", progress="in_progress", previous=planned[0])
        packet[0]["body"]["progress"] = "completed"
        with self.assertRaises(ContractError):
            self.append(packet)
        packet = self.progress(decision, revision=3, at="10:30", record_id="remediation:progress", progress="in_progress")
        with self.assertRaisesRegex(ContractError, "latest revision"):
            self.append(packet)
        packet = self.progress(decision, revision=3, at="10:30", record_id="remediation:progress", progress="in_progress", previous=planned[0])
        uri = packet[0]["body"]["progress_evidence_ref"]["uri"]
        packet[1][uri] += b" "
        with self.assertRaisesRegex(ContractError, "digest mismatch"):
            self.append(packet)

    def test_completion_does_not_close_and_overdue_uses_explicit_time(self):
        decision = self.decision()
        self.append(decision)
        planned = self.progress(decision)
        self.append(planned)
        self.assertTrue(self.projection("2026-09-15T00:00:00Z")["findings"][0]["remediation_cases"][0]["overdue"])
        self.assertFalse(self.projection("2026-09-14T12:00:00Z")["findings"][0]["remediation_cases"][0]["overdue"])
        progress = self.progress(decision, revision=3, at="10:30", record_id="remediation:progress", progress="in_progress", previous=planned[0])
        self.append(progress)
        completed = self.progress(decision, revision=4, at="10:40", record_id="remediation:completed", progress="completed", previous=progress[0])
        self.append(completed)
        finding = self.projection("2026-09-15T00:00:00Z")["findings"][0]
        self.assertEqual(finding["state"], "open")
        self.assertFalse(finding["remediation_cases"][0]["overdue"])
        self.assertEqual(self.append(completed)["outcome"], "duplicate")
        with self.assertRaisesRegex(ContractError, "Invalid remediation progress"):
            self.append(self.progress(decision, revision=5, at="10:50", record_id="remediation:regress", previous=completed[0]))

    def test_later_observation_advances_shared_revision_without_losing_decision(self):
        decision = self.decision()
        self.append(decision)
        passing, resources = synthetic_packet(self.profile, result="pass", observed_at="2026-09-13T10:20:00Z",
                                               recorded_at="2026-09-13T10:20:00Z", run_id="later-pass")
        append_observation(self.ledger, passing, resources, self.profile, expected_revision=2)
        self.append(self.progress(decision, revision=3, at="10:30"))
        finding = self.projection()["findings"][0]
        self.assertEqual((finding["revision"], finding["evidence_status"], finding["state"]), (4, "pass", "open"))

    def test_mixed_history_demo_rebuilds_and_preserves_historical_projection(self):
        ledger = self.root / "demo"
        index = run_action_demo(ledger, self.root / "index.json")
        self.assertEqual(index, strict_json((ROOT / "status/governance-lifecycle-synthetic-index.json").read_bytes()))
        self.assertEqual(load_transactions(ledger), load_transactions(ROOT / "governance/lifecycle/synthetic"))
        before = project(load_transactions(ledger), self.profile, as_of="2026-09-13T11:30:00Z")
        self.assertEqual(before, strict_json((ROOT / "tests/fixtures/governance-lifecycle/clg02-index.json").read_bytes()))
        during = project(load_transactions(ledger), self.profile, as_of="2026-09-13T12:00:00Z")
        self.assertIsNotNone(during["findings"][0]["active_decision_ref"])
        self.assertIsNone(index["findings"][0]["active_decision_ref"])
        self.assertEqual(index["findings"][0]["state"], "needs_clarification")
        tampered = load_transactions(ledger)
        tampered[-1]["event"]["body"]["revision"] += 1
        with self.assertRaises(ContractError):
            project(tampered, self.profile, as_of="2026-09-13T11:30:00Z")

    def test_cli_accepts_explicit_packet_and_rejects_missing_synthetic_flag(self):
        packet = self.decision()
        record_path = self.root / "record.json"
        record_path.write_bytes(json_bytes(packet[0]))
        directory = self.root / "resources"
        directory.mkdir()
        for uri, data in packet[1].items():
            (directory / uri.removeprefix("fixture://")).write_bytes(data)
        command = [sys.executable, str(ROOT / "scripts/intake_governance_lifecycle_action.py"), "--ledger", str(self.ledger),
                   "--record", str(record_path), "--resources", str(directory), "--expected-revision", "1"]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(missing.returncode, 0)
        accepted = subprocess.run(command + ["--synthetic"], capture_output=True, text=True)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(strict_json(accepted.stdout)["outcome"], "accepted")

    def test_withdrawal_and_progress_compete_for_same_revision_across_processes(self):
        decision = self.decision()
        self.append(decision)
        planned = self.progress(decision)
        self.append(planned)
        withdrawal = self.decision(revision=3, at="10:30", record_id="decision:revoke", disposition="revoke", previous=decision[0])
        progress = self.progress(decision, revision=3, at="10:30", record_id="remediation:progress", progress="in_progress", previous=planned[0])
        ctx = multiprocessing.get_context("spawn")
        barrier, queue = ctx.Barrier(3), ctx.Queue()
        workers = [ctx.Process(target=racing_action, args=(self.ledger, packet, self.profile, barrier, queue)) for packet in (withdrawal, progress)]
        try:
            for worker in workers: worker.start()
            barrier.wait(timeout=30)
            results = [queue.get(timeout=30) for _ in workers]
            for worker in workers:
                worker.join(timeout=30)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(results.count("accepted"), 1)
            self.assertEqual(sum("Stale expected finding revision" in r for r in results), 1)
            self.assertEqual(self.projection()["findings"][0]["revision"], 4)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(timeout=5)
            queue.close()


if __name__ == "__main__":
    unittest.main()
