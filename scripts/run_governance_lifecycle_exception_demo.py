#!/usr/bin/env python3
"""Exercise partial/overlapping coverage, recurrence, withdrawal, expiry and fresh consent."""
import argparse
from pathlib import Path

from generate_governance_lifecycle_index import DEFAULT_PROFILE
from generate_governance_lifecycle_exceptions import generate
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import append_action, append_exception, append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from lib.governance_lifecycle.synthetic_actions import decision_packet, remediation_packet
from lib.governance_lifecycle.synthetic_exceptions import exception_packet

EXCEPTION_AS_OF = "2026-09-14T00:10:00Z"


def run_exception_demo(ledger, output, report):
    require(not load_transactions(ledger), "Exception demo requires an empty ledger")
    for path in (output, report):
        require(not path.resolve().is_relative_to(ledger.resolve()), "Output must be outside immutable history")
    profile = strict_json(DEFAULT_PROFILE.read_bytes())
    observations = []
    def observe(at, run, revision):
        packet = synthetic_packet(profile, result="fail", observed_at=at, recorded_at=at, run_id=run)
        append_observation(ledger, *packet, profile, expected_revision=revision)
        observations.append(packet[0])
    observe("2026-09-13T15:00:00Z", "exception-demo-1", 0)
    observe("2026-09-13T15:10:00Z", "exception-demo-2", 1)
    decision = decision_packet(profile, observations[0], record_id="decision:exception-demo", revision=2,
                               at="2026-09-13T15:20:00Z", case_id="remediation-case:exception-demo")
    append_action(ledger, *decision, profile, expected_revision=2)
    planned = remediation_packet(*decision, record_id="remediation:exception-demo-planned", revision=3, at="2026-09-13T15:30:00Z")
    append_action(ledger, *planned, profile, expected_revision=3)
    first = exception_packet(profile, observations[:1], record_id="exception:partial", revision=4,
                             at="2026-09-13T16:00:00Z", waiver_id="synthetic-waiver:partial")
    append_exception(ledger, *first, profile, expected_revision=4)
    second = exception_packet(profile, observations[1:], record_id="exception:remaining", revision=5,
                              at="2026-09-13T16:10:00Z", waiver_id="synthetic-waiver:remaining")
    append_exception(ledger, *second, profile, expected_revision=5)
    observe("2026-09-13T16:20:00Z", "exception-demo-new-failure", 6)
    revoke = exception_packet(profile, observations[:1], record_id="exception:withdraw", revision=7,
        at="2026-09-13T16:30:00Z", disposition="revoke", previous=first[0], previous_resources=first[1])
    append_exception(ledger, *revoke, profile, expected_revision=7)
    at_expiry = project(load_transactions(ledger), profile, as_of="2026-09-14T00:00:00Z")["findings"][0]
    require(at_expiry["exception_treatment"]["coverage"] == "none" and at_expiry["exception_treatment"]["renewed_decision_required"],
            "Expiry must expose all uncovered observations and renewed decision need")
    renewal = exception_packet(profile, observations, record_id="exception:renewal", revision=8,
                              at=EXCEPTION_AS_OF, waiver_id="synthetic-waiver:renewal", expiry="2026-09-14")
    append_exception(ledger, *renewal, profile, expected_revision=8)
    require(append_exception(ledger, *first, profile, expected_revision=4)["outcome"] == "duplicate",
            "Old approval retry must never reactivate withdrawn coverage")
    return generate(ledger, output, report, as_of=EXCEPTION_AS_OF)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    index = run_exception_demo(args.ledger, args.output, args.report)
    print(f"Synthetic exception demo completed: {index['counts']}; finding remains open.")


if __name__ == "__main__":
    main()
