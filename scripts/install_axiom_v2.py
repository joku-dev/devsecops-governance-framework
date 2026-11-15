#!/usr/bin/env python3
"""Install a pinned prepared AXIOM V2 package into a fresh private prefix, offline."""
import argparse
import json
from pathlib import Path
import re
import sys
import subprocess
import zipfile
from lib.v2_distribution import install


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('package',type=Path)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--prefix',type=Path,required=True)
    parser.add_argument('--python',type=Path,default=Path(sys.executable))
    parser.add_argument('--port',type=int,default=8875)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(install(args.package,args.sha256,args.prefix,args.python,port=args.port),sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError,zipfile.BadZipFile) as error:
        code=str(error) if isinstance(error,ValueError) else ''
        if not re.fullmatch('[a-z][a-z0-9_]{0,100}',code):code='v2_installation_failed'
        print(json.dumps({'execution':'error','diagnostics':[code]}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
