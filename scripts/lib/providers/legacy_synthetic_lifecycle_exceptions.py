#!/usr/bin/env python3
"""Generate a synthetic exception projection/report at an explicit evaluation instant."""
import argparse
from pathlib import Path

from generate_governance_lifecycle_index import DEFAULT_PROFILE
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import load_transactions

EXCEPTION_LEDGER = ROOT / "governance/lifecycle/synthetic-exceptions"
EXCEPTION_INDEX = ROOT / "status/governance-lifecycle-exception-index.json"
EXCEPTION_REPORT = ROOT / "generated/reports/governance-lifecycle-exceptions.md"


def render_report(index):
    lines = ["# CLG-05 Synthetic Exceptions", "", f"As of: `{index['as_of']}`", "",
             "Environment: **synthetic**; **report-only**; official state: **false**.",
             "Coverage refers to explicitly accepted failing observations, not unobserved resources or future failures.",
             "Fixture consent does not authenticate real authority. Live acceptance remains pending.", "",
             "| Finding state | Evidence | Coverage | Covered observations | Uncovered observations | Renewed decision required |",
             "|---|---|---|---|---|---|"]
    for finding in index["findings"]:
        t = finding.get("exception_treatment", {})
        lines.append(f"| {finding['state']} | {finding['evidence_status']} | {t.get('coverage', 'none')} | "
                     f"{len(t.get('covered_observation_refs', []))} | {len(t.get('uncovered_observation_refs', []))} | "
                     f"{str(t.get('renewed_decision_required', False)).lower()} |")
    lines += ["", "| Exception record | Disposition | Effective status | Valid from | Expires at (exclusive) |",
              "|---|---|---|---|---|"]
    for finding in index["findings"]:
        for record in finding.get("exception_treatment", {}).get("exception_records", []):
            lines.append(f"| `{record['record_ref']['id']}` | {record['disposition']} | {record['status']} | {record['valid_from']} | {record['expires_at']} |")
    lines += ["", "Risk acceptance does not count as remediation or closure. Finding state, conflicts and work progress remain independently visible in the JSON index.", ""]
    return "\n".join(lines)


def generate(ledger, output, report, *, as_of):
    for path in (output, report):
        require(not path.resolve().is_relative_to(ledger.resolve()), "Output must be outside immutable history")
    require(output.resolve() != report.resolve(), "Index and report paths must differ")
    index = project(load_transactions(ledger), strict_json(DEFAULT_PROFILE.read_bytes()), as_of=as_of)
    for path, data in ((output, json_bytes(index)), (report, render_report(index).encode())):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=EXCEPTION_LEDGER)
    parser.add_argument("--output", type=Path, default=EXCEPTION_INDEX)
    parser.add_argument("--report", type=Path, default=EXCEPTION_REPORT)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    result = generate(args.ledger, args.output, args.report, as_of=args.as_of)
    print(f"Synthetic exception projection: {result['counts']}; no waiver-based closure.")


if __name__ == "__main__":
    main()
