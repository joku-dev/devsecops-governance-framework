"""CLG-04 accepted evidence, closure/reopening, concurrency and publication boundaries."""
import base64
from copy import deepcopy
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_governance_lifecycle_index import DEFAULT_PROFILE
from generate_governance_lifecycle_pilot import generate, render_report
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, approval_target, record_ref
from lib.governance_lifecycle.kernel import project, replay, transaction_name
from lib.governance_lifecycle.store import append_action, append_closure, append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from lib.governance_lifecycle.synthetic_actions import closure_packet, decision_packet, remediation_packet, resource
from run_governance_lifecycle_closure_demo import PILOT_AS_OF, run_closure_demo
from validate_governance_lifecycle_ledger import check_accepted_prefix, validate_pilot

PILOT = ROOT / "governance/lifecycle/synthetic-closure"


def seed(ledger):
    directory = ledger / "transactions"
    directory.mkdir(parents=True)
    for path in sorted((PILOT / "transactions").glob("*.json"))[:6]:
        shutil.copyfile(path, directory / path.name)


def race_closure(ledger, packet, profile, closure, barrier, queue):
    try:
        barrier.wait(timeout=30)
        append = append_closure if closure else append_observation
        queue.put(append(ledger, *packet, profile, expected_revision=6)["outcome"])
    except Exception as error:
        queue.put(str(error))


class LifecycleClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        seed(self.ledger)
        self.profile = strict_json(DEFAULT_PROFILE.read_bytes())
        self.original = load_transactions(PILOT)
        self.closure = deepcopy(self.original[6]["record"])
        self.resources = {uri: base64.b64decode(data) for uri, data in self.original[6]["resources"].items()}

    def append(self, record=None, resources=None, revision=None):
        record = record or self.closure
        return append_closure(self.ledger, record, self.resources if resources is None else resources, self.profile,
                              expected_revision=record["body"]["expected_revision"] if revision is None else revision)

    def projection(self, at=PILOT_AS_OF):
        return project(load_transactions(self.ledger), self.profile, as_of=at)

    def resign(self):
        approval = self.closure["approval"]
        approval["target_digest"] = approval_target(self.closure)
        proof, self.resources = resource({"environment": "synthetic", "approval": {k: v for k, v in approval.items() if k != "proof_ref"}})
        approval["proof_ref"] = proof

    def advance(self, revision, at="14:10"):
        self.closure["body"]["expected_revision"] = revision
        self.closure["approval"]["expected_revision"] = revision
        self.closure["recorded_at"] = self.closure["body"]["as_of"] = self.closure["approval"]["issued_at"] = f"2026-09-13T{at}:00Z"
        self.resign()

    def observation(self, result="fail", observed="14:10", recorded="14:10", run="new", revision=6, policy="0.1.0"):
        packet = synthetic_packet(self.profile, result=result, observed_at=f"2026-09-13T{observed}:00Z",
                                  recorded_at=f"2026-09-13T{recorded}:00Z", run_id=run, policy_version=policy)
        append_observation(self.ledger, *packet, self.profile, expected_revision=revision)
        return packet

    def test_pass_and_completed_work_remain_open_until_bound_closure(self):
        before = self.projection()["findings"][0]
        self.assertEqual((before["state"], before["evidence_status"]), ("open", "pass"))
        self.append()
        index = self.projection()
        self.assertEqual(index["schema_version"], "0.3.0")
        self.assertEqual(index["findings"][0]["state"], "closed")
        self.assertEqual(index["findings"][0]["active_closure_ref"], record_ref(self.closure))
        self.assertFalse(index["official_state"])

    def test_late_old_failure_preserves_closure_new_failure_reopens_same_finding(self):
        self.append()
        identity = self.projection()["findings"][0]["finding_id"]
        self.observation(observed="13:05", recorded="14:10", revision=7)
        self.assertEqual(self.projection()["findings"][0]["state"], "closed")
        self.observation(observed="14:20", recorded="14:20", run="recurrence", revision=8)
        after = self.projection()["findings"][0]
        self.assertEqual((after["finding_id"], after["state"], after["reopen_count"]), (identity, "open", 1))
        self.assertEqual(after["closure_refs"], [record_ref(self.closure)])
        self.assertEqual(after["occurrences"], 3)
        self.assertIsNone(after["active_closure_ref"])
        self.assertEqual(self.append()["outcome"], "duplicate")
        self.assertEqual(self.projection()["findings"][0]["state"], "open")

    def test_new_conflict_after_closure_is_visible_and_cannot_claim_active_closure(self):
        self.append()
        self.observation(result="fail", observed="13:50", recorded="14:10", run="conflict", revision=7)
        finding = self.projection()["findings"][0]
        self.assertEqual(finding["state"], "needs_clarification")
        self.assertIsNone(finding["active_closure_ref"])
        self.assertEqual(len(finding["closure_refs"]), 1)

    def test_conflicting_or_incompatible_evidence_prevents_closure(self):
        for policy in ("0.1.0", "0.2.0"):
            with self.subTest(policy=policy):
                ledger = self.root / policy
                seed(ledger)
                packet = synthetic_packet(self.profile, result="fail", observed_at="2026-09-13T13:50:00Z",
                    recorded_at="2026-09-13T14:00:00Z", run_id="conflict", policy_version=policy)
                append_observation(ledger, *packet, self.profile, expected_revision=6)
                self.advance(7)
                with self.assertRaisesRegex(ContractError, "Unresolved evidence conflict"):
                    append_closure(ledger, self.closure, self.resources, self.profile, expected_revision=7)

    def test_latest_evidence_cannot_be_bypassed_with_older_pass(self):
        self.observation()
        self.advance(7)
        with self.assertRaisesRegex(ContractError, "latest accepted observation"):
            self.append()

    def test_role_content_scope_and_revision_bindings_are_required(self):
        for field, value in (("subject_id", "test-human:decision-owner"), ("role", "remediation_decider"),
                             ("subject_type", "bot"), ("finding_id", "finding:" + "0" * 64)):
            self.closure = deepcopy(self.original[6]["record"])
            self.closure["approval"][field] = value
            self.resign()
            with self.subTest(field=field), self.assertRaises((ContractError, ValidationError)):
                self.append()
        self.closure = deepcopy(self.original[6]["record"])
        self.resign()
        self.closure["body"]["rationale"] = "Changed after consent"
        with self.assertRaisesRegex(ContractError, "content binding"):
            self.append()

    def test_rejected_revoked_live_or_old_contract_closures_are_not_accepted(self):
        for target, field, value in (("approval", "disposition", "reject"), ("approval", "disposition", "revoke"),
                                     (None, "environment", "live"), (None, "schema_version", "0.1.0")):
            self.closure = deepcopy(self.original[6]["record"])
            (self.closure[target] if target else self.closure)[field] = value
            self.resign()
            with self.subTest(value=value), self.assertRaises((ContractError, ValidationError)):
                self.append()

    def test_missing_tampered_or_caller_supplied_replacement_evidence_fails(self):
        with self.assertRaises(ContractError):
            self.append(resources={})
        extra = dict(self.resources)
        extra.update({uri: base64.b64decode(data) for uri, data in self.original[5]["resources"].items()})
        with self.assertRaisesRegex(ContractError, "Only the bound closure"):
            self.append(resources=extra)
        uri = next(iter(self.resources))
        self.resources[uri] += b" "
        with self.assertRaisesRegex(ContractError, "digest mismatch"):
            self.append()

    def test_stale_revision_and_consent_before_head_are_rejected(self):
        with self.assertRaisesRegex(ContractError, "Stale expected"):
            self.append(revision=5)
        self.closure["approval"]["issued_at"] = "2026-09-13T13:45:00Z"
        self.resign()
        with self.assertRaisesRegex(ContractError, "consent predates"):
            self.append()

    def test_as_of_cannot_hide_acceptance_time_and_stale_pass_cannot_close(self):
        self.closure["recorded_at"] = "2026-09-15T14:00:00Z"
        self.resign()
        with self.assertRaisesRegex(ContractError, "as_of must equal"):
            self.append()
        self.closure["body"]["as_of"] = self.closure["recorded_at"]
        self.closure["approval"]["issued_at"] = self.closure["recorded_at"]
        self.resign()
        with self.assertRaisesRegex(ContractError, "stale"):
            self.append()

    def test_wrong_record_digest_or_nonlatest_remediation_is_rejected(self):
        self.closure["body"]["remediation_ref"] = record_ref(self.original[3]["record"])
        self.resign()
        with self.assertRaisesRegex(ContractError, "latest remediation"):
            self.append()
        self.closure["body"]["remediation_ref"] = record_ref(self.original[4]["record"])
        self.closure["body"]["passing_observation_ref"]["digest"] = "0" * 64
        self.resign()
        with self.assertRaisesRegex(ContractError, "reference binding"):
            self.append()

    def test_revoked_remediation_authority_cannot_close(self):
        decision = self.original[1]["record"]
        withdrawal = decision_packet(self.profile, self.original[0]["observation"], record_id="decision:withdraw",
            revision=6, at="2026-09-13T14:00:00Z", case_id="remediation-case:closure-demo", disposition="revoke", previous=decision)
        append_action(self.ledger, *withdrawal, self.profile, expected_revision=6)
        self.advance(7)
        with self.assertRaisesRegex(ContractError, "approval is not active"):
            self.append()

    def test_closed_finding_rejects_new_action_and_duplicate_closure_identity_change(self):
        self.append()
        decision = decision_packet(self.profile, self.original[0]["observation"], record_id="decision:new", revision=7,
            at="2026-09-13T14:10:00Z", case_id="remediation-case:new", previous=self.original[1]["record"])
        with self.assertRaisesRegex(ContractError, "Finding is closed"):
            append_action(self.ledger, *decision, self.profile, expected_revision=7)
        self.closure["body"]["rationale"] = "Changed history"
        self.resign()
        with self.assertRaisesRegex(ContractError, "different immutable content"):
            self.append()
        self.closure["record_id"] = "closure:another"
        self.advance(7)
        with self.assertRaisesRegex(ContractError, "already closed"):
            self.append()

    def test_old_completed_work_cannot_close_a_new_failure(self):
        self.append()
        self.observation(observed="14:10", recorded="14:10", revision=7)
        passing = self.observation(result="pass", observed="14:20", recorded="14:20", run="new-pass", revision=8)
        self.closure["record_id"] = "closure:again"
        self.closure["body"]["passing_observation_ref"] = record_ref(passing[0])
        self.advance(9, at="14:30")
        with self.assertRaisesRegex(ContractError, "Remediation must follow every"):
            self.append()

    def test_new_decision_and_work_can_close_a_reopened_finding(self):
        self.append()
        failing = self.observation(observed="14:10", recorded="14:10", revision=7)[0]
        decision = decision_packet(self.profile, failing, record_id="decision:second-cycle", revision=8,
            at="2026-09-13T14:20:00Z", case_id="remediation-case:second-cycle", previous=self.original[1]["record"])
        append_action(self.ledger, *decision, self.profile, expected_revision=8)
        previous = None
        for revision, progress, at in ((9, "planned", "14:30"), (10, "in_progress", "14:40"), (11, "completed", "14:50")):
            packet = remediation_packet(*decision, record_id="remediation:second-" + progress, revision=revision,
                at=f"2026-09-13T{at}:00Z", progress=progress, previous=previous)
            append_action(self.ledger, *packet, self.profile, expected_revision=revision)
            previous = packet[0]
        passing = self.observation(result="pass", observed="15:00", recorded="15:00", run="second-pass", revision=12)[0]
        closure = closure_packet(self.profile, failing, passing, previous, record_id="closure:second", revision=13,
                                 at="2026-09-13T15:10:00Z")
        append_closure(self.ledger, *closure, self.profile, expected_revision=13)
        finding = self.projection("2026-09-13T15:10:00Z")["findings"][0]
        self.assertEqual((finding["state"], len(finding["closure_refs"]), finding["reopen_count"]), ("closed", 2, 1))

    def test_demo_and_explicit_time_rebuild_preserve_history(self):
        ledger = self.root / "demo"
        output, report = self.root / "index.json", self.root / "report.md"
        index = run_closure_demo(ledger, output, report)
        self.assertEqual(load_transactions(ledger), self.original)
        self.assertEqual(index, strict_json((ROOT / "status/governance-lifecycle-closure-index.json").read_bytes()))
        self.assertEqual(report.read_text(), (ROOT / "generated/reports/governance-lifecycle-pilot.md").read_text())
        self.assertEqual(project(self.original, self.profile, as_of="2026-09-13T14:10:00Z")["findings"][0]["state"], "closed")
        self.assertEqual(index, project(self.original, self.profile, as_of=PILOT_AS_OF))
        bad = deepcopy(self.original)
        bad[-1]["event"]["body"]["event_type"] = "observation_added"
        with self.assertRaises(ContractError):
            project(bad, self.profile, as_of="2026-09-13T13:00:00Z")

    def test_closure_and_new_failure_race_accepts_exactly_one_revision(self):
        packet = synthetic_packet(self.profile, result="fail", observed_at="2026-09-13T14:00:00Z",
                                  recorded_at="2026-09-13T14:00:00Z", run_id="racer")
        ctx = multiprocessing.get_context("spawn")
        barrier, queue = ctx.Barrier(3), ctx.Queue()
        workers = [ctx.Process(target=race_closure, args=(self.ledger, p, self.profile, closure, barrier, queue))
                   for p, closure in (((self.closure, self.resources), True), (packet, False))]
        try:
            for worker in workers: worker.start()
            barrier.wait(timeout=30)
            results = [queue.get(timeout=30) for _ in workers]
            for worker in workers:
                worker.join(timeout=30)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(results.count("accepted"), 1)
            self.assertEqual(sum("Stale expected finding revision" in r for r in results), 1)
            self.assertEqual(self.projection()["findings"][0]["revision"], 7)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(timeout=5)
            queue.close()

    def test_cli_accepts_closure_using_only_bound_consent_file(self):
        record = self.root / "record.json"
        record.write_bytes(json_bytes(self.closure))
        resources = self.root / "resources"
        resources.mkdir()
        for uri, data in self.resources.items():
            (resources / uri.removeprefix("fixture://")).write_bytes(data)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/intake_governance_lifecycle_action.py"),
            "--synthetic", "--ledger", str(self.ledger), "--record", str(record), "--resources", str(resources),
            "--expected-revision", "6"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.projection()["findings"][0]["state"], "closed")


if __name__ == "__main__":
    unittest.main()
