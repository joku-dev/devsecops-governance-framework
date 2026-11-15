"""Private full typed verification and explicitly admitted diagnostic results."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib.candidate_workspace import private_directory
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest, repository_key
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import TYPED_PROVIDERS, typed_import, typed_verify, typed_capture_live
from lib.supplement_application import safe_bytes, write_lock
from lib.typed_result_ledger import TypedLedger

DEFAULT_BUDGET = 2 * 1024**3


def identity(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('invalid_typed_assessment_id')
    return value


def validate(value, settings):
    try:
        Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-typed-assessment.schema.json'),
                             format_checker=FormatChecker()).validate(value)
    except ValidationError:
        raise ValueError('invalid_typed_assessment_wrapper') from None
    if (value['node_id'] != settings['node_id'] or value['runtime_source_digest'] != source_digest()
            or value['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()):
        raise ValueError('typed_node_runtime_or_source_changed')
    if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > 16 * 1024**2:
        raise ValueError('typed_assessment_record_limit')
    if value['verification']['execution']['provider'] != value['provider']:
        raise ValueError('typed_verification_provider_changed')
    if (value['input_origin'] == 'native_reader'
            and value['capture']['verified_at'] != value['assessed_at']):
        raise ValueError('typed_native_verification_time_changed')
    if (value['verification']['verified_archive_bytes'] + value['verification']['verified_material_bytes']
            > value['storage_budget_bytes']):
        raise ValueError('typed_verification_budget_changed')


def replay(value, root, settings):
    validate(value, settings)
    raw = root / 'raw' / value['input_manifest_sha256']
    normalized = typed_verify(value['provider'], raw, value['input_manifest_sha256'],
        value['assessed_at'], budget=value['storage_budget_bytes'])
    if normalized != value['verification']:
        raise ValueError('typed_assessment_differs_from_exact_sources')
    return value


def load(root, assessment_id, settings):
    path = root / 'assessments' / (identity(assessment_id) + '.json')
    value = json.loads(safe_bytes(path), object_pairs_hook=unique)
    if canonical_digest(value) != assessment_id:
        raise ValueError('typed_assessment_identity_changed')
    return replay(value, root, settings)


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_typed_assessment_key')
        result[key] = value
    return result


def _run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 typed', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    local = commands.add_parser('verify-local')
    local.add_argument('--bundle', type=Path, required=True)
    local.add_argument('--sha256', required=True)
    local.add_argument('--at', required=True)
    live = commands.add_parser('capture')
    live.add_argument('--repository', required=True)
    live.add_argument('--run-id', required=True)
    live.add_argument('--credential', required=True)
    live.add_argument('--request-budget', type=int, default=100)
    for command in (local, live):
        command.add_argument('--provider', choices=TYPED_PROVIDERS, required=True)
        command.add_argument('--storage-budget-bytes', type=int, default=DEFAULT_BUDGET)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--id', required=True)
    intake = commands.add_parser('intake')
    intake.add_argument('--id', required=True)
    index = commands.add_parser('index')
    index.add_argument('--limit', type=int, default=100)
    index.add_argument('--offset', type=int, default=0)
    args = parser.parse_args(arguments)
    instance_root = Path(instance_root)
    private_directory(instance_root / 'state')
    root = private_directory(instance_root / 'state/typed')
    if args.command == 'index':
        ledger = TypedLedger(private_directory(root / 'ledger'))
        try:
            projection = ledger.projection(limit=args.limit, offset=args.offset)
        finally:
            ledger.close()
        print(json.dumps(projection, sort_keys=True))
        return 0
    if args.command in ('inspect', 'intake'):
        value = load(root, args.id, settings)
        if args.command == 'inspect':
            print(json.dumps({'assessment_id': args.id, 'bytes_reverified_now': True,
                'native_metadata_rechecked_now': False, 'assessment': value}, sort_keys=True))
        else:
            ledger = TypedLedger(private_directory(root / 'ledger'))
            try:
                receipt = ledger.admit(value['verification']['repository'], value['verification']['snapshots'],
                    origin=value['input_origin'], assessment_id=args.id, at=value['assessed_at'])
            finally:
                ledger.close()
            print(json.dumps(receipt, sort_keys=True))
        return 0
    if not 0 < args.storage_budget_bytes <= 16 * 1024**3:
        raise ValueError('invalid_typed_storage_budget')
    if args.command == 'verify-local':
        if datetime.fromisoformat(args.at.replace('Z', '+00:00')).tzinfo is None:
            raise ValueError('explicit_typed_timezone_required')
        identity(args.sha256)
    else:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}\.json', args.credential):
            raise ValueError('invalid_typed_credential_name')
    raw_root = private_directory(root / 'raw')
    with tempfile.TemporaryDirectory(prefix='.incoming-', dir=raw_root) as directory:
        staged = Path(directory) / 'capture'
        if args.command == 'verify-local':
            sha = args.sha256
            normalized = typed_import(args.provider, args.bundle, sha, staged, args.at,
                budget=args.storage_budget_bytes)
            at, origin = args.at, 'operator_bundle'
            proof = {'native_metadata_rechecked': False, 'independent_attestation': False}
        else:
            normalized, sha, proof = typed_capture_live(args.provider, args.repository, args.run_id,
                instance_root / 'credentials' / args.credential, staged,
                requests=args.request_budget, budget=args.storage_budget_bytes)
            at, origin = proof['verified_at'], 'native_reader'
            proof['independent_attestation'] = False
        value = {'schema_version': 1, 'kind': 'v1-compatible-typed-verification',
            'node_id': settings['node_id'], 'provider': args.provider,
            'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(),
            'runtime_source_digest': source_digest(),
            'source_worktree_clean': not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip()),
            'assessed_at': at, 'input_origin': origin, 'input_manifest_sha256': sha,
            'storage_budget_bytes': args.storage_budget_bytes,
            'mode': 'report-only', 'evidence_trust': 'unverified',
            'official_acceptance': False, 'production_approval': False,
            'risk_acceptance': False, 'authority_transferred': False,
            'capture': proof, 'verification': normalized}
        validate(value, settings)
        with write_lock(root):
            target = raw_root / identity(sha)
            if target.is_symlink():
                raise ValueError('unsafe_typed_raw_store')
            if not target.exists():
                os.rename(staged, target)
            replay(value, root, settings)
            assessments = private_directory(root / 'assessments')
            assessment_id = canonical_digest(value)
            path = assessments / (assessment_id + '.json')
            if path.exists() or path.is_symlink():
                if json.loads(safe_bytes(path), object_pairs_hook=unique) != value:
                    raise ValueError('immutable_typed_assessment_conflict')
            else:
                atomic_json(path, value)
    print(json.dumps({'assessment_id': assessment_id, 'repository_key': repository_key(normalized['repository']),
        'mode': 'report-only', 'input_origin': origin, 'official_acceptance': False,
        'evidence_trust': 'unverified', 'reported_initial_trust':
        {key: row['trust']['effective_level'] for key, row in normalized['snapshots'].items()}}, sort_keys=True))
    return 0


def run(arguments, instance_root, settings):
    try:
        return _run(arguments, instance_root, settings)
    except ValidationError:
        raise ValueError('invalid_typed_evidence') from None
    except sqlite3.Error:
        raise ValueError('typed_ledger_state_unavailable') from None
