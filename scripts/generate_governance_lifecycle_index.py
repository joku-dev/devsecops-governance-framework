#!/usr/bin/env python3
"""Generate a synthetic-only index from the complete immutable lifecycle ledger."""
import argparse
from pathlib import Path

from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.kernel import project
from lib.governance_lifecycle.store import load_transactions

DEFAULT_LEDGER = ROOT / "governance/lifecycle/synthetic"
DEFAULT_INDEX = ROOT / "status/governance-lifecycle-synthetic-index.json"
DEFAULT_PROFILE = ROOT / "model/governance/lifecycle/synthetic-grs002-profile.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    require(not args.output.resolve().is_relative_to(args.ledger.resolve()), "Projection must be outside the immutable ledger")
    index = project(load_transactions(args.ledger), strict_json(DEFAULT_PROFILE.read_bytes()), as_of=args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(json_bytes(index))
    print(f"Wrote {args.output}; synthetic only, {index['counts']['findings']} findings")


if __name__ == "__main__":
    main()
