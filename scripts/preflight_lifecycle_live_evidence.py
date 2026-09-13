#!/usr/bin/env python3
"""Capture or replay diagnostic live evidence; never submit lifecycle observations."""
import argparse
from lib.governance_lifecycle.live_evidence import collect_preflight, replay_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run-id")
    mode.add_argument("--verify-bundle")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    if args.run_id:
        if not args.output_dir:
            parser.error("--run-id requires --output-dir")
        result = collect_preflight(args.run_id, args.output_dir)
    else:
        if args.output_dir:
            parser.error("--verify-bundle does not write an output")
        result = replay_capture(args.verify_bundle)
    print(f"GRS-002: {result['criterion']['status']}; {len(result['checks'])} capture checks passed. "
          "Diagnostic only; lifecycle acceptance not evaluated.")


if __name__ == "__main__":
    main()
