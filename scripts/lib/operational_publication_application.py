"""One-shot whole original operational proposals and closed source-free replay."""
import argparse,json,posixpath
from pathlib import Path
from lib.operational_publication_ports import (execute,NativeIO,Record,read_record,encode,AUTHORITY,owned_directory,current_source,ROOT,
    ledger,transaction_name,temporary_parent,capture_parser_context,DEFAULT_PROVIDER_EXECUTABLE,public_environment,environment_valid,outputs)
from lib.pilot_run_intake_io import ReplayRunIO
from lib.synthetic_lifecycle_application import closed_validator,result_value
from lib.synthetic_lifecycle_io import path_spec
from lib.retained_argparse import validate_context
from lib.requirement_validation_budget import InputAdmissionError
PROFILE='legacy-operational-publisher-v1'
TRANSPORT_PROFILES=('legacy-operational-publisher-native-v1','legacy-operational-publisher-local-test-v1')
SCOPE={'verification_scope':'whole_original_operational_publisher','native_publication_requested':True,
    'external_completion_independently_proven':False,'automatic_retry_or_rollback':False,'publisher_service_activated':False}
COMPONENTS=('operational_publication.py','operational_publication_process.py','operational_publication_paths.py',
    'operational_publication_context.py','operational_publication_ports.py','operational_publication_application.py',
    'operational_publication_gate_context.py','operational_publication_gate_ports.py','operational_publication_gates.py',
    'providers/operational_publication_record.py','providers/operational_publication_paths.py','providers/operational_publication_protocol.py',
    'providers/operational_publication_profile.py','providers/operational_publication_process.py','providers/operational_publication_api.py')

def request_valid(value):
    fields={'schema_version','profile','transport_profile','source_label','cwd_label','subject','argv','invocation','environment',
        'parser_context','provider_executable','temporary_parent','export_mode','resources','local_origin_root','private_state_label'}
    if type(value) is not dict or set(value)!=fields or type(value['schema_version']) is not int or value['schema_version']!=1 or value['profile']!=PROFILE or value['transport_profile'] not in TRANSPORT_PROFILES or value['invocation'] not in ('publish','main'):raise ValueError('publisher_request_changed')
    path_spec(value['source_label'],value['source_label'],value['cwd_label']);path_spec(value['cwd_label'],value['cwd_label'],value['cwd_label'])
    if type(value['subject']) is not dict or set(value['subject'])!={'scope','repository','run_id','attempt'} or any(type(v) is not str for v in value['subject'].values()):raise ValueError('publisher_subject_changed')
    from lib.operational_publication_ports import LegacyPublisherProtocol
    try:LegacyPublisherProtocol(value['source_label'],**value['subject'],cwd=value['cwd_label'],local_origin_root=value['local_origin_root'])
    except InputAdmissionError as error:raise ValueError(str(error)) from None
    if type(value['argv']) is not list or len(value['argv'])>256 or any(type(v) is not str or len(v)>8192 or '\0' in v for v in value['argv']):raise ValueError('publisher_original_argv_changed')
    path_spec(value['private_state_label'],value['private_state_label'],value['cwd_label'])
    environment_valid(value['environment'],value['subject']);validate_context(value['parser_context'])
    if type(value['provider_executable']) is not str or not value['provider_executable'] or len(value['provider_executable'])>8192 or '\0' in value['provider_executable']:raise ValueError('publisher_provider_executable_changed')
    local=value['local_origin_root']
    if (value['transport_profile']=='legacy-operational-publisher-local-test-v1')!=(local is not None):raise ValueError('publisher_local_origin_profile_changed')
    if local is not None:path_spec(local,local,value['cwd_label'])
    from lib.synthetic_lifecycle_application import PROFILE as REPORT_PROFILE,request_fields_valid
    request_fields_valid({**{k:value[k] for k in ('schema_version','source_label','cwd_label','export_mode','resources')},'argv':[],'profile':REPORT_PROFILE,'generator':'index'})
    path_spec(value['temporary_parent'],value['temporary_parent'],value['cwd_label'])
    return value

def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and encode(node)!=encode(source.get('node_context')):raise ValueError('publisher_foreign_node')
    path_spec(source.get('source_root'),source.get('source_root'),request['cwd_label']);current['source_root']=source['source_root']
    if encode(source)!=encode(current):raise ValueError('publisher_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
        or type(retained['schema_version']) is not int or retained['schema_version']!=1 or any(type(retained.get(k)) is not type(v) or retained.get(k)!=v for k,v in AUTHORITY.items())
        or type(retained['touched_files']) is not dict or len(events)<3 or encode(events[0])!=encode({'kind':'opened',**AUTHORITY}) or encode(events[1])!=encode({'kind':'execution-intent','request':request})):
        raise ValueError('publisher_record_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:raise ValueError('publisher_terminal_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,'external_writes_may_have_occurred':True,**SCOPE,**AUTHORITY}
    owner=ReplayRunIO(events,blob,request['export_mode'],request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)
    kernel=execute(request,owner,validator_class=closed_validator(owner,request));owner.finish()
    if (encode(result_value(kernel,owner))!=encode(retained['result']) or encode(owner.touched)!=encode(retained['touched_files'])
        or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed()):raise ValueError('publisher_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],'original_return_value':kernel['return_value'],'kernel_exception':kernel['kernel_exception'],
        'original_exit_signal':kernel['original_exit_signal'],'native_process_operations':kernel['native_process_observations'],'pipeline_append_observations':kernel['pipeline_append_observations'],
        'external_writes_may_have_occurred':any(v['write_requested'] and v['started'] for v in kernel['native_process_observations']),
        'retained_declared_replay_consistent':True,'native_source_or_exports_repeated':False,**SCOPE,**AUTHORITY}

