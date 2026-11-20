"""Whole original requirement report execution with explicit retained outputs."""
import argparse
import json
from pathlib import Path,PurePosixPath
import sys

from lib.requirement_review_context import execute
from lib.requirement_review_output import OUTPUTS,MODES,EMPTY_MIN_ERRORS,ReplayOutput
from lib.requirement_validation_replay import Replay,IntegrityError
from lib.requirement_review_ports import (Source,Output,Record,read_record,owned_directory,encode,
    AUTHORITY,current_source,LEGACY_MIGRATION_INVENTORY,empty_min_error)

PROFILE='legacy-requirement-review-v1'


def request_valid(value):
    if (type(value) is not dict or set(value)!={'schema_version','profile','kind','source_label','export_mode','empty_min_error'}
            or type(value['schema_version']) is not int or value['schema_version']!=1
            or value['profile']!=PROFILE or type(value['kind']) is not str or value['kind'] not in OUTPUTS
            or type(value['export_mode']) is not str or value['export_mode'] not in MODES
            or value['empty_min_error'] not in EMPTY_MIN_ERRORS or type(value['source_label']) is not str):
        raise ValueError('requirement_review_request_changed')
    label=value['source_label'];path=PurePosixPath(label)
    if (not path.is_absolute() or str(path)!=label or '..' in path.parts or len(label)>8192
            or any(ord(c)<32 for c in label)):
        raise ValueError('requirement_review_source_label_invalid')
    return value


def inspect(root,*,node=None):
    request,source,retained,events,blob,closed=read_record(root)
    request_valid(request)
    current=current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and source.get('node_context')!=node:
        raise ValueError('requirement_review_foreign_node')
    current['source_root']=source.get('source_root')
    if current!=source:raise ValueError('requirement_review_product_generation_changed')
    if (set(retained)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version']!=1
            or any(retained.get(k)!=v for k,v in AUTHORITY.items()) or type(retained['touched_files']) is not dict
            or len(events)<3 or events[0]!={'kind':'opened',**AUTHORITY}
            or events[1]!={'kind':'execution-intent','request':request}):
        raise ValueError('requirement_review_authority_or_intent_changed')
    if retained['state'] not in ('complete','incomplete') or retained['state']=='complete' and retained['exception_type'] is not None:
        raise ValueError('requirement_review_terminal_state_changed')
    if retained['state']=='incomplete':
        return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
    if set(events[-2])!={'kind','trace'} or events[-2]['kind']!='source-trace':
        raise ValueError('requirement_review_source_trace_missing')
    source_replay=Replay(json.loads(blob(events[-2]['trace'])),{},blob)
    output_replay=ReplayOutput(events,blob,request['kind'],request['export_mode'])
    kernel=execute(request['kind'],request['source_label'],source_replay,output_replay,
        inventory_roots=LEGACY_MIGRATION_INVENTORY if request['kind']=='implemented-migration' else None,
        empty_min_error=request['empty_min_error'])
    source_replay.finish();output_replay.finish()
    expected={'exit_code':kernel['exit_code'],'kernel_result':kernel,'output_files':output_replay.files}
    if (encode(expected)!=encode(retained['result']) or output_replay.touched!=retained['touched_files']
            or events[-1]!={'kind':'terminal','state':'complete','exit_code':kernel['exit_code']} or not closed()):
        raise ValueError('requirement_review_whole_result_changed')
    return {'state':'complete','original_exit_code':kernel['exit_code'],
            'kernel_exception':None if kernel['kernel_exception'] is None else kernel['kernel_exception']['type'],
            'output_files':output_replay.files,'source_export_requested':request['export_mode']=='source-worktree',
            'source_paths_touched':sorted(output_replay.touched),
            'retained_declared_replay_consistent':True,'native_source_or_exports_repeated':False,**AUTHORITY}


def generate(options,instance,settings):
    node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')}
    request=request_valid({'schema_version':1,'profile':PROFILE,'kind':options['kind'],
        'source_label':str(Path(options['source_worktree']).expanduser().absolute()),
        'export_mode':'source-worktree' if options.get('write_source_reports') else 'private-candidate',
        'empty_min_error':empty_min_error()})
    source=current_source(node)
    state=Path(instance)/'state/requirement-review/records';observed=Path(request['source_label'])
    if state.is_relative_to(observed) or observed.is_relative_to(state):
        raise ValueError('requirement_review_source_state_overlap')
    state=owned_directory(state,True);record=Record(state,request,source)
    record.append({'kind':'execution-intent','request':request})
    trace=[];result=error=None;output=None
    try:
        native=Source(request['source_label'],trace,record)
        output=Output(record,request['source_label'],request['kind'],request['export_mode'])
        kernel=execute(request['kind'],request['source_label'],native,output,
            inventory_roots=LEGACY_MIGRATION_INVENTORY if request['kind']=='implemented-migration' else None,
            empty_min_error=request['empty_min_error'])
        result={'exit_code':kernel['exit_code'],'kernel_result':kernel,'output_files':output.files}
        if current_source(node)!=source:raise ValueError('requirement_review_product_changed')
        record.append({'kind':'source-trace','trace':record.blob(encode(trace))})
    except Exception as failure:error=failure
    completeness='incomplete' if error is not None or record.capture_incomplete else 'complete'
    record.finish(completeness,result,{} if output is None else output.touched,error)
    if completeness=='complete':inspect(record.root,node=node)
    return {'state':completeness,'record_root':str(record.root),
            'exit_code':2 if completeness=='incomplete' else result['exit_code'],
            'original_exit_code':result['exit_code'] if completeness=='complete' else None,
            'export_mode':request['export_mode'],'source_export_requested':request['export_mode']=='source-worktree',
            'source_paths_touched':sorted({} if output is None else output.touched),**AUTHORITY},result


def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 requirement-review',allow_abbrev=False)
    sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('generate',allow_abbrev=False)
    command.add_argument('--kind',choices=tuple(OUTPUTS),required=True)
    command.add_argument('--profile',choices=(PROFILE,),required=True)
    command.add_argument('--source-worktree',required=True)
    command.add_argument('--write-source-reports',action='store_true',help='Explicitly write the two original fixed report paths in the selected owned source worktree.')
    command.add_argument('--format',choices=('receipt','legacy'),default='receipt')
    for name in ('inspect','replay'):
        item=sub.add_parser(name,allow_abbrev=False);item.add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':
        value=inspect(options.record);print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
    if instance is None or settings is None:raise ValueError('requirement_review_instance_required')
    node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')}
    if options.command=='inspect':
        value=inspect(options.record,node=node);print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
    receipt,result=generate(vars(options),instance,settings)
    if options.format=='legacy' and receipt['state']=='complete':
        value=result['kernel_result'];sys.stdout.write(value['stdout']);sys.stderr.write(value['stderr'])
        if value['kernel_exception'] is not None:
            print(json.dumps({'execution':'captured_exception','diagnostics':[value['kernel_exception']['type']]}),file=sys.stderr)
    else:print(json.dumps(receipt,indent=2))
    return receipt['exit_code']
