"""Private, replayable physical source observations with no SCM identity claim."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import onboarding_readiness
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import (local_source_profile, capture_local_source, validate_local_source,
    local_source_facts, LOCAL_SOURCE_MAX_FILE, LOCAL_SOURCE_MAX_TEXT, LOCAL_SOURCE_MAX_FACTS)
from lib.report_application import file_descriptors, MAX_OUTPUT
from lib.report_data import report_time
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.source_inspection_application import KINDS, INTEGRATION, ONBOARDING, MAX_RECORD
from lib.supplement_application import write_lock


def checked_profile(value):
    if not isinstance(value, dict) or value != local_source_profile(value.get('profile')):
        raise ValueError('invalid_local_source_profile')
    return value


def render_files(observation, texts, *, product_label, origin, repository_id, at):
    kind = observation['inspection_kind']
    facts = local_source_facts(observation, texts, product_label=product_label,
                              target_label=origin, at=report_time(at))
    files = {}
    if kind in ('integration', 'all'):
        files[INTEGRATION] = (json.dumps(facts['integration'], indent=2, allow_nan=False) + '\n').encode()
    if kind in ('onboarding', 'all'):
        report = onboarding_readiness.assess_surface(repository_id, surface=facts['surface'],
            ci_files=facts['onboarding_ci_files'], ci_text=facts['onboarding_ci_text'],
            integration=facts['integration'], at=report_time(at), target_label=origin)
        files[ONBOARDING + '.json'] = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
        files[ONBOARDING + '.md'] = onboarding_readiness.render_markdown(report).encode()
    return files


def private_members(root, expected):
    """Exact flat regular-file membership; check permissions before any read."""
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError('private_local_source_directory_required')
    actual = set()
    for path in root.iterdir():
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise ValueError('private_local_source_file_required')
        actual.add(path.name)
        if len(actual) > 100000: raise ValueError('local_source_member_budget')
    if actual != set(expected): raise ValueError('local_source_members_changed')


class LocalSourceInspectionContext:
    def __init__(self, instance_root, settings):
        self.instance_root = Path(instance_root).resolve()
        private_directory(self.instance_root / 'state')
        self.root = private_directory(self.instance_root / 'state/local-source-inspections')
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
            raise ValueError('local_source_product_changed')

    def validate(self, value):
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-local-source-inspection.schema.json'),
                                 format_checker=FormatChecker()).validate(value)
        except ValidationError:
            raise ValueError('invalid_local_source_assessment') from None
        if any(value.get(k) != v for k, v in self.binding.items()):
            raise ValueError('local_source_node_runtime_or_product_changed')
        checked_profile(value['source_inspection_profile']); explicit_time(value['assessed_at'])
        if value['inspection_kind'] != 'integration' and value['declared_repository_id'] is None:
            raise ValueError('local_source_repository_id_required')
        if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > MAX_RECORD:
            raise ValueError('local_source_record_budget')

    def input_data(self, input_id):
        root = self.inputs / identity(input_id)
        # Validate the directory itself before following its children.
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
            raise ValueError('private_local_source_directory_required')
        if {p.name for p in root.iterdir()} != {'facts.json', 'blobs'}:
            raise ValueError('local_source_members_changed')
        facts = root / 'facts.json'
        if facts.is_symlink() or not facts.is_file() or facts.stat().st_mode & 0o077:
            raise ValueError('private_local_source_file_required')
        observation = strict_json(safe_bytes(facts, limit=LOCAL_SOURCE_MAX_FACTS))
        if canonical_digest(observation) != input_id: raise ValueError('local_source_input_changed')
        # Check the closed structure before using any declared digest as a path.
        rows = observation.get('text_files')
        if not isinstance(rows, dict) or len(rows) > 100000:
            raise ValueError('invalid_local_source_text_members')
        digests = set(); total = 0
        for row in rows.values():
            if not isinstance(row, dict) or set(row) != {'sha256', 'bytes'}:
                raise ValueError('invalid_local_source_text_member')
            digests.add(identity(row['sha256']))
            if type(row['bytes']) is not int or not 0 <= row['bytes'] <= LOCAL_SOURCE_MAX_FILE:
                raise ValueError('local_source_text_budget')
            total += row['bytes']
            if total > LOCAL_SOURCE_MAX_TEXT: raise ValueError('local_source_text_budget')
        blobs = root / 'blobs'; private_members(blobs, digests)
        raw = {digest: safe_bytes(blobs / digest, limit=LOCAL_SOURCE_MAX_FILE) for digest in digests}
        texts = {name: raw[row['sha256']] for name, row in rows.items()}
        validate_local_source(observation, texts)
        return observation, texts

    def create(self, kind, repository, repository_id, profile, at=None):
        checked_profile(profile)
        if kind not in KINDS: raise ValueError('unsupported_source_inspection_kind')
        if repository_id is not None and (not isinstance(repository_id, str) or not 1 <= len(repository_id) <= 512
                or any(ord(c) < 32 or ord(c) == 127 for c in repository_id)):
            raise ValueError('invalid_source_repository_id')
        if kind != 'integration' and repository_id is None: raise ValueError('local_source_repository_id_required')
        origin = Path(repository).expanduser().absolute()
        if any(p.is_symlink() for p in (origin, *origin.parents)):
            raise ValueError('local_source_root_symlink_forbidden')
        origin = origin.resolve()
        if self.instance_root.is_relative_to(origin.resolve()):
            raise ValueError('local_source_state_must_be_outside_target')
        clock = 'explicit_operator_time' if at is not None else 'runtime_clock'
        if at is None: at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        explicit_time(at)
        reserve(self.root, LOCAL_SOURCE_MAX_TEXT + LOCAL_SOURCE_MAX_FACTS + MAX_RECORD)
        observation, texts = capture_local_source(origin, kind, profile['profile'])
        persisted = (json.dumps(observation, sort_keys=True, indent=2) + '\n').encode()
        if len(persisted) > LOCAL_SOURCE_MAX_FACTS: raise ValueError('local_source_facts_budget')
        input_id = canonical_digest(observation)
        files = render_files(observation, texts, product_label=self.binding['product_label'],
                             origin=str(origin), repository_id=repository_id, at=at)
        value = {'schema_version': 1, 'kind': 'local-source-signatures', **self.binding,
            'source_worktree_clean': self.clean, 'inspection_kind': kind, 'assessed_at': at,
            'clock_provenance': clock, 'source_inspection_profile': deepcopy(profile), 'input_id': input_id,
            'source_repository_path': str(origin), 'declared_repository_id': repository_id,
            'files': file_descriptors(files), 'source_scope': 'retained-local-source-observation-v1',
            'source_origin': 'local_filesystem_observation', 'content_commit_verified': False,
            'working_tree_used': True, 'repository_identity_verified': False, 'evidence_trust': 'unverified',
            'mode': 'report-only', 'official_acceptance': False, 'production_approval': False,
            'risk_acceptance': False, 'authority_transferred': False, 'operating_acceptance_inherited': False,
            'provider_invoked': False, 'published': False}
        self.validate(value); assessment_id = canonical_digest(value)
        reserve(self.root, sum(map(len, files.values())) + len(persisted) + sum(map(len, texts.values())))
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.root) as temporary:
            incoming = Path(temporary); staged = incoming / 'input'; staged.mkdir(mode=0o700)
            (staged / 'facts.json').write_bytes(persisted); (staged / 'facts.json').chmod(0o600)
            blobs = staged / 'blobs'; blobs.mkdir(mode=0o700)
            for name, raw in texts.items():
                path = blobs / observation['text_files'][name]['sha256']
                path.write_bytes(raw); path.chmod(0o600)
            reports = incoming / 'reports'; reports.mkdir(mode=0o700)
            # Artifacts use a flat private store; logical V1 paths stay in the manifest.
            for name, raw in files.items():
                path = reports / Path(name).name; path.write_bytes(raw); path.chmod(0o600)
            # This is a second bounded observation, not an atomic filesystem snapshot.
            current, current_texts = capture_local_source(origin, kind, profile['profile'])
            if current != observation or current_texts != texts: raise ValueError('local_source_changed_before_commit')
            self.assert_current()
            with write_lock(self.root):
                target = self.inputs / input_id; outputs = self.artifacts / assessment_id
                record = self.assessments / (assessment_id + '.json')
                if any(p.is_symlink() for p in (target, outputs, record)): raise ValueError('unsafe_local_source_store')
                if not target.exists(): os.rename(staged, target)
                if self.input_data(input_id) != (observation, texts): raise ValueError('immutable_local_source_input_conflict')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=MAX_RECORD)) != value:
                        raise ValueError('immutable_local_source_record_conflict')
                    self.inspect(assessment_id)
                elif outputs.exists(): raise ValueError('incomplete_local_source_requires_recovery')
                else:
                    os.rename(reports, outputs); atomic_json(record, value)
        return assessment_id, deepcopy(value)

    def inspect(self, assessment_id):
        assessment_id = identity(assessment_id); record = self.assessments / (assessment_id + '.json')
        if record.is_symlink() or not record.is_file() or record.stat().st_mode & 0o077:
            raise ValueError('private_local_source_file_required')
        value = strict_json(safe_bytes(record, limit=MAX_RECORD))
        if canonical_digest(value) != assessment_id: raise ValueError('local_source_record_changed')
        self.validate(value)
        observation, texts = self.input_data(value['input_id'])
        if (observation['profile'] != value['source_inspection_profile']['profile']
                or observation['inspection_kind'] != value['inspection_kind']):
            raise ValueError('local_source_input_profile_or_kind_changed')
        files = render_files(observation, texts, product_label=value['product_label'],
            origin=value['source_repository_path'], repository_id=value['declared_repository_id'], at=value['assessed_at'])
        if file_descriptors(files) != value['files']: raise ValueError('local_source_reports_differ')
        root = self.artifacts / assessment_id
        private_members(root, [Path(name).name for name in files])
        for name, raw in files.items():
            if safe_bytes(root / Path(name).name, limit=MAX_OUTPUT) != raw: raise ValueError('local_source_output_changed')
        self.assert_current()
        return value

    def legacy_exit(self, assessment_id):
        value = self.inspect(assessment_id); root = self.artifacts / assessment_id
        reports = [strict_json(safe_bytes(root / Path(name).name, limit=MAX_OUTPUT))
                   for name in value['files'] if name.endswith('.json')]
        return int(any(report['status'] not in ('pass', 'ready', 'ready_with_gaps') for report in reports))


def export_file(destination, raw, *, instance_root, parents):
    """An explicitly requested local report export, never a publisher action."""
    path = Path(destination).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_local_source_export')
    path = path.resolve()
    if (path.is_relative_to(Path(instance_root).resolve()) or path.is_relative_to(ROOT.resolve())):
        raise ValueError('unsafe_local_source_export')
    if parents: path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() and not path.is_file(): raise ValueError('unsafe_local_source_export')
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temporary, 0o600); os.replace(temporary, path)
    finally: Path(temporary).unlink(missing_ok=True)
    print(f'Wrote {path}')


def run(args, instance_root, settings):
    if args.command == 'observe':
        # Reject self-observation before creating this family's private state.
        if Path(instance_root).resolve().is_relative_to(args.repo.expanduser().resolve()):
            raise ValueError('local_source_state_must_be_outside_target')
        if args.format == 'legacy' and args.kind == 'all': raise ValueError('legacy_output_requires_single_kind')
        if args.kind == 'integration' and (args.output_json or args.output_md): raise ValueError('onboarding_output_options_require_onboarding')
        if args.kind != 'integration' and args.output_file: raise ValueError('integration_output_option_requires_integration')
        if any((args.output_file, args.output_json, args.output_md)) and args.format != 'legacy':
            raise ValueError('original_output_options_require_legacy_format')
    context = LocalSourceInspectionContext(instance_root, settings)
    if args.command == 'inspect-observation':
        value = context.inspect(args.id)
        print(json.dumps({'assessment_id': args.id, 'assessment': value,
            'retained_observation_and_complete_outputs_reverified': True,
            'live_directory_rechecked': False, 'content_commit_verified': False}, sort_keys=True))
        return 0
    identifier, value = context.create(args.kind, args.repo, args.repository_id,
                                      local_source_profile(args.profile), args.at)
    finding_exit = context.legacy_exit(identifier)
    if args.format == 'legacy':
        root = context.artifacts / identifier
        if args.kind == 'integration':
            raw = safe_bytes(root / Path(INTEGRATION).name, limit=MAX_OUTPUT)
            if args.output_file: export_file(args.output_file, raw, instance_root=instance_root, parents=False)
            else: print(raw.decode(), end='')
        else:
            raw = safe_bytes(root / (Path(ONBOARDING).name + '.json'), limit=MAX_OUTPUT)
            if args.output_json: export_file(args.output_json, raw, instance_root=instance_root, parents=True)
            else: print(raw.decode(), end='')
            if args.output_md:
                export_file(args.output_md, safe_bytes(root / (Path(ONBOARDING).name + '.md'), limit=MAX_OUTPUT),
                            instance_root=instance_root, parents=True)
    else:
        print(json.dumps({'assessment_id': identifier, 'artifact_directory': str(context.artifacts / identifier),
            'source_signature_only': True, 'working_tree_used': True, 'content_commit_verified': False,
            'original_finding_exit': finding_exit, 'finding_exit_requested': args.fail_on_findings,
            'official_acceptance': False, 'published': False}, sort_keys=True))
    return finding_exit if args.fail_on_findings else 0
