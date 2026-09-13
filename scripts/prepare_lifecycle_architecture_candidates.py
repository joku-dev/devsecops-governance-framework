#!/usr/bin/env python3
"""Prepare diagnostic architecture gate candidates without inferring marker findings."""
import argparse
from pathlib import Path

from lib.governance_lifecycle.architecture_candidates import adapt_architecture
from prepare_lifecycle_devsecops_candidates import write_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluated-at", required=True)
    args = parser.parse_args()
    result = write_candidates(args.report, args.context, args.output, evaluated_at=args.evaluated_at, adapter=adapt_architecture)
    print(f"Prepared {len(result['candidates'])} unverified gate candidates; no marker inference or lifecycle intake.")


if __name__ == "__main__":
    main()
