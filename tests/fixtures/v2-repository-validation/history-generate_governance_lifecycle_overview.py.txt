#!/usr/bin/env python3
"""Replay three separate synthetic histories into an explicit-time overview."""
import argparse
from collections import Counter
from pathlib import Path

from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, record_ref, require, schema_validator, timestamp
from lib.governance_lifecycle.kernel import project, transaction_ref
from lib.governance_lifecycle.store import load_transactions

SCENARIOS = ("synthetic", "synthetic-closure", "synthetic-exceptions")
PROFILE = "model/governance/lifecycle/synthetic-grs002-profile.json"
OUTPUT = "status/governance-lifecycle-overview.json"
REPORT = "generated/reports/governance-lifecycle-overview.md"
EVENT_TYPES = ("finding_opened", "observation_added", "clarification_required", "decision_recorded",
               "remediation_recorded", "finding_closed", "finding_reopened", "exception_recorded")


def tally(values, keys):
    counts = Counter(values)
    require(set(counts) <= set(keys), "Unsupported metric category; reporting contract needs review")
    return {key: counts[key] for key in keys}


def summarize(transactions, profile, *, as_of):
    # project verifies the ENTIRE chain before applying its recorded-time cutoff.
    index = project(transactions, profile, as_of=as_of)
    visible = [tx for tx in transactions if timestamp(tx["recorded_at"]) <= timestamp(as_of)]
    events = [{"transaction_ref": transaction_ref(tx), "event_ref": record_ref(tx["event"]),
               "finding_id": tx["event"]["finding"]["finding_id"],
               "revision": tx["event"]["body"]["revision"],
               "event_type": tx["event"]["body"]["event_type"],
               "recorded_at": tx["event"]["recorded_at"],
               "effective_at": tx["event"]["body"]["effective_at"]}
              for tx in visible if tx["event"]]
    observations = [tx["observation"] for tx in visible if "observation" in tx and tx["outcome"] == "accepted"]
    cases = [case for f in index["findings"] for case in f.get("remediation_cases", [])]
    exceptions = [record for f in index["findings"]
                  for record in f.get("exception_treatment", {}).get("exception_records", [])]
    metrics = {
        "records": {name: index["counts"].get(name, 0) for name in
                    ("transactions", "observations", "events", "conflicts", "decisions", "remediations", "closures", "exceptions")},
        "event_types": tally((event["event_type"] for event in events), EVENT_TYPES),
        "accepted_observation_results": tally((r["body"]["result"] for r in observations), ("pass", "fail")),
        "current_finding_states": tally((f["state"] for f in index["findings"]), ("open", "closed", "needs_clarification")),
        "current_remediation_progress": tally((case["progress"] for case in cases), ("planned", "in_progress", "completed")),
        "current_overdue_cases": sum(case["overdue"] for case in cases),
        "current_exception_statuses": tally((record["status"] for record in exceptions),
                                             ("scheduled", "active", "expired", "revoked", "rejected", "withdrawal_recorded")),
        "current_coverage_by_finding": tally((f.get("exception_treatment", {}).get("coverage", "not_evaluated") for f in index["findings"]),
                                             ("not_evaluated", "not_applicable", "none", "partial", "full")),
        "current_findings_needing_renewed_decision": sum(f.get("exception_treatment", {}).get("renewed_decision_required", False)
                                                        for f in index["findings"]),
    }
    return {"projection": index, "metrics": metrics, "events": events}


def build_overview(repo=ROOT, *, as_of):
    root = Path(repo)
    profile = strict_json((root / PROFILE).read_bytes())
    scenarios = []
    for name in SCENARIOS:
        ledger_path = f"governance/lifecycle/{name}"
        ledger = root / ledger_path
        require(ledger.is_dir() and (ledger / "transactions").is_dir(), "Required scenario ledger is missing")
        result = summarize(load_transactions(ledger), profile, as_of=as_of)
        scenarios.append({"scenario_id": name, "ledger_path": ledger_path, **result})
    overview = {"schema_version": "0.1.0", "report_type": "governance-lifecycle-synthetic-overview",
                "environment": "synthetic", "official_state": False, "enforcement": "report_only",
                "as_of": as_of, "aggregation": "separate_scenarios", "scenarios": scenarios}
    schema_validator("overview").validate(overview)
    return overview


