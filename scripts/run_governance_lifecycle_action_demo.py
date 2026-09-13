#!/usr/bin/env python3
"""Reproduce CLG-02 then append synthetic CLG-03 consent, progress and withdrawal."""
import argparse
from pathlib import Path

from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import append_action, load_transactions
from lib.governance_lifecycle.synthetic_actions import decision_packet, remediation_packet
from generate_governance_lifecycle_index import DEFAULT_PROFILE
from run_governance_lifecycle_synthetic_demo import run_demo

ACTION_AS_OF = "2026-09-13T12:10:00Z"


def append_demo_actions(ledger, output):
    require(not output.resolve().is_relative_to(ledger.resolve()), "Projection must be outside immutable history")
    profile = strict_json(DEFAULT_PROFILE.read_bytes())
    history = load_transactions(ledger)
    golden = strict_json((Path(__file__).resolve().parents[1] / "tests/fixtures/governance-lifecycle/clg02-index.json").read_bytes())
    require(project(history, profile, as_of=golden["as_of"]) == golden and len(history) == 5,
            "Action demo requires the exact CLG-02 history")
    observation = history[0]["observation"]
    decision, resources = decision_packet(profile, observation, record_id="decision:demo-approve", revision=5,
                                         at="2026-09-13T11:40:00Z", case_id="remediation-case:demo-1")
    append_action(ledger, decision, resources, profile, expected_revision=5)
    planned, planned_resources = remediation_packet(decision, resources, record_id="remediation:demo-planned", revision=6,
                                                    at="2026-09-13T11:50:00Z")
    append_action(ledger, planned, planned_resources, profile, expected_revision=6)
    progress, progress_resources = remediation_packet(decision, resources, record_id="remediation:demo-progress", revision=7,
                                                      at="2026-09-13T12:00:00Z", progress="in_progress", previous=planned)
    append_action(ledger, progress, progress_resources, profile, expected_revision=7)
    withdrawal, withdrawal_resources = decision_packet(profile, observation, record_id="decision:demo-revoke", revision=8,
        at="2026-09-13T12:10:00Z", case_id="remediation-case:demo-1", disposition="revoke", previous=decision)
    append_action(ledger, withdrawal, withdrawal_resources, profile, expected_revision=8)
    require(append_action(ledger, decision, resources, profile, expected_revision=5)["outcome"] == "duplicate",
            "Retry must not reactivate revoked consent")
    index = project(load_transactions(ledger), profile, as_of=ACTION_AS_OF)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(index))
    return index


def run_action_demo(ledger, output):
    run_demo(ledger, output)
    return append_demo_actions(ledger, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = run_action_demo(args.ledger, args.output)
    print(f"Synthetic action demo complete: {index['counts']}; approval withdrawn, finding remains open for clarification.")


if __name__ == "__main__":
    main()
