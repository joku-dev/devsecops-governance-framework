#!/usr/bin/env python3
"""Check pinned tools or run the complete own-source V2 local validation suite."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lib.validation_suite_application import execute,inspect


def main(argv=None):
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--environment',type=Path)
    parser.add_argument('--check-tools',action='store_true')
    parser.add_argument('--instance',type=Path)
    parser.add_argument('--package',type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--at')
    parser.add_argument('--state-directory',type=Path)
    parser.add_argument('--development',action='store_true')
    parser.add_argument('--output',choices=('json','legacy'),default='json')
    parser.add_argument('--inspect',type=Path,help='Inspect retained declared observations, without launching processes.')
    parser.add_argument('--parent-record',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args.inspect is None:
        if args.environment is None:parser.error('--environment is required')
        if not args.check_tools and any(v is None for v in (args.instance,args.package,args.sha256,args.at)):
            parser.error('the full default requires --instance, --package, --sha256 and --at')
    try:
        if args.inspect is not None:
            report=inspect(args.inspect);print(json.dumps(report,sort_keys=True));return 0 if report['retained_declared_replay_consistent'] else 2
        report,streams,code=execute(vars(args))
        if args.output=='legacy':
            sys.stdout.buffer.write(streams['stdout']);sys.stderr.buffer.write(streams['stderr'])
            return code
        print(json.dumps(report,sort_keys=True))
        return 2 if report['state']=='incomplete' else 0 if code==0 else 1
    except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:
        reason=str(error) if isinstance(error,(ValueError,RuntimeError)) else ''
        if not re.fullmatch('[a-z][a-z0-9_]{0,100}',reason):reason='validation_suite_request_or_capture_invalid'
        print(json.dumps({'state':'incomplete','diagnostics':[reason],
            'official_acceptance':False,'authority_transferred':False}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
