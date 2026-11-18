"""Private product runtime validation with retained inputs and offline replay."""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import secrets
import sys

from lib import validation_sources
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import source_digest
from lib.provider_ports import ValidationOPA, ValidationWorktree
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.runtime_validation import RuntimeValidation
from lib.validation_files import MAX_FILE, MAX_FILES, MAX_TOTAL, WORKING_PROFILE, ValidationFiles
from lib.validation_operations import RuntimeValidationEnvironment
from lib.validation_replay import ReplayOPA, encoded
from lib.v2_boundary import safe_source

MAX_RECORD = 48 * 1024**2
MANIFEST_LIMIT = 4 * 1024**2
AUTHORITY = {'mode': 'report-only', 'official_acceptance': False, 'production_approval': False,
    'risk_acceptance': False, 'authority_transferred': False, 'operating_acceptance_inherited': False,
    'published': False, 'independent_execution_attested': False}
PENDING_FIELDS = {'schema_version', 'kind', 'node_id', 'runtime_source_digest', 'source_revision',
    'assessed_at', 'input_id', 'source_tree', 'source_scope', 'source_worktree_clean',
    'working_tree_used', 'original_display_root', 'operation_id', *AUTHORITY}


def descriptors(files):
    ValidationFiles(files)
    return {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            for name, raw in files.items()}


def write_files(root, files):
    root.mkdir(mode=0o700)
    for name, raw in files.items():
        path = safe_source(root, name)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        for parent in path.parents:
            if parent == root:
                break
            parent.chmod(0o700)
        path.write_bytes(raw)
        path.chmod(0o600)


def retained_files(root, expected):
    if (not isinstance(expected, dict) or len(expected) > MAX_FILES or root.is_symlink()
            or not root.is_dir() or root.stat().st_mode & 0o077):
        raise ValueError('invalid_validation_retained_files')
    files = {}
    for path in root.rglob('*'):
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError('unsafe_validation_retained_files')
        if path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if name not in expected or len(files) >= MAX_FILES:
            raise ValueError('validation_retained_membership_changed')
        files[name] = safe_bytes(path, limit=MAX_FILE)
        if sum(map(len, files.values())) > MAX_TOTAL:
            raise ValueError('validation_retained_byte_budget')
    if canonical_digest(descriptors(files)) != canonical_digest(expected):
        raise ValueError('validation_retained_bytes_changed')
    return files


def execute(files, port):
    environment = RuntimeValidationEnvironment(files, port)
    error_type = None
    try:
        code = RuntimeValidation(environment).main()
    except Exception as error:
        # Original uncaught Python failures are a recorded incomplete execution,
        # not a fabricated equivalent traceback or a completed validation result.
        error_type = type(error).__name__
        code = 2
    return {'execution': 'complete' if error_type is None else 'incomplete', 'exit_code': code,
        'exception_type': error_type,
        'stdout_base64': base64.b64encode(environment.stdout.getvalue().encode()).decode('ascii'),
        'stderr_base64': base64.b64encode(environment.stderr.getvalue().encode()).decode('ascii'),
        'generator_commands': environment.commands}, environment


