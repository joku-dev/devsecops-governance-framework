"""CLG-02 persistence, replay, concurrency and Git-merge regression checks."""
from copy import deepcopy
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.governance_lifecycle.adapter import adapt_grs002, json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, canonical_digest, require
from lib.governance_lifecycle.kernel import project, replay, transaction_name
from lib.governance_lifecycle.store import append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from generate_governance_lifecycle_index import DEFAULT_PROFILE
from run_governance_lifecycle_synthetic_demo import DEMO_AS_OF, run_demo
from validate_governance_lifecycle_ledger import check_accepted_prefix, validate_current


def concurrent_append(root, profile, run_id, barrier, queue):
    try:
        observation, resources = synthetic_packet(profile, result="fail", observed_at="2026-09-13T10:00:00Z",
                                                   recorded_at="2026-09-13T10:00:00Z", run_id=run_id)
        barrier.wait(timeout=30)
        queue.put(append_observation(root, observation, resources, profile, expected_revision=0)["outcome"])
    except Exception as error:
        queue.put(type(error).__name__ + ": " + str(error))


class LifecycleKernelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        self.profile = strict_json(DEFAULT_PROFILE.read_bytes())

    def packet(self, result="fail", observed="10:00", recorded=None, run="run-1", policy="0.1.0"):
        return synthetic_packet(self.profile, result=result, observed_at=f"2026-09-13T{observed}:00Z",
                                recorded_at=f"2026-09-13T{recorded or observed}:00Z", run_id=run,
                                policy_version=policy)

    def append(self, packet, expected=0, ledger=None):
        return append_observation(ledger or self.ledger, *packet, self.profile, expected_revision=expected)

    def projection(self, as_of=DEMO_AS_OF):
        return project(load_transactions(self.ledger), self.profile, as_of=as_of)

    def test_adapter_preserves_criterion_and_raw_bytes_without_changing_inputs(self):
        observation, resources = self.packet()
        trust = deepcopy(observation["body"]["trust"])
        context = deepcopy(observation["body"]["source_context"])
        before = deepcopy((trust, context))
        raw = resources[observation["body"]["snapshot_ref"]["uri"]]
        again, rebuilt = adapt_grs002(raw, context, trust, recorded_at=observation["recorded_at"],
                                      profile=self.profile, policy_version="0.1.0")
        self.assertEqual(observation, again)
        self.assertEqual(resources, rebuilt)
        self.assertEqual(before, (trust, context))
        self.assertEqual(again["body"]["result"], "fail")

    def test_adapter_rejects_live_context_or_summary_without_criterion(self):
        record, resources = self.packet()
        raw = resources[record["body"]["snapshot_ref"]["uri"]]
        context = deepcopy(record["body"]["source_context"])
        context["kind"] = "mainline"
        with self.assertRaisesRegex(ContractError, "synthetic test context"):
            adapt_grs002(raw, context, record["body"]["trust"], recorded_at=record["recorded_at"],
                          profile=self.profile, policy_version="0.1.0")
        context["kind"] = "test"
        report = strict_json(raw)
        report["criteria"] = [c for c in report["criteria"] if c["id"] != "GRS-002"]
        with self.assertRaisesRegex(ContractError, "Exactly one GRS-002"):
            adapt_grs002(json_bytes(report), context, record["body"]["trust"], recorded_at=record["recorded_at"],
                          profile=self.profile, policy_version="0.1.0")

    def test_strict_json_rejects_ambiguous_objects_and_nonfinite_numbers(self):
        for payload in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                strict_json(payload)

    def test_first_fail_opens_one_finding_and_pass_alone_does_not_close(self):
        self.append(self.packet())
        self.append(self.packet("pass", "11:00", run="run-2"), expected=1)
        index = self.projection()
        self.assertEqual(index["counts"], {"transactions": 2, "observations": 2, "events": 2, "conflicts": 0, "findings": 1})
        finding = index["findings"][0]
        self.assertEqual((finding["state"], finding["evidence_status"], finding["occurrences"]), ("open", "pass", 1))
        self.assertFalse(finding["closure_supported"])
        self.assertFalse(index["official_state"])

    def test_pass_before_first_failure_is_preserved_without_phantom_finding(self):
        self.append(self.packet("pass", "10:00"))
        self.assertEqual(self.projection()["counts"], {"transactions": 1, "observations": 1, "events": 0, "conflicts": 0, "findings": 0})
        self.append(self.packet("fail", "10:10", run="run-2"))
        self.assertEqual(self.projection()["findings"][0]["revision"], 1)
        self.assertEqual(len(self.projection()["findings"][0]["observation_refs"]), 2)

    def test_identical_redelivery_is_durable_noop_even_with_original_revision(self):
        first = self.packet()
        self.append(first)
        before = {p.name: p.read_bytes() for p in (self.ledger / "transactions").iterdir()}
        self.assertEqual(self.append(self.packet(recorded="10:01"))["outcome"], "duplicate")
        after = {p.name: p.read_bytes() for p in (self.ledger / "transactions").iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(self.projection()["findings"][0]["occurrences"], 1)

    def test_independent_failure_increments_existing_finding(self):
        self.append(self.packet())
        original_id = self.projection()["findings"][0]["finding_id"]
        self.append(self.packet(observed="10:10", run="run-2"), expected=1)
        self.assertEqual(self.projection()["findings"][0]["finding_id"], original_id)
        self.assertEqual(self.projection()["findings"][0]["occurrences"], 2)

    def test_late_failure_does_not_replace_newer_pass(self):
        self.append(self.packet())
        self.append(self.packet("pass", "11:00", run="run-2"), expected=1)
        self.append(self.packet("fail", "10:10", "11:10", "run-3"), expected=2)
        finding = self.projection()["findings"][0]
        self.assertEqual(finding["evidence_status"], "pass")
        self.assertEqual(finding["occurrences"], 2)
        self.assertEqual(finding["revision"], 3)

    def test_newer_failure_is_visible_without_claiming_reopening(self):
        self.append(self.packet())
        self.append(self.packet("pass", "10:10", run="run-2"), expected=1)
        self.append(self.packet("fail", "11:00", run="run-3"), expected=2)
        self.assertEqual(self.projection()["findings"][0]["evidence_status"], "fail")
        self.assertEqual(self.projection()["findings"][0]["state"], "open")

    def test_same_producer_conflict_is_quarantined_idempotently(self):
        self.append(self.packet())
        conflict = self.packet("pass", "10:00", "10:10")
        self.assertEqual(self.append(conflict, expected=1)["outcome"], "quarantined")
        self.assertEqual(self.append(conflict, expected=1)["outcome"], "duplicate")
        index = self.projection()
        self.assertEqual(index["counts"]["observations"], 1)
        self.assertEqual(index["counts"]["conflicts"], 1)
        self.assertEqual(index["findings"][0]["state"], "needs_clarification")
        self.assertEqual(index["findings"][0]["occurrences"], 1)
        self.assertEqual(load_transactions(self.ledger)[1]["reason"], "producer_conflict")

    def test_changed_trust_assessment_is_preserved_for_review(self):
        self.append(self.packet())
        record, resources = self.packet(recorded="10:10")
        trust = deepcopy(record["body"]["trust"])
        trust["verified_at"] = "2026-09-13T10:05:00Z"
        changed, changed_resources = adapt_grs002(
            resources[record["body"]["snapshot_ref"]["uri"]], record["body"]["source_context"], trust,
            recorded_at=record["recorded_at"], profile=self.profile, policy_version="0.1.0")
        self.assertEqual(self.append((changed, changed_resources), expected=1)["outcome"], "quarantined")
        transactions = load_transactions(self.ledger)
        self.assertEqual(transactions[-1]["reason"], "reassessment_required")
        self.assertEqual(transactions[-1]["observation"]["body"]["trust"], trust)
        self.assertEqual(self.projection()["counts"]["observations"], 1)

    def test_tampered_resource_is_rejected_before_publication(self):
        record, resources = self.packet()
        resources[record["body"]["snapshot_ref"]["uri"]] += b" "
        with self.assertRaisesRegex(ContractError, "digest mismatch"):
            self.append((record, resources))
        self.assertEqual(load_transactions(self.ledger), [])

    def test_incompatible_policy_and_ambiguous_time_are_visible_conflicts(self):
        self.append(self.packet())
        self.append(self.packet(observed="10:10", run="run-2", policy="0.2.0"), expected=1)
        self.append(self.packet("pass", "10:00", "10:20", "run-3"), expected=2)
        self.assertEqual([tx["reason"] for tx in load_transactions(self.ledger)],
                         ["new_observation", "incompatible_version", "ambiguous_time"])
        self.assertEqual(self.projection()["findings"][0]["occurrences"], 1)

    def test_conflict_before_first_failure_still_appears_in_index(self):
        self.append(self.packet("pass"))
        self.append(self.packet("fail", "10:00", "10:10"))
        index = self.projection()
        self.assertEqual(index["counts"]["findings"], 0)
        self.assertEqual(len(index["conflict_refs"]), 1)

    def test_stale_revision_fails_without_any_append(self):
        self.append(self.packet())
        with self.assertRaisesRegex(ContractError, "Stale expected finding revision"):
            self.append(self.packet(observed="10:10", run="run-2"), expected=0)
        self.assertEqual(len(load_transactions(self.ledger)), 1)

    def test_two_real_processes_cannot_both_consume_revision_zero(self):
        ctx = multiprocessing.get_context("spawn")
        barrier, queue = ctx.Barrier(3), ctx.Queue()
        workers = [ctx.Process(target=concurrent_append, args=(self.ledger, self.profile, f"writer-{i}", barrier, queue)) for i in range(2)]
        try:
            for worker in workers:
                worker.start()
            barrier.wait(timeout=30)
            results = [queue.get(timeout=30) for _ in workers]
            for worker in workers:
                worker.join(timeout=30)
                self.assertEqual(worker.exitcode, 0)
            self.assertEqual(results.count("accepted"), 1)
            self.assertEqual(sum("Stale expected finding revision" in value for value in results), 1)
            self.assertEqual(self.projection()["counts"]["events"], 1)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(timeout=5)
            queue.close()

    def test_failure_before_atomic_publication_leaves_no_transaction(self):
        with patch("lib.governance_lifecycle.store.os.link", side_effect=OSError("simulated publish failure")):
            with self.assertRaisesRegex(OSError, "publish failure"):
                self.append(self.packet())
        self.assertEqual(load_transactions(self.ledger), [])
        self.assertEqual(list((self.ledger / "transactions").iterdir()), [])
        self.assertEqual(self.append(self.packet())["outcome"], "accepted")

    def test_retry_after_publication_error_does_not_duplicate_commit(self):
        with patch("lib.governance_lifecycle.store.os.fsync", side_effect=[None, OSError("after link")]):
            with self.assertRaisesRegex(OSError, "after link"):
                self.append(self.packet())
        self.assertEqual(len(load_transactions(self.ledger)), 1)
        self.assertEqual(self.append(self.packet())["outcome"], "duplicate")

    def test_partial_unpublished_file_is_ignored_and_symlink_is_rejected(self):
        directory = self.ledger / "transactions"
        directory.mkdir(parents=True)
        (directory / ".pending-crashed").write_text('{"partial":')
        self.append(self.packet())
        self.assertEqual(len(load_transactions(self.ledger)), 1)
        (directory / "bad.json").symlink_to(next(directory.glob("*.json")))
        with self.assertRaisesRegex(ContractError, "symlink"):
            load_transactions(self.ledger)

    def test_replay_detects_tampering_sequence_gaps_and_mutated_events(self):
        self.append(self.packet())
        original = load_transactions(self.ledger)
        for field in ("sequence", "transaction_id", "event"):
            with self.subTest(field=field):
                data = deepcopy(original)
                if field == "sequence": data[0][field] = 2
                elif field == "transaction_id": data[0][field] = "transaction:" + "0" * 64
                else: data[0]["event"]["recorded_at"] = "2026-09-13T10:01:00Z"
                with self.assertRaises(ContractError):
                    replay(data, self.profile)

    def test_as_of_replay_is_deterministic_without_modifying_sources(self):
        self.append(self.packet())
        self.append(self.packet("pass", "11:00", run="run-2"), expected=1)
        transactions = load_transactions(self.ledger)
        before = deepcopy(transactions)
        at_first = project(transactions, self.profile, as_of="2026-09-13T10:00:00Z")
        self.assertEqual(at_first["counts"]["observations"], 1)
        self.assertEqual(at_first["findings"][0]["evidence_status"], "fail")
        self.assertEqual(self.projection(), self.projection())
        self.assertEqual(transactions, before)
        self.assertEqual(self.projection("2026-09-13T09:59:59Z")["counts"]["findings"], 0)

    def test_demo_rebuild_matches_checked_in_ledger_and_projection(self):
        output = self.root / "index.json"
        result = run_demo(self.ledger, output)
        expected = strict_json((ROOT / "status/governance-lifecycle-synthetic-index.json").read_bytes())
        self.assertEqual(result, expected)
        self.assertEqual(load_transactions(self.ledger), load_transactions(ROOT / "governance/lifecycle/synthetic"))
        self.assertEqual(result["findings"][0]["state"], "needs_clarification")
        self.assertEqual(result["findings"][0]["evidence_status"], "pass")
        self.assertEqual(result["findings"][0]["occurrences"], 3)
        with self.assertRaisesRegex(ContractError, "empty ledger"):
            run_demo(self.ledger, output)

    def test_current_index_cannot_hide_later_history_or_invent_counts(self):
        output = self.root / "index.json"
        run_demo(self.ledger, output)
        index = self.projection("2026-09-13T10:00:00Z")
        output.write_bytes(json_bytes(index))
        with self.assertRaisesRegex(ContractError, "cannot hide"):
            validate_current(self.ledger, output, DEFAULT_PROFILE)
        index = self.projection()
        index["counts"]["observations"] = 999
        output.write_bytes(json_bytes(index))
        with self.assertRaisesRegex(ContractError, "differs"):
            validate_current(self.ledger, output, DEFAULT_PROFILE)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL).strip()

    def setup_git(self):
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Lifecycle Test")
        self.git("config", "user.email", "lifecycle@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.ledger = self.root / "governance/lifecycle/synthetic"
        profile_path = self.root / "model/governance/lifecycle/synthetic-grs002-profile.json"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_bytes(DEFAULT_PROFILE.read_bytes())
        (self.root / ".gitignore").write_text(".append.lock\n.pending-*\n")
        self.append(self.packet())
        self.git("add", ".")
        self.git("commit", "-m", "accepted initial observation")
        return self.git("rev-parse", "HEAD")

    def test_git_prefix_rejects_modified_deleted_or_reprofiled_history(self):
        base = self.setup_git()
        self.assertEqual(check_accepted_prefix(self.root, base), 1)
        path = next((self.ledger / "transactions").glob("*.json"))
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(ContractError, "modified"):
            check_accepted_prefix(self.root, base)
        path.unlink()
        with self.assertRaisesRegex(ContractError, "deleted"):
            check_accepted_prefix(self.root, base)
        path.write_bytes(original)
        profile_path = self.root / "model/governance/lifecycle/synthetic-grs002-profile.json"
        profile_path.write_bytes(profile_path.read_bytes() + b" ")
        with self.assertRaisesRegex(ContractError, "versioned migration"):
            check_accepted_prefix(self.root, base)

    def test_two_individually_valid_git_branches_fail_after_merge_then_can_reprepare(self):
        base = self.setup_git()
        self.git("checkout", "-b", "proposal-a")
        self.append(self.packet(observed="10:10", run="proposal-a"), expected=1)
        self.git("add", ".")
        self.git("commit", "-m", "first proposal")
        first = self.git("rev-parse", "HEAD")
        replay(load_transactions(self.ledger), self.profile)
        self.git("checkout", "-b", "proposal-b", base)
        packet_b = self.packet(observed="10:20", run="proposal-b")
        self.append(packet_b, expected=1)
        self.git("add", ".")
        self.git("commit", "-m", "second proposal")
        second_tx = load_transactions(self.ledger)[-1]
        replay(load_transactions(self.ledger), self.profile)
        self.git("merge", "--no-edit", "proposal-a")
        # Git merges the different transaction filenames cleanly; semantic replay rejects the fork.
        with self.assertRaises(ContractError):
            replay(load_transactions(self.ledger), self.profile)
        check_accepted_prefix(self.root, first)
        (self.ledger / "transactions" / transaction_name(second_tx)).unlink()
        self.append(packet_b, expected=2)
        check_accepted_prefix(self.root, first)
        index = self.projection()
        self.assertEqual(index["findings"][0]["revision"], 3)
        self.assertEqual(index["findings"][0]["occurrences"], 3)


if __name__ == "__main__":
    unittest.main()
