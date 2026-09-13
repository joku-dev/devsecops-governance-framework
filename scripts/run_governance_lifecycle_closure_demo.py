#!/usr/bin/env python3
"""Run an isolated synthetic FAIL/consent/remediation/PASS/closure/reopening pilot."""
import argparse
from pathlib import Path

from generate_governance_lifecycle_index import DEFAULT_PROFILE
from generate_governance_lifecycle_pilot import generate
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import append_action, append_closure, append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from lib.governance_lifecycle.synthetic_actions import closure_packet, decision_packet, remediation_packet

PILOT_AS_OF = "2026-09-13T14:20:00Z"


def run_closure_demo(ledger, output, report):
    require(not load_transactions(ledger), "Closure demo requires an empty ledger; no accepted history is reset")
    for path in (output, report):
        require(not path.resolve().is_relative_to(ledger.resolve()), "Output must be outside immutable history")
    profile = strict_json(DEFAULT_PROFILE.read_bytes())
    def observation(result, observed, recorded, run, revision):
        packet = synthetic_packet(profile, result=result, observed_at=f"2026-09-13T{observed}:00Z",
                                  recorded_at=f"2026-09-13T{recorded}:00Z", run_id=run)
        append_observation(ledger, *packet, profile, expected_revision=revision)
        return packet[0]
    failing = observation("fail", "13:00", "13:00", "closure-demo-fail", 0)
    decision = decision_packet(profile, failing, record_id="decision:closure-demo", revision=1,
                               at="2026-09-13T13:10:00Z", case_id="remediation-case:closure-demo")
    append_action(ledger, *decision, profile, expected_revision=1)
    previous = None
    for revision, progress, at in ((2, "planned", "13:20"), (3, "in_progress", "13:30"), (4, "completed", "13:40")):
        packet = remediation_packet(*decision, record_id="remediation:closure-demo-" + progress,
                                    revision=revision, at=f"2026-09-13T{at}:00Z", progress=progress, previous=previous)
        append_action(ledger, *packet, profile, expected_revision=revision)
        previous = packet[0]
    passing = observation("pass", "13:50", "13:50", "closure-demo-pass", 5)
    closure = closure_packet(profile, failing, passing, previous, record_id="closure:demo", revision=6,
                             at="2026-09-13T14:00:00Z")
    append_closure(ledger, *closure, profile, expected_revision=6)
    require(project(load_transactions(ledger), profile, as_of="2026-09-13T14:00:00Z")["findings"][0]["state"] == "closed",
            "Synthetic closure checkpoint failed")
    observation("fail", "13:05", "14:10", "closure-demo-late", 7)
    require(project(load_transactions(ledger), profile, as_of="2026-09-13T14:10:00Z")["findings"][0]["state"] == "closed",
            "Historical failure incorrectly reopened finding")
    observation("fail", "14:20", "14:20", "closure-demo-recurrence", 8)
    require(append_closure(ledger, *closure, profile, expected_revision=6)["outcome"] == "duplicate",
            "Closure retry must not close a reopened finding")
    return generate(ledger, output, report, as_of=PILOT_AS_OF)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    index = run_closure_demo(args.ledger, args.output, args.report)
    print(f"Synthetic pilot completed: {index['counts']}; finding reopened, closure history retained.")


if __name__ == "__main__":
    main()
