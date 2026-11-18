"""Private whole repository validation, explicit legacy profile and offline replay."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys

from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT
from lib.portable.runtime import source_digest, approved_opa_hashes
from lib.provider_ports import (REPOSITORY_ENGINE_PROFILES, repository_engine_profile, repository_git_tool,
    execute_repository_operation, load_repository_operation, repository_operation_header, inspect_repository_worker)
from lib import repository_capture as capture
from lib import repository_operation as contract
from lib.repository_inspection import inspect_repository_operation
from lib.result_assessments import identity
from lib.result_snapshot_store import explicit_time


class RepositoryContext:
    def __init__(self, instance_root, settings, *, product_root=ROOT):
        self.product = Path(product_root).resolve(strict=True)
        self.settings = deepcopy(settings)
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
            'source_revision': git_read(self.product, 'rev-parse', 'HEAD').decode().strip(),
            'source_tree': git_read(self.product, 'rev-parse', 'HEAD^{tree}').decode().strip()}
        if (any(settings.get(key) != self.binding[key] for key in ('node_id', 'runtime_source_digest', 'source_revision'))
                or settings.get('source_root') != str(self.product)):
            raise ValueError('repository_validation_current_instance_required')
        instance = private_directory(Path(instance_root)).resolve()
        self.root = private_directory(private_directory(instance / 'state') / 'repository-validation')
        self.operations = private_directory(self.root / 'operations')

    def assert_current(self):
        if (self.binding['runtime_source_digest'] != source_digest()
                or self.binding['source_revision'] != git_read(self.product, 'rev-parse', 'HEAD').decode().strip()
                or self.binding['source_tree'] != git_read(self.product, 'rev-parse', 'HEAD^{tree}').decode().strip()):
            raise ValueError('repository_validation_product_changed_during_operation')

    def create(self, at, *, engine_profile, source_worktree=None):
        explicit_time(at)
        options = repository_engine_profile(engine_profile)
        source = self.product
        profile = capture.COMMITTED
        if source_worktree is not None:
            if Path(source_worktree).is_symlink():raise ValueError('ordinary_repository_worktree_required')
            source = Path(source_worktree).resolve(strict=True)
            if source == self.product:raise ValueError('separate_repository_worktree_required')
            profile = capture.WORKING
        self.assert_current()
        reserve(self.root, 2 * capture.MAX_TOTAL + 576 * 1024**2)
        operation = secrets.token_hex(32)
        header = {'schema_version': 1, 'kind': 'product-repository-validation', **self.binding,
            'source_root': str(source), 'profile': profile, 'engine_profile': engine_profile,
            'assessed_at': at, 'operation_id': operation, **contract.AUTHORITY}
        contract.binding(header)
        target = self.operations / operation; target.mkdir(mode=0o700)
        value = execute_repository_operation(target, header, source=source, git_tool=repository_git_tool(),
            opa_tool=self.settings['opa'], approved_opa_hashes=frozenset(approved_opa_hashes('1.18.2')),
            clock=lambda: at, engine_options=options, assert_current=self.assert_current)
        return operation, value

    def load(self, operation):
        self.assert_current()
        operation = identity(operation)
        target = self.operations / operation
        header = contract.binding(repository_operation_header(target))
        if (header['operation_id'] != operation
                or any(header[key] != value for key, value in self.binding.items())):
            raise ValueError('repository_operation_node_runtime_or_source_changed')
        value = load_repository_operation(target, header)
        self.assert_current()
        return value

    def inspect(self, operation, *, bounded_worker=False):
        if type(bounded_worker) is not bool:raise ValueError('repository_inspection_execution_required')
        value = self.load(operation)
        if value['state'] != 'recorded_complete_replay_unverified':return self.summary(value)
        if bounded_worker:
            observed = inspect_repository_worker(self.operations / operation, value['binding'])
            self.assert_current()
            return observed
        profile = value['binding']['engine_profile']
        observed = inspect_repository_operation(value, **repository_engine_profile(profile), engine_profile=profile,
            approved_opa_hashes=frozenset(approved_opa_hashes('1.18.2')))
        self.assert_current()
        return observed

    @staticmethod
    def summary(value):
        result = {'binding': deepcopy(value['binding']), 'state': value['state'], **contract.AUTHORITY}
        if 'outcome' in value:result['outcome'] = deepcopy(value['outcome'])
        return result

    def status(self):
        rows = []
        for path in sorted(self.operations.iterdir()):
            try:
                value = self.inspect(path.name)
                rows.append({'operation_id': path.name, 'state': value['state'],
                    'execution': value.get('execution', value.get('outcome', {}).get('execution')),
                    'exit_code': value.get('exit_code', value.get('outcome', {}).get('exit_code'))})
            except (ValueError, OSError, KeyError, TypeError):
                rows.append({'operation_id': path.name, 'state': 'invalid_or_foreign_operation'})
        return rows


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 validation', allow_abbrev=False)
    sub = parser.add_subparsers(dest='operation', required=True)
    repository = sub.add_parser('repository', allow_abbrev=False)
    repository.add_argument('--at', required=True)
    repository.add_argument('--profile', required=True, choices=REPOSITORY_ENGINE_PROFILES)
    repository.add_argument('--source-worktree', type=Path,
        help='Explicit separate working data at this exact product revision; its programs are never executed.')
    repository.add_argument('--output', choices=('json', 'legacy'), default='json')
    inspect = sub.add_parser('repository-inspect', allow_abbrev=False)
    inspect.add_argument('--assessment', required=True)
    inspect.add_argument('--bounded-worker', action='store_true',
        help='Replay the retained operation in an isolated, resource-monitored product worker.')
    sub.add_parser('repository-status', allow_abbrev=False)
    args = parser.parse_args(arguments)
    context = RepositoryContext(instance_root, settings)
    if args.operation == 'repository-status':
        print(json.dumps({'operations': context.status(), **contract.AUTHORITY}, indent=2)); return 0
    if args.operation == 'repository-inspect':
        print(json.dumps(context.inspect(args.assessment, bounded_worker=args.bounded_worker), indent=2)); return 0
    operation, value = context.create(args.at, engine_profile=args.profile, source_worktree=args.source_worktree)
    if args.output == 'legacy':
        sys.stdout.write(value['outcome']['stdout']); sys.stderr.write(value['outcome']['stderr'])
    else:
        print(json.dumps({'assessment_id': operation, **context.summary(value)}, indent=2))
    return value['outcome']['exit_code']
