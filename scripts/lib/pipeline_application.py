"""Private declared platform-context and pipeline-evidence projections."""
import argparse
from copy import deepcopy
from datetime import timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import pipeline_evidence as projection
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import copy_file, hash_file, reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import DECLARED_PIPELINE_PROFILES, declared_pipeline_environment
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock
from lib.v2_boundary import safe_source

KINDS = ('context', 'pipeline', 'all')
MAX_RECORD = 4 * 1024**2
BUDGET = 2 * 1024**3
LIMITS = {'artifact': BUDGET, 'sbom': 256 * 1024**2, 'scan': 16 * 1024**2, 'signature': 16 * 1024**2}
OUTPUTS = {'context': 'generated/evidence/platform-context.json', 'evidence': 'generated/evidence/pipeline-evidence.json', 'gate': 'generated/evidence/baseline-gate-result.json'}
FLAGS = {'official_acceptance': False, 'production_approval': False, 'risk_acceptance': False,
         'authority_transferred': False, 'operating_acceptance_inherited': False, 'published': False,
         'pipeline_execution_verified': False, 'branch_protection_verified': False,
         'waiver_approval_verified': False, 'signature_verified': False, 'native_metadata_rechecked': False}
DEFAULTS = {'artifact_path': 'dist/application-source.tar.gz', 'sbom_path': 'security/sbom.cyclonedx.json',
            'vulnerability_scan_path': 'security/vulnerability-scan.json', 'signature_path': '',
            'governance_mode': 'report-only', 'max_allowed_severity': 'high', 'release_candidate': False,
            'artifact_type': 'application-build-output', 'protected_branch': '', 'direct_push_allowed': '',
            'review_required': '', 'branch_protection_status': 'not_checked_by_platform_adapter'}


def wire(value): return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def parameters(value):
    try:
        Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-pipeline-parameters.schema.json'),
                             format_checker=FormatChecker()).validate(value)
    except ValidationError: raise ValueError('invalid_declared_pipeline_parameters') from None
    result = {**DEFAULTS, **value}
    for key in ('artifact_path', 'sbom_path', 'vulnerability_scan_path', 'signature_path'):
        if result[key]: result[key] = str(Path(result[key]))
    return result


def scan_severity(raw, fallback):
    # The old CLI falls back on absent/malformed JSON. Valid non-object JSON was
    # never supported and is an invalid operation, not a successful assessment.
    try: value = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeError): return fallback
    if not isinstance(value, dict): raise ValueError('invalid_declared_pipeline_scan_shape')
    return str(value.get('max_severity', fallback)).lower()


def render(manifest, data, kind, at):
    if kind not in KINDS: raise ValueError('unsupported_declared_pipeline_kind')
    facts = declared_pipeline_environment(manifest['profile'], manifest['environment'])
    context = deepcopy(facts['context']); files = {}
    if kind in ('context', 'all'): files[OUTPUTS['context']] = wire(context)
    if kind in ('pipeline', 'all'):
        for key, value in (manifest['context_override'] or {}).items():
            if value not in (None, ''): context[key] = value
        inputs = deepcopy(manifest['files'])
        if 'scan' in inputs:
            inputs['scan']['max_severity'] = scan_severity(safe_bytes(data / 'scan', limit=LIMITS['scan']), facts['scan_fallback'])
        evidence, gate = projection.project(context, manifest['profile'], manifest['parameters'], facts, inputs,
                                             explicit_time(at).astimezone(timezone.utc).isoformat())
        files[OUTPUTS['evidence']] = wire(evidence); files[OUTPUTS['gate']] = wire(gate)
    if any(len(raw) > MAX_RECORD for raw in files.values()): raise ValueError('declared_pipeline_output_budget')
    return files


