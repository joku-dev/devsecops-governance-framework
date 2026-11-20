"""Whole daily operations CLI with private raw capture and complete replay."""
import argparse
import json
from pathlib import PurePosixPath
import sys

from lib.operations_application_replay import run_kernel
from lib.operations_input_binding import check_labels
from lib.operations_output_replay import ReplayOutput
from lib.operations_ports import Session, capture_source, ReplayEnvironment, profile, read_record, AUTHORITY, encode
from lib.operations_replay import ReplayCalls

REQUEST_FIELDS = {'schema_version', 'profile', 'provided_observation', 'as_of', 'live_admitted',
    'source_label', 'credential_kind', 'token_selected', 'token_value_retained',
    'config_label', 'schema_label', 'observation_label', 'output_label'}


def label(value):
    return (isinstance(value, str) and len(value) <= 8192 and PurePosixPath(value).is_absolute()
            and str(PurePosixPath(value)) == value and '..' not in PurePosixPath(value).parts
            and not any(ord(c) < 32 for c in value))


def inspect(root, *, node=None):
    request, source, retained, events, blob, closed = read_record(root)
    if (set(request) != REQUEST_FIELDS or type(request['schema_version']) is not int
            or request['schema_version'] != 1 or request['profile'] != profile.PROFILE
            or any(type(request[k]) is not bool for k in ('provided_observation', 'live_admitted', 'token_selected'))
            or request['token_value_retained'] is not False
            or request['credential_kind'] != ('explicit_private_file' if request['token_selected'] else 'none')
            or request['as_of'] is not None and not isinstance(request['as_of'], str)
            or not all(label(request[k]) for k in ('config_label', 'schema_label', 'output_label'))
            or request['provided_observation'] != (request['observation_label'] is not None)
            or request['observation_label'] is not None and not label(request['observation_label'])
            or request['live_admitted'] != (request['source_label'] is not None)
            or request['source_label'] is not None and not label(request['source_label'])
            or not request['provided_observation'] and not request['live_admitted']
            or not request['live_admitted'] and request['token_selected']):
        raise ValueError('operations_retained_request_changed')
    if (set(retained) != {'schema_version', 'state', 'result', 'touched_files', 'exception_type', 'event_count', 'event_tip', *AUTHORITY}
            or type(retained['schema_version']) is not int or retained['schema_version'] != 1
            or any(retained.get(k) != v for k, v in AUTHORITY.items())
            or not events or events[0] != {'kind': 'opened', **AUTHORITY}):
        raise ValueError('operations_retained_authority_changed')
    if node is not None and source.get('node_context') != node:
        raise ValueError('operations_retained_node_context_changed')
    if not label(source.get('source_root')):
        raise ValueError('operations_retained_source_label_changed')
    current = capture_source(source.get('node_context'), source.get('product_tree'))
    current['source_root'] = source['source_root']  # Recorded label; not a source to execute/read.
    if source != current:
        raise ValueError('operations_retained_source_changed')
    check_labels(request, source, profile.PRODUCT_INPUTS)
    if retained['state'] != 'complete' or retained['exception_type'] is not None:
        return {'state': 'incomplete', 'record_root': str(root), 'retained_declared_replay_consistent': False, **AUTHORITY}
    calls = ReplayCalls(events, blob, expected_opened={'kind': 'opened', **AUTHORITY})
    environment = ReplayEnvironment(calls, request, source)
    output = ReplayOutput(calls, request['output_label'])
    result = run_kernel(request, environment, output, profile)
    calls.finish(result)
    for snapshot in retained['touched_files'].values():
        output.snapshot(snapshot)
    if encode(result) != encode(retained['result']) or encode(output.files) != encode(retained['touched_files']) or not closed():
        raise ValueError('operations_complete_retained_replay_changed')
    return {'state': 'complete', 'record_root': str(root), 'original_exit_code': result['exit_code'],
        'kernel_exception': None if result['kernel_exception'] is None else result['kernel_exception']['type'],
        'retained_declared_replay_consistent': True, 'native_HTTP_signature_clock_or_source_repeated': False,
        'current_exports_rechecked': False, 'source_digest': source['source_digest'], **AUTHORITY}


def generate(options, instance, settings):
    session = Session(options, instance, settings)
    result = error = None
    try:
        try:
            result = run_kernel(session.request, session.environment, session.output, profile)
            session.checkpoint()
        except Exception as failure:
            error = failure
        state = 'incomplete' if error is not None or session.record.capture_incomplete else 'complete'
        session.record.finish(state, result, session.output.files, error)
        receipt = {'state': state, 'record_root': str(session.record.root),
            'output_directory': str(session.output.root), 'exit_code': 2 if state == 'incomplete' else result['exit_code'],
            'original_exit_code': None if result is None else result['exit_code'],
            'source_digest': session.source['source_digest'], **AUTHORITY}
        if state == 'complete':
            inspect(session.record.root, node=session.node)
        return receipt, result, receipt['exit_code']
    finally:
        session.close()


def run(arguments, instance=None, settings=None):
    parser = argparse.ArgumentParser(prog='axiom-v2 operations-report', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('generate', allow_abbrev=False)
    create.add_argument('--profile', choices=(profile.PROFILE,), required=True)
    create.add_argument('--config')
    create.add_argument('--observation')
    create.add_argument('--as-of')
    create.add_argument('--source-worktree')
    create.add_argument('--token-file')
    create.add_argument('--allow-live-fallback', action='store_true')
    create.add_argument('--output-dir', dest='output_directory')
    create.add_argument('--format', choices=('receipt', 'legacy'), default='receipt')
    for name in ('inspect', 'replay'):
        sub = commands.add_parser(name, allow_abbrev=False)
        sub.add_argument('--record', required=True)
    options = parser.parse_args(arguments)
    if options.command in ('inspect', 'replay'):
        if options.command == 'inspect' and (instance is None or settings is None):
            raise ValueError('operations_explicit_instance_required')
        node = None if options.command == 'replay' else {k: settings[k] for k in ('node_id', 'source_revision', 'runtime_source_digest')}
        receipt = inspect(options.record, node=node)
        print(json.dumps(receipt, indent=2))
        return 0 if receipt['state'] == 'complete' else 2
    if instance is None or settings is None:
        raise ValueError('operations_explicit_instance_required')
    receipt, result, code = generate(vars(options), instance, settings)
    if options.format == 'legacy':
        if result is not None:
            sys.stdout.write(result['stdout'])
            sys.stderr.write(result['stderr'])
            if result['kernel_exception'] is not None:
                print(json.dumps({'execution': 'captured_exception', 'diagnostics': [result['kernel_exception']['type']]}), file=sys.stderr)
    else:
        print(json.dumps(receipt, indent=2))
    return code
