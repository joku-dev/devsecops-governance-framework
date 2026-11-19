"""Retained complete-operation inspection with actual suboperation/byte bindings.

This is consistency of declared local execution evidence, not independent
execution authentication, Trust, governance acceptance or operating authority.
"""
from pathlib import Path
import hashlib
import json

import control_evaluation as controls

from lib import compliance_operation as contract
from lib.local_source_application import LocalSourceInspectionContext
from lib.repository_application import RepositoryContext
from lib.providers import compliance_decisions
from lib.providers.compliance_execution import supervision
from lib.providers.compliance_record_checks import (pin, package_source, check_opa,
    unit_files, final_source, preflight_files)
from lib.providers.repository_journal import read_journal
from lib.result_bytes import safe_bytes, strict_json
from lib.source_inspection_application import INTEGRATION


def read(root, name, limit):
    path = Path(root)/name
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('private_compliance_record_file_required')
    return safe_bytes(path,limit=limit)


def core_run_events(decision):
    return [e for e in decision['events'] if e['port']=='run']


def check_core_trace(acquisition, decision):
    expected=[]
    for index,event in enumerate(decision['events'],1):
        expected.extend([
            {'kind':'compliance-port','index':index,'phase':'intent',
                'observation':{k:event[k] for k in ('port','arguments')}},
            {'kind':'compliance-port','index':index,'phase':'finished','observation':event}])
    actual=[r for r in acquisition if r.get('kind')=='compliance-port']
    if actual!=expected:
        raise ValueError('compliance_global_core_trace_changed')
    active=None
    for row in acquisition:
        if row.get('kind')=='compliance-port':
            if row['phase']=='intent':
                if active is not None:
                    raise ValueError('compliance_nested_logical_phase_changed')
                active=row['index']
            else:
                if active!=row['index']:
                    raise ValueError('compliance_logical_completion_order_changed')
                active=None
        elif row.get('kind') in ('compliance-suboperation','compliance-own-unit-tests',
                'compliance-opa','compliance-own-source-write','compliance-control-native-path-binding') and active is None:
            raise ValueError('compliance_native_effect_outside_logical_phase')
    if active is not None:
        raise ValueError('compliance_logical_phase_not_finished')


def check_exports(root, decision, result):
    attempts=[e for e in decision['events'] if e['port']=='write']
    if len(attempts)!=len(result['export_effects']):
        raise ValueError('compliance_retained_export_count_changed')
    prior={}
    for index,(event,row) in enumerate(zip(attempts,result['export_effects']),1):
        returned='value' in event
        if (set(row)!={'path','before','after','outcome','error_type'}
                or row['path']!=event['arguments'][0]
                or row['outcome']!=('returned' if returned else 'raised')
                or row['error_type']!=(None if returned else event['exception']['type'])):
            raise ValueError('compliance_retained_export_effect_changed')
        states={}
        for phase in ('before','after'):
            state=row[phase]
            if state.get('kind') in ('missing','directory') and set(state)=={'kind'}:
                states[phase]=state
            elif state.get('kind')=='file' and set(state)=={'kind','retained','bytes','sha256'}:
                if state['retained']!='export-effect-'+str(index)+'-'+phase+'.bin':
                    raise ValueError('compliance_retained_export_effect_changed')
                raw=read(Path(root)/'work',state['retained'],16*1024**2)
                if {k:state[k] for k in ('bytes','sha256')}!=pin(raw):
                    raise ValueError('compliance_retained_export_effect_changed')
                states[phase]={'kind':'file',**pin(raw)}
                if phase=='after' and returned and raw!=event['arguments'][1].encode():
                    raise ValueError('compliance_retained_export_effect_changed')
            else:
                raise ValueError('compliance_retained_export_effect_changed')
        if returned and states['after']['kind']!='file':
            raise ValueError('compliance_retained_export_effect_changed')
        if row['path'] in prior and prior[row['path']]!=states['before']:
            raise ValueError('compliance_retained_alias_sequence_changed')
        prior[row['path']]=states['after']
    # Live exports may have been deliberately overwritten by a later rerun.
    # Inspect their retained exact chronological effects, never those live paths.


def check_clock_stdout(header, decision, result):
    expected=contract.legacy_timestamp(header['assessed_at'])
    clocks=[e for e in decision['events'] if e['port']=='timestamp']
    if (len(clocks)>1 or any(e.get('value')!=expected for e in clocks)
            or decision['outcome']['kind']=='returned' and len(clocks)!=1):
        raise ValueError('compliance_original_clock_not_bound_to_header')
    stdout=''.join(e['arguments'][0]+'\n' for e in decision['events']
                   if e['port']=='print' and 'value' in e)
    if result['legacy_stdout']!=stdout:
        raise ValueError('compliance_legacy_stdout_not_original_print_effect')


