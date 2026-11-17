"""Private source-signature assessments with retained exact Git input proofs."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import onboarding_readiness, source_snapshot_proof
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import INSPECTION_PROFILES, source_inspection_profile, source_inspection_facts, source_inspection_ci_paths
from lib.report_application import file_descriptors, MAX_OUTPUT, MAX_FILES
from lib.report_data import report_time
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock
from lib.v2_boundary import safe_source

KINDS = ('integration', 'onboarding', 'all')
MAX_RECORD = 4 * 1024**2
INTEGRATION = 'generated/reports/repository-integration.json'
ONBOARDING = 'generated/reports/repository-onboarding-readiness'


def checked_profile(profile):
    if (not isinstance(profile, dict) or profile.get('source_signature_only') is not True
            or profile != source_inspection_profile(profile.get('profile'))):
        raise ValueError('invalid_source_inspection_profile')
    return profile


def render_files(data, kind, *, profile, product_label, origin, repository_id, at, ci_paths=None):
    if kind not in KINDS: raise ValueError('unsupported_source_inspection_kind')
    checked_profile(profile)
    facts = source_inspection_facts(profile['profile'], data, product_label=product_label,
                                    target_label=origin, at=report_time(at), ci_paths=ci_paths)
    files = {}
    if kind in ('integration', 'all'):
        files[INTEGRATION] = (json.dumps(facts['integration'], indent=2, allow_nan=False) + '\n').encode()
    if kind in ('onboarding', 'all'):
        value = onboarding_readiness.assess_repository(Path(data), repository_id,
            ci_files=facts['onboarding_ci_files'], ci_text=facts['onboarding_ci_text'],
            integration=facts['integration'], at=report_time(at), target_label=origin)
        files[ONBOARDING + '.json'] = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
        files[ONBOARDING + '.md'] = onboarding_readiness.render_markdown(value).encode()
    return files


class SourceInspectionContext:
    def __init__(self, instance_root, settings):
        self.instance_root = Path(instance_root).resolve()
        private_directory(self.instance_root / 'state')
        self.root = private_directory(self.instance_root / 'state/source-inspections')
        self.inputs = private_directory(self.root / 'inputs')
        self.artifacts = private_directory(self.root / 'artifacts')
        self.assessments = private_directory(self.root / 'assessments')
        self.binding = {'node_id': settings['node_id'], 'product_label': settings['product'],
            'runtime_source_digest': source_digest(),
            'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())

    def assert_current(self):
        if (self.binding['runtime_source_digest'] != source_digest()
                or self.binding['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()):
            raise ValueError('source_inspection_product_changed')

    def validate(self, value):
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-source-inspection.schema.json'),
                                 format_checker=FormatChecker()).validate(value)
        except ValidationError:
            raise ValueError('invalid_source_inspection_assessment') from None
        if any(value.get(k) != expected for k, expected in self.binding.items()):
            raise ValueError('source_inspection_node_runtime_or_product_changed')
        checked_profile(value['source_inspection_profile']); explicit_time(value['assessed_at'])
        if not Path(value['source_repository_path']).is_absolute(): raise ValueError('source_inspection_absolute_origin_required')
        if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > MAX_RECORD:
            raise ValueError('source_inspection_record_budget')

    def input_data(self, input_id):
        root = self.inputs / identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
            raise ValueError('private_source_inspection_input_required')
        manifest = strict_json(safe_bytes(root / 'manifest.json', limit=source_snapshot_proof.MAX_MANIFEST))
        if canonical_digest(manifest) != input_id: raise ValueError('source_inspection_input_changed')
        source_snapshot_proof.verify(root / 'data', manifest)
        return root / 'data', manifest

    def capture_input(self, repository, revision):
        with tempfile.TemporaryDirectory(prefix='.incoming-input-', dir=self.inputs) as temporary:
            staged = Path(temporary) / 'snapshot'; staged.mkdir(mode=0o700)
            data = staged / 'data'; data.mkdir(mode=0o700)
            manifest = source_snapshot_proof.capture(repository, revision, data)
            input_id = canonical_digest(manifest)
            atomic_json(staged / 'manifest.json', manifest)
            self.assert_current()
            with write_lock(self.root):
                target = self.inputs / input_id
                if target.is_symlink(): raise ValueError('unsafe_source_inspection_input')
                if not target.exists(): os.rename(staged, target)
                actual, recorded = self.input_data(input_id)
                if recorded != manifest: raise ValueError('immutable_source_inspection_input_conflict')
        return input_id, actual, recorded

    def create(self, kind, repository, revision, repository_id, profile, at):
        checked_profile(profile); explicit_time(at)
        if kind not in KINDS: raise ValueError('unsupported_source_inspection_kind')
        if (not isinstance(repository_id, str) or not 1 <= len(repository_id) <= 512
                or any(ord(c) < 32 or ord(c) == 127 for c in repository_id)):
            raise ValueError('invalid_source_repository_id')
        origin = str(Path(repository).resolve())
        input_id, data, manifest = self.capture_input(repository, revision)
        ci_paths = source_inspection_ci_paths(profile['profile'], data)
        files = render_files(data, kind, profile=profile, product_label=self.binding['product_label'],
                             origin=origin, repository_id=repository_id, at=at, ci_paths=ci_paths)
        value = {'schema_version': 2, 'kind': 'consumer-source-signatures', **self.binding,
            'source_worktree_clean': self.clean, 'inspection_kind': kind, 'assessed_at': at,
            'source_inspection_profile': deepcopy(profile), 'ci_iteration_paths': ci_paths, 'input_id': input_id,
            'consumer_commit': manifest['commit'], 'consumer_tree': manifest['tree'],
            'source_repository_path': origin, 'declared_repository_id': repository_id,
            'files': file_descriptors(files), 'source_scope': 'retained-consumer-git-snapshot-v1',
            'working_tree_used': False, 'repository_identity_verified': False, 'evidence_trust': 'unverified', 'mode': 'report-only', 'official_acceptance': False,
            'production_approval': False, 'risk_acceptance': False, 'authority_transferred': False,
            'operating_acceptance_inherited': False, 'provider_invoked': False, 'published': False}
        self.validate(value); assessment_id = canonical_digest(value)
        reserve(self.root, sum(map(len, files.values())) + MAX_RECORD)
        with tempfile.TemporaryDirectory(prefix='.incoming-reports-', dir=self.artifacts) as temporary:
            staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
            for name, raw in files.items():
                path = safe_source(staged, name); path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                path.write_bytes(raw); path.chmod(0o600)
            self.input_data(input_id); self.assert_current()
            with write_lock(self.root):
                target = self.artifacts / assessment_id; record = self.assessments / (assessment_id + '.json')
                if target.is_symlink() or record.is_symlink(): raise ValueError('unsafe_source_inspection_store')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=MAX_RECORD)) != value: raise ValueError('immutable_source_inspection_record_conflict')
                    self.inspect(assessment_id)
                elif target.exists(): raise ValueError('incomplete_source_inspection_requires_recovery')
                else:
                    os.rename(staged, target); atomic_json(record, value)
        return assessment_id, deepcopy(value)

    def inspect(self, assessment_id):
        assessment_id = identity(assessment_id)
        value = strict_json(safe_bytes(self.assessments / (assessment_id + '.json'), limit=MAX_RECORD))
        if canonical_digest(value) != assessment_id: raise ValueError('source_inspection_record_changed')
        self.validate(value)
        data, manifest = self.input_data(value['input_id'])
        if manifest['commit'] != value['consumer_commit'] or manifest['tree'] != value['consumer_tree']:
            raise ValueError('source_inspection_commit_binding_changed')
        files = render_files(data, value['inspection_kind'], profile=value['source_inspection_profile'],
            product_label=value['product_label'], origin=value['source_repository_path'],
            repository_id=value['declared_repository_id'], at=value['assessed_at'], ci_paths=value['ci_iteration_paths'])
        if file_descriptors(files) != value['files']: raise ValueError('source_inspection_reports_differ')
        root = self.artifacts / assessment_id
        if root.is_symlink() or not root.is_dir(): raise ValueError('unsafe_source_inspection_artifact')
        actual = set()
        for path in root.rglob('*'):
            if path.is_symlink(): raise ValueError('unsafe_source_inspection_artifact')
            if not path.is_dir(): actual.add(path.relative_to(root).as_posix())
            if len(actual) > MAX_FILES: raise ValueError('source_inspection_output_budget')
        if actual != set(files): raise ValueError('source_inspection_output_members_changed')
        for name, raw in files.items():
            if safe_bytes(safe_source(root, name), limit=MAX_OUTPUT) != raw: raise ValueError('source_inspection_output_changed')
        self.assert_current()
        return value

    def legacy_exit(self, assessment_id):
        value = self.inspect(assessment_id); root = self.artifacts / assessment_id
        integration = strict_json(safe_bytes(root / INTEGRATION, limit=MAX_OUTPUT)) if INTEGRATION in value['files'] else None
        onboarding = strict_json(safe_bytes(root / (ONBOARDING + '.json'), limit=MAX_OUTPUT)) if ONBOARDING + '.json' in value['files'] else None
        return int(bool((integration and integration['status'] != 'pass') or
                        (onboarding and onboarding['status'] not in ('ready', 'ready_with_gaps'))))


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 source-inspection', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create', allow_abbrev=False)
    create.add_argument('--kind', choices=KINDS, required=True); create.add_argument('--repo', type=Path, required=True)
    create.add_argument('--revision', required=True); create.add_argument('--repository-id', required=True)
    create.add_argument('--profile', choices=INSPECTION_PROFILES, required=True); create.add_argument('--at', required=True)
    create.add_argument('--fail-on-findings', action='store_true')
    inspect = commands.add_parser('inspect', allow_abbrev=False); inspect.add_argument('--id', required=True)
    args = parser.parse_args(arguments); context = SourceInspectionContext(instance_root, settings)
    if args.command == 'inspect':
        value = context.inspect(args.id)
        print(json.dumps({'assessment_id': args.id, 'assessment': value,
            'retained_git_source_and_complete_outputs_reverified': True, 'native_metadata_rechecked': False}, sort_keys=True))
        return 0
    identifier, value = context.create(args.kind, args.repo, args.revision, args.repository_id,
                                      source_inspection_profile(args.profile), args.at)
    legacy_exit = context.legacy_exit(identifier)
    print(json.dumps({'assessment_id': identifier, 'artifact_directory': str(context.artifacts / identifier),
        'source_signature_only': True, 'original_finding_exit': legacy_exit,
        'finding_exit_requested': args.fail_on_findings, 'official_acceptance': False, 'published': False}, sort_keys=True))
    return legacy_exit if args.fail_on_findings else 0
