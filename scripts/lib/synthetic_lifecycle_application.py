"""Whole synthetic lifecycle entrypoints, private records and source-bound replay."""
import argparse,json,sys
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry,Resource
from referencing.jsonschema import DRAFT202012
from referencing.exceptions import NoSuchResource

from lib.synthetic_lifecycle_context import execute,GENERATORS
from lib.synthetic_lifecycle_io import ReplayIO,path_spec
from lib.synthetic_lifecycle_projection import PRIVATE_MASK
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_lifecycle_ports import NativeIO,Record,read_record,encode,AUTHORITY,owned_directory,current_source,ROOT,capture_parser_context

from lib.retained_argparse import validate_context as validate_parser_context

PROFILE='legacy-synthetic-lifecycle-reporting-v1'


def request_fields_valid(value):
 keys={'schema_version','profile','generator','source_label','cwd_label','argv','export_mode','resources'}
 if (type(value) is not dict or set(value)!=keys or type(value['schema_version']) is not int or value['schema_version']!=1
     or value['profile']!=PROFILE or type(value['generator']) is not str or value['generator'] not in GENERATORS
     or type(value['export_mode']) is not str or value['export_mode'] not in ('private-candidate','selected-files')
     or type(value['argv']) is not list or len(value['argv'])>64
     or any(type(arg) is not str or len(arg)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in arg) for arg in value['argv'])
     or sum(map(len,value['argv']))>32768):raise ValueError('synthetic_lifecycle_request_changed')
 for key in ('source_label','cwd_label'):path_spec(value[key],value[key],value['cwd_label'])
 resources=value['resources'];seen=set()
 if type(resources) is not list or len(resources)>128:raise ValueError('synthetic_lifecycle_schema_resource_budget')
 for row in resources:
  if type(row) is not dict or set(row)!={'uri','label'}:raise ValueError('synthetic_lifecycle_schema_resource_invalid')
  uri,label=row['uri'],row['label']
  if (type(uri) is not str or not uri or len(uri)>8192 or uri in seen
      or any(ord(c)<33 or 0xd800<=ord(c)<=0xdfff for c in uri)):raise ValueError('synthetic_lifecycle_schema_resource_invalid')
  path_spec(label,label,value['cwd_label']);seen.add(uri)
 return value


def request_valid(value):
 """Execution admission; metadata-only bridge validation never executes a request."""
 if type(value) is not dict or 'parser_context' not in value:raise ValueError('synthetic_lifecycle_request_changed')
 validate_parser_context(value['parser_context'])
 request_fields_valid({key:item for key,item in value.items() if key!='parser_context'})
 return value


def closed_validator(io,request):
 """Resolve only local schema registries and explicitly retained resource bytes."""
 resources={row['uri']:row['label'] for row in request['resources']}
 def retrieve(uri):
  if uri not in resources:
   # referencing wraps resolver errors. Preserve technical incompleteness even
   # when the original generator catches the resulting schema error.
   if hasattr(io,'record'):io.record.capture_incomplete=True
   raise NoSuchResource(ref=uri)
  label=resources[uri]
  return Resource.from_contents(json.loads(io.read(label,label)),default_specification=DRAFT202012)
 def validator(schema,**options):
  registry=Registry(retrieve=retrieve)
  if 'registry' in options:registry=registry.combine(options.pop('registry'))
  return Draft202012Validator(schema,registry=registry,**options)
 validator.check_schema=Draft202012Validator.check_schema
 return validator


def result_value(kernel,io):
 return {'exit_code':kernel['exit_code'],'kernel_result':kernel,'successful_outputs':io.files,
  'successful_writes':io.writes,'private_projected_changes':io.projected_changes}


def inspect(root,*,node=None):
 request,source,retained,events,blob,closed=read_record(root);request_valid(request)
 current=current_source(source.get('node_context'),source.get('product_tree'))
 if node is not None and encode(source.get('node_context'))!=encode(node):raise ValueError('synthetic_lifecycle_foreign_node')
 path_spec(source.get('source_root'),source.get('source_root'),request['cwd_label']);current['source_root']=source['source_root']
 if encode(source)!=encode(current):raise ValueError('synthetic_lifecycle_product_generation_changed')
 if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
     or type(retained['schema_version']) is not int or retained['schema_version']!=1
     or any(type(retained.get(key)) is not type(value) or retained.get(key)!=value for key,value in AUTHORITY.items())
     or type(retained['touched_files']) is not dict or len(events)<3
     or encode(events[0])!=encode({'kind':'opened',**AUTHORITY})
     or encode(events[1])!=encode({'kind':'execution-intent','request':request})):raise ValueError('synthetic_lifecycle_authority_or_intent_changed')
 if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:raise ValueError('synthetic_lifecycle_terminal_changed')
 if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
 io=ReplayIO(events,blob,request['export_mode'],request['cwd_label'])
 kernel=execute(request['source_label'],request['cwd_label'],request['generator'],request['argv'],io,validator_class=closed_validator(io,request),parser_context=request['parser_context']);io.finish()
 if (encode(result_value(kernel,io))!=encode(retained['result']) or encode(io.touched)!=encode(retained['touched_files'])
     or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed()):raise ValueError('synthetic_lifecycle_whole_result_changed')
 return {'state':'complete','generator':request['generator'],'original_exit_code':kernel['exit_code'],
  'original_exit_signal':kernel['original_exit_signal'],'kernel_exception':kernel['kernel_exception'],
  'successful_outputs':io.files,'successful_writes':io.writes,'private_projected_changes':io.projected_changes,
  'private_creation_mask':PRIVATE_MASK if request['export_mode']=='private-candidate' else None,
  'source_output_paths_observed':sorted(io.touched),'source_export_requested':request['export_mode']=='selected-files',
  'retained_declared_replay_consistent':True,'native_source_or_exports_repeated':False,**AUTHORITY}


