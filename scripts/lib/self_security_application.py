"""Private complete security reports with visible fact gaps and retained replay."""
import argparse
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys

import yaml

from lib import self_security
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import source_digest
from lib.provider_ports import (SELF_SECURITY_PROFILE, SecurityCollector, SecurityAPI,
    ReplaySecurityAPI, capture_security_source, security_clock,
    security_repository_default, security_request_paths)
from lib.release_validation_application import ReleaseValidationContext
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.validation_application import AUTHORITY, descriptors, write_files, retained_files

MAX_RECORD = 48 * 1024**2
MODEL = 'model/controls/governance-repository-security.yaml'
FILES = ('report.json', 'report.md', 'stdout.txt')
KIND = 'explicit-repository-self-security'
PENDING = {'schema_version', 'kind', 'profile', 'operation_id', 'node_id',
    'runtime_source_digest', 'source_revision', 'source_tree', 'repository',
    'provided_observation', 'requested_observed_at', 'resolved_observed_at',
    'source_root', 'model_sha256', 'input_files', 'fail_on_findings', *AUTHORITY}
OUTCOME = {'execution', 'exception_type', 'exit_code', 'release_assessment',
    'native_responses', 'output_files'}


def render(model_raw, observation, fail_on_findings):
    """Retain the original whole JSON/Markdown/stdout and optional finding exit."""
    model = yaml.safe_load(model_raw.decode('utf-8'))
    report = self_security.assess(model, observation)
    files = {'report.json': (json.dumps(report, indent=2) + '\n').encode('utf-8'),
        'report.md': self_security.render_markdown(report).encode('utf-8'),
        'stdout.txt': (f"Governance repository self-security: {report['overall_status']} "
            f"({report['summary']['pass']} pass, {report['summary']['fail']} fail)\n").encode('utf-8')}
    # The legacy codec permits nonfinite values; an uninspectable result remains
    # incomplete rather than being relabelled as a successfully retained report.
    json.dumps(report, allow_nan=False)
    return files, int(bool(fail_on_findings and report['overall_status'] != 'pass'))


