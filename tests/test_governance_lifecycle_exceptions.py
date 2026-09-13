"""CLG-05 authority, observation coverage, expiry, withdrawal and immutable history."""
import base64
from copy import deepcopy
import hashlib
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
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, approval_target, record_ref
from lib.governance_lifecycle.exceptions import exception_profile
from lib.governance_lifecycle.kernel import project, replay
from lib.governance_lifecycle.store import append_action, append_closure, append_exception, append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from lib.governance_lifecycle.synthetic_actions import closure_packet, decision_packet, remediation_packet, resource
from lib.governance_lifecycle.synthetic_exceptions import exception_packet
from run_governance_lifecycle_exception_demo import EXCEPTION_AS_OF, run_exception_demo
from validate_governance_lifecycle_ledger import check_accepted_prefix

LEDGER = ROOT / "governance/lifecycle/synthetic-exceptions"


def race(ledger, packet, profile, exception, barrier, queue):
    try:
        barrier.wait(timeout=30)
        append = append_exception if exception else append_observation
        queue.put(append(ledger, *packet, profile, expected_revision=2)["outcome"])
    except Exception as error:
        queue.put(str(error))


class LifecycleExceptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        (self.ledger / "transactions").mkdir(parents=True)
        for path in sorted((LEDGER / "transactions").glob("*.json"))[:2]:
            shutil.copyfile(path, self.ledger / "transactions" / path.name)
        self.profile = strict_json(DEFAULT_PROFILE.read_bytes())
        self.observations = [tx["observation"] for tx in load_transactions(self.ledger)]

    def packet(self, observations=None, revision=2, at="2026-09-13T15:20:00Z", record_id="exception:first", **kwargs):
        return exception_packet(self.profile, self.observations[:1] if observations is None else observations,
                                record_id=record_id, revision=revision, at=at, **kwargs)

    def append(self, packet, expected=None):
        return append_exception(self.ledger, *packet, self.profile,
                                expected_revision=packet[0]["body"]["expected_revision"] if expected is None else expected)

    def projection(self, as_of="2026-09-13T17:00:00Z"):
        return project(load_transactions(self.ledger), self.profile, as_of=as_of)

    def treatment(self, as_of="2026-09-13T17:00:00Z"):
        return self.projection(as_of)["findings"][0]["exception_treatment"]

    def resign(self, packet):
        record, resources = packet
        approval = record["approval"]
        resources.pop(approval["proof_ref"]["uri"])
        approval["target_digest"] = approval_target(record)
        proof, extra = resource({"environment": "synthetic", "approval": {k: v for k, v in approval.items() if k != "proof_ref"}})
        approval["proof_ref"] = proof
        resources.update(extra)
        return packet

    def change_waiver(self, packet, changes):
        record, resources = packet
        waiver = strict_json(resources.pop(record["body"]["waiver_ref"]["uri"]))
        waiver.update(changes)
        ref, extra = resource(waiver)
        record["body"]["waiver_ref"] = ref
        resources.update(extra)
        return self.resign(packet)

    def observe(self, revision, at="2026-09-13T15:40:00Z", run="new", result="fail"):
        packet = synthetic_packet(self.profile, result=result, observed_at=at, recorded_at=at, run_id=run)
        append_observation(self.ledger, *packet, self.profile, expected_revision=revision)
        return packet[0]

    def test_partial_coverage_leaves_residual_without_changing_state_or_occurrences(self):
        self.append(self.packet())
        finding = self.projection()["findings"][0]
        t = finding["exception_treatment"]
        self.assertEqual((finding["state"], finding["occurrences"], finding["evidence_status"]), ("open", 2, "fail"))
        self.assertEqual(t["coverage"], "partial")
        self.assertEqual(t["covered_observation_refs"], [record_ref(self.observations[0])])
        self.assertEqual(t["uncovered_observation_refs"], [record_ref(self.observations[1])])
        self.assertEqual(self.projection()["counts"]["closures"], 0)

    def test_overlapping_grants_union_without_double_counting_and_new_fail_stays_uncovered(self):
        self.append(self.packet())
        self.append(self.packet(self.observations, revision=3, at="2026-09-13T15:30:00Z",
                                record_id="exception:second", waiver_id="synthetic-waiver:second"))
        self.assertEqual(self.treatment()["coverage"], "full")
        self.assertEqual(len(self.treatment()["covered_observation_refs"]), 2)
        new = self.observe(4)
        self.assertEqual(self.treatment()["coverage"], "partial")
        self.assertEqual(self.treatment()["uncovered_observation_refs"], [record_ref(new)])
        self.assertEqual(self.projection()["findings"][0]["state"], "open")

    def test_revoking_one_overlapping_grant_preserves_other_active_coverage(self):
        first = self.packet(self.observations)
        self.append(first)
        self.append(self.packet(self.observations, revision=3, at="2026-09-13T15:30:00Z",
                                record_id="exception:second", waiver_id="synthetic-waiver:second"))
        self.append(self.packet(self.observations, revision=4, at="2026-09-13T15:40:00Z", record_id="exception:revoke",
                               disposition="revoke", previous=first[0], previous_resources=first[1]))
        self.assertEqual(self.treatment()["coverage"], "full")
        self.assertFalse(self.treatment()["renewed_decision_required"])

    def test_reopened_finding_cannot_reuse_previous_episode_coverage(self):
        ledger = self.root / "reopened"
        source = ROOT / "governance/lifecycle/synthetic-closure"
        shutil.copytree(source, ledger, ignore=shutil.ignore_patterns('.append.lock', '.pending-*'))
        history = load_transactions(ledger)
        old = history[0]["observation"]
        packet = exception_packet(self.profile, [old], record_id="exception:old-episode", revision=9,
                                  at="2026-09-13T15:00:00Z")
        with self.assertRaisesRegex(ContractError, "previous closed episode"):
            append_exception(ledger, *packet, self.profile, expected_revision=9)
        new = history[-1]["observation"]
        packet = exception_packet(self.profile, [new], record_id="exception:new-episode", revision=9,
                                  at="2026-09-13T15:00:00Z")
        append_exception(ledger, *packet, self.profile, expected_revision=9)
        finding = project(load_transactions(ledger), self.profile, as_of="2026-09-13T16:00:00Z")["findings"][0]
        self.assertEqual((finding["state"], finding["exception_treatment"]["coverage"], finding["reopen_count"]), ("open", "full", 1))
        self.assertEqual(len(finding["exception_treatment"]["covered_observation_refs"]), 1)

    def test_expiry_is_exclusive_and_computed_without_changing_source_flag(self):
        packet = self.packet(self.observations)
        self.append(packet)
        before = load_transactions(self.ledger)
        self.assertEqual(self.treatment("2026-09-13T23:59:59Z")["coverage"], "full")
        expired = self.treatment("2026-09-14T00:00:00Z")
        self.assertEqual(expired["coverage"], "none")
        self.assertTrue(expired["renewed_decision_required"])
        self.assertEqual(expired["exception_records"][0]["status"], "expired")
        self.assertEqual(before, load_transactions(self.ledger))
        self.assertFalse(strict_json(packet[1][packet[0]["body"]["waiver_ref"]["uri"]])["expired"])

    def test_future_start_does_not_cover_early(self):
        self.append(self.packet(valid_from="2026-09-13T18:00:00Z"))
        self.assertEqual(self.treatment()["coverage"], "none")
        self.assertEqual(self.treatment()["exception_records"][0]["status"], "scheduled")
        self.assertEqual(self.treatment("2026-09-13T18:00:00Z")["coverage"], "partial")

    def test_withdrawal_and_old_retry_cannot_reactivate_coverage(self):
        grant = self.packet(self.observations)
        self.append(grant)
        revoke = self.packet(self.observations, revision=3, at="2026-09-13T15:30:00Z", record_id="exception:revoke",
                             disposition="revoke", previous=grant[0], previous_resources=grant[1])
        self.append(revoke)
        self.assertEqual(self.append(grant)["outcome"], "duplicate")
        self.assertEqual(self.append(revoke)["outcome"], "duplicate")
        self.assertEqual(self.treatment()["coverage"], "none")
        self.assertTrue(self.treatment()["renewed_decision_required"])
        again = self.packet(revision=4, at="2026-09-13T15:40:00Z", record_id="exception:again",
                            disposition="revoke", previous=grant[0], previous_resources=grant[1])
        with self.assertRaisesRegex(ContractError, "not yet withdrawn"):
            self.append(again)

    def test_withdrawal_after_expiry_is_still_auditable(self):
        grant = self.packet()
        self.append(grant)
        self.append(self.packet(revision=3, at="2026-09-14T00:10:00Z", record_id="exception:late-revoke",
            disposition="revoke", previous=grant[0], previous_resources=grant[1]))
        self.assertEqual(self.treatment("2026-09-14T00:10:00Z")["exception_records"][0]["status"], "revoked")

    def test_rejection_grants_no_authority(self):
        rejected = self.packet(disposition="reject")
        self.append(rejected)
        self.assertEqual(self.treatment()["coverage"], "none")
        self.assertEqual(self.treatment()["exception_records"][0]["status"], "rejected")
        revoke = self.packet(revision=3, record_id="exception:bad-revoke", at="2026-09-13T15:30:00Z",
                             disposition="revoke", previous=rejected[0], previous_resources=rejected[1])
        with self.assertRaisesRegex(ContractError, "previously approved"):
            self.append(revoke)

    def test_all_risk_classes_use_existing_authority_snapshot_and_critical_is_joint(self):
        p = exception_profile()
        self.assertEqual(p["authority_model"].encode(), (ROOT / "model/waivers/waiver-authorities.yaml").read_bytes())
        for i, risk in enumerate(p["bindings"]):
            packet = self.packet(risk=risk, revision=2+i, record_id=f"exception:risk-{i}", waiver_id=f"synthetic-waiver:risk-{i}")
            self.append(packet)
        self.assertEqual(len(p["bindings"]["critical"]["subjects"]), 2)
        for subjects in (["test-human:cdo"], ["test-human:cscso"], ["test-human:cdo", "test-human:cdo"]):
            packet = self.packet(risk="critical", revision=7, record_id="exception:bad-critical", waiver_id="synthetic-waiver:bad")
            packet[0]["approval"]["subjects"] = subjects
            with self.subTest(subjects=subjects), self.assertRaises((ContractError, ValidationError)):
                self.append(self.resign(packet))

    def test_remediation_actor_wrong_authority_bot_or_unbound_profile_is_rejected(self):
        for field, value in (("subjects", ["test-human:decision-owner"]), ("authority", "CISO"), ("subject_type", "bot")):
            packet = self.packet()
            packet[0]["approval"][field] = value
            with self.subTest(field=field), self.assertRaises((ContractError, ValidationError)):
                self.append(self.resign(packet))
        packet = self.packet()
        packet[0]["approval"]["exception_profile_ref"]["digest"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "profile binding"):
            self.append(self.resign(packet))

    def test_waiver_contract_scope_requirement_and_controls_are_checked(self):
        for changes in ({"scope":"refs/heads/other"}, {"object_id":"finding:other"}, {"affected_requirements":["ARCH-001"]},
                        {"compensating_controls":[]}, {"approval_authority":"CISO"}, {"approved_by":"bot"},
                        {"environment":"live"}, {"status":"requested"}, {"expired":True}):
            with self.subTest(changes=changes), self.assertRaises((ContractError, ValidationError)):
                self.append(self.change_waiver(self.packet(), changes))

    def test_architecture_exception_payload_does_not_enter_devsecops_adapter(self):
        packet = self.packet()
        record, resources = packet
        resources.pop(record["body"]["waiver_ref"]["uri"])
        ref, extra = resource({"environment":"synthetic", "status":"approved", "target":{"type":"guardrail","id":"ARCH-001"}})
        record["body"]["waiver_ref"] = ref
        resources.update(extra)
        with self.assertRaises(ValidationError):
            self.append(self.resign(packet))

    def test_content_changes_and_missing_or_tampered_proofs_fail(self):
        packet = self.packet()
        packet[0]["body"]["covered_observation_refs"] = [record_ref(self.observations[1])]
        with self.assertRaisesRegex(ContractError, "content binding"):
            self.append(packet)
        for change in ("missing", "tamper"):
            packet = self.packet()
            uri = packet[0]["approval"]["proof_ref"]["uri"]
            if change == "missing": packet[1].pop(uri)
            else: packet[1][uri] += b" "
            with self.subTest(change=change), self.assertRaises(ContractError): self.append(packet)

    def test_stale_revision_relabelled_consent_and_reused_id_fail(self):
        packet = self.packet()
        self.append(packet)
        with self.assertRaisesRegex(ContractError, "Stale expected"):
            self.append(self.packet(record_id="exception:stale", waiver_id="synthetic-waiver:stale"))
        new = self.packet(revision=3, at="2026-09-13T15:30:00Z", record_id="exception:new", waiver_id="synthetic-waiver:new")
        new[0]["approval"]["issued_at"] = "2026-09-13T15:15:00Z"
        with self.assertRaisesRegex(ContractError, "consent predates"):
            self.append(self.resign(new))
        changed = deepcopy(packet)
        changed[0]["body"]["valid_from"] = "2026-09-13T16:00:00Z"
        with self.assertRaisesRegex(ContractError, "different immutable content"):
            self.append(self.resign(changed))

    def test_window_mismatch_retroactivity_and_invalid_expiry_are_rejected(self):
        for field, value in (("valid_from","2026-09-13T15:00:00Z"), ("expires_at","2026-09-14T00:00:01Z"),
                             ("valid_from","2026-09-15T00:00:00Z")):
            packet = self.packet()
            packet[0]["body"][field] = value
            with self.subTest(field=field,value=value), self.assertRaises(ContractError): self.append(self.resign(packet))
        with self.assertRaises(ContractError):
            self.append(self.packet(expiry="2026-09-12"))

    def test_coverage_cannot_include_pass_unknown_or_mutated_refs(self):
        passing = self.observe(2, result="pass")
        with self.assertRaisesRegex(ContractError, "accepted failures"):
            self.append(self.packet([passing], revision=3, at="2026-09-13T15:50:00Z"))
        packet = self.packet(revision=3, at="2026-09-13T15:50:00Z")
        packet[0]["body"]["covered_observation_refs"][0]["digest"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "reference binding"):
            self.append(self.resign(packet))

    def test_withdrawal_cannot_change_coverage_or_deadline(self):
        first = self.packet()
        self.append(first)
        revoke = self.packet(revision=3, at="2026-09-13T15:30:00Z", record_id="exception:revoke",
                             disposition="revoke", previous=first[0], previous_resources=first[1])
        revoke[0]["body"]["covered_observation_refs"] = [record_ref(self.observations[1])]
        with self.assertRaisesRegex(ContractError, "unchanged grant"):
            self.append(self.resign(revoke))

    def test_renewal_needs_fresh_id_consent_and_does_not_duplicate_coverage(self):
        self.append(self.packet())
        with self.assertRaisesRegex(ContractError, "fresh waiver ID"):
            self.append(self.packet(revision=3, at="2026-09-14T00:10:00Z", record_id="exception:renewal", expiry="2026-09-14"))
        self.append(self.packet(self.observations, revision=3, at="2026-09-14T00:10:00Z", record_id="exception:renewal",
                                waiver_id="synthetic-waiver:renewed", expiry="2026-09-14"))
        t = self.treatment("2026-09-14T00:10:00Z")
        self.assertEqual(t["coverage"], "full")
        self.assertFalse(t["renewed_decision_required"])
        self.assertEqual(t["exception_records"][0]["status"], "expired")

    def test_remediation_progress_and_exception_coverage_coexist(self):
        decision = decision_packet(self.profile, self.observations[0], record_id="decision:parallel", revision=2,
                                   at="2026-09-13T15:20:00Z", case_id="remediation-case:parallel")
        append_action(self.ledger, *decision, self.profile, expected_revision=2)
        self.append(self.packet(self.observations, revision=3, at="2026-09-13T15:30:00Z"))
        planned = remediation_packet(*decision, record_id="remediation:parallel", revision=4, at="2026-09-13T15:40:00Z")
        append_action(self.ledger, *planned, self.profile, expected_revision=4)
        finding = self.projection()["findings"][0]
        self.assertEqual((finding["state"], finding["remediation_cases"][0]["progress"], finding["exception_treatment"]["coverage"]),
                         ("open", "planned", "full"))

    def test_conflicts_remain_visible_even_with_full_accepted_observation_coverage(self):
        self.append(self.packet(self.observations))
        packet = synthetic_packet(self.profile, result="pass", observed_at="2026-09-13T15:00:00Z",
                                  recorded_at="2026-09-13T15:30:00Z", run_id="conflicting")
        append_observation(self.ledger, *packet, self.profile, expected_revision=3)
        finding = self.projection()["findings"][0]
        self.assertEqual(finding["state"], "needs_clarification")
        self.assertEqual(len(finding["conflict_refs"]), 1)
        self.assertEqual(finding["exception_treatment"]["coverage"], "full")

    def test_genuine_closure_ends_outstanding_episode_without_waiver_based_closure(self):
        ledger = self.root / "closure"
        (ledger / "transactions").mkdir(parents=True)
        source = ROOT / "governance/lifecycle/synthetic-closure/transactions"
        for path in sorted(source.glob("*.json"))[:6]: shutil.copyfile(path, ledger / "transactions" / path.name)
        history = load_transactions(ledger)
        packet = exception_packet(self.profile, [history[0]["observation"]], record_id="exception:closing", revision=6,
                                  at="2026-09-13T13:55:00Z")
        append_exception(ledger, *packet, self.profile, expected_revision=6)
        self.assertEqual(project(load_transactions(ledger), self.profile, as_of="2026-09-13T13:55:00Z")["findings"][0]["state"], "open")
        closure = closure_packet(self.profile, history[0]["observation"], history[5]["observation"], history[4]["record"],
                                 record_id="closure:after-waiver", revision=7, at="2026-09-13T14:00:00Z")
        append_closure(ledger, *closure, self.profile, expected_revision=7)
        finding = project(load_transactions(ledger), self.profile, as_of="2026-09-14T01:00:00Z")["findings"][0]
        self.assertEqual((finding["state"], finding["exception_treatment"]["coverage"]), ("closed", "not_applicable"))
        self.assertFalse(finding["exception_treatment"]["renewed_decision_required"])

    def test_demo_rebuild_expiry_and_historical_replay_are_deterministic(self):
        ledger = self.root / "demo"
        result = run_exception_demo(ledger, self.root / "index.json", self.root / "report.md")
        self.assertEqual(load_transactions(ledger), load_transactions(LEDGER))
        self.assertEqual(result, strict_json((ROOT / "status/governance-lifecycle-exception-index.json").read_bytes()))
        self.assertEqual((self.root / "report.md").read_bytes(), (ROOT / "generated/reports/governance-lifecycle-exceptions.md").read_bytes())
        for at, coverage in (("16:00", "partial"), ("16:10", "full"), ("16:20", "partial"), ("16:30", "partial")):
            historical = project(load_transactions(ledger), self.profile, as_of=f"2026-09-13T{at}:00Z")
            self.assertEqual(historical["findings"][0]["exception_treatment"]["coverage"], coverage)
        bad = load_transactions(ledger)
        bad[-1]["event"]["body"]["revision"] += 1
        with self.assertRaises(ContractError):
            project(bad, self.profile, as_of="2026-09-13T15:00:00Z")

    def test_cli_intake_requires_explicit_synthetic_consent_resources(self):
        packet = self.packet()
        record = self.root / "record.json"
        record.write_bytes(json_bytes(packet[0]))
        directory = self.root / "resources"
        directory.mkdir()
        for uri, data in packet[1].items(): (directory / uri.removeprefix("fixture://")).write_bytes(data)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/intake_governance_lifecycle_action.py"), "--synthetic",
            "--ledger", str(self.ledger), "--record", str(record), "--resources", str(directory), "--expected-revision", "2"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(strict_json(result.stdout)["outcome"], "accepted")

    def test_concurrent_exception_and_failure_cannot_consume_same_revision(self):
        failure = synthetic_packet(self.profile, result="fail", observed_at="2026-09-13T15:20:00Z",
                                   recorded_at="2026-09-13T15:20:00Z", run_id="racer")
        ctx = multiprocessing.get_context("spawn")
        barrier, queue = ctx.Barrier(3), ctx.Queue()
        workers = [ctx.Process(target=race, args=(self.ledger, packet, self.profile, is_exception, barrier, queue))
                   for packet, is_exception in ((self.packet(), True), (failure, False))]
        try:
            for worker in workers: worker.start()
            barrier.wait(timeout=30)
            results = [queue.get(timeout=30) for _ in workers]
            for worker in workers:
                worker.join(timeout=30)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(results.count("accepted"), 1)
            self.assertEqual(sum("Stale expected finding revision" in r for r in results), 1)
        finally:
            for worker in workers:
                if worker.is_alive(): worker.terminate(); worker.join(timeout=5)
            queue.close()

    def test_git_prefix_protects_exception_transactions_and_profile_snapshot(self):
        root = self.root / "git"
        root.mkdir()
        def git(*args): return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()
        git("init", "-b", "main");git("config", "user.name", "Test");git("config", "user.email", "test@example.invalid");git("config", "commit.gpgsign", "false")
        target = root / "governance/lifecycle/synthetic-exceptions"
        shutil.copytree(LEDGER, target, ignore=shutil.ignore_patterns('.append.lock', '.pending-*'))
        models = root / "model/governance/lifecycle"
        models.mkdir(parents=True)
        for name in ("synthetic-grs002-profile.json", "synthetic-exception-profile.json"):
            shutil.copyfile(ROOT / "model/governance/lifecycle" / name, models / name)
        git("add", ".");git("commit", "-m", "accepted exception scenario")
        base = git("rev-parse", "HEAD")
        self.assertEqual(check_accepted_prefix(root, base), 9)
        profile = models / "synthetic-exception-profile.json"
        profile.write_bytes(profile.read_bytes() + b" ")
        with self.assertRaisesRegex(ContractError, "versioned migration"):
            check_accepted_prefix(root, base)
        profile.write_bytes((ROOT / "model/governance/lifecycle/synthetic-exception-profile.json").read_bytes())
        next((target / "transactions").glob("*.json")).unlink()
        with self.assertRaisesRegex(ContractError, "deleted"):
            check_accepted_prefix(root, base)


if __name__ == "__main__":
    unittest.main()
