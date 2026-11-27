"""One-shot whole original self-security publish and source-free replay."""
from pathlib import Path
import argparse,json,posixpath
from lib.self_security_publication_ports import (execute,NativeIO,ReplaySelfSecurityIO,Record,read_record,encode,AUTHORITY,owned_directory,current_source,ROOT,ledger,transaction_name,public_environment,environment_valid,output_paths,LegacySelfSecurityPublicationProtocol,DEFAULT_PROVIDER_EXECUTABLE)
from lib.synthetic_lifecycle_application import result_value
from lib.synthetic_lifecycle_io import path_spec
from lib.requirement_validation_budget import InputAdmissionError
PROFILE='legacy-self-security-publisher-v1'
TRANSPORT_PROFILES=('legacy-self-security-publisher-native-v1','legacy-self-security-publisher-local-test-v1')
SCOPE={'verification_scope':'whole_original_self_security_publisher','source_report_write_mode':'selected-files','native_publication_requested':True,'publisher_service_activated':False,'external_completion_independently_proven':False,'automatic_retry_or_rollback':False}
COMPONENTS=('self_security_publication.py','self_security_publication_context.py','self_security_publication_io.py','self_security_publication_ports.py','self_security_publication_application.py','providers/self_security_publication_profile.py','providers/self_security_publication_api.py','providers/self_security_publication_protocol.py','providers/self_security_publication_process.py','providers/self_security_publication_io.py')


def request_valid(value):
    fields={'schema_version','profile','transport_profile','source_label','cwd_label','subject','environment','provider_executable','local_origin_root','private_state_label','invocation','export_mode'}
    if type(value) is not dict or set(value)!=fields or type(value['schema_version']) is not int or value['schema_version']!=1 or value['profile']!=PROFILE or value['transport_profile'] not in TRANSPORT_PROFILES or value['invocation'] not in ('main','publish') or value['export_mode']!='selected-files':raise ValueError('self_security_request_changed')
    for key in ('source_label','cwd_label','private_state_label'):path_spec(value[key],value[key],value['cwd_label'])
    if type(value['subject']) is not dict or set(value['subject'])!={'repository','run_id','attempt'} or any(type(v) is not str for v in value['subject'].values()):raise ValueError('self_security_subject_changed')
    local=value['local_origin_root']
    if (value['transport_profile']=='legacy-self-security-publisher-local-test-v1')!=(local is not None):raise ValueError('self_security_local_origin_profile_changed')
    if local is not None:path_spec(local,local,value['cwd_label'])
    try:LegacySelfSecurityPublicationProtocol(value['source_label'],**value['subject'],cwd=value['cwd_label'],local_origin_root=local,private_state_label=value['private_state_label'])
    except InputAdmissionError as error:raise ValueError(str(error)) from None
    environment_valid(value['environment'],value['subject'])
    tool=value['provider_executable']
    if type(tool) is not str or not tool or len(tool)>8192 or '\0' in tool:raise ValueError('self_security_provider_executable_changed')
    return value


