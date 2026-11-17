"""Instance-owned full measured assessments, separate from accepted result indexes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib.candidate_workspace import private_directory
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import (MEASURED_PROVIDERS, measured_import, measured_capture_live,
                                measured_export, measured_validate)


def assessment(result, *, provider, kind, at, origin, input_sha256, capture):
    timestamp = datetime.fromisoformat(at.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('explicit_measured_timezone_required')
    measured_validate(provider, kind, result)
    value = {'schema_version': 1, 'kind': 'v1-compatible-measured-assessment',
            'domain': kind, 'provider': provider, 'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(),
            'runtime_source_digest': source_digest(),
            'source_worktree_clean': not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip()),
            'assessed_at': at, 'input_origin': origin, 'input_manifest_sha256': input_sha256,
            'mode': 'report-only', 'evidence_trust': 'unverified', 'official_acceptance': False,
            'production_approval': False, 'risk_acceptance': False,
            'authority_transferred': False, 'capture': capture, 'report': result}
    validate(value)
    return value


def validate(value):
    try:
        Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-measured-assessment.schema.json'),
                             format_checker=FormatChecker()).validate(value)
    except ValidationError:
        raise ValueError('invalid_measured_assessment_wrapper') from None
    if value['runtime_source_digest'] != source_digest():
        raise ValueError('measured_assessment_runtime_changed')
    if value['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip():
        raise ValueError('measured_assessment_source_changed')
    measured_validate(value['provider'], value['domain'], value['report'])


def persist(value, root):
    # Validate the V1 wire report again before publishing the private receipt.
    validate(value)
    base = private_directory(root / 'assessments')
    identity = canonical_digest(value)
    target = base / (identity + '.json')
    if target.is_symlink():
        raise ValueError('unsafe_measured_assessment')
    if target.exists():
        if read_json(target) != value:
            raise ValueError('immutable_measured_assessment_conflict')
    else:
        atomic_json(target, value)
    return {'assessment_id': identity, 'domain': value['domain'], 'mode': 'report-only',
            'official_acceptance': False, 'evidence_trust': 'unverified',
            'input_manifest_sha256': value['input_manifest_sha256'],
            'summary': value['report'].get('summary', value['report'].get('counts', {}))}


def run(arguments, instance_root):
    parser = argparse.ArgumentParser(prog='axiom-v2 measured', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    local = commands.add_parser('verify-local')
    local.add_argument('--bundle', type=Path, required=True)
    local.add_argument('--sha256', required=True)
    live = commands.add_parser('capture')
    live.add_argument('--repository', required=True)
    live.add_argument('--run-id', required=True)
    live.add_argument('--credential', required=True, help='Private instance credential filename, never a token value')
    live.add_argument('--request-budget', type=int, default=500)
    for command in (local, live):
        command.add_argument('--provider', choices=MEASURED_PROVIDERS, required=True)
        command.add_argument('--kind', choices=('l1', 'containers'), required=True)
        command.add_argument('--at', required=True)
    args = parser.parse_args(arguments)
    timestamp = datetime.fromisoformat(args.at.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('explicit_measured_timezone_required')
    instance_root = Path(instance_root)
    if (instance_root / 'state').is_symlink():
        raise ValueError('unsafe_measured_state')
    root = private_directory(instance_root / 'state/measured')
    bundle_path = None
    if args.command == 'verify-local':
        result = measured_import(args.provider, args.bundle, args.sha256, args.kind)
        sha = args.sha256
        origin = 'operator_bundle'
        proof = {'native_metadata_rechecked': False, 'independent_attestation': False}
    else:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,95}\.json', args.credential):
            raise ValueError('invalid_measured_credential_name')
        credential = instance_root / 'credentials' / args.credential
        result, proof, captured = measured_capture_live(args.provider, args.repository, args.run_id,
            credential, budget=args.request_budget, kind=args.kind)
        proof['acquired_at'] = datetime.now(timezone.utc).isoformat()
        proof['independent_attestation'] = False
        raw_root = private_directory(root / 'raw')
        bundle_path = raw_root / secrets.token_hex(16)
        sha = measured_export(args.provider, captured, bundle_path, args.kind)
        origin = 'native_reader'
    value = assessment(result, provider=args.provider, kind=args.kind, at=args.at, origin=origin,
                       input_sha256=sha, capture=proof)
    receipt = persist(value, root)
    if bundle_path is not None:
        receipt['raw_bundle'] = str(bundle_path)
    print(json.dumps(receipt, sort_keys=True))
    return 0
