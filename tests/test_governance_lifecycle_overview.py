"""Derived scenario metrics must retain the lifecycle's evidence and time boundaries."""
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_governance_lifecycle_overview import (
    OUTPUT, PROFILE, REPORT, SCENARIOS, build_overview, generate, render_report, summarize, validate_overview,
)
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, record_ref, schema_validator
from lib.governance_lifecycle.kernel import transaction_ref
from lib.governance_lifecycle.store import load_transactions

AS_OF = "2026-09-14T00:10:00Z"


class LifecycleOverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = strict_json((ROOT / PROFILE).read_bytes())
        cls.histories = {name: load_transactions(ROOT / "governance/lifecycle" / name) for name in SCENARIOS}

    def summary(self, scenario="synthetic-closure", at=AS_OF):
        return summarize(self.histories[scenario], self.profile, as_of=at)

    def test_checked_in_overview_is_exact_replay_with_separate_scenario_identity(self):
        actual = validate_overview()
        self.assertEqual(len(actual["scenarios"]), 3)
        ids = [s["projection"]["findings"][0]["finding_id"] for s in actual["scenarios"]]
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual([s["scenario_id"] for s in actual["scenarios"]], list(SCENARIOS))
        self.assertFalse(actual["official_state"])
        self.assertEqual(actual["aggregation"], "separate_scenarios")
        self.assertNotIn("totals", actual)

    def test_closure_completion_and_reopening_are_distinct(self):
        before = self.summary(at="2026-09-13T13:50:00Z")["metrics"]
        self.assertEqual(before["current_remediation_progress"]["completed"], 1)
        self.assertEqual(before["current_finding_states"]["open"], 1)
        self.assertEqual(before["event_types"]["finding_closed"], 0)
        late = self.summary(at="2026-09-13T14:10:00Z")["metrics"]
        self.assertEqual(late["current_finding_states"]["closed"], 1)
        self.assertEqual(late["event_types"]["finding_reopened"], 0)
        final = self.summary()["metrics"]
        self.assertEqual(final["event_types"]["finding_closed"], 1)
        self.assertEqual(final["event_types"]["finding_reopened"], 1)
        self.assertEqual(final["current_finding_states"]["closed"], 0)
        self.assertEqual(final["current_finding_states"]["open"], 1)
        self.assertEqual(final["records"]["remediations"], 3)
        self.assertEqual(sum(final["current_remediation_progress"].values()), 1)

    def test_quarantine_is_not_an_accepted_failure_or_implicit_pass_closure(self):
        result = self.summary("synthetic")
        m = result["metrics"]
        self.assertEqual(m["accepted_observation_results"], {"pass": 1, "fail": 3})
        self.assertEqual(m["records"]["conflicts"], 1)
        self.assertEqual(m["current_finding_states"]["needs_clarification"], 1)
        self.assertEqual(m["event_types"]["finding_closed"], 0)
        self.assertEqual(result["projection"]["findings"][0]["remediation_cases"][0]["authorization_status"], "revoked")

    def test_exception_expiry_is_time_derived_without_an_invented_event(self):
        before = self.summary("synthetic-exceptions", "2026-09-13T23:59:59Z")
        expired = self.summary("synthetic-exceptions", "2026-09-14T00:00:00Z")
        self.assertEqual(before["events"], expired["events"])
        self.assertEqual(before["metrics"]["current_coverage_by_finding"]["partial"], 1)
        self.assertEqual(expired["metrics"]["current_coverage_by_finding"]["none"], 1)
        self.assertEqual(expired["metrics"]["current_findings_needing_renewed_decision"], 1)
        renewed = self.summary("synthetic-exceptions")["metrics"]
        self.assertEqual(renewed["current_coverage_by_finding"]["full"], 1)
        self.assertEqual(renewed["current_finding_states"]["open"], 1)
        self.assertEqual(renewed["event_types"]["finding_closed"], 0)
        self.assertEqual(renewed["current_findings_needing_renewed_decision"], 0)
        self.assertEqual(renewed["current_exception_statuses"],
                         {"scheduled": 0, "active": 1, "expired": 1, "revoked": 1, "rejected": 0, "withdrawal_recorded": 1})

    def test_recording_time_controls_visibility_and_preserves_source_digests(self):
        result = self.summary(at="2026-09-13T14:09:59Z")
        self.assertEqual(result["metrics"]["accepted_observation_results"]["fail"], 1)
        for event, tx in zip(result["events"], self.histories["synthetic-closure"]):
            self.assertEqual(event["transaction_ref"], transaction_ref(tx))
            self.assertEqual(event["event_ref"], record_ref(tx["event"]))
        self.assertEqual(sum(result["metrics"]["event_types"].values()), result["metrics"]["records"]["events"])

    def test_overdue_uses_explicit_time_and_retains_withdrawn_case(self):
        before = self.summary("synthetic", "2026-09-14T12:00:00Z")["metrics"]
        after = self.summary("synthetic", "2026-09-15T12:00:00Z")["metrics"]
        self.assertEqual(before["current_overdue_cases"], 0)
        self.assertEqual(after["current_overdue_cases"], 1)
        self.assertEqual(before["event_types"], after["event_types"])

    def test_before_first_event_is_empty_and_has_no_inferred_coverage(self):
        overview = build_overview(as_of="2026-09-12T00:00:00Z")
        for scenario in overview["scenarios"]:
            self.assertEqual(scenario["events"], [])
            self.assertEqual(scenario["projection"]["findings"], [])
            self.assertEqual(sum(scenario["metrics"]["current_coverage_by_finding"].values()), 0)
        self.assertIn("no findings", render_report(overview))

    def test_invalid_future_suffix_cannot_be_hidden_by_earlier_cutoff(self):
        bad = deepcopy(self.histories["synthetic-closure"])
        bad[-1]["event"]["body"]["event_type"] = "observation_added"
        with self.assertRaises(ContractError):
            summarize(bad, self.profile, as_of="2026-09-13T14:00:00Z")

    def test_schema_rejects_live_claims_negative_counts_and_extra_totals(self):
        original = strict_json((ROOT / OUTPUT).read_bytes())
        for mutate in (lambda o: o.update(official_state=True), lambda o: o.update(totals={}),
                       lambda o: o["scenarios"][0]["metrics"]["records"].update(events=-1),
                       lambda o: o.update(as_of="2026-09-14T00:10:00+00:00")):
            bad = deepcopy(original)
            mutate(bad)
            with self.assertRaises(ValidationError):
                schema_validator("overview").validate(bad)

    def test_missing_scenario_cannot_be_reported_as_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / PROFILE).parent.mkdir(parents=True)
            shutil.copyfile(ROOT / PROFILE, root / PROFILE)
            with self.assertRaisesRegex(ContractError, "scenario ledger is missing"):
                build_overview(root, as_of=AS_OF)

    def test_generator_protects_history_models_and_output_aliases(self):
        for output, report in ((ROOT / "governance/lifecycle/new.json", ROOT / REPORT),
                               (ROOT / PROFILE, ROOT / REPORT), (ROOT / OUTPUT, ROOT / OUTPUT)):
            with self.assertRaises(ContractError):
                generate(as_of=AS_OF, output=output, report=report)
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / "history"
            alias.symlink_to(ROOT / "governance/lifecycle", target_is_directory=True)
            with self.assertRaises(ContractError):
                generate(as_of=AS_OF, output=alias / "bad.json")

    def test_deterministic_generation_and_validation_rejects_stale_or_tampered_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (PROFILE,):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, root / relative)
            shutil.copytree(ROOT / "governance/lifecycle", root / "governance/lifecycle")
            generate(root, as_of=AS_OF)
            self.assertEqual((root / OUTPUT).read_bytes(), (ROOT / OUTPUT).read_bytes())
            self.assertEqual((root / REPORT).read_bytes(), (ROOT / REPORT).read_bytes())
            broken = strict_json((root / OUTPUT).read_bytes())
            broken["scenarios"][0]["metrics"]["records"]["events"] += 1
            (root / OUTPUT).write_bytes(json_bytes(broken))
            with self.assertRaisesRegex(ContractError, "overview differs"):
                validate_overview(root)
            generate(root, as_of="2026-09-13T14:00:00Z")
            with self.assertRaisesRegex(ContractError, "cannot hide later"):
                validate_overview(root)
            generate(root, as_of=AS_OF)
            (root / REPORT).write_text("unverified report\n")
            with self.assertRaisesRegex(ContractError, "report differs"):
                validate_overview(root)


if __name__ == "__main__":
    unittest.main()
