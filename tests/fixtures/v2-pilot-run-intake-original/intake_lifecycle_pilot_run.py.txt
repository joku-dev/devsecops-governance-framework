#!/usr/bin/env python3
"""Collect fresh provider evidence into durable pilot validation; no live activation."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from lib.governance_lifecycle.contracts import ROOT
from lib.governance_lifecycle.live_admission import VALIDATION_LEDGER, append_capture, load_operating
from lib.governance_lifecycle.live_evidence import collect_preflight


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-sequence", type=int, required=True)
    args=parser.parse_args()
    profile=load_operating()
    with tempfile.TemporaryDirectory() as temporary:
        capture=Path(temporary)/"capture"
        collect_preflight(args.run_id, capture)
        at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
        result=append_capture(ROOT / VALIDATION_LEDGER,capture,profile,recorded_at=at,expected_sequence=args.expected_sequence)
    print(result)


if __name__ == "__main__":
    main()
