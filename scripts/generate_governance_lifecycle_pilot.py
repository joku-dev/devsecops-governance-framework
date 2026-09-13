#!/usr/bin/env python3
"""Generate explicit-time synthetic CLG-04 projection and pilot report."""
import argparse
from pathlib import Path

from generate_governance_lifecycle_index import DEFAULT_PROFILE
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import load_transactions

PILOT_LEDGER = ROOT / "governance/lifecycle/synthetic-closure"
PILOT_INDEX = ROOT / "status/governance-lifecycle-closure-index.json"
PILOT_REPORT = ROOT / "generated/reports/governance-lifecycle-pilot.md"


def render_report(index):
    counts = index["counts"]
    lines = ["# CLG-04 Synthetic Lifecycle Pilot", "", f"As of: `{index['as_of']}`", "",
             "Environment: **synthetic**. Enforcement: **report-only**. Official state: **false**.",
             "Live pilot acceptance: **pending LD-01–05 and LD-07**. Fixture consent does not authenticate a human.", "",
             f"Transactions: {counts['transactions']}; observations: {counts['observations']}; events: {counts['events']}; "
             f"closures: {counts.get('closures', 0)}; conflicts: {counts['conflicts']}.", "",
             "| Finding | State | Evidence | Revision | Occurrences | Closures | Reopenings |",
             "|---|---|---|---|---|---|---|"]
    for finding in index["findings"]:
        lines.append(f"| `{finding['finding_id']}` | {finding['state']} | {finding['evidence_status']} | "
                     f"{finding['revision']} | {finding['occurrences']} | {len(finding.get('closure_refs', []))} | "
                     f"{finding.get('reopen_count', 0)} |")
    lines += ["", "## Immutable event history", "", "The index references the accepted ledger head and each closure. "
              "Replay retains completed closure history after reopening; a late older failure does not undo closure.", "",
              "This separate pilot does not resolve the original CLG-02/03 conflict, change consumer results or activate live intake.", ""]
    return "\n".join(lines)


def generate(ledger, index_path, report_path, *, as_of):
    for path in (index_path, report_path):
        require(not path.resolve().is_relative_to(ledger.resolve()), "Generated output must be outside immutable history")
    require(index_path.resolve() != report_path.resolve(), "Index and report paths must differ")
    index = project(load_transactions(ledger), strict_json(DEFAULT_PROFILE.read_bytes()), as_of=as_of)
    for path, data in ((index_path, json_bytes(index)), (report_path, render_report(index).encode())):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=PILOT_LEDGER)
    parser.add_argument("--output", type=Path, default=PILOT_INDEX)
    parser.add_argument("--report", type=Path, default=PILOT_REPORT)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    index = generate(args.ledger, args.output, args.report, as_of=args.as_of)
    print(f"Generated synthetic pilot: {index['counts']}; live acceptance pending.")


if __name__ == "__main__":
    main()
