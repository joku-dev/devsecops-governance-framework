"""Whole requirement checks with private retained source/history observations."""
import argparse
import json
from pathlib import Path, PurePosixPath
import sys
from lib.requirement_validation_context import validate
from lib.requirement_validation_replay import Replay
from lib.requirement_validation_ports import (Source, History, history_commands, Record, read_record,
    owned_directory, encode, AUTHORITY, current_source)

PROFILE = 'legacy-requirement-validation-v1'


def request_valid(request):
    if (type(request) is not dict or set(request) != {'schema_version','profile','source_label','base_ref','resources'}
            or request['schema_version'] != 1 or type(request['schema_version']) is not int
            or request['profile'] != PROFILE or type(request['source_label']) is not str):
        raise ValueError('requirement_validation_request_changed')
    label = request['source_label']; path = PurePosixPath(label)
    if (not path.is_absolute() or str(path) != label or '..' in path.parts or len(label) > 8192
            or any(ord(c) < 32 for c in label)):
        raise ValueError('requirement_validation_source_label_invalid')
    base = request['base_ref']
    if base is not None and (type(base) is not str or not base or base.startswith('-') or len(base)>2048
            or any(ord(c)<33 or ord(c)>126 for c in base)):
        raise ValueError('requirement_validation_base_selector_invalid')
    resources=request['resources']
    if not isinstance(resources,list) or len(resources)>128:
        raise ValueError('requirement_schema_resource_budget')
    seen=set()
    for row in resources:
        if type(row) is not dict or set(row)!={'uri','label'}:
            raise ValueError('requirement_schema_resource_invalid')
        uri,label=row['uri'],row['label']
        if (type(uri) is not str or not uri or len(uri)>8192 or any(ord(c)<33 for c in uri)
                or uri in seen or type(label) is not str):
            raise ValueError('requirement_schema_resource_invalid')
        path=PurePosixPath(label)
        if (not path.is_absolute() or str(path)!=label or '..' in path.parts or len(label)>8192
                or any(ord(c)<32 for c in label)):
            raise ValueError('requirement_schema_resource_path_invalid')
        seen.add(uri)
    return request


def inspect(root, *, node=None):
    request, source, retained, events, blob, closed = read_record(root)
    request_valid(request)
    current = current_source(source.get('node_context'),source.get('product_tree'))
    if node is not None and source.get('node_context') != node:
        raise ValueError('requirement_validation_foreign_node')
    current['source_root'] = source.get('source_root')
    if current != source:
        raise ValueError('requirement_validation_product_generation_changed')
    if (set(retained) != {'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version'] != 1
            or any(retained.get(k) != v for k,v in AUTHORITY.items()) or retained['touched_files'] != {}
            or not events or events[0] != {'kind':'opened',**AUTHORITY}
            or len(events)<3 or events[1] != {'kind':'execution-intent','request':request}):
        raise ValueError('requirement_validation_authority_or_intent_changed')
    if retained['state'] != 'complete' or retained['exception_type'] is not None:
        return {'state':'incomplete','retained_declared_replay_consistent':False,**AUTHORITY}
    histories = {}; position = 2
    while position<len(events)-2:
        intent, returned = events[position:position+2]
        if (set(intent) != {'kind','operation','action','arguments'} or intent['kind']!='intent'
                or intent['operation'] != position or intent['action']!='requirement_history'
                or type(intent['arguments']) is not dict or set(intent['arguments']) != {'action','base','path'}
                or intent['arguments']['base'] != request['base_ref']
                or returned.get('kind')!='returned' or returned.get('operation')!=position
                or set(returned) != {'kind','operation','encoding','value'} or returned['encoding']!='json'):
            raise ValueError('requirement_validation_history_event_changed')
        query = intent['arguments']; expected = history_commands(query['action'],query['base'],query['path'])
        rows = json.loads(blob(returned['value']))
        if not isinstance(rows,list) or not 1<=len(rows)<=len(expected):
            raise ValueError('requirement_validation_history_rows_changed')
        for index,row in enumerate(rows):
            if (type(row) is not dict or set(row) != {'arguments','completed_successfully','stdout'}
                    or row['arguments'] != list(expected[index]) or type(row['completed_successfully']) is not bool
                    or row['completed_successfully'] != (row['stdout'] is not None)
                    or index<len(rows)-1 and row['completed_successfully']):
                raise ValueError('requirement_validation_history_outcome_changed')
            if row['stdout'] is not None: blob(row['stdout'])
        if not rows[-1]['completed_successfully'] and len(rows)!=len(expected):
            raise ValueError('requirement_validation_history_fallback_missing')
        histories[position] = {'request':query,'rows':rows}; position+=2
    if (position!=len(events)-2 or set(events[position])!={'kind','trace'}
            or events[position]['kind']!='source-trace'):
        raise ValueError('requirement_validation_trace_event_changed')
    trace = json.loads(blob(events[position]['trace']))
    replay = Replay(trace,histories,blob,request['resources'])
    actual = validate(request['source_label'],replay,replay,base_ref=request['base_ref'],resource=replay.resource)
    replay.finish()
    if (events[-1] != {'kind':'terminal','state':'complete','exit_code':actual['exit_code']}
            or encode(actual)!=encode(retained['result']) or not closed()):
        raise ValueError('requirement_validation_complete_result_changed')
    return {'state':'complete','original_exit_code':actual['exit_code'],
            'kernel_exception':None if actual['kernel_exception'] is None else actual['kernel_exception']['type'],
            'retained_declared_replay_consistent':True,'native_source_or_history_repeated':False,**AUTHORITY}