class ValidationContext:
    def __init__(self, instance_root, settings, *, product_root=ROOT):
        self.product = Path(product_root).resolve()
        self.root = private_directory(private_directory(Path(instance_root) / 'state') / 'validation')
        self.operations = private_directory(self.root / 'operations')
        self.settings = settings
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
            'source_revision': git_read(self.product, 'rev-parse', 'HEAD').decode().strip()}

    def assert_current(self):
        if (self.binding['runtime_source_digest'] != source_digest()
                or self.binding['source_revision'] != git_read(self.product, 'rev-parse', 'HEAD').decode().strip()):
            raise ValueError('validation_product_changed_during_operation')

    def create(self, at, *, source_worktree=None):
        explicit_time(at)
        working = source_worktree is not None
        source = self.product if not working else Path(source_worktree).resolve()
        if working and source == self.product:
            raise ValueError('separate_validation_source_worktree_required')
        acquisition = None if not working else ValidationWorktree(source_worktree, self.binding['source_revision'])
        def capture():
            return (validation_sources.capture(self.product, self.binding['source_revision'])
                    if acquisition is None else acquisition.capture())
        data, manifest = capture()
        kind = ('working-tree-product-runtime-validation' if working else 'committed-product-runtime-validation')
        value = {'schema_version': 1, 'kind': kind, **self.binding,
            'assessed_at': at, 'input_id': validation_sources.digest(manifest),
            'source_tree': manifest['tree'], 'source_scope': manifest['scope'],
            'source_worktree_clean': (acquisition.clean() if working else
                not bool(git_read(source, 'status', '--porcelain', '--untracked-files=all').strip())),
            'working_tree_used': working, 'original_display_root': str(source), **AUTHORITY}
        reserve(self.root, 2 * MAX_TOTAL + MAX_RECORD + MANIFEST_LIMIT)
        self.assert_current()
        operation = secrets.token_hex(32)
        target = self.operations / operation
        target.mkdir(mode=0o700)
        # The journal precedes all native validation invocations. An interrupted
        # operation is retained as pending and is never automatically resumed.
        value['operation_id'] = operation
        write_files(target / 'inputs', data)
        atomic_json(target / 'input-manifest.json', manifest)
        atomic_json(target / 'pending.json', value)
        port = ValidationOPA(self.settings['opa'], product_root=self.product)
        files = ValidationFiles(data, manifest['membership'], label=str(source),
            native_profile=WORKING_PROFILE if working else 'product')
        outcome, environment = execute(files, port)
        value.update(outcome, opa_available=port.available, opa_sha256=port.tool_sha256,
            native_observations=encoded(port.observations), output_files=descriptors(files.files))
        if len((json.dumps(value) + '\n').encode()) > MAX_RECORD:
            raise ValueError('validation_record_byte_budget')
        write_files(target / 'outputs', files.files)
        self.assert_current()
        if capture()[1] != manifest:
            raise ValueError('validation_product_inputs_changed')
        atomic_json(target / 'assessment.json', value)
        return operation, deepcopy(value)

    def inspect(self, operation):
        operation = identity(operation)
        target = self.operations / operation
        if target.is_symlink() or not target.is_dir() or target.stat().st_mode & 0o077:
            raise ValueError('unsafe_validation_operation')
        if not (target / 'assessment.json').exists():
            raise ValueError('validation_operation_pending_requires_review')
        value = strict_json(safe_bytes(target / 'assessment.json', limit=MAX_RECORD))
        pending = strict_json(safe_bytes(target / 'pending.json', limit=MANIFEST_LIMIT))
        if set(pending) != PENDING_FIELDS:
            raise ValueError('invalid_validation_operation_contract')
        expected = {*pending, 'execution', 'exit_code', 'exception_type', 'stdout_base64', 'stderr_base64',
                    'generator_commands', 'opa_available', 'opa_sha256', 'native_observations', 'output_files'}
        if (set(value) != expected
                or canonical_digest({k: value.get(k) for k in pending}) != canonical_digest(pending)
                or value.get('operation_id') != operation or type(value.get('schema_version')) is not int
                or value.get('schema_version') != 1 or type(value.get('exit_code')) is not int
                or value.get('kind') not in ('committed-product-runtime-validation', 'working-tree-product-runtime-validation')
                or canonical_digest({k: value.get(k) for k in {**self.binding, **AUTHORITY}})
                   != canonical_digest({**self.binding, **AUTHORITY})):
            raise ValueError('validation_record_binding_or_authority_changed')
        explicit_time(value['assessed_at'])
        retained = strict_json(safe_bytes(target / 'input-manifest.json', limit=MANIFEST_LIMIT))
        working = value['kind'] == 'working-tree-product-runtime-validation'
        if working:
            if set(retained) != {'schema_version', 'scope', 'commit', 'tree', 'source_root', 'membership', 'files'}:
                raise ValueError('invalid_validation_worktree_manifest')
            data = retained_files(target / 'inputs', retained['files'])
            validation_sources.check_working_manifest(retained, data,
                revision=self.binding['source_revision'],
                tree=git_read(self.product, 'rev-parse', 'HEAD^{tree}').decode().strip())
            manifest = retained
            display_root = retained['source_root']
        else:
            data, manifest = validation_sources.capture(self.product, self.binding['source_revision'])
            display_root = str(self.product)
        if (canonical_digest(manifest) != canonical_digest(retained) or validation_sources.digest(manifest) != value['input_id']
                or manifest['tree'] != value['source_tree'] or manifest['scope'] != value['source_scope']
                or value['working_tree_used'] is not working or type(value['source_worktree_clean']) is not bool
                or value['original_display_root'] != display_root
                or retained_files(target / 'inputs', manifest['files']) != data):
            raise ValueError('validation_input_binding_changed')
        if value['execution'] != 'complete' or value['exception_type'] is not None:
            raise ValueError('validation_incomplete_execution_cannot_replay')
        port = ReplayOPA(value['native_observations'], available=value['opa_available'], tool_sha256=value['opa_sha256'])
        files = ValidationFiles(data, manifest['membership'], label=value['original_display_root'],
            native_profile=WORKING_PROFILE if working else 'product')
        result, _ = execute(files, port)
        port.finish()
        if (canonical_digest({k: value.get(k) for k in result}) != canonical_digest(result)
                or retained_files(target / 'outputs', value['output_files']) != files.files):
            raise ValueError('validation_replay_changed')
        self.assert_current()
        return deepcopy(value)

    def status(self):
        rows = []
        for path in sorted(self.operations.iterdir()):
            operation = identity(path.name)
            try:
                value = self.inspect(operation)
                rows.append({'operation_id': operation, 'state': 'retained_declared_replay_consistent',
                    'execution': value['execution'], 'exit_code': value['exit_code']})
            except (ValueError, OSError):
                rows.append({'operation_id': operation, 'state': 'pending_incomplete_or_invalid'})
        return rows


