"""Whole original document rendering, explicit effects and source-bound replay."""
import argparse,json,math,os,sys
from pathlib import Path

from lib.document_rendering_context import execute
from lib.document_rendering_io import ReplayIO,path_spec
from lib.requirement_validation_budget import InputAdmissionError
from lib.document_rendering_ports import (Data,Output,Tools,Record,read_record,
    owned_directory,encode,AUTHORITY,current_source,ROOT,capture_parser_context)

from lib.retained_argparse import validate_context as validate_parser_context

PROFILE='legacy-governance-documents-v1'


def request_valid(value):
    keys={'schema_version','profile','source_label','cwd_label','argv','export_mode','tool_path','source_date_epoch','tool_timeout','parser_context'}
    if (type(value) is not dict or set(value)!=keys or type(value['schema_version']) is not int or value['schema_version']!=1 or value['profile']!=PROFILE
            or value['export_mode'] not in ('private-candidate','selected-files')
            or type(value['argv']) is not list or len(value['argv'])>64
            or any(type(arg) is not str or len(arg)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in arg) for arg in value['argv'])
            or sum(map(len,value['argv']))>32768 or type(value['tool_timeout']) not in (int,float)
            or not math.isfinite(value['tool_timeout']) or not 0<value['tool_timeout']<=600):raise ValueError('document_rendering_request_changed')
    validate_parser_context(value['parser_context'])
    for key in ('source_label','cwd_label'):path_spec({'path':value[key],'label':value[key]})
    for key,limit in (('tool_path',32768),('source_date_epoch',8192)):
        if value[key] is not None and (type(value[key]) is not str or len(value[key])>limit or '\0' in value[key]):raise ValueError('document_rendering_environment_context_changed')
    return value


def result_value(kernel,output):
    return {'exit_code':kernel['exit_code'],'kernel_result':kernel,'successful_outputs':output.files,
        'successful_writes':output.writes,'observed_tool_outputs':output.tool_files}


def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and source.get('node_context')!=node:raise ValueError('document_rendering_foreign_node')
    current['source_root']=source.get('source_root')
    if encode(source)!=encode(current):raise ValueError('document_rendering_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version']!=1
            or any(type(retained.get(k)) is not type(v) or retained.get(k)!=v for k,v in AUTHORITY.items())
            or type(retained['touched_files']) is not dict or len(events)<3
            or encode(events[0])!=encode({'kind':'opened',**AUTHORITY})
            or encode(events[1])!=encode({'kind':'execution-intent','request':request})):
        raise ValueError('document_rendering_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:raise ValueError('document_rendering_terminal_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
    io=ReplayIO(events,blob,request['export_mode'],request['source_label'],request)
    kernel=execute(request['source_label'],request['argv'],io,io,io,parser_context=request['parser_context']);io.finish()
    if (encode(result_value(kernel,io))!=encode(retained['result']) or encode(io.touched)!=encode(retained['touched_files'])
            or encode(events[-1])!=encode({'kind':'terminal','state':'complete','exit_code':kernel['exit_code']}) or not closed()):
        raise ValueError('document_rendering_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],'original_exit_signal':kernel['original_exit_signal'],
        'kernel_exception':kernel['kernel_exception'],'successful_outputs':io.files,'successful_writes':io.writes,
        'observed_tool_outputs':io.tool_files,'source_output_paths_observed':sorted(io.touched),
        'source_export_requested':request['export_mode']=='selected-files','retained_declared_replay_consistent':True,
        'native_source_tool_or_exports_repeated':False,**AUTHORITY}


def generate(options,instance,settings):
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
    source_label=str(Path(options['source_worktree']).expanduser().absolute())
    cwd=str(Path(options.get('working_directory') or Path.cwd()).expanduser().absolute())
    argv=list(options['legacy_arguments'])
    if argv[:1]==['--']:argv=argv[1:]
    request=request_valid({'schema_version':1,'profile':PROFILE,'source_label':source_label,'cwd_label':cwd,
        'argv':argv,'export_mode':'selected-files' if options.get('write_selected_reports') else 'private-candidate',
        'tool_path':options.get('tool_path') if options.get('tool_path') is not None else os.environ.get('PATH'),
        'source_date_epoch':options.get('source_date_epoch') if options.get('source_date_epoch') is not None else os.environ.get('SOURCE_DATE_EPOCH'),
        'tool_timeout':options.get('tool_timeout') if options.get('tool_timeout') is not None else 120,'parser_context':capture_parser_context()})
    source=current_source(node);instance=Path(instance);state=owned_directory(instance/'state/document-rendering/records',True)
    record=Record(state,request,source);record.append({'kind':'execution-intent','request':request})
    output=result=error=None
    try:
        output=Output(record,request['export_mode'],source_label,instance,ROOT);data=Data(record,output,instance)
        environment=dict(os.environ)
        for key,value in (('PATH',request['tool_path']),('SOURCE_DATE_EPOCH',request['source_date_epoch'])):
            if value is None:environment.pop(key,None)
            else:environment[key]=value
        tools=Tools(record,output,instance/'state/document-rendering/scratch',cwd=cwd,environment=environment,timeout=request['tool_timeout'])
        kernel=execute(source_label,argv,data,output,tools,parser_context=request['parser_context']);result=result_value(kernel,output)
        if current_source(node)!=source:raise InputAdmissionError('document_rendering_product_changed')
    except Exception as caught:error=caught
    state='incomplete' if error is not None or record.capture_incomplete else 'complete'
    record.finish(state,result,{} if output is None else output.touched,error)
    if state=='complete':inspect(record.root,node=node)
    return {'state':state,'record_root':str(record.root),'exit_code':2 if state=='incomplete' else result['exit_code'],
        'original_exit_code':None if state=='incomplete' else result['exit_code'],'export_mode':request['export_mode'],
        'source_export_requested':request['export_mode']=='selected-files',
        'source_output_paths_observed':sorted({} if output is None else output.touched),**AUTHORITY},result


def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 document-rendering',allow_abbrev=False)
    sub=parser.add_subparsers(dest='command',required=True)
    item=sub.add_parser('generate',allow_abbrev=False)
    item.add_argument('--profile',choices=(PROFILE,),required=True);item.add_argument('--source-worktree',required=True)
    item.add_argument('--working-directory');item.add_argument('--write-selected-reports',action='store_true')
    item.add_argument('--tool-path');item.add_argument('--source-date-epoch');item.add_argument('--tool-timeout',type=float,default=120)
    item.add_argument('--format',choices=('receipt','legacy'),default='receipt')
    item.add_argument('legacy_arguments',nargs=argparse.REMAINDER,help='Use -- then original --document-id filters or --help.')
    for name in ('inspect','replay'):sub.add_parser(name,allow_abbrev=False).add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':value=inspect(options.record)
    else:
        if instance is None or settings is None:raise ValueError('document_rendering_instance_required')
        if options.command=='inspect':value=inspect(options.record,node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')})
        else:
            receipt,result=generate(vars(options),instance,settings)
            if options.format=='legacy' and receipt['state']=='complete':
                kernel=result['kernel_result'];sys.stdout.write(kernel['stdout']);sys.stderr.write(kernel['stderr'])
                if kernel['kernel_exception'] is not None:print(json.dumps({'execution':'captured_exception',**kernel['kernel_exception']}),file=sys.stderr)
            else:print(json.dumps(receipt,indent=2))
            return receipt['exit_code']
    print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