def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request);current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and encode(node)!=encode(source.get('node_context')):raise ValueError('self_security_foreign_node')
    path_spec(source.get('source_root'),source.get('source_root'),request['cwd_label']);current['source_root']=source['source_root']
    if encode(source)!=encode(current):raise ValueError('self_security_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY} or type(retained['schema_version']) is not int or retained['schema_version']!=1 or any(type(retained.get(k)) is not type(v) or retained.get(k)!=v for k,v in AUTHORITY.items()) or type(retained['touched_files']) is not dict or len(events)<3 or encode(events[0])!=encode({'kind':'opened',**AUTHORITY}) or encode(events[1])!=encode({'kind':'execution-intent','request':request})):raise ValueError('self_security_record_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:raise ValueError('self_security_terminal_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,'external_writes_may_have_occurred':True,**SCOPE,**AUTHORITY}
    owner=ReplaySelfSecurityIO(events,blob,request['export_mode'],request['cwd_label'],source=request['source_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name);kernel=execute(request,owner);owner.finish()
    if encode(result_value(kernel,owner))!=encode(retained['result']) or encode(owner.touched)!=encode(retained['touched_files']) or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed():raise ValueError('self_security_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],'original_return_value':kernel['return_value'],'kernel_exception':kernel['kernel_exception'],'original_exit_signal':kernel['original_exit_signal'],'known_source_worktree_transitions':kernel['known_source_worktree_transitions'],'successful_source_writes':owner.writes,'pipeline_append_observations':kernel['pipeline_append_observations'],'native_process_observations':kernel['native_process_observations'],'external_writes_may_have_occurred':any(v['write_requested'] and v['started'] for v in kernel['native_process_observations']) or bool(owner.writes),'retained_declared_replay_consistent':True,'native_source_or_exports_repeated':False,**SCOPE,**AUTHORITY}


def generate(options,instance,settings,*,native_environment=None):
    from lib.v2_source import selected_paths
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):raise ValueError('self_security_closure_not_registered')
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')};instance=owned_directory(instance)
    source_root=posixpath.normpath(str(Path(options['source_worktree']).expanduser().absolute()));cwd=posixpath.normpath(str(Path(options.get('working_directory') or Path.cwd()).expanduser().absolute()));origin=options.get('local_origin_root');origin=None if origin is None else posixpath.normpath(str(Path(origin).expanduser().absolute()))
    request=request_valid({'schema_version':1,'profile':PROFILE,'transport_profile':options['transport_profile'],'source_label':source_root,'cwd_label':cwd,'subject':{k:options[k] for k in ('repository','run_id','attempt')},'environment':public_environment(options),'provider_executable':options.get('provider_executable',DEFAULT_PROVIDER_EXECUTABLE),'local_origin_root':origin,'private_state_label':str(instance),'invocation':options.get('invocation','main'),'export_mode':'selected-files'})
    if Path(source_root).is_relative_to(instance) or instance.is_relative_to(Path(source_root)) or Path(source_root).is_relative_to(ROOT) or ROOT.is_relative_to(Path(source_root)):raise ValueError('self_security_source_instance_or_product_overlap')
    for output in output_paths(request['environment'],cwd):
        if Path(output).is_relative_to(instance) or Path(output).is_relative_to(Path(source_root)) or Path(output).is_relative_to(ROOT):raise ValueError('self_security_pipeline_output_source_or_instance_overlap')
    source=current_source(node);record=Record(owned_directory(instance/'state/self-security-publisher/records',True),request,source);record.append({'kind':'execution-intent','request':request});owner=result=error=None
    try:
        owner=NativeIO(record,source=source_root,mode='selected-files',cwd=cwd,private_state=instance,product_root=ROOT,ledger=ledger(source_root),transaction_name=transaction_name);kernel=execute(request,owner,native_environment=native_environment);result=result_value(kernel,owner)
        if encode(current_source(node))!=encode(source):raise InputAdmissionError('self_security_product_changed')
    except Exception as caught:error=caught
    state='incomplete' if error is not None or record.capture_incomplete else 'complete';journal_complete=True
    try:record.finish(state,result,{} if owner is None else owner.touched,error)
    except Exception:state='incomplete';journal_complete=False
    if state=='complete':inspect(record.root,node=node)
    return {'state':state,'record_root':str(record.root),'journal_terminal_written':journal_complete,'exit_code':2 if state=='incomplete' else result['exit_code'],'original_exit_code':None if state=='incomplete' else result['exit_code'],'original_return_value':None if state=='incomplete' else result['kernel_result']['return_value'],'external_writes_may_have_occurred':True if state=='incomplete' else any(v['write_requested'] and v['started'] for v in result['kernel_result']['native_process_observations']) or bool(owner.writes),**SCOPE,**AUTHORITY},result


def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 self-security-publisher',allow_abbrev=False);sub=parser.add_subparsers(dest='command',required=True);item=sub.add_parser('publish',allow_abbrev=False);item.add_argument('--profile',choices=(PROFILE,),required=True);item.add_argument('--transport-profile',choices=TRANSPORT_PROFILES,required=True)
    for name in ('source-worktree','repository','run-id','attempt'):item.add_argument('--'+name,required=True)
    item.add_argument('--workflow-ref',required=True,help='Declared original workflow ref; this does not attest a protected workflow or transfer authority.');item.add_argument('--working-directory');item.add_argument('--provider-executable',default=DEFAULT_PROVIDER_EXECUTABLE);item.add_argument('--local-origin-root');item.add_argument('--invocation',choices=('main','publish'),default='main');item.add_argument('--output-file');item.add_argument('--summary-file')
    for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':value=inspect(options.record)
    else:
        if instance is None or settings is None:raise ValueError('self_security_instance_required')
        if options.command=='inspect':value=inspect(options.record,node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')})
        else:receipt,_=generate(vars(options),instance,settings);print(json.dumps(receipt,indent=2));return receipt['exit_code']
    print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
