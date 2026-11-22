"""Complete original pilot update and operating-write APIs with closed reconstruction."""
import argparse,json,posixpath,sys
from pathlib import Path
from lib.pilot_update_ports import (NativeIO,Record,read_record,encode,AUTHORITY,
    owned_directory,current_source,ROOT,TRANSPORT_PROFILES,execute_request as execute,capture_parser_context,
    DEFAULT_PROVIDER_EXECUTABLE,transaction_name,replay_owner,temporary_parent)
from lib.synthetic_lifecycle_application import closed_validator,result_value,request_fields_valid as report_request
from lib.synthetic_lifecycle_io import path_spec
from lib.synthetic_lifecycle_projection import PRIVATE_MASK
from lib.retained_argparse import validate_context as validate_parser_context
from lib.requirement_validation_budget import InputAdmissionError

PROFILE='legacy-pilot-update-v1'
SCOPE={'verification_scope':'whole_original_pilot_update_run_and_operating_capture_generate','publication_included':False,'node_operating_activation_included':False}

def observed_paths(owner,kernel):
    paths=set() if owner is None else set(owner.touched)
    if kernel is not None:
        for values in kernel['native_ledger_observations'].values():paths.update(values)
    return sorted(paths)

def request_valid(value):
    keys={'schema_version','profile','source_label','cwd_label','argv','export_mode','resources','transport_profile','parser_context','provider_executable','temporary_parent','invocation'}
    if type(value) is not dict or set(value)!=keys or value['profile']!=PROFILE:raise ValueError('pilot_update_request_changed')
    if type(value['transport_profile']) is not str or value['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('pilot_update_transport_profile_not_supported')
    if type(value['provider_executable']) is not str or not value['provider_executable'] or len(value['provider_executable'])>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value['provider_executable']):raise ValueError('pilot_update_provider_executable_changed')
    path_spec(value['temporary_parent'],value['temporary_parent'],value['cwd_label'])
    validate_parser_context(value['parser_context'])
    invocation=value['invocation']
    if invocation is not None:
        if (type(invocation) is not dict or set(invocation)!={'method','arguments'} or invocation['method'] not in ('capture','generate','run') or type(invocation['arguments']) is not dict):raise ValueError('pilot_update_API_invocation_changed')
        if invocation['method']=='run':
            args=invocation['arguments']
            if (not {'operation'}<=set(args)<= {'operation','run_id','request_path'} or type(args['operation']) is not str or any(v is not None and (type(v) is not str or len(v)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in v)) for v in args.values())):raise ValueError('pilot_update_run_arguments_changed')
        elif invocation['arguments']:raise ValueError('pilot_update_helper_arguments_changed')
        if value['argv']:raise ValueError('pilot_update_API_and_parser_arguments_conflict')

    from lib.synthetic_lifecycle_application import PROFILE as REPORT_PROFILE
    subset={key:value[key] for key in ('schema_version','source_label','cwd_label','argv','export_mode','resources')}
    report_request({**subset,'profile':REPORT_PROFILE,'generator':'index'})
    return value

