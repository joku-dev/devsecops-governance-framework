"""Atomic private dispatcher state/log generations and complete offline replay."""
from copy import deepcopy
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import review_dispatch as logic, review_planning
from lib.candidate_workspace import CandidateWorkspace, inventory, private_directory
from lib.ci_bundle_storage import private_parents, reserve
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import (review_dispatch_profile, capture_dispatch_source,
                               observe_dispatch_source, validate_dispatch_source,
                               DISPATCH_FILE_PROFILES, dispatch_file_label)
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.review_metadata_application import FLAGS
from lib.v2_boundary import safe_source

PROFILE = 'legacy-role-dispatch-v1'
DEFAULT_STATE = 'generated/agent-usage/recording-state.json'
CONTEXT = '.axiom/context.json'
OPERATION = '.axiom/operation.json'
STDOUT = '.axiom/stdout.bin'
SOURCE = '.axiom/source.json'
MAX_JSON = 8 * 1024**2
MAX_OUTPUT = 8 * 1024**2


def schema(value, definition):
    contract = read_json(ROOT / 'schemas/axiom-v2-review-dispatch.schema.json')
    try:
        Draft202012Validator({'$ref': '#/$defs/' + definition, '$defs': contract['$defs']},
                             format_checker=FormatChecker()).validate(value)
    except ValidationError:
        raise ValueError('invalid_dispatch_' + definition) from None


def business_name(name):
    logic.text(name)
    if name == '.axiom' or name.startswith('.axiom/'):
        raise ValueError('dispatch_metadata_path_reserved')
    path = Path(name)
    if name == '.' or path.is_absolute() or '..' in path.parts or str(path) != name or '\\' in name or ':' in name:
        raise ValueError('invalid_dispatch_business_path')
    return name


