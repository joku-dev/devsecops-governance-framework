#!/usr/bin/env python3
"""Start an instance-owned V2 Workbench, bootstrapping a missing environment."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from lib.environment_bootstrap import BootstrapFailure
from lib.workbench_startup_application import execute


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--environment',type=Path,required=True)
    parser.add_argument('--instance',type=Path,required=True)
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--port',type=int,default=8875)
    parser.add_argument('--state-directory',type=Path)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--wheelhouse',type=Path)
    parser.add_argument('--opa-cache',type=Path)
    parser.add_argument('--opa-mirror',default='')
    parser.add_argument('--attempts',type=int,default=3)
    parser.add_argument('--timeout',type=int,default=120)
    parser.add_argument('--development',action='store_true')
    parser.add_argument('--enable-pr',action='store_true')
    parser.add_argument('--publication-profile',type=Path)
    args=parser.parse_args(argv)
    try:return execute(vars(args))
    except (BootstrapFailure,ValueError,OSError,KeyError,TypeError) as error:
        code=error.code if isinstance(error,BootstrapFailure) else str(error) if isinstance(error,ValueError) else ''
        if not re.fullmatch('[a-z][a-z0-9_]{0,100}',code):code='workbench_startup_request_invalid'
        print(json.dumps({'state':'incomplete','diagnostics':[code],
            'official_acceptance':False,'authority_transferred':False}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
