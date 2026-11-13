#!/usr/bin/env python3
"""Prepare synthetic review packets or grade supplied answers offline; never call models."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.lib.agent_evaluation import DEFAULT_DATASET, grade_evaluation, load_dataset, prepare_evaluation
from scripts.lib.agent_receipts import private_destination, write_private_artifact as _write


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',type=Path,default=DEFAULT_DATASET)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',type=Path,metavar='NEW_DIRECTORY')
    mode.add_argument('--responses',type=Path)
    parser.add_argument('--output',type=Path,help='New private report file outside checkout, required for grading')
    args=parser.parse_args(argv)
    try:
        dataset=load_dataset(args.dataset)
        if args.prepare:
            if args.output:
                raise ValueError('--prepare does not use --output')
            report=prepare_evaluation(ROOT,dataset,args.prepare)
        else:
            if not args.output:
                raise ValueError('Grading requires --output')
            report=grade_evaluation(dataset,json.loads(args.responses.read_text()))
            path=private_destination(ROOT,args.output)
            path.parent.mkdir(parents=True,exist_ok=True)
            _write(path,report)
        print(json.dumps({'evaluation_id':report['evaluation_id'],'case_count':len(report['cases']),
                          'provider_invoked':False,'complete_coverage':report.get('complete_coverage')}))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(f'error: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