def render_report(overview):
    lines = ["# CLG-06.1 Synthetic Lifecycle Overview", "", f"As of: `{overview['as_of']}`", "",
             "Environment: **synthetic**; **report-only**; official state: **false**.",
             "These are separate test histories sharing a finding identity, not three portfolio repositories.",
             "No cross-scenario totals or production performance claims are calculated.",
             "Live acceptance remains pending LD-01–05 and LD-07; fixture consent is not authenticated human approval.", "",
             "| Scenario | Open | Closed | Clarification | Accepted FAIL / PASS | Quarantines | Closure events | Reopen events |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for scenario in overview["scenarios"]:
        m = scenario["metrics"]
        states, results, events = m["current_finding_states"], m["accepted_observation_results"], m["event_types"]
        lines.append(f"| {scenario['scenario_id']} | {states['open']} | {states['closed']} | {states['needs_clarification']} | "
                     f"{results['fail']} / {results['pass']} | {m['records']['conflicts']} | {events['finding_closed']} | {events['finding_reopened']} |")
    lines += ["", "Historical closure events remain counted after reopening. PASS, completed work and waiver coverage do not themselves close findings.", "",
              "| Scenario | Work cases: planned / in progress / completed | Overdue cases | Coverage by finding | Renewed decision needed |",
              "|---|---|---:|---|---:|"]
    for scenario in overview["scenarios"]:
        m = scenario["metrics"]
        work = m["current_remediation_progress"]
        coverage = ", ".join(f"{key}: {count}" for key, count in m["current_coverage_by_finding"].items() if count) or "no findings"
        lines.append(f"| {scenario['scenario_id']} | {work['planned']} / {work['in_progress']} / {work['completed']} | "
                     f"{m['current_overdue_cases']} | {coverage} | {m['current_findings_needing_renewed_decision']} |")
    lines += ["", "Work counts include retained cases with withdrawn authorization; each case's authorization is visible in the JSON projection.",
              "Coverage concerns explicit accepted failing observations. `not_evaluated` means this projection has no exception treatment dimension.",
              "Expiry and overdue status are evaluated at `as_of`; they do not invent ledger events.", ""]
    for scenario in overview["scenarios"]:
        head = scenario["projection"]["ledger_head_ref"]
        lines += [f"## {scenario['scenario_id']}", "", f"Ledger: `{scenario['ledger_path']}`",
                  f"Evaluated head: `{head['id'] if head else 'none'}`", "",
                  "| Revision | Event | Recorded at | Effective at |", "|---:|---|---|---|"]
        for event in scenario["events"]:
            lines.append(f"| {event['revision']} | {event['event_type']} | {event['recorded_at']} | {event['effective_at']} |")
        lines += ["", "The JSON overview binds each event to its immutable event and transaction digests and embeds the verified finding projection.", ""]
    return "\n".join(lines)


def generate(repo=ROOT, *, as_of, output=None, report=None):
    root = Path(repo)
    output, report = Path(output) if output else root / OUTPUT, Path(report) if report else root / REPORT
    require(output.resolve() != report.resolve(), "JSON and report paths must differ")
    for path in (output, report):
        require(not path.resolve().is_relative_to((root / "governance/lifecycle").resolve()), "Output must be outside immutable history")
        require(not path.resolve().is_relative_to((root / "model").resolve()), "Output must be outside source models")
    overview = build_overview(root, as_of=as_of)
    for path, data in ((output, json_bytes(overview)), (report, render_report(overview).encode())):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return overview


def validate_overview(repo=ROOT):
    root = Path(repo)
    actual = strict_json((root / OUTPUT).read_bytes())
    expected = build_overview(root, as_of=actual["as_of"])
    require(actual == expected, "Lifecycle overview differs from immutable history")
    for scenario in SCENARIOS:
        transactions = load_transactions(root / "governance/lifecycle" / scenario)
        require(not transactions or timestamp(actual["as_of"]) >= timestamp(transactions[-1]["recorded_at"]),
                "Current overview cannot hide later accepted history")
    require((root / REPORT).read_text() == render_report(expected), "Lifecycle overview report differs from projection")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    generate(as_of=args.as_of, output=args.output, report=args.report)
    print("Generated three separate synthetic scenario summaries; no official portfolio state.")


if __name__ == "__main__":
    main()
