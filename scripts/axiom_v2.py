#!/usr/bin/env python3
"""AXIOM V2: explicit portable application commands and fresh private instances."""
import argparse
import json
import re
from pathlib import Path
import sys
from lib.v2_application import VERSION, initialize, run
from lib.provider_errors import AccessFailure


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version=VERSION)
    parser.add_argument('--instance',type=Path)
    parser.add_argument('command',choices=('init','check','runtime','evidence','collector','workbench','parity','evaluate'))
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    try:
        if args.command=='init':
            sub=argparse.ArgumentParser(prog='axiom-v2 init')
            sub.add_argument('--port',type=int,default=8875)
            sub.add_argument('--opa',type=Path,required=True)
            sub.add_argument('--development',action='store_true')
            settings=sub.parse_args(args.arguments)
            if not args.instance:parser.error('init requires --instance FRESH_PRIVATE_DIRECTORY')
            value=initialize(args.instance,port=settings.port,opa=settings.opa,development=settings.development)
            print(json.dumps({'product':value['product'],'version':value['version'],
                              'node_id':value['node_id'],'mode':'paused','source_revision':value['source_revision']}))
            return 0
        return run(args.command,args.arguments,instance_path=args.instance)
    except (ValueError,OSError,KeyError,TypeError,AccessFailure) as error:
        code=str(error) if isinstance(error,(ValueError,AccessFailure)) else ''
        if not re.fullmatch('[a-z][a-z0-9_]{0,100}',code):code='v2_operation_failed'
        print(json.dumps({'execution':'error','diagnostics':[code]}),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
