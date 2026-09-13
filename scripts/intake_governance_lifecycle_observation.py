#!/usr/bin/env python3
"""Append one explicitly synthetic GRS-002 packet to a local lifecycle ledger."""
import argparse
import json
from pathlib import Path

from lib.governance_lifecycle.adapter import adapt_grs002, strict_json
from lib.governance_lifecycle.contracts import ROOT
from lib.governance_lifecycle.store import append_observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--trust", type=Path, required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--policy-version", required=True)
    parser.add_argument("--expected-revision", type=int, required=True)
    args = parser.parse_args()
    profile = strict_json((ROOT / "model/governance/lifecycle/synthetic-grs002-profile.json").read_bytes())
    record, resources = adapt_grs002(args.report.read_bytes(), strict_json(args.context.read_bytes()),
                                    strict_json(args.trust.read_bytes()), recorded_at=args.recorded_at,
                                    profile=profile, policy_version=args.policy_version)
    result = append_observation(args.ledger, record, resources, profile, expected_revision=args.expected_revision)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
