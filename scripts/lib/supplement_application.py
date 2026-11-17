"""Private, replayable assurance and staging projections with explicit source IDs.

Inner V1 reports preserve their original vocabulary. The surrounding receipt is
unverified diagnostic evidence; it cannot accept a source or authorize deployment.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib.assurance_projection import build_assurance
from lib.candidate_workspace import private_directory
from lib.consolidated_projection import build_consolidated
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.measured_application import validate as validate_measured
from lib.measurement_logic import decode_json
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import measured_supplement_profile
from lib.staging_projection import normalize_bundle

MAX_FILE = 16 * 1024 * 1024
MAX_BUNDLE = 128 * 1024 * 1024


def identity(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('invalid_supplement_source_id')
    return value


def safe_bytes(path, limit=MAX_FILE):
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('unsafe_supplement_source')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError('oversize_or_nonregular_supplement_source')
        with os.fdopen(descriptor, 'rb') as handle:
            descriptor = -1
            raw = handle.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > limit:
        raise ValueError('oversize_supplement_source')
    return raw


@contextmanager
def write_lock(root):
    descriptor = os.open(root / 'write.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise ValueError('private_supplement_lock_required')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('supplement_writer_busy') from None
        yield
    finally:
        os.close(descriptor)


def measured_source(instance_root, source_id):
    path = instance_root / 'state/measured/assessments' / (identity(source_id) + '.json')
    value = decode_json(safe_bytes(path))
    if canonical_digest(value) != source_id:
        raise ValueError('measured_source_identity_changed')
    validate_measured(value)
    if value['domain'] != 'l1':
        raise ValueError('measured_l1_source_required')
    return value


def logical_measured_path(measured):
    return (f"status/measured-l1-results/{measured['repository_id'].replace('/', '__')}/"
            f"run-{measured['run']['id']}-attempt-{measured['run']['attempt']}.json")


def typed_snapshots(value):
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'snapshots'}
            or value['schema_version'] != 1 or not isinstance(value['snapshots'], list)
            or len(value['snapshots']) > 64):
        raise ValueError('invalid_supplement_typed_bundle')
    validator = Draft202012Validator(read_json(ROOT / 'schemas/typed-evidence-result.schema.json'),
                                     format_checker=FormatChecker())
    snapshots = []
    for row in value['snapshots']:
        if not isinstance(row, dict) or set(row) != {'snapshot', 'source_file'}:
            raise ValueError('invalid_supplement_typed_row')
        path = row['source_file']
        if (not isinstance(path, str) or not path.startswith('status/typed-evidence-results/')
                or not path.endswith('.json') or '\\' in path or ':' in path
                or any(part in ('', '.', '..') for part in path.split('/'))):
            raise ValueError('invalid_supplement_typed_source_label')
        validator.validate(row['snapshot'])
        item = deepcopy(row['snapshot'])
        item['_source_file'] = path
        snapshots.append(item)
    return snapshots


def bundle_snapshot(path):
    path = Path(path).absolute()
    if (not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,127}', path.name)
            or any(part.is_symlink() for part in (path, *path.parents)) or not path.is_dir()):
        raise ValueError('unsafe_staging_bundle')
    files = {}
    total = 0
    for child in sorted(path.iterdir()):
        if len(files) >= 128 or not re.fullmatch('[A-Za-z0-9._-]+', child.name):
            raise ValueError('invalid_staging_bundle_member')
        raw = safe_bytes(child)
        total += len(raw)
        if total > MAX_BUNDLE:
            raise ValueError('oversize_staging_bundle')
        files[child.name] = raw
    return path.name, files


def bundle_manifest(name, files):
    return {'bundle_name': name, 'files': {key: {'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw)} for key, raw in sorted(files.items())}}


def staging_report(name, files, measured, profile, commit, at):
    # Parse the two decision-bearing JSON documents before the V1 projection so
    # duplicate keys cannot hide a different subject or approval.
    for filename in ('deployment-receipt.json', 'deployment-approval.json'):
        if filename not in files:
            raise ValueError('incomplete_staging_bundle')
        decode_json(files[filename])
    with tempfile.TemporaryDirectory(prefix='axiom-staging-') as directory:
        bundle = Path(directory) / name
        bundle.mkdir(mode=0o700)
        for filename, raw in files.items():
            target = bundle / filename
            target.write_bytes(raw)
            target.chmod(0o600)
        return normalize_bundle(bundle, root=ROOT, measured=measured,
            repository=profile['repository'], baseline=profile['baseline'],
            evidence_repository_commit=commit, verified_at=at)


def validate(value):
    try:
        Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-supplement.schema.json'),
                             format_checker=FormatChecker()).validate(value)
    except ValidationError:
        raise ValueError('invalid_supplement_wrapper') from None
    # Atomic storage uses this encoding. Reject a receipt that its own bounded
    # reader could not load (for example, amplified escaping in a typed bundle).
    if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > MAX_FILE:
        raise ValueError('oversize_supplement_receipt')
    if (value['runtime_source_digest'] != source_digest()
            or value['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()):
        raise ValueError('supplement_runtime_or_source_changed')


def replay(value, instance_root, settings):
    validate(value)
    if value['node_id'] != settings['node_id']:
        raise ValueError('supplement_foreign_node')
    source = measured_source(instance_root, value['inputs']['measured_id'])
    if value['provider'] != source['provider']:
        raise ValueError('supplement_provider_changed')
    measured = source['report']
    profile = measured_supplement_profile(source['provider'], measured)
    domain = value['domain']
    if domain == 'assurance':
        raw = value['inputs']['typed_bundle_raw']
        sha = value['inputs']['typed_bundle_sha256']
        if raw is None:
            if sha is not None or value['inputs']['typed_bundle'] != {'schema_version': 1, 'snapshots': []}:
                raise ValueError('typed_bundle_binding_changed')
        elif (hashlib.sha256(raw.encode('utf-8')).hexdigest() != sha
                or decode_json(raw.encode('utf-8')) != value['inputs']['typed_bundle']):
            raise ValueError('typed_bundle_binding_changed')
        expected = build_assurance(measured, typed_snapshots(value['inputs']['typed_bundle']),
            root=ROOT, measured_source_file=logical_measured_path(measured), verified_at=value['assessed_at'])
    elif domain == 'staging':
        manifest = value['inputs']['bundle_manifest']
        raw_root = instance_root / 'state/supplements/raw' / canonical_digest(manifest)
        name, files = bundle_snapshot(raw_root / manifest['bundle_name'])
        if bundle_manifest(name, files) != manifest:
            raise ValueError('staging_raw_bundle_changed')
        expected = staging_report(name, files, measured, profile,
            value['inputs']['evidence_repository_commit'], value['assessed_at'])
    else:
        staging = load(instance_root, value['inputs']['staging_id'], settings, expected_domain='staging')
        if staging['domain'] != 'staging' or staging['inputs']['measured_id'] != value['inputs']['measured_id']:
            raise ValueError('exact_staging_source_required')
        expected = build_consolidated(measured, staging['report'], root=ROOT,
            profile=profile['consolidated_profile'], measured_source_file=logical_measured_path(measured),
            staging_source_file=staging['report']['source_file'])
    if expected != value['report']:
        raise ValueError('supplement_report_differs_from_exact_sources')
    return value


def load(instance_root, supplement_id, settings, *, expected_domain=None):
    path = instance_root / 'state/supplements/assessments' / (identity(supplement_id) + '.json')
    value = decode_json(safe_bytes(path))
    if canonical_digest(value) != supplement_id:
        raise ValueError('supplement_identity_changed')
    if expected_domain is not None and value.get('domain') != expected_domain:
        raise ValueError('exact_staging_source_required')
    # Check dependency domain before following sources, preventing cyclic joins.
    return replay(value, instance_root, settings)


def _run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 supplement', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    assurance = commands.add_parser('assurance')
    assurance.add_argument('--typed-bundle', type=Path)
    assurance.add_argument('--sha256')
    staging = commands.add_parser('staging')
    staging.add_argument('--bundle', type=Path, required=True)
    staging.add_argument('--evidence-repository-commit', required=True)
    consolidated = commands.add_parser('consolidate')
    consolidated.add_argument('--staging', required=True)
    for command in (assurance, staging, consolidated):
        command.add_argument('--measured', required=True)
        command.add_argument('--at', required=True)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--id', required=True)
    args = parser.parse_args(arguments)
    instance_root = Path(instance_root)
    private_directory(instance_root / 'state')
    root = private_directory(instance_root / 'state/supplements')
    if args.command == 'inspect':
        value = load(instance_root, args.id, settings)
        print(json.dumps(value, sort_keys=True))
        return 0
    at = datetime.fromisoformat(args.at.replace('Z', '+00:00'))
    if at.tzinfo is None:
        raise ValueError('explicit_supplement_timezone_required')
    source = measured_source(instance_root, args.measured)
    profile = measured_supplement_profile(source['provider'], source['report'])
    inputs = {'measured_id': args.measured}
    raw_bundle = None
    if args.command == 'assurance':
        if bool(args.typed_bundle) != bool(args.sha256):
            raise ValueError('typed_bundle_and_digest_required_together')
        raw = safe_bytes(args.typed_bundle, 4 * 1024 * 1024) if args.typed_bundle else None
        if raw is not None and hashlib.sha256(raw).hexdigest() != identity(args.sha256):
            raise ValueError('supplement_input_digest_changed')
        typed = decode_json(raw) if raw is not None else {'schema_version': 1, 'snapshots': []}
        inputs['typed_bundle'] = typed
        inputs['typed_bundle_raw'] = raw.decode('utf-8') if raw is not None else None
        inputs['typed_bundle_sha256'] = args.sha256
        report = build_assurance(source['report'], typed_snapshots(typed), root=ROOT,
            measured_source_file=logical_measured_path(source['report']), verified_at=args.at)
        domain = 'assurance'
    elif args.command == 'staging':
        name, files = bundle_snapshot(args.bundle)
        inputs['bundle_manifest'] = bundle_manifest(name, files)
        inputs['evidence_repository_commit'] = args.evidence_repository_commit
        report = staging_report(name, files, source['report'], profile, args.evidence_repository_commit, args.at)
        raw_bundle = name, files
        domain = 'staging'
    else:
        supplement = load(instance_root, args.staging, settings, expected_domain='staging')
        if supplement['domain'] != 'staging' or supplement['inputs']['measured_id'] != args.measured:
            raise ValueError('exact_staging_source_required')
        inputs['staging_id'] = args.staging
        report = build_consolidated(source['report'], supplement['report'], root=ROOT,
            profile=profile['consolidated_profile'], measured_source_file=logical_measured_path(source['report']),
            staging_source_file=supplement['report']['source_file'])
        domain = 'consolidated'
    value = {'schema_version': 1, 'kind': 'v1-compatible-supplement', 'domain': domain,
        'node_id': settings['node_id'], 'provider': source['provider'],
        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(),
        'runtime_source_digest': source_digest(),
        'source_worktree_clean': not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip()),
        'assessed_at': args.at, 'inputs': inputs, 'report': report, 'mode': 'report-only',
        'evidence_trust': 'unverified', 'reported_trust_only': True, 'official_acceptance': False,
        'production_approval': False, 'risk_acceptance': False, 'authority_transferred': False}
    try:
        validate(value)
        with write_lock(root):
            if raw_bundle:
                name, files = raw_bundle
                raw_root = private_directory(root / 'raw')
                base = raw_root / canonical_digest(inputs['bundle_manifest'])
                if base.is_symlink():
                    raise ValueError('unsafe_staging_raw_store')
                if not base.exists():
                    temporary = Path(tempfile.mkdtemp(dir=raw_root))
                    try:
                        (temporary / name).mkdir(mode=0o700)
                        for filename, raw in files.items():
                            target = temporary / name / filename
                            target.write_bytes(raw)
                            target.chmod(0o600)
                        os.rename(temporary, base)
                    finally:
                        if temporary.exists():
                            import shutil
                            shutil.rmtree(temporary)
            replay(value, instance_root, settings)
            assessments = private_directory(root / 'assessments')
            supplement_id = canonical_digest(value)
            target = assessments / (supplement_id + '.json')
            if target.exists() or target.is_symlink():
                if decode_json(safe_bytes(target)) != value:
                    raise ValueError('immutable_supplement_conflict')
            else:
                atomic_json(target, value)
    except ValidationError:
        raise ValueError('invalid_supplement_evidence') from None
    print(json.dumps({'supplement_id': supplement_id, 'domain': domain, 'mode': 'report-only',
        'evidence_trust': 'unverified', 'official_acceptance': False, 'summary': report.get('summary', report.get('tests', {}))}, sort_keys=True))
    return 0


def run(arguments, instance_root, settings):
    try:
        return _run(arguments, instance_root, settings)
    except ValidationError:
        raise ValueError('invalid_supplement_evidence') from None
