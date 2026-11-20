"""Source-bound complete synthetic ledger capture, inspection and inert replay."""
import argparse, json, posixpath, sys
from pathlib import Path

from lib.synthetic_ledger_execution import execute
from lib.synthetic_ledger_context import PROGRAMS
from lib.synthetic_ledger_io import ReplayIO
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.synthetic_lifecycle_application import closed_validator, request_valid as report_request
from lib.synthetic_lifecycle_io import path_spec
from lib.synthetic_lifecycle_projection import PRIVATE_MASK
from lib.retained_argparse import validate_context as validate_parser_context
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_ledger_ports import (NativeIO, NativeLedgerEffects, Record, read_record, encode,
    AUTHORITY, owned_directory, current_source, ROOT, capture_parser_context)

PROFILE = 'legacy-synthetic-ledger-v1'


def request_valid(value):
    keys = {'schema_version', 'profile', 'program', 'source_label', 'cwd_label', 'argv', 'export_mode', 'resources','parser_context'}
    if (type(value) is not dict or set(value) != keys or value['profile'] != PROFILE
            or type(value['program']) is not str or value['program'] not in PROGRAMS):
        raise ValueError('synthetic_ledger_request_changed')
    # Reuse the exact finite text/path/resource admission contract. The
    # reporting discriminator here is only a validator bridge, never execution.
    from lib.synthetic_lifecycle_application import PROFILE as REPORT_PROFILE
    validate_parser_context(value['parser_context'])
    report_request({**{k: v for k, v in value.items() if k not in ('profile', 'program','parser_context')},
                    'profile': REPORT_PROFILE, 'generator': 'index'})
    return value


def factory(request, *, record=None, instance=None, events=None, blob=None):
    selected = []
    names = RepositoryLifecycle(ROOT, validator_class=None)
    name_of = lambda raw: names.kernel.transaction_name(names.adapter.strict_json(raw))
    def bind(binding):
        if record is not None:
            inputs = NativeIO(record, mode=request['export_mode'], cwd=request['cwd_label'],
                private_state=instance, product_root=ROOT, ledger=binding['path'], transaction_name=name_of)
            inputs.append({'kind': 'synthetic-ledger-root-bound', 'selection': binding})
            effects = (PrivateLedgerPort(inputs, binding['path']) if request['export_mode'] == 'private-candidate'
                       else NativeLedgerEffects(inputs, binding['path'], transaction_name=name_of))
        else:
            inputs = ReplayIO(events, blob, request['export_mode'], request['cwd_label'],
                ledger=binding['path'], transaction_name=name_of)
            if encode(inputs.row()) != encode({'kind': 'synthetic-ledger-root-bound', 'selection': binding}):
                raise ValueError('synthetic_ledger_root_binding_changed')
            effects = (PrivateLedgerPort(inputs, binding['path']) if request['export_mode'] == 'private-candidate'
                       else ReplayLedgerEffects(inputs, binding['path'], transaction_name=name_of))
        selected.append((inputs, effects))
        return inputs, effects
    return bind, selected


def result_value(execution, request):
    io, effects = execution['io'], execution['effects']
    native = request['export_mode'] == 'selected-files'
    state = {} if effects is None or not native else effects.state.observed
    resources = ({} if effects is None else effects.state.descriptors if native else effects.descriptors)
    return {'exit_code': execution['kernel_result']['exit_code'], 'kernel_result': execution['kernel_result'],
            'ledger_binding': execution['binding'], 'successful_outputs': io.files, 'successful_writes': io.writes,
            'private_projected_changes': io.projected_changes, 'native_ledger_observations': state,
            'kernel_end_descriptors': [{'descriptor': key, **value} for key, value in sorted(resources.items())]}