def generate(options,instance,settings):
 node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
 root=str(Path(options['source_worktree']).expanduser().absolute());cwd=str(Path(options.get('working_directory') or root).expanduser().absolute())
 argv=list(options['legacy_arguments'])
 if argv[:1]==['--']:argv=argv[1:]
 request=request_valid({'schema_version':1,'profile':PROFILE,'generator':options['generator'],
  'source_label':root,'cwd_label':cwd,'argv':argv,'export_mode':'selected-files' if options.get('write_selected_reports') else 'private-candidate',
  'resources':[{'uri':uri,'label':str(Path(path).expanduser().absolute())} for uri,path in options.get('schema_resource',[]) or []],
  'parser_context':capture_parser_context()})
 instance=owned_directory(instance)
 if Path(root).is_relative_to(instance) or instance.is_relative_to(Path(root)):raise ValueError('synthetic_lifecycle_source_instance_overlap')
 source=current_source(node);state=owned_directory(instance/'state/synthetic-lifecycle/records',True)
 record=Record(state,request,source);record.append({'kind':'execution-intent','request':request});io=result=error=None
 try:
  io=NativeIO(record,mode=request['export_mode'],cwd=cwd,private_state=instance,product_root=ROOT)
  kernel=execute(root,cwd,request['generator'],argv,io,validator_class=closed_validator(io,request),parser_context=request['parser_context']);result=result_value(kernel,io)
  if encode(current_source(node))!=encode(source):raise InputAdmissionError('synthetic_lifecycle_product_changed')
 except Exception as caught:error=caught
 completeness='incomplete' if error is not None or record.capture_incomplete else 'complete';journal_complete=True
 try:record.finish(completeness,result,{} if io is None else io.touched,error)
 except Exception:completeness='incomplete';journal_complete=False
 if completeness=='complete':inspect(record.root,node=node)
 return {'state':completeness,'record_root':str(record.root),'journal_terminal_written':journal_complete,
  'generator':request['generator'],'exit_code':2 if completeness=='incomplete' else result['exit_code'],
  'original_exit_code':None if completeness=='incomplete' else result['exit_code'],'export_mode':request['export_mode'],
  'source_export_requested':request['export_mode']=='selected-files','source_effects_may_be_partial':request['export_mode']=='selected-files' and (completeness=='incomplete' or result['exit_code']!=0),
  'source_output_paths_observed':sorted({} if io is None else io.touched),**AUTHORITY},result


def run(arguments,instance=None,settings=None):
 parser=argparse.ArgumentParser(prog='axiom-v2 synthetic-lifecycle',allow_abbrev=False);sub=parser.add_subparsers(dest='command',required=True)
 item=sub.add_parser('generate',allow_abbrev=False);item.add_argument('--profile',choices=(PROFILE,),required=True)
 item.add_argument('--generator',choices=tuple(GENERATORS),required=True);item.add_argument('--source-worktree',required=True)
 item.add_argument('--working-directory');item.add_argument('--write-selected-reports',action='store_true')
 item.add_argument('--schema-resource',nargs=2,action='append',default=[],metavar=('URI','FILE'),help='Retain selected external schema bytes; no implicit HTTP or file URI retrieval.')
 item.add_argument('--format',choices=('receipt','legacy'),default='receipt');item.add_argument('legacy_arguments',nargs=argparse.REMAINDER,help='Use -- then the unchanged original generator arguments.')
 for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
 options=parser.parse_args(arguments)
 if options.command=='replay':value=inspect(options.record)
 else:
  if instance is None or settings is None:raise ValueError('synthetic_lifecycle_instance_required')
  if options.command=='inspect':value=inspect(options.record,node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')})
  else:
   receipt,result=generate(vars(options),instance,settings)
   if options.format=='legacy' and receipt['state']=='complete':
    kernel=result['kernel_result'];sys.stdout.write(kernel['stdout']);sys.stderr.write(kernel['stderr'])
    if kernel['kernel_exception'] is not None:print(json.dumps({'execution':'captured_exception',**kernel['kernel_exception']}),file=sys.stderr)
   else:print(json.dumps(receipt,indent=2))
   return receipt['exit_code']
 print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
