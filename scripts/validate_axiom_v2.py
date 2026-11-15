#!/usr/bin/env python3
"""Check the V2 architecture boundary; no provider access or mutation."""
import argparse
import json
from pathlib import Path
from lib.v2_boundary import validate_boundaries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    report=validate_boundaries(args.root)
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