def inspect(root, *, node=None):
    request, source, retained, events, blob, closed = read_record(root); request_valid(request)
    current = current_source(source.get('node_context'), source.get('product_tree'))
    if node is not None and encode(source.get('node_context')) != encode(node):
        raise ValueError('synthetic_ledger_foreign_node')
    path_spec(source.get('source_root'), source.get('source_root'), request['cwd_label'])
    current['source_root'] = source['source_root']
    if encode(current) != encode(source): raise ValueError('synthetic_ledger_product_generation_changed')
    if (set(retained) != {'schema_version', 'state', 'result', 'touched_files', 'exception_type', 'event_count', 'event_tip', *AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version'] != 1
            or any(type(retained.get(k)) is not type(v) or retained[k] != v for k, v in AUTHORITY.items())
            or type(retained['touched_files']) is not dict or len(events) < 3
            or encode(events[0]) != encode({'kind': 'opened', **AUTHORITY})
            or encode(events[1]) != encode({'kind': 'execution-intent', 'request': request})):
        raise ValueError('synthetic_ledger_authority_or_intent_changed')
    if retained['state'] not in ('complete', 'incomplete') or retained['state'] == 'complete' and retained['exception_type'] is not None:
        raise ValueError('synthetic_ledger_terminal_changed')
    if retained['state'] == 'incomplete':
        return {'state': 'incomplete', 'retained_declared_replay_consistent': False, **AUTHORITY}
    bind, selected = factory(request, events=events, blob=blob)
    execution = execute(request['source_label'], request['cwd_label'], request['program'], request['argv'],
        port_factory=bind, validator_factory=lambda io: closed_validator(io, request),parser_context=request['parser_context'])
    if selected: selected[0][0].finish()
    elif len(events) != 3: raise ValueError('synthetic_ledger_unbound_execution_events_changed')
    result = result_value(execution, request)
    if (encode(result) != encode(retained['result']) or encode(execution['io'].touched) != encode(retained['touched_files'])
            or encode(events[-1]) != encode({'kind': 'terminal', 'state': 'complete', 'exit_code': result['exit_code']})
            or not closed()):
        raise ValueError('synthetic_ledger_whole_result_changed')
    return {'state': 'complete', 'program': request['program'], 'original_exit_code': result['exit_code'],
            'kernel_exception': result['kernel_result']['kernel_exception'],
            'original_exit_signal': result['kernel_result']['original_exit_signal'],
            'ledger_binding': result['ledger_binding'], 'successful_outputs': result['successful_outputs'],
            'private_projected_changes': result['private_projected_changes'],
            'native_ledger_observations': result['native_ledger_observations'],
            'kernel_end_descriptors': result['kernel_end_descriptors'],
            'private_creation_mask': PRIVATE_MASK if request['export_mode'] == 'private-candidate' else None,
            'source_output_paths_observed': sorted(set(execution['io'].touched) | set(result['native_ledger_observations'])),
            'source_export_requested': request['export_mode'] == 'selected-files',
            'retained_declared_replay_consistent': True, 'native_source_or_exports_repeated': False, **AUTHORITY}


def generate(options, instance, settings):
    node = {key: settings[key] for key in ('node_id', 'source_revision', 'runtime_source_digest')}
    root = posixpath.normpath(str(Path(options['source_worktree']).expanduser().absolute()))
    cwd = posixpath.normpath(str(Path(options.get('working_directory') or root).expanduser().absolute()))
    argv = list(options['legacy_arguments'])
    if argv[:1] == ['--']: argv = argv[1:]
    request = request_valid({'schema_version': 1, 'profile': PROFILE, 'program': options['program'],
        'source_label': root, 'cwd_label': cwd, 'argv': argv,
        'export_mode': 'selected-files' if options.get('write_selected_files') else 'private-candidate',
        'parser_context':capture_parser_context(),
        'resources': [{'uri': uri, 'label': posixpath.normpath(str(Path(path).expanduser().absolute()))}
                      for uri, path in options.get('schema_resource', []) or []]})
    instance = owned_directory(instance)
    if Path(root).is_relative_to(instance) or instance.is_relative_to(Path(root)):
        raise ValueError('synthetic_ledger_source_instance_overlap')
    source = current_source(node)
    record = Record(owned_directory(instance / 'state/synthetic-ledger/records', True), request, source)
    record.append({'kind': 'execution-intent', 'request': request})
    bind, selected = factory(request, record=record, instance=instance)
    execution = result = error = None
    cleanup = {'required': False, 'observed_descriptors': 0, 'released_descriptors': 0,
               'remaining_descriptors': 0, 'buffered_streams': 0, 'errors': []}
    try:
        execution = execute(root, cwd, request['program'], argv, port_factory=bind,
            validator_factory=lambda io: closed_validator(io, request),parser_context=request['parser_context'])
        result = result_value(execution, request)
        if encode(current_source(node)) != encode(source): raise InputAdmissionError('synthetic_ledger_product_changed')
    except Exception as caught: error = caught
    finally:
        # Keep end-of-kernel facts immutable. Adapter-owned host handles must
        # still be released when admission/journal failure prevents the
        # original finally operations from running. This is not kernel replay.
        if selected and request['export_mode'] == 'selected-files':
            try:
                cleanup = selected[0][1].release_resources()
                if cleanup['remaining_descriptors'] or cleanup['buffered_streams'] or cleanup['errors']:
                    record.capture_incomplete = True
            except Exception as caught:
                record.capture_incomplete = True
                cleanup = {'required': True, 'error_type': type(caught).__name__}
    state = 'incomplete' if error is not None or record.capture_incomplete else 'complete'
    io = selected[0][0] if selected else None
    paths = sorted(set({} if io is None else io.touched) | set({} if result is None else result['native_ledger_observations']))
    terminal = True
    try: record.finish(state, result, {} if io is None else io.touched, error)
    except Exception: state, terminal = 'incomplete', False
    replay_consistent = False
    if state == 'complete':
        try: replay_consistent = inspect(record.root, node=node)['retained_declared_replay_consistent']
        except Exception: state = 'incomplete'
    return {'state': state, 'record_root': str(record.root), 'journal_terminal_written': terminal,
            'retained_declared_replay_consistent': replay_consistent, 'program': request['program'],
            'exit_code': 2 if state == 'incomplete' else result['exit_code'],
            'original_exit_code': None if state == 'incomplete' else result['exit_code'],
            'export_mode': request['export_mode'], 'source_export_requested': request['export_mode'] == 'selected-files',
            'host_resource_release': cleanup,
            'source_effects_may_be_partial': request['export_mode'] == 'selected-files' and (state == 'incomplete' or result['exit_code'] != 0),
            'source_output_paths_observed': paths, **AUTHORITY}, result


def run(arguments, instance=None, settings=None):
    parser = argparse.ArgumentParser(prog='axiom-v2 synthetic-ledger', allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True)
    item = sub.add_parser('generate', allow_abbrev=False)
    item.add_argument('--profile', choices=(PROFILE,), required=True)
    item.add_argument('--program', choices=tuple(PROGRAMS), required=True)
    item.add_argument('--source-worktree', required=True); item.add_argument('--working-directory')
    item.add_argument('--write-selected-files', action='store_true')
    item.add_argument('--schema-resource', nargs=2, action='append', default=[], metavar=('URI', 'FILE'))
    item.add_argument('--format', choices=('receipt', 'legacy'), default='receipt')
    item.add_argument('legacy_arguments', nargs=argparse.REMAINDER)
    for name in ('inspect', 'replay'): sub.add_parser(name, allow_abbrev=False).add_argument('--record', required=True)
    options = parser.parse_args(arguments)
    if options.command == 'replay': value = inspect(options.record)
    else:
        if instance is None or settings is None: raise ValueError('synthetic_ledger_instance_required')
        if options.command == 'inspect': value = inspect(options.record, node={k: settings[k] for k in ('node_id', 'source_revision', 'runtime_source_digest')})
        else:
            receipt, result = generate(vars(options), instance, settings)
            if options.format == 'legacy' and receipt['state'] == 'complete':
                kernel = result['kernel_result']; sys.stdout.write(kernel['stdout']); sys.stderr.write(kernel['stderr'])
                if kernel['kernel_exception'] is not None: print(json.dumps({'execution': 'captured_exception', **kernel['kernel_exception']}), file=sys.stderr)
            else: print(json.dumps(receipt, indent=2))
            return receipt['exit_code']
    print(json.dumps(value, indent=2))
    return 0 if value['state'] == 'complete' else 2
