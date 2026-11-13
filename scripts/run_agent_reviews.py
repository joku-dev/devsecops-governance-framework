#!/usr/bin/env python3
"""Prepare bounded private role tasks; --execute explicitly starts provider sessions."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.lib.agent_execution import run_reviews
from jsonschema import ValidationError


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--execute',action='store_true',help='Authorize live provider calls, which may consume account credits; forbidden in CI')
    parser.add_argument('--parallel-specialists',type=int,default=1)
    parser.add_argument('--timeout-seconds',type=int,default=180)
    parser.add_argument('--validation-results',type=Path,help='Existing private results JSON containing actual recorded validations; no checks are run here')
    args=parser.parse_args(argv)
    try:
        validations=json.loads(args.validation_results.read_text())['validations'] if args.validation_results else None
        manifest=run_reviews(ROOT,json.loads(args.plan.read_text()),args.output_dir,execute=args.execute,
            parallel_specialists=args.parallel_specialists,timeout_seconds=args.timeout_seconds,validations=validations)
        print(json.dumps({'run_id':manifest['run_id'],'mode':manifest['mode'],
                          'provider_invoked':manifest['provider_invoked'],
                          'eligible_for_human_review':manifest.get('completion',{}).get('eligible_for_human_review',False)}))
        return 0 if not args.execute or manifest.get('completion',{}).get('eligible_for_human_review') else 1
    except ValidationError:
        print('error: Review input schema is invalid; private input is omitted.',file=sys.stderr)
        return 2
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'error: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