def run(arguments, instance_root, settings):
    if arguments and arguments[0] in ('releases','release-inspect','release-status'):
        from lib.release_validation_application import run as release_run
        return release_run(arguments,instance_root,settings)
    parser = argparse.ArgumentParser(prog='axiom-v2 validation', allow_abbrev=False)
    sub = parser.add_subparsers(dest='operation', required=True)
    runtime = sub.add_parser('runtime', allow_abbrev=False)
    runtime.add_argument('--at', required=True)
    runtime.add_argument('--output', choices=('json', 'legacy'), default='json')
    runtime.add_argument('--source-worktree', type=Path,
        help='Separate explicit current-data worktree at this exact product commit; never executes its scripts.')
    inspect = sub.add_parser('inspect', allow_abbrev=False)
    inspect.add_argument('--assessment', required=True)
    sub.add_parser('status', allow_abbrev=False)
    for name in ('releases','release-inspect','release-status'):
        sub.add_parser(name,allow_abbrev=False,add_help=False,
            help='Explicit private release-signature verification and retained replay.')
    args = parser.parse_args(arguments)
    context = ValidationContext(instance_root, settings)
    if args.operation == 'status':
        print(json.dumps({'operations': context.status(), **AUTHORITY}, indent=2))
        return 0
    if args.operation == 'inspect':
        print(json.dumps(context.inspect(args.assessment), indent=2))
        return 0
    operation, value = context.create(args.at, source_worktree=args.source_worktree)
    if args.output == 'legacy':
        sys.stdout.write(base64.b64decode(value['stdout_base64']).decode())
        sys.stderr.write(base64.b64decode(value['stderr_base64']).decode())
    else:
        print(json.dumps({'assessment_id': operation, **value}, indent=2))
    return value['exit_code']
