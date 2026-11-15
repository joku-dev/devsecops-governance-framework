#!/usr/bin/env python3
"""Report missing/stale/incomplete PR review metadata without enforcing a gate."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.lib.agent_review_status import inspect_pr, receipt_block, render_status
from jsonschema import ValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event-file', type=Path)
    parser.add_argument('--output-json', type=Path)
    parser.add_argument('--output-md', type=Path)
    parser.add_argument('--receipt', type=Path, help='Print the allowlisted receipt block to paste into a PR description')
    args = parser.parse_args(argv)
    try:
        if args.receipt:
            if any((args.event_file, args.output_json, args.output_md)):
                raise ValueError('--receipt cannot be combined with report arguments')
            print(receipt_block(json.loads(args.receipt.read_text())))
            return 0
        if not all((args.event_file, args.output_json, args.output_md)):
            raise ValueError('Reporting requires event-file and both output paths')
        report = inspect_pr(ROOT, json.loads(args.event_file.read_text()))
        for path, contents in ((args.output_json, json.dumps(report, indent=2) + '\n'),
                               (args.output_md, render_status(report))):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents)
        print(report['status'])
        return 0  # Findings never introduce a blocking review requirement.
    except ValidationError:
        print('error: Receipt schema is invalid; private input is omitted.', file=sys.stderr)
        return 2
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