def check_presence(root, decision, result, files):
    """Use retained owned source and chronological exports, never live exports."""
    source=Path(decision['root']);actual=Path(root)/'work/admitted/source'
    directories={p.relative_to(actual).as_posix() for p in actual.rglob('*')
                 if p.is_dir() and p.relative_to(actual).parts[0]!='.git'}
    written={};index=0
    for event in decision['events']:
        if event['port']=='write':
            row=result['export_effects'][index];index+=1
            written[row['path']]=row['after']['kind']!='missing'
        elif event['port']=='exists':
            name=event['arguments'][0];path=Path(name)
            if path.is_relative_to(source):
                relative=path.relative_to(source).as_posix()
                expected=relative in files or relative in directories
            elif name in written:
                expected=written[name]
            else:
                raise ValueError('compliance_unbound_artifact_presence_path')
            if event.get('value') is not expected:
                raise ValueError('compliance_artifact_presence_not_retained_state')


def load(root, header, settings):
    root=Path(root);contract.binding(header)
    packet=contract.request(strict_json(read(root,'request.json',64*1024)))
    if packet['binding']!=header:
        raise ValueError('compliance_operation_request_binding_changed')
    pending={'binding':header,'state':'pending_incomplete','execution':'incomplete',
             'modern_exit':2,'independent_execution_authenticated':False,**contract.AUTHORITY}
    if not (root/'supervision/outcome.json').exists() or not (root/'result.json').exists():
        return pending
    parent=supervision(root,packet)
    chain=read_journal(root/'acquisition',expected_header=header)
    events=[r['payload'] for r in chain]
    terminals=[i for i,r in enumerate(events) if r.get('kind')=='complete-compliance-child-finished']
    if not terminals:
        return pending
    if terminals!=[len(events)-1]:
        raise ValueError('compliance_child_terminal_order_changed')
    raw=read(root,'result.json',8*1024**2)
    if {k:events[-1][k] for k in ('bytes','sha256')}!=pin(raw):
        raise ValueError('compliance_child_result_bytes_changed')
    result=strict_json(raw)
    if (result['binding']!=header or any(type(result.get(k)) is not type(v) or result[k]!=v for k,v in contract.AUTHORITY.items())
            or result['execution'] not in ('complete','incomplete')
            or type(result['modern_exit']) is not int or result['modern_exit'] not in (0,1,2)
            or result['modern_exit']!=parent['exit_code']):
        raise ValueError('compliance_child_result_binding_or_exit_changed')
    reply=strict_json(read(root/'supervision','controller-stdout.bin',65536))
    if (reply['operation_id']!=header['operation_id'] or reply['result_sha256']!=pin(raw)['sha256']
            or any(type(reply.get(k)) is not type(v) or reply[k]!=v for k,v in contract.AUTHORITY.items())
            or any(reply[k]!=result[k] for k in ('execution','original_finding_exit','modern_exit'))):
        raise ValueError('compliance_parent_child_reply_changed')
    if result['decision_recorded'] is not True:
        if result['execution']!='incomplete' or result['modern_exit']!=2:
            raise ValueError('compliance_unrecorded_decision_cannot_be_complete')
        return {**pending,'state':'recorded_incomplete','error_type':result['error_type']}
    retained=compliance_decisions.load(root/'decisions',contract.decision_binding(header))
    decision=retained['decision'];selected=packet['options']
    if (decision['root']!=str(root/'work/admitted/source') or decision['cwd']!=selected['cwd']
            or decision['options']!={k:selected[k] for k in ('output_file','target_repo','input_file','skip_unit_tests')}
            or result['execution_source_root']!=decision['root']):
        raise ValueError('compliance_decision_options_or_source_changed')
    check_core_trace(events,decision)
    check_clock_stdout(header,decision,result)
    if (result['full_default_unit_scope'] is not (not selected['skip_unit_tests'])
            or decision['outcome']['kind']=='raised'
            and result['error_type']!=decision['outcome']['exception']['type']):
        raise ValueError('compliance_original_error_or_default_scope_changed')
    subevents=[r['observation'] for r in events if r.get('kind')=='compliance-suboperation']
    if result['suboperations']!=subevents or [r['kind'] for r in subevents] not in ([],['integration'],['integration','repository']):
        raise ValueError('compliance_actual_suboperation_order_changed')
    if result['execution']=='complete' and [r['kind'] for r in subevents]!=['integration','repository']:
        raise ValueError('compliance_complete_native_suboperations_required')
    commands=core_run_events(decision)
    manifest,files,modes=package_source(root,header)
    if subevents:
        context=LocalSourceInspectionContext(header['instance_root'],settings)
        identifier=subevents[0]['assessment_id'];observation=context.inspect(identifier)
        if (observation['inspection_kind']!='integration' or observation['assessed_at']!=header['assessed_at']
                or observation['source_repository_path']!=decision['events'][0]['value']):
            raise ValueError('compliance_integration_subject_changed')
        integration=safe_bytes(context.artifacts/identifier/Path(INTEGRATION).name,limit=8*1024**2).decode()
        expected={'returncode':context.legacy_exit(identifier),'stdout':integration,'stderr':''}
        if commands[0].get('value')!=expected:
            raise ValueError('compliance_integration_observation_not_actual_record')
    if len(subevents)==2:
        context=RepositoryContext(header['instance_root'],settings)
        identifier=subevents[1]['assessment_id'];value=context.load(identifier)
        if value['binding']['source_root']!=decision['root'] or value['binding']['assessed_at']!=header['assessed_at']:
            raise ValueError('compliance_repository_subject_changed')
        replay=context.inspect(identifier)
        if value['outcome']['execution']=='complete' and replay['state']!='retained_declared_replay_consistent':
            raise ValueError('compliance_repository_full_replay_changed')
        if value['inputs']!=files:
            raise ValueError('compliance_repository_initial_package_differs')
        expected={'returncode':value['outcome']['exit_code'],**{k:value['outcome'][k] for k in ('stdout','stderr')}}
        if commands[1].get('value')!=expected:
            raise ValueError('compliance_repository_observation_not_actual_record')
        for name in set(value['outputs'])-set(files):modes[name]='100644'
        files=value['outputs']
    if result['execution']!='complete':
        check_exports(root,decision,result)
        return {**pending,'state':'retained_declared_incomplete_decision_consistent',
            'decision_replay_verified':True,'original_finding_exit':result['original_finding_exit'],
            'legacy_stdout':result['legacy_stdout'],'error_type':result['error_type'],
            'retained_partial_export_bytes_verified':True,
            'other_partial_native_acquisition_fully_verified':False}
    preflight_files(root,result,events)
    unit_events=[r for r in events if r.get('kind')=='compliance-own-unit-tests']
    expected_phases=[] if selected['skip_unit_tests'] else ['intent','finished']
    if [r['phase'] for r in unit_events]!=expected_phases or selected['skip_unit_tests']!=(result['unit_outcome'] is None):
        raise ValueError('compliance_explicit_whole_unit_scope_changed')
    if unit_events and (unit_events[-1]['native_outcome']!=result['unit_outcome']
            or unit_events[-1]['statistics']!=result['unit_statistics']
            or unit_events[-1]['final_source_files']!=result['final_source_files']):
        raise ValueError('compliance_whole_unit_global_outcome_changed')
    files,modes,unit=unit_files(root,result,files,modes)
    if unit is not None:
        expected={'returncode':result['unit_outcome']['returncode'],**{k:v.decode() for k,v in unit.items()}}
        if commands[2].get('value')!=expected:
            raise ValueError('compliance_whole_unit_observation_not_actual_record')
    opa=check_opa(root,header,selected,result,manifest,files)
    opa_events=[r['observation'] for r in events if r.get('kind')=='compliance-opa' and r.get('phase')=='finished']
    if opa_events!=result['opa_observations']:
        raise ValueError('compliance_opa_global_trace_changed')
    outer=commands[2 if selected['skip_unit_tests'] else 3:]
    if len(outer)!=11 or [r.get('value') for r in outer]!=opa[1:12]:
        raise ValueError('compliance_outer_policy_observations_not_actual_records')
    # Rebuild all46 control decisions from frozen input/current own models and
    # the retained ten inner actual OPA results, without a native OPA rerun.
    snapshot=Path(root)/'work/control-input.json';position=0
    from types import SimpleNamespace
    def control_native(command):
        nonlocal position
        queries=list(controls.POLICY_QUERIES.values())
        expected=['opa','eval','-f','json','-d',str(controls.ROOT/'policies/opa'),'-i',str(snapshot),queries[position]]
        if command!=expected:
            raise ValueError('compliance_inner_control_query_order_changed')
        value=opa[12+position];position+=1
        return SimpleNamespace(**value)
    control=controls.generate_control_evaluation_report(snapshot,native_run=control_native)
    label=Path(result['input_label']);source=Path(result['execution_source_root'])
    control['input_file']=str(label.relative_to(source)) if label.is_relative_to(source) else str(label)
    observed=[e['value'] for e in decision['events'] if e['port']=='control_report']
    markdown=[e['value'] for e in decision['events'] if e['port']=='control_markdown']
    if (position!=10 or observed!=[control]
            or json.dumps(observed[0],indent=2)!=json.dumps(control,indent=2)
            or markdown!=[controls.render_control_evaluation_markdown(control)]):
        raise ValueError('compliance_complete_controls_not_actual_input_and_opa')
    from lib.providers.compliance_worker import native_status
    status=native_status(decision['outcome'],SimpleNamespace(suboperations=subevents,
        unit_outcome=result['unit_outcome'],opa=SimpleNamespace(observations=result['opa_observations'])),selected)
    if any(result[k]!=status[k] for k in status):
        raise ValueError('compliance_native_acquisition_status_changed')
    final_source(root,result,files,modes);check_exports(root,decision,result)
    check_presence(root,decision,result,files)
    return {'binding':header,'state':'retained_declared_complete_compliance_consistent',
        **status,'decision_replay_verified':True,'native_suboperation_records_reverified':True,
        'whole_source_and_retained_export_effects_equal':True,
        'independent_execution_authenticated':False,'legacy_stdout':result['legacy_stdout'],
        'unit_tests':'not_run' if selected['skip_unit_tests'] else 'pass' if result['unit_outcome']['returncode']==0 else 'fail',
        'unit_statistics':result['unit_statistics'],'file_count':len(files),**contract.AUTHORITY}