class SecurityContext:
    def __init__(self, instance_root, settings, *, product_root=ROOT):
        self.product = Path(product_root).resolve()
        self.instance = private_directory(Path(instance_root)).resolve()
        self.root = private_directory(private_directory(self.instance / 'state') / 'self-security')
        self.operations = private_directory(self.root / 'operations')
        self.settings = settings
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
            'source_revision': git_read(self.product, 'rev-parse', 'HEAD').decode().strip(),
            'source_tree': git_read(self.product, 'rev-parse', 'HEAD^{tree}').decode().strip()}

    def assert_current(self):
        if (source_digest() != self.binding['runtime_source_digest'] or
                git_read(self.product, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']):
            raise ValueError('security_product_changed')

    def releases(self):
        return ReleaseValidationContext(self.instance, self.settings, product_root=self.product)

    def create(self, *, profile, repository, observation_raw=None, observed_at=None,
               model_raw=None, source_worktree=None, token_file=None, fail_on_findings=False):
        if profile != SELF_SECURITY_PROFILE:
            raise ValueError('unsupported_self_security_profile')
        provided = observation_raw is not None
        if not provided:
            security_request_paths(repository)
        if provided and (source_worktree is not None or token_file is not None):
            raise ValueError('provided_security_observation_has_no_native_acquisition')
        if not provided and source_worktree is None:
            raise ValueError('explicit_security_source_worktree_required')
        if type(fail_on_findings) is not bool:
            raise ValueError('invalid_security_finding_exit')
        if model_raw is None:
            model_raw = safe_bytes(self.product / MODEL)
        if not isinstance(model_raw, bytes) or len(model_raw) > 16 * 1024**2:
            raise ValueError('security_model_budget')
        if not provided and Path(source_worktree).is_symlink():
            raise ValueError('ordinary_security_source_required')
        source = None if provided else Path(source_worktree).resolve(strict=True)
        inputs = {'model.yaml': model_raw}
        if provided:
            if not isinstance(observation_raw, bytes) or len(observation_raw) > 16 * 1024**2:
                raise ValueError('security_observation_budget')
            inputs['observation.json'] = observation_raw
        else:
            inputs.update({'source/' + name: raw for name, raw in capture_security_source(source).items()})
        resolved_at = None if provided else observed_at or security_clock()
        if observed_at is not None and not isinstance(observed_at, str):
            raise ValueError('invalid_security_observation_time')
        reserve(self.root, 512 * 1024**2)
        self.assert_current()
        operation = secrets.token_hex(32)
        target = self.operations / operation
        target.mkdir(mode=0o700)
        value = {'schema_version': 1, 'kind': KIND, 'profile': profile,
            'operation_id': operation, **self.binding, 'repository': repository,
            'provided_observation': provided, 'requested_observed_at': observed_at,
            'resolved_observed_at': resolved_at, 'source_root': None if provided else str(source),
            'model_sha256': hashlib.sha256(model_raw).hexdigest(), 'input_files': descriptors(inputs),
            'fail_on_findings': fail_on_findings, **AUTHORITY}
        write_files(target / 'inputs', inputs)
        # Even an empty workflow surface is a retained explicit empty directory.
        if not provided:
            private_directory(target / 'inputs/source')
        requests = private_directory(target / 'requests')
        results = private_directory(target / 'responses')
        atomic_json(target / 'pending.json', value)
        api = None
        release_id = None
        try:
            if provided:
                observation = json.loads(observation_raw.decode('utf-8'))
            else:
                def intent(row): atomic_json(requests / f"{row['sequence']:02}.json", row)
                def response(row): atomic_json(results / f"{row['sequence']:02}.json", row)
                api = SecurityAPI(repository, token_file=token_file, on_intent=intent, on_result=response)
                def release():
                    nonlocal release_id
                    release_id, release_value = self.releases().create(security_clock(), source_worktree=source)
                    if release_value['execution'] != 'complete':
                        raise ValueError('security_release_verification_incomplete')
                    return release_value['report']
                observation = SecurityCollector(target / 'inputs/source', api, release).collect_live(repository, resolved_at)
            files, code = render(model_raw, observation, fail_on_findings)
            if any(len(raw) > 16 * 1024**2 for raw in files.values()):
                raise ValueError('security_report_byte_budget')
            write_files(target / 'outputs', files)
            outcome = {'execution': 'complete', 'exception_type': None, 'exit_code': code,
                'release_assessment': release_id, 'native_responses': [] if api is None else deepcopy(api.rows),
                'output_files': descriptors(files)}
        except Exception as error:
            outcome = {'execution': 'incomplete', 'exception_type': type(error).__name__, 'exit_code': 2,
                'release_assessment': release_id, 'native_responses': [] if api is None else deepcopy(api.rows),
                'output_files': {}}
        value.update(outcome)
        if len(json.dumps(value, allow_nan=False).encode()) > MAX_RECORD:
            raise ValueError('security_record_budget')
        atomic_json(target / 'native-results.json', value)
        self.assert_current()
        if not provided:
            current = {'source/' + name: raw for name, raw in capture_security_source(source).items()}
            if current != {name: raw for name, raw in inputs.items() if name.startswith('source/')}:
                raise ValueError('security_source_changed_during_acquisition')
        atomic_json(target / 'assessment.json', value)
        return operation, deepcopy(value)

    def inspect(self, operation):
        from lib.provider_ports import capture_retained_security_tree
        from lib.retained_security import security
        operation = identity(operation)
        target = self.operations / operation
        if target.is_symlink() or not target.is_dir() or target.stat().st_mode & 0o077:
            raise ValueError('private_security_operation_required')
        self.assert_current()
        tree = capture_retained_security_tree(target)
        value, _ = security(tree, self.binding, operation,
            lambda child: self.releases().inspect(child, with_replayed_report=True))
        self.assert_current()
        return value


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 self-security', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('assess', allow_abbrev=False)
    create.add_argument('--profile', choices=(SELF_SECURITY_PROFILE,), required=True)
    create.add_argument('--repository', default=security_repository_default())
    create.add_argument('--model', type=Path)
    create.add_argument('--observation', type=Path)
    create.add_argument('--observed-at')
    create.add_argument('--source-worktree', type=Path)
    create.add_argument('--token-file', type=Path)
    create.add_argument('--output-json', type=Path)
    create.add_argument('--output-md', type=Path)
    create.add_argument('--format', choices=('receipt', 'legacy'), default='receipt')
    create.add_argument('--fail-on-findings', action='store_true')
    inspect = commands.add_parser('inspect', allow_abbrev=False)
    inspect.add_argument('--id', required=True)
    args = parser.parse_args(arguments)
    context = SecurityContext(instance_root, settings)
    if args.command == 'inspect':
        value = context.inspect(args.id)
        print(json.dumps({'assessment': value, 'captured_facts_and_complete_reports_replayed': True,
            'native_metadata_rechecked': False, 'native_signature_verification_repeated': False,
            'independent_execution_authenticated': False}, indent=2))
        return 0
    operation, value = context.create(profile=args.profile, repository=args.repository,
        model_raw=None if args.model is None else safe_bytes(args.model),
        observation_raw=None if args.observation is None else safe_bytes(args.observation),
        observed_at=args.observed_at, source_worktree=args.source_worktree,
        token_file=args.token_file, fail_on_findings=args.fail_on_findings)
    if value['execution'] == 'complete':
        context.inspect(operation)
        output = context.operations / operation / 'outputs'
        # Explicit exports are local report writes; no SCM publication occurs.
        from lib.local_source_application import export_file
        for destination, name in ((args.output_json, 'report.json'), (args.output_md, 'report.md')):
            if destination is not None:
                resolved = destination.resolve()
                if (args.token_file is not None and resolved == args.token_file.resolve()
                        or args.source_worktree is not None and resolved.is_relative_to(args.source_worktree.resolve())):
                    raise ValueError('security_export_overlaps_source_or_credential')
                with redirect_stdout(io.StringIO()):
                    export_file(destination, safe_bytes(output / name), instance_root=instance_root, parents=True)
        if args.format == 'legacy':
            sys.stdout.write(safe_bytes(output / 'stdout.txt').decode('utf-8'))
        else:
            print(json.dumps({'assessment_id': operation, 'artifact_directory': str(output), **value}, indent=2))
    else:
        print(json.dumps({'assessment_id': operation, **value}, indent=2))
    return value['exit_code']
