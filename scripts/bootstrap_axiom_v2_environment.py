#!/usr/bin/env python3
"""Create or update an owned AXIOM environment before installing dependencies."""
from pathlib import Path
import argparse
import json
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from lib.environment_bootstrap import BootstrapFailure
from lib.environment_bootstrap_application import execute, inspect_record

PROFILES={'validation':'validation-environment-v1','source-intake':'source-intake-environment-v1'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('command',choices=(*PROFILES,'inspect'))
    parser.add_argument('--environment',type=Path)
    parser.add_argument('--python',default=sys.executable,help='Operator-selected interpreter; never consumer configuration.')
    parser.add_argument('--state-directory',type=Path)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--wheelhouse',type=Path)
    parser.add_argument('--opa-cache',type=Path)
    parser.add_argument('--opa-mirror',default='')
    parser.add_argument('--attempts',type=int,default=3)
    parser.add_argument('--timeout',type=int,default=120)
    parser.add_argument('--development',action='store_true',help='Explicit working-source setup; grants no operating approval.')
    parser.add_argument('--record',type=Path,help='Private retained operation directory for inspect.')
    args=parser.parse_args(argv)
    if args.command=='inspect':
        if args.record is None:parser.error('inspect requires --record')
    elif args.environment is None:parser.error('creation/update requires --environment')
    try:
        if args.command=='inspect':
            report=inspect_record(args.record);code=0 if report['declared_result'] is not None else 2
        else:
            options=vars(args).copy();options.pop('command');options.pop('record')
            report=execute(PROFILES[args.command],options);code=report['exit_code']
        print(json.dumps(report,sort_keys=True));return code
    except (BootstrapFailure,ValueError,OSError,KeyError,TypeError) as error:
        reason=error.code if isinstance(error,BootstrapFailure) else str(error) if isinstance(error,ValueError) else ''
        if not re.fullmatch('[a-z][a-z0-9_]{0,100}',reason):reason='bootstrap_request_or_capture_invalid'
        print(json.dumps({'state':'incomplete','diagnostics':[reason],
            'official_acceptance':False,'authority_transferred':False}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
