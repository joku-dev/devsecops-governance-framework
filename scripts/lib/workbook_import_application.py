"""Complete original workbook import, private or explicit selected file effects."""
import argparse
import json
from pathlib import Path,PurePosixPath
import sys

from lib.workbook_import_context import execute
from lib.workbook_import_io import ReplayIO,MODES,path_spec
from lib.requirement_validation_budget import InputAdmissionError
from lib.workbook_import_ports import (Data,Output,Selection,Capture,Record,read_record,
    owned_directory,encode,AUTHORITY,current_source,ROOT,capture_parser_context)

from lib.retained_argparse import validate_context as validate_parser_context

PROFILE='legacy-harmonized-workbook-v1'


def request_valid(value):
    if (type(value) is not dict or set(value)!={'schema_version','profile','source_label','cwd_label','argv','export_mode','parser_context'}
            or type(value['schema_version']) is not int or value['schema_version']!=1 or value['profile']!=PROFILE
            or type(value['export_mode']) is not str or value['export_mode'] not in MODES
            or type(value['argv']) is not list or len(value['argv'])>64
            or any(type(arg) is not str or len(arg)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in arg) for arg in value['argv'])
            or sum(len(arg) for arg in value['argv'])>32768):raise ValueError('workbook_import_request_changed')
    validate_parser_context(value['parser_context'])
    for key in ('source_label','cwd_label'):
        path_spec({'path':value[key],'label':value[key]})
    return value


def result_value(kernel,output):
    return {'exit_code':kernel['exit_code'],'kernel_result':kernel,
            'successful_outputs':output.files,'successful_writes':output.writes}


def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root);request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and source.get('node_context')!=node:raise ValueError('workbook_import_foreign_node')
    current['source_root']=source.get('source_root')
    if source!=current:raise ValueError('workbook_import_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version']!=1
            or any(retained.get(k)!=v for k,v in AUTHORITY.items()) or type(retained['touched_files']) is not dict
            or len(events)<3 or events[0]!={'kind':'opened',**AUTHORITY} or events[1]!={'kind':'execution-intent','request':request}):
        raise ValueError('workbook_import_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:
        raise ValueError('workbook_import_terminal_state_changed')
    if retained['state']=='incomplete':return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
    io=ReplayIO(events,blob,request['export_mode'],request['cwd_label'])
    kernel=execute(request['source_label'],request['cwd_label'],request['argv'],io,io,selection=io.select,parser_context=request['parser_context'])
    io.finish()
    if (encode(result_value(kernel,io))!=encode(retained['result']) or io.touched!=retained['touched_files']
            or events[-1]!={'kind':'terminal','state':'complete','exit_code':kernel['exit_code']} or not closed()):
        raise ValueError('workbook_import_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],'original_exit_signal':kernel['original_exit_signal'],
            'kernel_exception':None if kernel['kernel_exception'] is None else kernel['kernel_exception']['type'],
            'kernel_exception_message':None if kernel['kernel_exception'] is None else kernel['kernel_exception']['message'],
            'successful_outputs':io.files,'successful_writes':io.writes,'source_paths_touched':sorted(io.touched),
            'source_export_requested':request['export_mode']=='selected-files','retained_declared_replay_consistent':True,
            'native_source_or_exports_repeated':False,**AUTHORITY}


def generate(options,instance,settings):
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
    root=str(Path(options['source_worktree']).expanduser().absolute())
    cwd=str(Path(options.get('working_directory') or root).expanduser().absolute())
    argv=list(options['legacy_arguments'])
    if argv[:1]==['--']:argv=argv[1:]
    request=request_valid({'schema_version':1,'profile':PROFILE,'source_label':root,'cwd_label':cwd,'argv':argv,
        'export_mode':'selected-files' if options.get('write_selected_reports') else 'private-candidate','parser_context':capture_parser_context()})
    source=current_source(node);instance=Path(instance);state=owned_directory(instance/'state/workbook-import/records',True)
    record=Record(state,request,source);capture=Capture(record);capture.append({'kind':'execution-intent','request':request})
    output=None;result=error=None
    try:
        data=Data(record);output=Output(record,request['export_mode']);selection=Selection(record,cwd,data,output,instance,ROOT)
        kernel=execute(root,cwd,argv,data,output,selection=selection,parser_context=request['parser_context'])
        result=result_value(kernel,output)
        if current_source(node)!=source:raise InputAdmissionError('workbook_import_product_changed')
    except Exception as failure:error=failure
    completeness='incomplete' if error is not None or record.capture_incomplete else 'complete'
    record.finish(completeness,result,{} if output is None else output.touched,error)
    if completeness=='complete':inspect(record.root,node=node)
    return {'state':completeness,'record_root':str(record.root),'exit_code':2 if completeness=='incomplete' else result['exit_code'],
            'original_exit_code':result['exit_code'] if completeness=='complete' else None,
            'export_mode':request['export_mode'],'source_export_requested':request['export_mode']=='selected-files',
            'source_paths_touched':sorted({} if output is None else output.touched),**AUTHORITY},result


def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 workbook-import',allow_abbrev=False)
    sub=parser.add_subparsers(dest='command',required=True)
    generate_parser=sub.add_parser('generate',allow_abbrev=False)
    generate_parser.add_argument('--profile',choices=(PROFILE,),required=True)
    generate_parser.add_argument('--source-worktree',required=True)
    generate_parser.add_argument('--working-directory')
    generate_parser.add_argument('--write-selected-reports',action='store_true')
    generate_parser.add_argument('--format',choices=('receipt','legacy'),default='receipt')
    generate_parser.add_argument('legacy_arguments',nargs=argparse.REMAINDER,help='Use -- then the complete original arguments, including --input-xlsx and optional original model/output paths.')
    for name in ('inspect','replay'):
        item=sub.add_parser(name,allow_abbrev=False);item.add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':
        value=inspect(options.record);print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
    if instance is None or settings is None:raise ValueError('workbook_import_instance_required')
    node={key:settings[key] for key in ('node_id','source_revision','runtime_source_digest')}
    if options.command=='inspect':
        value=inspect(options.record,node=node);print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
    receipt,result=generate(vars(options),instance,settings)
    if options.format=='legacy' and receipt['state']=='complete':
        kernel=result['kernel_result'];sys.stdout.write(kernel['stdout']);sys.stderr.write(kernel['stderr'])
        if kernel['kernel_exception'] is not None:
            print(json.dumps({'execution':'captured_exception','diagnostics':[kernel['kernel_exception']['type']],
                'message':kernel['kernel_exception']['message']}),file=sys.stderr)
    else:print(json.dumps(receipt,indent=2))
    return receipt['exit_code']