class PipelineContext:
    def __init__(self, instance_root, settings):
        self.instance_root = Path(instance_root).resolve(); private_directory(self.instance_root / 'state')
        self.root = private_directory(self.instance_root / 'state/pipeline-evidence')
        self.inputs = private_directory(self.root / 'inputs'); self.artifacts = private_directory(self.root / 'artifacts')
        self.assessments = private_directory(self.root / 'assessments')
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
                        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())

    def assert_current(self):
        if (source_digest() != self.binding['runtime_source_digest']
                or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']):
            raise ValueError('declared_pipeline_product_changed')

    def verify_input(self, input_id):
        root = self.inputs / identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
            raise ValueError('private_declared_pipeline_input_required')
        manifest = strict_json(safe_bytes(root / 'manifest.json', limit=MAX_RECORD))
        if canonical_digest(manifest) != input_id: raise ValueError('declared_pipeline_input_changed')
        if set(manifest) != {'schema_version', 'profile', 'environment', 'parameters', 'context_override', 'files'} or manifest['schema_version'] != 1:
            raise ValueError('invalid_declared_pipeline_input_manifest')
        declared_pipeline_environment(manifest['profile'], manifest['environment'])
        if parameters(manifest['parameters']) != manifest['parameters']:
            raise ValueError('declared_pipeline_parameters_changed')
        override = manifest['context_override']
        if override is not None and not isinstance(override, dict): raise ValueError('invalid_declared_pipeline_override')
        if not isinstance(manifest['files'], dict) or set(manifest['files']) - set(LIMITS): raise ValueError('invalid_declared_pipeline_files')
        data = root / 'data'
        if data.is_symlink() or not data.is_dir() or data.stat().st_mode & 0o077: raise ValueError('private_declared_pipeline_data_required')
        if {p.name for p in root.iterdir()} != {'manifest.json', 'data'} or {p.name for p in data.iterdir()} != set(manifest['files']):
            raise ValueError('unexpected_declared_pipeline_input_members')
        total = 0
        for slot, row in manifest['files'].items():
            if set(row) != {'sha256', 'bytes'} or hash_file(data / slot, LIMITS[slot]) != row:
                raise ValueError('declared_pipeline_input_bytes_changed')
            total += row['bytes']
        if total > BUDGET: raise ValueError('declared_pipeline_input_budget')
        if 'signature' in manifest['files'] and not manifest['parameters']['signature_path']:
            raise ValueError('declared_pipeline_signature_label_required')
        return data, manifest

    def capture(self, profile, environment, metadata, override, sources):
        declared_pipeline_environment(profile, environment); params = parameters(metadata)
        if set(sources) - set(LIMITS): raise ValueError('unsupported_declared_pipeline_input_slot')
        if override is not None and not isinstance(override, dict): raise ValueError('invalid_declared_pipeline_override')
        if 'signature' in sources and not params['signature_path']:
            raise ValueError('declared_pipeline_signature_label_required')
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.inputs) as temporary:
            staged = Path(temporary) / 'snapshot'; staged.mkdir(mode=0o700)
            data = staged / 'data'; data.mkdir(mode=0o700); files = {}; total = 0
            for slot, path in sources.items():
                path = Path(path)
                if path.is_symlink(): raise ValueError('unsafe_declared_pipeline_source')
                if not path.is_file(): continue
                path = path.resolve(); row = hash_file(path, LIMITS[slot]); total += row['bytes']
                if total > BUDGET: raise ValueError('declared_pipeline_input_budget')
                reserve(self.root, total + MAX_RECORD)
                copy_file(path, data / slot, limit=LIMITS[slot], expected=row, budget=row['bytes']); files[slot] = row
            manifest = {'schema_version': 1, 'profile': profile, 'environment': environment,
                        'parameters': params, 'context_override': override, 'files': files}
            if len(wire(manifest)) > MAX_RECORD: raise ValueError('declared_pipeline_manifest_budget')
            atomic_json(staged / 'manifest.json', manifest); input_id = canonical_digest(manifest)
            self.assert_current()
            with write_lock(self.root):
                target = self.inputs / input_id
                if target.is_symlink(): raise ValueError('unsafe_declared_pipeline_input')
                if not target.exists(): os.rename(staged, target)
                actual, saved = self.verify_input(input_id)
                if saved != manifest: raise ValueError('immutable_declared_pipeline_input_conflict')
        return input_id, actual, saved

    def validate(self, value):
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-pipeline-assessment.schema.json'),
                                 format_checker=FormatChecker()).validate(value)
        except ValidationError: raise ValueError('invalid_declared_pipeline_assessment') from None
        if any(value.get(k) != v for k, v in self.binding.items()): raise ValueError('declared_pipeline_binding_changed')
        if len(wire(value)) > MAX_RECORD: raise ValueError('declared_pipeline_assessment_budget')
        explicit_time(value['assessed_at'])

    def create(self, kind, profile, environment, metadata, override, sources, at):
        explicit_time(at)
        if kind not in KINDS: raise ValueError('unsupported_declared_pipeline_kind')
        input_id, data, manifest = self.capture(profile, environment, metadata, override, sources)
        files = render(manifest, data, kind, at)
        value = {'schema_version': 1, 'kind': 'declared-pipeline-evidence', **self.binding,
                 'projection_kind': kind, 'profile': profile, 'input_id': input_id, 'assessed_at': at,
                 'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in files.items()},
                 'source_worktree_clean': self.clean, 'mode': 'report-only', 'evidence_trust': 'unverified', **FLAGS}
        self.validate(value); assessment_id = canonical_digest(value); reserve(self.root, sum(map(len, files.values())) + MAX_RECORD)
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.artifacts) as temporary:
            staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
            for name, raw in files.items():
                path = safe_source(staged, name); path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                path.write_bytes(raw); path.chmod(0o600)
            self.verify_input(input_id); self.assert_current()
            with write_lock(self.root):
                target = self.artifacts / assessment_id; record = self.assessments / (assessment_id + '.json')
                if target.is_symlink() or record.is_symlink(): raise ValueError('unsafe_declared_pipeline_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=MAX_RECORD)) != value: raise ValueError('immutable_declared_pipeline_assessment_conflict')
                else:
                    if target.exists(): raise ValueError('unrecorded_declared_pipeline_artifact')
                    os.rename(staged, target); atomic_json(record, value)
        return assessment_id, self.inspect(assessment_id)

    def inspect(self, assessment_id):
        assessment_id = identity(assessment_id); value = strict_json(safe_bytes(self.assessments / (assessment_id + '.json'), limit=MAX_RECORD))
        self.validate(value)
        if canonical_digest(value) != assessment_id: raise ValueError('declared_pipeline_assessment_identity_changed')
        data, manifest = self.verify_input(value['input_id'])
        if manifest['profile'] != value['profile']: raise ValueError('declared_pipeline_profile_changed')
        files = render(manifest, data, value['projection_kind'], value['assessed_at'])
        descriptors = {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in files.items()}
        if descriptors != value['files']: raise ValueError('declared_pipeline_output_manifest_changed')
        root = self.artifacts / assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077: raise ValueError('private_declared_pipeline_artifacts_required')
        expected_dirs = {str(parent) for name in files for parent in Path(name).parents if str(parent) != '.'}
        actual_dirs = set(); actual_files = set()
        for path in root.rglob('*'):
            if path.is_symlink(): raise ValueError('unsafe_declared_pipeline_artifact')
            name = path.relative_to(root).as_posix()
            if path.is_dir(): actual_dirs.add(name)
            else: actual_files.add(name)
        if actual_dirs != expected_dirs or actual_files != set(files): raise ValueError('unexpected_declared_pipeline_artifact_members')
        for name, raw in files.items():
            if safe_bytes(safe_source(root, name), limit=MAX_RECORD) != raw: raise ValueError('declared_pipeline_output_changed')
        self.assert_current()
        gate = json.loads(files[OUTPUTS['gate']]) if OUTPUTS['gate'] in files else None
        return {**value, 'assessment_id': assessment_id, 'data_directory': str(root), 'declared_gate_status': gate['status'] if gate else None}


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 pipeline-evidence', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create'); create.add_argument('--kind', choices=KINDS, required=True)
    create.add_argument('--profile', choices=DECLARED_PIPELINE_PROFILES, required=True)
    create.add_argument('--environment', type=Path, required=True); create.add_argument('--metadata', type=Path)
    create.add_argument('--context-override', type=Path); create.add_argument('--at', required=True)
    for slot in LIMITS: create.add_argument('--'+slot, type=Path)
    create.add_argument('--fail-on-findings', action='store_true')
    inspect = commands.add_parser('inspect'); inspect.add_argument('--assessment', required=True)
    args = parser.parse_args(arguments); app = PipelineContext(instance_root, settings)
    if args.command == 'inspect': print(json.dumps(app.inspect(args.assessment), sort_keys=True)); return 0
    environment = strict_json(operator_bytes(args.environment)); metadata = strict_json(operator_bytes(args.metadata)) if args.metadata else {}
    override = strict_json(operator_bytes(args.context_override)) if args.context_override else None
    _, value = app.create(args.kind, args.profile, environment, metadata, override,
                         {slot: getattr(args, slot) for slot in LIMITS if getattr(args, slot)}, args.at)
    print(json.dumps({**value, 'finding_exit_requested': args.fail_on_findings}, sort_keys=True))
    return 1 if args.fail_on_findings and value['declared_gate_status'] == 'fail' else 0