def check(options, instance, settings):
    node = {k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')}
    request = request_valid({'schema_version':1,'profile':PROFILE,
        'source_label':str(Path(options['source_worktree']).expanduser().absolute()),'base_ref':options.get('base_ref'),
        'resources':[{'uri':uri,'label':str(Path(path).expanduser().absolute())} for uri,path in options.get('schema_resource',[]) or []]})
    source = current_source(node)
    root = Path(instance)/'state/requirement-validation/records'
    selected_source = Path(request['source_label'])
    if root.is_relative_to(selected_source) or selected_source.is_relative_to(root):
        raise ValueError('requirement_validation_state_overlaps_observed_source')
    if any(Path(row['label']).is_relative_to(root) for row in request['resources']):
        raise ValueError('requirement_schema_resource_overlaps_state')
    root = owned_directory(root,True)
    record = Record(root,request,source)
    record.append({'kind':'execution-intent','request':request})
    trace = []; result = error = None
    try:
        native = Source(request['source_label'],trace,record,request['resources'])
        history = History(request['source_label'],trace,record)
        result = validate(request['source_label'],native,history,base_ref=request['base_ref'],resource=native.resource)
        if current_source(node)!=source: raise ValueError('requirement_validation_product_changed')
        record.append({'kind':'source-trace','trace':record.blob(encode(trace))})
    except Exception as failure:
        error=failure
    state='incomplete' if error is not None or record.capture_incomplete else 'complete'
    record.finish(state,result,{},error)
    if state=='complete': inspect(record.root,node=node)
    return {'state':state,'record_root':str(record.root),'exit_code':2 if state=='incomplete' else result['exit_code'],
            'original_exit_code':result['exit_code'] if state=='complete' and result is not None else None,**AUTHORITY},result


def run(arguments,instance=None,settings=None):
    parser=argparse.ArgumentParser(prog='axiom-v2 requirement-validation',allow_abbrev=False)
    sub=parser.add_subparsers(dest='command',required=True)
    command=sub.add_parser('check',allow_abbrev=False)
    command.add_argument('--profile',choices=(PROFILE,),required=True)
    command.add_argument('--source-worktree',required=True)
    command.add_argument('--base-ref')
    command.add_argument('--schema-resource',nargs=2,action='append',default=[],metavar=('URI','FILE'),
        help='Explicit local bytes for a referenced schema URI; read only if requested, no implicit retrieval.')
    command.add_argument('--format',choices=('receipt','legacy'),default='receipt')
    for name in ('inspect','replay'):
        item=sub.add_parser(name,allow_abbrev=False);item.add_argument('--record',required=True)
    options=parser.parse_args(arguments)
    if options.command=='replay':
        value=inspect(options.record);print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
    if instance is None or settings is None:raise ValueError('requirement_validation_instance_required')
    node={k:settings[k] for k in ('node_id','source_revision','runtime_source_digest')}
    if options.command=='inspect':
        value=inspect(options.record,node=node);print(json.dumps(value,indent=2));return 0 if value['state']=='complete' else 2
    receipt,result=check(vars(options),instance,settings)
    if options.format=='legacy' and result is not None:
        sys.stdout.write(result['stdout']);sys.stderr.write(result['stderr'])
        if result['kernel_exception'] is not None:
            print(json.dumps({'execution':'captured_exception','diagnostics':[result['kernel_exception']['type']]}),file=sys.stderr)
    else:print(json.dumps(receipt,indent=2))
    return receipt['exit_code']
