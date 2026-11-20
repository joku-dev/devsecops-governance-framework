#!/usr/bin/env python3
"""Export a commit-bound SPDX SBOM before installing Python dependencies."""
import argparse,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lib.sbom_export_application import execute,inspect
from lib.sbom_export_ports import profile


def main(argv=None,*,instance_root=None,node=None):
 os.umask(0o077)
 argv=list(sys.argv[1:] if argv is None else argv)
 if not argv or argv[0] not in ('export','inspect'):argv.insert(0,'export')
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
 commands=parser.add_subparsers(dest='command',required=True)
 export=commands.add_parser('export',allow_abbrev=False)
 export.add_argument('--profile',choices=(profile.PROFILE,),default=profile.PROFILE)
 export.add_argument('--repository');export.add_argument('--commit');export.add_argument('--workflow-ref')
 export.add_argument('--anonymous',action='store_true');export.add_argument('--token-file',type=Path);export.add_argument('--legacy-environment',action='store_true')
 export.add_argument('--output-directory',type=Path);export.add_argument('--state-directory',type=Path)
 export.add_argument('--output',choices=('json','legacy'),default='json')
 check=commands.add_parser('inspect',allow_abbrev=False);check.add_argument('--record',type=Path,required=True)
 args=parser.parse_args(argv)
 if args.command=='export' and not args.legacy_environment and (args.repository is None or args.commit is None):parser.error('explicit --repository and --commit are required')
 try:
  if args.command=='inspect':
   report=inspect(args.record,node=node);print(json.dumps(report,sort_keys=True));return 0 if report['retained_declared_replay_consistent'] else 2
  report,result,code=execute(vars(args),instance_root=instance_root,node=node)
  if args.output=='legacy' and result is not None:
   sys.stdout.write(result['stdout']);sys.stderr.write(result['stderr'])
  else:print(json.dumps(report,sort_keys=True))
  return code
 except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:
  code=str(error) if isinstance(error,(ValueError,RuntimeError)) else ''
  if not re.fullmatch('[a-z][a-z0-9_]{0,100}',code):code='sbom_request_or_capture_invalid'
  print(json.dumps({'state':'incomplete','diagnostics':[code],'official_acceptance':False,'authority_transferred':False}),file=sys.stderr)
  return 2


if __name__=='__main__':raise SystemExit(main())
