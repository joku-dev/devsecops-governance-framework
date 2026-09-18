#!/usr/bin/env python3
"""Intake an already-authorized, report-only staging deployment evidence bundle."""

from argparse import ArgumentParser
from pathlib import Path

from lib.consolidated_l1 import reconcile as reconcile_consolidated
from lib.measured_l1 import load_snapshots as load_measured_snapshots
from lib.staging_deployment import RESULT_ROOT, normalize_bundle, store_snapshot


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--evidence-repository-commit", required=True)
    parser.add_argument("--verified-at")
    args = parser.parse_args()
    result = normalize_bundle(
        args.bundle,
        evidence_repository_commit=args.evidence_repository_commit,
        verified_at=args.verified_at,
    )
    print(store_snapshot(RESULT_ROOT, result).relative_to(RESULT_ROOT.parents[1]))
    for path in reconcile_consolidated(
            load_measured_snapshots(RESULT_ROOT.parents[1] / "status/measured-l1-results"), [result]):
        print(path.relative_to(RESULT_ROOT.parents[1]))


if __name__ == "__main__":
    main()