def generate(options,instance,settings,*,native_environment=None):
    from lib.v2_source import selected_paths
    if not {'scripts/lib/'+v for v in COMPONENTS}<=set(selected_paths(ROOT)):raise ValueError('publisher_closure_not_registered')
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
    source_root=posixpath.normpath(str(Path(options['source_worktree']).expanduser().absolute()));cwd=posixpath.normpath(str(Path(options.get('working_directory') or Path.cwd()).expanduser().absolute()))
    origin=options.get('local_origin_root');origin=None if origin is None else posixpath.normpath(str(Path(origin).expanduser().absolute()))
    invocation=options.get('invocation','main');argv=options.get('original_arguments');argv=['--scope',options['scope']] if argv is None else argv
    request=request_valid({'schema_version':1,'profile':options['profile'],'transport_profile':options['transport_profile'],'source_label':source_root,'cwd_label':cwd,
        'subject':{key:options[key] for key in ('scope','repository','run_id','attempt')},'argv':argv,'invocation':invocation,'environment':public_environment(options),
        'parser_context':capture_parser_context(),'provider_executable':options.get('provider_executable',DEFAULT_PROVIDER_EXECUTABLE),'temporary_parent':temporary_parent('selected-files' if options.get('native_temporaries') else 'private-candidate',options.get('temporary_parent')),
        'export_mode':'selected-files' if options.get('native_temporaries') else 'private-candidate','resources':[{'uri':uri,'label':posixpath.normpath(str(Path(path).expanduser().absolute()))} for uri,path in options.get('schema_resource',[]) or []],'local_origin_root':origin,'private_state_label':posixpath.normpath(str(Path(instance).expanduser().absolute()))})
    instance=owned_directory(instance)
    if Path(source_root).is_relative_to(instance) or instance.is_relative_to(Path(source_root)) or Path(source_root).is_relative_to(ROOT) or ROOT.is_relative_to(Path(source_root)):raise ValueError('publisher_source_instance_or_product_overlap')
    for output in outputs(request['environment'],cwd):
        if Path(output).is_relative_to(instance) or Path(output).is_relative_to(Path(source_root)) or Path(output).is_relative_to(ROOT):raise ValueError('publisher_pipeline_output_source_or_instance_overlap')
    source=current_source(node);record=Record(owned_directory(instance/'state/operational-publisher/records',True),request,source);record.append({'kind':'execution-intent','request':request});owner=result=error=None
    try:
        owner=NativeIO(record,mode=request['export_mode'],cwd=cwd,private_state=instance,product_root=ROOT,ledger=ledger(source_root),transaction_name=transaction_name)
        kernel=execute(request,owner,validator_class=closed_validator(owner,request),native_environment=native_environment);result=result_value(kernel,owner)
        if encode(current_source(node))!=encode(source):raise InputAdmissionError('publisher_product_changed')
    except Exception as caught:error=caught
    state='incomplete' if error is not None or record.capture_incomplete else 'complete';journal_complete=True
    try:record.finish(state,result,{} if owner is None else owner.touched,error)
    except Exception:state='incomplete';journal_complete=False
    if state=='complete':inspect(record.root,node=node)
    return {'state':state,'record_root':str(record.root),'journal_terminal_written':journal_complete,'exit_code':2 if state=='incomplete' else result['exit_code'],
        'original_exit_code':None if state=='incomplete' else result['exit_code'],'original_return_value':None if state=='incomplete' else result['kernel_result']['return_value'],'external_writes_may_have_occurred':True if state=='incomplete' else any(v['write_requested'] and v['started'] for v in result['kernel_result']['native_process_observations']),
        'host_resource_release':[] if owner is None else getattr(owner,'adapter_cleanup',[]),**SCOPE,**AUTHORITY},result

def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 operational-publisher',allow_abbrev=False);sub=parser.add_subparsers(dest='command',required=True)
    item=sub.add_parser('publish',allow_abbrev=False);item.add_argument('--profile',choices=(PROFILE,),required=True);item.add_argument('--transport-profile',choices=TRANSPORT_PROFILES,required=True)
    for name in ('source-worktree','scope','repository','run-id','attempt'):item.add_argument('--'+name,required=True)
    item.add_argument('--workflow-ref',required=True,help='Declared original workflow ref; this does not attest a protected workflow or transfer operating authority.')
    item.add_argument('--invocation',choices=('main','publish'),default='main');item.add_argument('--working-directory');item.add_argument('--provider-executable',default=DEFAULT_PROVIDER_EXECUTABLE);item.add_argument('--local-origin-root')
    item.add_argument('--output-file');item.add_argument('--summary-file');item.add_argument('--temporary-parent');item.add_argument('--native-temporaries',action='store_true');item.add_argument('--schema-resource',nargs=2,action='append',metavar=('URI','FILE'));item.add_argument('--original-arguments',nargs=argparse.REMAINDER)
    for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':value=inspect(options.record)
    else:
        if instance is None or settings is None:raise ValueError('publisher_instance_required')
        if options.command=='inspect':value=inspect(options.record,node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')})
        else:
            receipt,_=generate(vars(options),instance,settings);print(json.dumps(receipt,indent=2));return receipt['exit_code']
    print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
