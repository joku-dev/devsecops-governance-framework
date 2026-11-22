"""Whole GET-only provider observation, private technical capture and inert replay."""
from pathlib import Path
import argparse,json,posixpath
from lib.provider_observation_ports import (execute,NativeIO,ReplayIO,Record,read_record,encode,
    AUTHORITY,owned_directory,current_source,ROOT,capture_parser_context)
from lib.synthetic_lifecycle_io import path_spec
from lib.retained_argparse import validate_context
from lib.requirement_validation_budget import InputAdmissionError

PROFILE='legacy-provider-observation-v1'
SCOPE={'verification_scope':'whole_original_provider_observation','provider_access':'GET_only',
    'credential_payload_retained':False,'producer_identity_authenticated':False,'publisher_service_activated':False,
    'automatic_retry_or_rollback':False}


def request_valid(value):
    fields={'schema_version','profile','source_label','cwd_label','private_state_label','argv','parser_context'}
    if (type(value) is not dict or set(value)!=fields or type(value['schema_version']) is not int or value['schema_version']!=1
            or value['profile']!=PROFILE or type(value['argv']) is not list or len(value['argv'])>64
            or any(type(arg) is not str or len(arg)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in arg) for arg in value['argv'])
            or sum(map(len,value['argv']))>32768):raise ValueError('provider_observation_request_changed')
    for key in ('source_label','cwd_label','private_state_label'):path_spec(value[key],value[key],value['cwd_label'])
    validate_context(value['parser_context']);return value


def result_value(kernel,owner):
    return {'exit_code':kernel['exit_code'],'kernel_result':kernel,'observed_directory_effects':owner.touched}


def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and encode(source.get('node_context'))!=encode(node):raise ValueError('provider_observation_foreign_node')
    path_spec(source.get('source_root'),source.get('source_root'),request['cwd_label']);current['source_root']=source['source_root']
    if encode(source)!=encode(current) or request['source_label']!=source['source_root']:raise ValueError('provider_observation_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version']!=1
            or any(type(retained.get(k)) is not type(v) or retained.get(k)!=v for k,v in AUTHORITY.items())
            or type(retained['touched_files']) is not dict or len(events)<3
            or encode(events[0])!=encode({'kind':'opened',**AUTHORITY})
            or encode(events[1])!=encode({'kind':'execution-intent','request':request})):raise ValueError('provider_observation_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:raise ValueError('provider_observation_terminal_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,**SCOPE,**AUTHORITY}
    owner=ReplayIO(events,blob,'selected-files',request['cwd_label']);kernel=execute(request,owner,source['node_context'])
    if (encode(result_value(kernel,owner))!=encode(retained['result']) or encode(owner.touched)!=encode(retained['touched_files'])
            or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed()):raise ValueError('provider_observation_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],'original_return_value':kernel['return_value'],
        'original_exit_signal':kernel['original_exit_signal'],'kernel_exception':kernel['kernel_exception'],
        'atomic_output_snapshot':kernel['atomic_output_snapshot'],'retained_declared_replay_consistent':True,
        'native_source_or_exports_repeated':False,**SCOPE,**AUTHORITY}


def generate(options,instance,settings,*,clock=None):
    instance=owned_directory(instance);node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')}
    source=current_source(node);argv=list(options['legacy_arguments']);argv=argv[1:] if argv[:1]==['--'] else argv
    cwd=posixpath.normpath(str(Path(options.get('working_directory') or Path.cwd()).expanduser().absolute()))
    request=request_valid({'schema_version':1,'profile':PROFILE,'source_label':str(ROOT),'cwd_label':cwd,
        'private_state_label':str(instance),'argv':argv,'parser_context':capture_parser_context()})
    if instance.is_relative_to(ROOT) or ROOT.is_relative_to(instance):raise ValueError('provider_observation_instance_product_overlap')
    record=Record(owned_directory(instance/'state/provider-observation/records',True),request,source)
    record.append({'kind':'execution-intent','request':request});owner=result=error=None
    try:
        owner=NativeIO(record,mode='selected-files',cwd=cwd,private_state=instance,product_root=ROOT)
        kernel=execute(request,owner,node,clock=clock);result=result_value(kernel,owner)
        if encode(current_source(node))!=encode(source):raise InputAdmissionError('provider_observation_product_changed')
    except Exception as caught:error=caught
    state='incomplete' if error is not None or record.capture_incomplete else 'complete';journal_complete=True
    try:record.finish(state,result,{} if owner is None else owner.touched,error)
    except Exception:state='incomplete';journal_complete=False
    if state=='complete':inspect(record.root,node=node)
    return {'state':state,'record_root':str(record.root),'journal_terminal_written':journal_complete,
        'exit_code':2 if state=='incomplete' else result['exit_code'],'original_exit_code':None if state=='incomplete' else result['exit_code'],
        'original_return_value':None if state=='incomplete' else result['kernel_result']['return_value'],**SCOPE,**AUTHORITY},result


def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 provider-observation',allow_abbrev=False);sub=parser.add_subparsers(dest='command',required=True)
    item=sub.add_parser('capture',allow_abbrev=False);item.add_argument('--profile',required=True,choices=(PROFILE,));item.add_argument('--working-directory');item.add_argument('legacy_arguments',nargs=argparse.REMAINDER,help='Use -- followed by the unchanged original observe_provider_assurance.py arguments.')
    for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':value=inspect(options.record)
    else:
        if instance is None or settings is None:raise ValueError('provider_observation_instance_required')
        if options.command=='inspect':value=inspect(options.record,node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')})
        else:receipt,_=generate(vars(options),instance,settings);print(json.dumps(receipt,indent=2));return receipt['exit_code']
    print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