def descriptor(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def derive(request, before_state, before_log, *, dispatch=None, roles=None):
    value = logic.transition(request, before_state, before_log, dispatch=dispatch, roles=roles)
    for key, limit, code in [('state_bytes', logic.MAX_STATE, 'dispatch_state_output_budget'),
            ('log_bytes', logic.MAX_LOG, 'dispatch_log_output_budget'),
            ('stdout', MAX_OUTPUT, 'dispatch_stdout_budget')]:
        if value[key] is not None and len(value[key]) > limit: raise ValueError(code)
    return value


def write(root, name, raw):
    path = safe_source(root, name); private_parents(root, Path(name))
    path.write_bytes(raw); path.chmod(0o600)


class DispatchWorkspace:
    def __init__(self, instance_root, name, settings, profile=PROFILE):
        review_dispatch_profile(profile)
        self.instance = Path(instance_root).resolve(); private_directory(self.instance / 'state')
        self.root = private_directory(self.instance / 'state/review-dispatch')
        private_directory(self.root / 'state')
        self.workspace = CandidateWorkspace(self.root, name, node_id=settings['node_id'])
        self.name = name; self.profile = profile
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
                        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())

    def assert_current(self):
        if (source_digest() != self.binding['runtime_source_digest']
                or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']):
            raise ValueError('dispatch_product_changed')

    def context(self, root):
        value = strict_json(safe_bytes(root / CONTEXT, limit=65536)); schema(value, 'context')
        if any(value[key] != expected for key, expected in self.binding.items()) or value['profile'] != self.profile:
            raise ValueError('dispatch_node_runtime_or_source_changed')
        return value

    def shape(self, root, generation=None):
        if any(path.is_symlink() for path in (root, *root.parents)):
            raise ValueError('unsafe_dispatch_generation')
        members = inventory(root)
        if generation is not None and canonical_digest(members) != identity(generation):
            raise ValueError('dispatch_generation_changed')
        expected_dirs = {parent.as_posix() for name in members for parent in Path(name).parents if parent != Path('.')}
        actual_dirs = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_dir()}
        if actual_dirs != expected_dirs: raise ValueError('dispatch_directory_members_changed')
        self.context(root)
        business = {name: digest for name, digest in members.items() if not name.startswith('.axiom/')}
        for name in business: business_name(name)
        return members, business

    def generation(self, identifier):
        identifier = identity(identifier); root = self.workspace.generations / identifier
        members, business = self.shape(root, identifier)
        return root, members, business

    def initialize(self):
        with self.workspace.lock():
            marker = self.workspace.root / 'current.json'
            if marker.exists() or marker.is_symlink(): raise ValueError('fresh_dispatch_workspace_required')
            reserve(self.workspace.root, 128 * 1024**2)
            with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.workspace.root) as temporary:
                staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
                context = {'schema_version': 1, 'kind': 'private-review-dispatch-workspace',
                    'product': 'axiom-v2', **self.binding, 'profile': self.profile,
                    'source_worktree_clean': self.clean, 'mode': 'report-only', 'evidence_trust': 'unverified', **FLAGS}
                schema(context, 'context'); write(staged, CONTEXT, logic.wire(context))
                self.verify(staged); self.assert_current(); marker = self.workspace.commit(staged)
            return self.inspect(marker['generation'])

    def source_data(self, root, operation):
        source = operation['source']
        if source is None:
            if operation['request']['action'] == 'dispatch': raise ValueError('dispatch_source_required')
            return None, None, None, set()
        if operation['request']['action'] != 'dispatch': raise ValueError('unexpected_dispatch_source')
        facts = strict_json(safe_bytes(root / SOURCE, limit=MAX_JSON))
        rows = facts.get('files')
        if not isinstance(rows, dict) or len(rows) > 401: raise ValueError('invalid_dispatch_source_members')
        raw = {}; members = {SOURCE}
        for name, row in rows.items():
            if not isinstance(row, dict) or not isinstance(row.get('sha256'), str):
                raise ValueError('invalid_dispatch_source_descriptor')
            blob = '.axiom/blobs/' + identity(row['sha256']) + '.bin'; members.add(blob)
            raw[name] = safe_bytes(root / blob, limit=1024**2)
        roles, routing = validate_dispatch_source(facts, raw, self.profile)
        if source['explicit_paths']:
            if facts['selection_mode'] != 'explicit_paths' or facts['changed_paths'] != source['explicit_paths']:
                raise ValueError('dispatch_explicit_source_changed')
        elif facts['selection_mode'] != 'working_tree': raise ValueError('dispatch_working_source_changed')
        dispatch = review_planning.dispatch(facts['changed_paths'], roles, routing, review_dispatch_profile(self.profile))
        return dispatch, roles, facts, members

    def selected(self, root, request, state_name):
        state_name = business_name(state_name)
        state_path = safe_source(root, state_name)
        before_state = safe_bytes(state_path, limit=logic.MAX_STATE) if state_path.exists() else None
        log_name = request['usage_log']
        if request['action'] == 'dispatch':
            previous = logic.state(before_state)
            if logic.active(previous): log_name = previous.get('usage_log', logic.DEFAULT_LOG)
        log_name = business_name(log_name)
        if unicodedata.normalize('NFC', log_name).casefold() == unicodedata.normalize('NFC', state_name).casefold():
            raise ValueError('dispatch_state_log_alias')
        path = safe_source(root, log_name)
        before_log = safe_bytes(path, limit=logic.MAX_LOG) if path.exists() else None
        return state_name, log_name, before_state, before_log

    def verify(self, root):
        members, business = self.shape(root)
        if OPERATION not in members:
            if set(members) != {CONTEXT}: raise ValueError('dispatch_initial_members_changed')
            return None, None
        operation = strict_json(safe_bytes(root / OPERATION, limit=MAX_JSON)); schema(operation, 'operation')
        request = operation['request']; logic.checked_request(request)
        business_name(request['usage_log'])
        parent, _, before_business = self.generation(operation['parent_generation'])
        if self.context(parent) != self.context(root): raise ValueError('dispatch_parent_context_changed')
        state_name, log_name, before_state, before_log = self.selected(parent, request, operation['usage_state'])
        dispatch, roles, _, source_members = self.source_data(root, operation)
        derived = derive(request, before_state, before_log, dispatch=dispatch, roles=roles)
        expected = dict(before_business)
        for name, key in [(state_name, 'state_bytes'), (log_name, 'log_bytes')]:
            raw = derived[key]
            if raw is None: expected.pop(name, None)
            else: expected[name] = hashlib.sha256(raw).hexdigest()
        if expected != business: raise ValueError('dispatch_business_outputs_changed')
        if set(members) - set(business) != {CONTEXT, OPERATION, STDOUT} | source_members:
            raise ValueError('dispatch_metadata_members_changed')
        stdout = safe_bytes(root / STDOUT, limit=MAX_OUTPUT)
        if stdout != derived['stdout'] or descriptor(stdout) != operation['stdout']:
            raise ValueError('dispatch_stdout_changed')
        effects = {'state_changed': derived['state_changed'], 'log_changed': derived['log_changed'],
                   'event_appended': derived['event'] is not None,
                   'selected_usage_log': derived['selected_usage_log'], 'provider_invoked': False}
        if operation['effects'] != effects: raise ValueError('dispatch_effects_changed')
        return operation, derived

    def inspect(self, identifier):
        root, _, business = self.generation(identifier); operation, _ = self.verify(root)
        self.assert_current()
        return {'schema_version': 1, 'workspace': self.name, 'generation': identifier, **self.binding,
            'operation': operation['request']['action'] if operation else 'initialize',
            'assessed_at': operation['request']['at'] if operation else None,
            'clock_provenance': operation['clock_provenance'] if operation else None,
            'data_directory': str(root), 'stdout_file': str(root / STDOUT) if operation else None,
            'stdout': operation['stdout'] if operation else None,
            'effects': deepcopy(operation['effects']) if operation else None,
            'business_files': business, 'retained_complete_outputs_reverified': True,
            'target_current_state_rechecked': False, 'mode': 'report-only', 'evidence_trust': 'unverified', **FLAGS}

    def execute(self, request, *, usage_state=DEFAULT_STATE, repository=None, base_ref=None, paths=None,
                clock_provenance='explicit_operator_time'):
        logic.checked_request(request); business_name(request['usage_log']); business_name(usage_state)
        if request['action'] == 'dispatch':
            if repository is None: raise ValueError('dispatch_repository_required')
            repository = Path(repository).expanduser().absolute()
            target = repository.resolve()
            if self.instance.is_relative_to(target) or target.is_relative_to(self.root):
                raise ValueError('dispatch_private_state_must_be_outside_target')
        elif repository is not None or base_ref is not None or paths:
            raise ValueError('unexpected_dispatch_repository')
        with self.workspace.lock():
            current, marker = self.workspace.current(); self.inspect(marker['generation'])
            reserve(self.workspace.root, 128 * 1024**2)
            facts = raw = source = None
            if repository is not None:
                facts, raw = capture_dispatch_source(repository, base_ref, paths or [], self.profile)
                source = {'repository_path': str(repository.resolve()), 'base_ref': base_ref,
                          'explicit_paths': facts['changed_paths'] if paths else []}
            state_name, log_name, before_state, before_log = self.selected(current, request, usage_state)
            dispatch = roles = None
            if facts is not None:
                roles, routing = validate_dispatch_source(facts, raw, self.profile)
                dispatch = review_planning.dispatch(facts['changed_paths'], roles, routing, review_dispatch_profile(self.profile))
            derived = derive(request, before_state, before_log, dispatch=dispatch, roles=roles)
            operation = {'schema_version': 1, 'kind': 'private-review-dispatch-operation',
                'request': deepcopy(request), 'usage_state': usage_state, 'parent_generation': marker['generation'],
                'source': source, 'clock_provenance': clock_provenance,
                'stdout': descriptor(derived['stdout']), 'effects': {
                    'state_changed': derived['state_changed'], 'log_changed': derived['log_changed'],
                    'event_appended': derived['event'] is not None,
                    'selected_usage_log': derived['selected_usage_log'], 'provider_invoked': False}}
            schema(operation, 'operation')
            if len(logic.wire(operation)) > MAX_JSON: raise ValueError('dispatch_operation_budget')
            with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.workspace.root) as temporary:
                staged = Path(temporary) / 'data'; shutil.copytree(current, staged)
                context = safe_bytes(staged / CONTEXT, limit=65536)
                shutil.rmtree(staged / '.axiom'); write(staged, CONTEXT, context)
                for name, key in [(state_name, 'state_bytes'), (log_name, 'log_bytes')]:
                    if derived[key] is not None: write(staged, name, derived[key])
                write(staged, OPERATION, logic.wire(operation)); write(staged, STDOUT, derived['stdout'])
                if facts is not None:
                    write(staged, SOURCE, logic.wire(facts))
                    for item in raw.values(): write(staged, '.axiom/blobs/' + hashlib.sha256(item).hexdigest() + '.bin', item)
                self.verify(staged); self.assert_current()
                if repository is not None and observe_dispatch_source(repository, base_ref, paths or [], self.profile) != (facts, raw):
                    raise ValueError('dispatch_target_changed_before_commit')
                result = self.workspace.commit(staged)
            receipt = self.inspect(result['generation'])
            receipt['target_current_state_rechecked'] = repository is not None
            return receipt


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 review-dispatch', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    initialize = commands.add_parser('init', allow_abbrev=False)
    initialize.add_argument('--workspace', required=True)
    initialize.add_argument('--profile', choices=(PROFILE,), required=True)
    inspect = commands.add_parser('inspect', allow_abbrev=False)
    inspect.add_argument('--workspace', required=True); inspect.add_argument('--generation', required=True)
    external_inspect = commands.add_parser('external-inspect', allow_abbrev=False)
    external_inspect.add_argument('--id', required=True)
    external_apply = commands.add_parser('external-apply', allow_abbrev=False)
    external_apply.add_argument('--id', required=True)
    external_apply.add_argument('--format', choices=('legacy', 'receipt'), default='receipt')
    external_abandon = commands.add_parser('external-abandon', allow_abbrev=False)
    external_abandon.add_argument('--id', required=True); external_abandon.add_argument('--reason', required=True)
    commands.add_parser('external-pending', allow_abbrev=False)
    execute = commands.add_parser('run', allow_abbrev=False)
    execute.add_argument('--workspace')
    execute.add_argument('--external-files', action='store_true', help='Use the original caller status/log files through an explicit local-file adapter.')
    execute.add_argument('--file-profile', choices=DISPATCH_FILE_PROFILES)
    execute.add_argument('--prepare-only', action='store_true', help='Retain an external-file plan without applying it.')
    execute.add_argument('--repo', type=Path)
    execute.add_argument('paths', nargs='*')
    execute.add_argument('--base-ref'); execute.add_argument('--json', action='store_true')
    execute.add_argument('--log-usage', action='store_true')
    execute.add_argument('--usage-log', default=logic.DEFAULT_LOG, help='Workspace-relative log, or explicit caller path in external-file mode.')
    execute.add_argument('--usage-state', default=DEFAULT_STATE, help='Workspace-relative state, or explicit caller path in external-file mode.')
    execute.add_argument('--usage-summary', action='store_true')
    execute.add_argument('--record-next', type=int); execute.add_argument('--record-continuous', action='store_true')
    execute.add_argument('--recording-status', action='store_true')
    execute.add_argument('--run-type', choices=('dispatch', 'provider_review'), default='dispatch')
    execute.add_argument('--provider-review'); execute.add_argument('--provider', default='none')
    execute.add_argument('--platform', default='local'); execute.add_argument('--source', default='manual')
    execute.add_argument('--at'); execute.add_argument('--format', choices=('legacy', 'receipt'), default='legacy')
    args = parser.parse_args(arguments)
    if args.command in ('external-inspect', 'external-apply', 'external-pending', 'external-abandon'):
        from lib.review_dispatch_external import ExternalDispatchContext
        context = ExternalDispatchContext(instance_root, settings)
        if args.command == 'external-pending':
            print(json.dumps({'pending_assessment_ids': context.pending(), 'provider_invoked': False}, sort_keys=True)); return 0
        if args.command == 'external-inspect':
            print(json.dumps(context.inspect(args.id), sort_keys=True)); return 0
        if args.command == 'external-abandon':
            print(json.dumps(context.abandon(args.id, args.reason), sort_keys=True)); return 0
        return external_apply_output(context, args.id, args.format)
    if args.command == 'run':
        action = ('record-window' if args.record_next is not None else 'record-continuous' if args.record_continuous
                  else 'recording-status' if args.recording_status else 'usage-summary' if args.usage_summary else 'dispatch')
        if args.external_files:
            if args.workspace is not None or args.file_profile is None: raise ValueError('external_dispatch_requires_file_profile_without_workspace')
        elif args.file_profile is not None or args.prepare_only:
            raise ValueError('dispatch_file_options_require_external_mode')
        elif args.workspace is None: raise ValueError('dispatch_private_workspace_required')
        if action == 'dispatch' or args.external_files:
            if args.repo is None: raise ValueError('dispatch_repository_required')
            if Path(instance_root).resolve().is_relative_to(args.repo.expanduser().resolve()):
                raise ValueError('dispatch_private_state_must_be_outside_target')
        provenance = 'explicit_operator_time' if args.at is not None else 'runtime_clock'
        at = args.at if args.at is not None else datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        request = logic.request(action, at, count=args.record_next if action == 'record-window' else None,
            usage_log=dispatch_file_label(args.repo.expanduser().absolute(), args.usage_log) if args.external_files else args.usage_log,
            json_output=args.json, log_usage=args.log_usage, run_type=args.run_type,
            provider=args.provider, platform=args.platform, source=args.source, provider_review=args.provider_review)
        if args.external_files:
            from lib.review_dispatch_external import ExternalDispatchContext
            context = ExternalDispatchContext(instance_root, settings)
            receipt = context.prepare(args.repo, args.usage_state, request, paths=args.paths, base_ref=args.base_ref,
                                      file_profile=args.file_profile, clock_provenance=provenance)
            if args.prepare_only:
                print(json.dumps(receipt, sort_keys=True)); return 0
            return external_apply_output(context, receipt['assessment_id'], args.format)
    context = DispatchWorkspace(instance_root, args.workspace, settings,
                                args.profile if args.command == 'init' else PROFILE)
    if args.command == 'init':
        print(json.dumps(context.initialize(), sort_keys=True)); return 0
    if args.command == 'inspect':
        print(json.dumps(context.inspect(args.generation), sort_keys=True)); return 0
    receipt = context.execute(request, usage_state=args.usage_state, clock_provenance=provenance,
        **({'repository': args.repo, 'base_ref': args.base_ref, 'paths': args.paths} if action == 'dispatch' else {}))
    if args.format == 'receipt': print(json.dumps(receipt, sort_keys=True))
    else: print(safe_bytes(Path(receipt['stdout_file']), limit=MAX_OUTPUT).decode('utf-8'), end='')
    return 0


def external_apply_output(context, identifier, output_format):
    """On partial failure, return the exact recovery ID without private payloads."""
    identifier = identity(identifier)
    try: receipt = context.apply(identifier)
    except (ValueError, OSError, KeyError, TypeError) as error:
        code = str(error) if isinstance(error, ValueError) else ''
        if not re.fullmatch('[a-z][a-z0-9_]{0,100}', code): code = 'external_dispatch_apply_failed'
        result = {'execution': 'error', 'assessment_id': identifier, 'diagnostics': [code],
                  'recovery_command': 'review-dispatch external-apply --id ' + identifier}
        if code == 'external_dispatch_pending_operation_requires_recovery': result['pending_assessment_ids'] = context.pending()
        print(json.dumps(result, sort_keys=True), file=sys.stderr); return 2
    if output_format == 'receipt': print(json.dumps(receipt, sort_keys=True))
    else: print(context.stdout(identifier).decode('utf-8'), end='')
    return 0
