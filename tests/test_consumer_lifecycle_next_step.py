"""The read-only lifecycle guidance follows the recorded action and evidence chain."""
import unittest

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.consumer_lifecycle_next_step import _current_step, build


class ConsumerLifecycleNextStepTests(unittest.TestCase):
    def setUp(self):
        self.index = {
            "official_state": True,
            "operating_acceptance": {"effective": True},
        }
        self.candidate = {"finding_state": "closed", "counts": {"quarantined": 0}}
        self.common = {
            "transaction_id": "transaction:" + "a" * 64,
            "sequence": 1,
            "recorded_at": "2026-10-03T10:00:00Z",
        }

    def test_closed_case_has_no_pending_action_and_links_to_workflow(self):
        step = _current_step(
            self.index,
            [],
            [],
            {"roles_active": True, "closure": self.common},
            self.candidate,
        )
        self.assertEqual("closed_wait", step["id"])
        self.assertIsNone(step["operation"])
        self.assertTrue(any(link["url"].endswith("consumer-lifecycle-update.yml") for link in step["links"]))

    def test_open_failure_recommends_a_decision_with_direct_evidence_links(self):
        failure = {
            **self.common,
            "outcome": "eligible_for_pilot",
            "criterion": {"status": "fail", "id": "operation_readiness"},
            "source": {"observed_at": "2026-10-03T09:00:00Z", "run_id": 12345, "run_attempt": 1},
        }
        step = _current_step(
            self.index,
            [failure],
            [],
            {"roles_active": True, "closure": None, "decision": None, "progress": None},
            {"finding_state": "open", "counts": {"quarantined": 0}},
        )
        self.assertEqual("decision_required", step["id"])
        self.assertTrue(any("actions/runs/12345" in link["url"] for link in step["links"]))
        self.assertTrue(any("transactions/00000001-" in link["url"] for link in step["links"]))

    def test_completed_work_requires_a_newer_pass_before_closure(self):
        failure = {
            **self.common,
            "outcome": "eligible_for_pilot",
            "criterion": {"status": "fail", "id": "operation_readiness"},
            "source": {"observed_at": "2026-10-03T08:00:00Z", "run_id": 100, "run_attempt": 1},
        }
        completed = {
            **self.common,
            "recorded_at": "2026-10-03T10:00:00Z",
            "request": {"discussion_number": 195, "body": {"kind": "progress", "progress": "completed"}},
        }
        decision = {
            **self.common,
            "request": {"discussion_number": 102, "body": {"kind": "decision"}},
        }
        step = _current_step(
            self.index,
            [failure],
            [completed],
            {"roles_active": True, "closure": None, "decision": decision, "progress": completed},
            {"finding_state": "open", "counts": {"quarantined": 0}},
        )
        self.assertEqual("fresh_pass_required", step["id"])
        self.assertTrue(any("architecture-baseline-l1-v0.1.0.yml" in link["url"] for link in step["links"]))

    def test_current_projection_matches_accepted_main_ledger_and_links_evidence(self):
        current = build(ROOT)
        self.assertEqual("closed", current["finding_state"])
        self.assertEqual("report_only", current["enforcement"])
        self.assertEqual(3, current["counts"]["receipts"])
        self.assertEqual(4, current["counts"]["actions"])
        latest = current["history"][-1]
        self.assertEqual("closure", latest["detail"])
        self.assertTrue(any("pull/198" in link["url"] for link in latest["links"]))
        self.assertEqual("closed_wait", current["next_step"]["id"])

    def test_quarantined_evidence_blocks_action_recommendation(self):
        step = _current_step(
            self.index,
            [],
            [],
            {"roles_active": True, "closure": None},
            {"finding_state": "needs_clarification", "counts": {"quarantined": 1}},
        )
        self.assertEqual("resolve_clarification", step["id"])


if __name__ == "__main__":
    unittest.main()
