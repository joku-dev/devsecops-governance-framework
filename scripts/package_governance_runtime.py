#!/usr/bin/env python3
"""Build/admit exact-source packages or prepare their runtime without dependency downloads."""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import zipfile

from lib.runtime_package import build,admit,prepare_environment


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['build','admit','prepare-environment'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--revision');parser.add_argument('--package',type=Path)
    parser.add_argument('--sha256');parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--opa',type=Path);parser.add_argument('--wheelhouse',type=Path)
    parser.add_argument('--system');parser.add_argument('--machine');parser.add_argument('--workbench',action='store_true')
    parser.add_argument('--python',type=Path,default=Path(sys.executable))
    args=parser.parse_args(argv);os.umask(0o077)
    if args.action=='build':
        if not args.revision:parser.error('build requires --revision')
        result=build(args.root,args.revision,args.destination,opa=args.opa,wheelhouse=args.wheelhouse,
                     system=args.system,machine=args.machine,workbench=args.workbench)
    elif args.action=='admit':
        if not args.package or not args.sha256:parser.error('admit requires --package and independently pinned --sha256')
        manifest=admit(args.package,args.sha256,args.destination)
        result={'source_commit':manifest['source_commit'],'source_tree':manifest['source_tree'],'admitted':True}
    else:
        if not args.package or not args.sha256:parser.error('prepare-environment requires the original --package and independently pinned --sha256')
        result=prepare_environment(args.root,args.destination,args.python,package=args.package,expected_sha256=args.sha256)
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError,zipfile.BadZipFile):
        print(json.dumps({'error':'runtime_package_invalid_or_unprepared'}),file=sys.stderr);raise SystemExit(2)
