#!/usr/bin/env python3
"""Reproduce a bounded synthetic CLG-02 history; no live repository settings change."""
import argparse
from pathlib import Path

from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from generate_governance_lifecycle_index import DEFAULT_PROFILE

DEMO_AS_OF = "2026-09-13T11:30:00Z"


def run_demo(ledger, output):
    require(not output.resolve().is_relative_to(ledger.resolve()), "Projection must be outside immutable history")
    require(not load_transactions(ledger), "Demo requires an empty ledger; existing history is never reset")
    profile = strict_json(DEFAULT_PROFILE.read_bytes())
    cases = [
        ("fail", "10:00", "10:00", "demo-1", 0, "accepted"),
        ("fail", "10:00", "10:01", "demo-1", 0, "duplicate"),
        ("fail", "10:10", "10:10", "demo-2", 1, "accepted"),
        ("pass", "11:00", "11:00", "demo-3", 2, "accepted"),
        ("fail", "10:05", "11:10", "demo-4", 3, "accepted"),
        ("fail", "11:00", "11:20", "demo-3", 4, "quarantined"),
        ("fail", "11:00", "11:21", "demo-3", 4, "duplicate"),
    ]
    for result, observed, recorded, run_id, revision, expected in cases:
        observation, resources = synthetic_packet(
            profile, result=result, observed_at=f"2026-09-13T{observed}:00Z",
            recorded_at=f"2026-09-13T{recorded}:00Z", run_id=run_id)
        outcome = append_observation(ledger, observation, resources, profile, expected_revision=revision)
        require(outcome["outcome"] == expected, "Unexpected synthetic demo outcome")
    index = project(load_transactions(ledger), profile, as_of=DEMO_AS_OF)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(index))
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = run_demo(args.ledger, args.output)
    print(f"Synthetic demo complete: {index['counts']}; no operational closure.")


if __name__ == "__main__":
    main()