def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and encode(source.get('node_context'))!=encode(node):raise ValueError('pilot_update_foreign_node')
    path_spec(source.get('source_root'),source.get('source_root'),request['cwd_label']);current['source_root']=source['source_root']
    if encode(source)!=encode(current):raise ValueError('pilot_update_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version']!=1
            or any(type(retained.get(k)) is not type(v) or retained.get(k)!=v for k,v in AUTHORITY.items())
            or type(retained['touched_files']) is not dict or len(events)<3
            or encode(events[0])!=encode({'kind':'opened',**AUTHORITY})
            or encode(events[1])!=encode({'kind':'execution-intent','request':request})):
        raise ValueError('pilot_update_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:
        raise ValueError('pilot_update_terminal_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
    owner=replay_owner(request,events,blob)
    kernel=execute(request,owner,validator_class=closed_validator(owner,request));owner.finish()
    if (encode(result_value(kernel,owner))!=encode(retained['result']) or encode(owner.touched)!=encode(retained['touched_files'])
            or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed()):
        raise ValueError('pilot_update_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],'kernel_exception':kernel['kernel_exception'],
        'original_exit_signal':kernel['original_exit_signal'],'original_return_value':kernel['return_value'],'successful_outputs':owner.files,'successful_writes':owner.writes,
        'private_projected_changes':owner.projected_changes,'private_creation_mask':PRIVATE_MASK if request['export_mode']=='private-candidate' else None,
        'source_export_requested':request['export_mode']=='selected-files','source_output_paths_observed':observed_paths(owner,kernel),
        'retained_declared_replay_consistent':True,'native_source_or_exports_repeated':False,
        'native_ledger_observations':kernel['native_ledger_observations'],'kernel_end_ledger_descriptors':kernel['kernel_end_ledger_descriptors'],**SCOPE,**AUTHORITY}

def generate(options,instance,settings):
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
    root=posixpath.normpath(str(Path(options['source_worktree']).expanduser().absolute()))
    cwd=posixpath.normpath(str(Path(options.get('working_directory') or root).expanduser().absolute()))
    argv=list(options['legacy_arguments'])
    if argv[:1]==['--']:argv=argv[1:]
    request=request_valid({'schema_version':1,'profile':PROFILE,'source_label':root,'cwd_label':cwd,'argv':argv,
        'export_mode':'selected-files' if options.get('write_selected_files') else 'private-candidate',
        'resources':[{'uri':uri,'label':posixpath.normpath(str(Path(path).expanduser().absolute()))} for uri,path in options.get('schema_resource',[]) or []],
        'transport_profile':options['transport_profile'],'provider_executable':options.get('provider_executable',DEFAULT_PROVIDER_EXECUTABLE),'parser_context':capture_parser_context(),
        'temporary_parent':temporary_parent('selected-files' if options.get('write_selected_files') else 'private-candidate',options.get('temporary_parent')),
        'invocation':options['invocation'] if 'invocation' in options else ({'method':options['helper'],'arguments':{}} if options.get('helper') else None)})
    instance=owned_directory(instance)
    if Path(root).is_relative_to(instance) or instance.is_relative_to(Path(root)):raise ValueError('pilot_update_source_instance_overlap')
    source=current_source(node);record=Record(owned_directory(instance/'state/pilot-update/records',True),request,source);record.append({'kind':'execution-intent','request':request})
    owner=result=error=None
    try:
        owner=NativeIO(record,mode=request['export_mode'],cwd=cwd,private_state=instance,product_root=ROOT,source=root,transaction_name=transaction_name)
        kernel=execute(request,owner,validator_class=closed_validator(owner,request));result=result_value(kernel,owner)
        if encode(current_source(node))!=encode(source):raise InputAdmissionError('pilot_update_product_changed')
    except Exception as caught:error=caught
    state='incomplete' if error is not None or record.capture_incomplete else 'complete';journal_complete=True
    try:record.finish(state,result,{} if owner is None else owner.touched,error)
    except Exception:state='incomplete';journal_complete=False
    if state=='complete':inspect(record.root,node=node)
    return {'state':state,'record_root':str(record.root),'journal_terminal_written':journal_complete,
        'exit_code':2 if state=='incomplete' else result['exit_code'],'original_exit_code':None if state=='incomplete' else result['exit_code'],
        'original_return_value':None if state=='incomplete' else result['kernel_result']['return_value'],
        'export_mode':request['export_mode'],'source_export_requested':request['export_mode']=='selected-files',
        'source_effects_may_be_partial':request['export_mode']=='selected-files' and (state=='incomplete' or result['exit_code']!=0),
        'source_output_paths_observed':observed_paths(owner,None if result is None else result['kernel_result']),
        'host_resource_release':[] if owner is None else getattr(owner,'adapter_cleanup',[]),**SCOPE,**AUTHORITY},result

def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 pilot-update',allow_abbrev=False)
    sub=parser.add_subparsers(dest='command',required=True);item=sub.add_parser('generate',allow_abbrev=False)
    item.add_argument('--transport-profile',choices=TRANSPORT_PROFILES,required=True);item.add_argument('--profile',choices=(PROFILE,),required=True)
    item.add_argument('--provider-executable',default=DEFAULT_PROVIDER_EXECUTABLE)
    item.add_argument('--temporary-parent');item.add_argument('--helper',choices=('capture','generate'))
    item.add_argument('--source-worktree',required=True);item.add_argument('--working-directory');item.add_argument('--write-selected-files',action='store_true')
    item.add_argument('--schema-resource',nargs=2,action='append',metavar=('URI','FILE'));item.add_argument('--format',choices=('receipt','legacy'),default='receipt')
    item.add_argument('legacy_arguments',nargs=argparse.REMAINDER)
    for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':value=inspect(options.record)
    else:
        if instance is None or settings is None:raise ValueError('pilot_update_instance_required')
        if options.command=='inspect':value=inspect(options.record,node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')})
        else:
            receipt,result=generate(vars(options),instance,settings)
            if options.format=='legacy' and receipt['state']=='complete':
                from lib.personal_channel_application import emit_legacy
                emit_legacy(result,read_record(receipt['record_root'])[4])
            else:print(json.dumps(receipt,indent=2))
            return receipt['exit_code']
    print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
