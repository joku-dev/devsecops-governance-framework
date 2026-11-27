"""Complete diagnostic pilot projections, captured history and pure replay."""
import argparse,json,posixpath,sys
from pathlib import Path
from lib.pilot_projection_ports import (NativeIO,Record,read_record,encode,
    AUTHORITY,owned_directory,current_source,ROOT,captured_provider,CAPTURE_PROFILES)
from lib.pilot_projection_context import execute,PROGRAMS
from lib.synthetic_lifecycle_application import closed_validator,result_value,request_fields_valid as report_request
from lib.synthetic_lifecycle_io import ReplayIO,path_spec
from lib.synthetic_lifecycle_projection import PRIVATE_MASK
from lib.requirement_validation_budget import InputAdmissionError

PROFILE='legacy-pilot-projection-v1'

def request_valid(value):
    keys={'schema_version','profile','program','source_label','cwd_label','argv','export_mode','resources','capture_profile'}
    if type(value) is not dict or set(value)!=keys or value['profile']!=PROFILE or type(value['program']) is not str or value['program'] not in PROGRAMS:
        raise ValueError('pilot_projection_request_changed')
    if type(value['capture_profile']) is not str or value['capture_profile'] not in CAPTURE_PROFILES:raise ValueError('pilot_projection_capture_profile_not_supported')
    from lib.synthetic_lifecycle_application import PROFILE as REPORT_PROFILE
    report_request({**{k:v for k,v in value.items() if k not in ('profile','program','capture_profile')},'profile':REPORT_PROFILE,'generator':'index'})
    return value

def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and encode(source.get('node_context'))!=encode(node):raise ValueError('pilot_projection_foreign_node')
    path_spec(source.get('source_root'),source.get('source_root'),request['cwd_label']);current['source_root']=source['source_root']
    if encode(source)!=encode(current):raise ValueError('pilot_projection_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version']!=1
            or any(type(retained.get(k)) is not type(v) or retained.get(k)!=v for k,v in AUTHORITY.items())
            or type(retained['touched_files']) is not dict or len(events)<3
            or encode(events[0])!=encode({'kind':'opened',**AUTHORITY})
            or encode(events[1])!=encode({'kind':'execution-intent','request':request})):
        raise ValueError('pilot_projection_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:
        raise ValueError('pilot_projection_terminal_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
    owner=ReplayIO(events,blob,request['export_mode'],request['cwd_label'])
    kernel=execute(request['source_label'],request['cwd_label'],request['program'],request['argv'],owner,
        validator_class=closed_validator(owner,request),provider_factory=captured_provider(request['capture_profile']));owner.finish()
    if (encode(result_value(kernel,owner))!=encode(retained['result']) or encode(owner.touched)!=encode(retained['touched_files'])
            or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed()):
        raise ValueError('pilot_projection_whole_result_changed')
    return {'state':'complete','program':request['program'],'original_exit_code':kernel['exit_code'],
        'kernel_exception':kernel['kernel_exception'],'original_exit_signal':kernel['original_exit_signal'],
        'successful_outputs':owner.files,'successful_writes':owner.writes,'private_projected_changes':owner.projected_changes,
        'private_creation_mask':PRIVATE_MASK if request['export_mode']=='private-candidate' else None,
        'source_export_requested':request['export_mode']=='selected-files','source_output_paths_observed':sorted(owner.touched),
        'retained_declared_replay_consistent':True,'native_source_or_exports_repeated':False,**AUTHORITY}

def generate(options,instance,settings):
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
    root=posixpath.normpath(str(Path(options['source_worktree']).expanduser().absolute()))
    cwd=posixpath.normpath(str(Path(options.get('working_directory') or root).expanduser().absolute()))
    argv=list(options['legacy_arguments'])
    if argv[:1]==['--']:argv=argv[1:]
    request=request_valid({'schema_version':1,'profile':PROFILE,'program':options['program'],'source_label':root,'cwd_label':cwd,
        'argv':argv,'export_mode':'selected-files' if options.get('write_selected_files') else 'private-candidate',
        'resources':[{'uri':uri,'label':posixpath.normpath(str(Path(path).expanduser().absolute()))} for uri,path in options.get('schema_resource',[]) or []],
        'capture_profile':options['capture_profile']})
    instance=owned_directory(instance)
    if Path(root).is_relative_to(instance) or instance.is_relative_to(Path(root)):raise ValueError('pilot_projection_source_instance_overlap')
    source=current_source(node);record=Record(owned_directory(instance/'state/pilot-projections/records',True),request,source);record.append({'kind':'execution-intent','request':request})
    owner=result=error=None
    try:
        owner=NativeIO(record,mode=request['export_mode'],cwd=cwd,private_state=instance,product_root=ROOT)
        kernel=execute(root,cwd,request['program'],argv,owner,validator_class=closed_validator(owner,request),provider_factory=captured_provider(request['capture_profile']));result=result_value(kernel,owner)
        if encode(current_source(node))!=encode(source):raise InputAdmissionError('pilot_projection_product_changed')
    except Exception as caught:error=caught
    completeness='incomplete' if error is not None or record.capture_incomplete else 'complete';journal_complete=True
    try:record.finish(completeness,result,{} if owner is None else owner.touched,error)
    except Exception:completeness='incomplete';journal_complete=False
    if completeness=='complete':inspect(record.root,node=node)
    return {'state':completeness,'record_root':str(record.root),'journal_terminal_written':journal_complete,
        'exit_code':2 if completeness=='incomplete' else result['exit_code'],'original_exit_code':None if completeness=='incomplete' else result['exit_code'],
        'export_mode':request['export_mode'],'source_export_requested':request['export_mode']=='selected-files',
        'source_effects_may_be_partial':request['export_mode']=='selected-files' and (completeness=='incomplete' or result['exit_code']!=0),
        'source_output_paths_observed':sorted({} if owner is None else owner.touched),**AUTHORITY},result

def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 pilot-projections',allow_abbrev=False)
    sub=parser.add_subparsers(dest='command',required=True);item=sub.add_parser('generate',allow_abbrev=False)
    item.add_argument('--capture-profile',choices=CAPTURE_PROFILES,required=True);item.add_argument('--profile',choices=(PROFILE,),required=True);item.add_argument('--program',choices=tuple(PROGRAMS),required=True);item.add_argument('--source-worktree',required=True)
    item.add_argument('--working-directory');item.add_argument('--write-selected-files',action='store_true');item.add_argument('--schema-resource',nargs=2,action='append',metavar=('URI','FILE'))
    item.add_argument('--format',choices=('receipt','legacy'),default='receipt');item.add_argument('legacy_arguments',nargs=argparse.REMAINDER)
    for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':value=inspect(options.record)
    else:
        if instance is None or settings is None:raise ValueError('pilot_projection_instance_required')
        if options.command=='inspect':value=inspect(options.record,node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')})
        else:
            receipt,result=generate(vars(options),instance,settings)
            if options.format=='legacy' and receipt['state']=='complete':
                kernel=result['kernel_result'];sys.stdout.write(kernel['stdout']);sys.stderr.write(kernel['stderr'])
                if kernel['kernel_exception'] is not None:print(json.dumps({'execution':'captured_exception',**kernel['kernel_exception']}),file=sys.stderr)
            else:print(json.dumps(receipt,indent=2))
            return receipt['exit_code']
    print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
