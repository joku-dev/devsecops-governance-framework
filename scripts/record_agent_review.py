#!/usr/bin/env python3
"""Export an allowlisted review receipt and separate declared usage statistics."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.lib.agent_receipts import (append_review_usage, build_receipt, load_review_usage,
    summarize_review_usage, write_receipt)
from jsonschema import ValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--usage-log", type=Path, help="New-format log outside the checkout; legacy logs stay unchanged")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.summary:
            if not args.usage_log or any((args.plan, args.results, args.output)):
                raise ValueError("--summary requires only --usage-log")
            print(json.dumps(summarize_review_usage(load_review_usage(args.usage_log)), indent=2))
            return 0
        if not all((args.plan, args.results, args.output)):
            raise ValueError("Export requires --plan, --results and --output")
        receipt = build_receipt(ROOT, json.loads(args.plan.read_text()), json.loads(args.results.read_text()))
        receipt = write_receipt(ROOT, args.output, receipt)
        recorded = append_review_usage(ROOT, args.usage_log, receipt) if args.usage_log else False
        print(json.dumps({"receipt_id": receipt["receipt_id"], "head_commit": receipt["head_commit"],
                          "eligible_for_human_review": receipt["eligible_for_human_review"], "usage_appended": recorded}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
