#!/usr/bin/env python3
"""Prepare diagnostic control candidates, never accepted lifecycle observations."""
import argparse
from pathlib import Path

from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.devsecops_candidates import adapt_devsecops


def write_candidates(report, context, output, *, evaluated_at, adapter=adapt_devsecops):
    report, context, output = Path(report), Path(context), Path(output)
    require(output.resolve() not in (report.resolve(), context.resolve()), "Output cannot overwrite adapter inputs")
    if output.resolve().is_relative_to(ROOT):
        require(any(output.resolve().is_relative_to((ROOT / path).resolve()) for path in
                    ("generated/reports/lifecycle-candidates", "docs/examples/lifecycle-candidates")),
                "Candidate outputs require a dedicated diagnostic path")
    result = adapter(report.read_bytes(), strict_json(context.read_bytes()), evaluated_at=evaluated_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json_bytes(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evaluated-at", required=True)
    args = parser.parse_args()
    result = write_candidates(args.report, args.context, args.output, evaluated_at=args.evaluated_at)
    print(f"Prepared {len(result['candidates'])} unverified control candidates; no lifecycle intake or state change.")


if __name__ == "__main__":
    main()
