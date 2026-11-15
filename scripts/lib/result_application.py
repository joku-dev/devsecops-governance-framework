"""Finite declared-result and private index application routes."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from jsonschema import ValidationError

from lib import ci_bundle_results as mappings
from lib import ci_bundle_storage as storage
from lib import result_index_application as indices
from lib.candidate_workspace import private_directory
from lib.portable.contracts import ROOT, repository_key
from lib.provider_ports import RESULT_EVENT_PROFILES
from lib.result_assessments import ResultContext, identity
from lib.result_snapshot_store import DOMAINS, ORIGINS, ResultLedger


def _run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 results', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    describe = commands.add_parser('describe')
    describe.add_argument('--bundle', type=Path, required=True)
    validate = commands.add_parser('validate-bundle')
    validate.add_argument('--bundle', type=Path, required=True)
    validate.add_argument('--sha256', required=True)
    validate.add_argument('--domain', choices=DOMAINS, required=True)
    verify = commands.add_parser('verify-bundle')
    verify.add_argument('--bundle', type=Path, required=True)
    verify.add_argument('--sha256', required=True)
    for command in (validate, verify):
        command.add_argument('--storage-budget-bytes', type=int, default=storage.DEFAULT_BUDGET)
    manual = commands.add_parser('manual')
    manual.add_argument('--summary', type=Path)
    for command in (verify, manual):
        command.add_argument('--metadata', type=Path, required=True)
        command.add_argument('--at', required=True)
    for name in ('inspect', 'intake', 'inspect-project'):
        command = commands.add_parser(name); command.add_argument('--id', required=True)
    records = commands.add_parser('records')
    records.add_argument('--origin', choices=ORIGINS, required=True)
    records.add_argument('--domain', choices=DOMAINS, required=True)
    records.add_argument('--realm')
    records.add_argument('--limit', type=int, default=100)
    records.add_argument('--offset', type=int, default=0)
    project = commands.add_parser('project')
    project.add_argument('--domain', choices=indices.DOMAINS, required=True)
    project.add_argument('--origin', choices=ORIGINS, required=True)
    project.add_argument('--scm', required=True)
    project.add_argument('--service', required=True)
    project.add_argument('--main-branch', required=True)
    project.add_argument('--event-profile', choices=RESULT_EVENT_PROFILES, required=True)
    project.add_argument('--at', required=True)
    args = parser.parse_args(arguments)
    context = ResultContext(instance_root, settings)
    if args.command == 'describe':
        value = storage.describe(args.bundle)
        print(json.dumps({key: value[key] for key in value if key != 'files'}, sort_keys=True))
        return 0
    if args.command == 'validate-bundle':
        with tempfile.TemporaryDirectory(prefix='.validation-', dir=context.root) as temporary:
            storage.copy_bundle(args.bundle, identity(args.sha256), Path(temporary) / 'copy',
                                budget=args.storage_budget_bytes)
            material = Path(temporary) / 'copy/material'; errors = []
            validator = mappings.validate_devsecops if args.domain == 'devsecops' else mappings.validate_architecture
            validator(material, errors, schema_root=ROOT)
        print(json.dumps({'validation': 'fail' if errors else 'pass', 'domain': args.domain,
            'diagnostics': errors, 'official_acceptance': False, 'provider_invoked': False}, sort_keys=True))
        return 2 if errors else 0
    if args.command in ('verify-bundle', 'manual'):
        assessment_id, value = context.create(metadata_path=args.metadata, at=args.at,
            bundle=args.bundle if args.command == 'verify-bundle' else None,
            sha256=args.sha256 if args.command == 'verify-bundle' else None,
            summary_path=args.summary if args.command == 'manual' else None,
            budget=args.storage_budget_bytes if args.command == 'verify-bundle' else storage.DEFAULT_BUDGET)
        print(json.dumps({'assessment_id': assessment_id, 'input_id': value['input_id'],
            'repository_key': repository_key(value['repository']), 'input_origin': value['input_origin'],
            'domains': sorted(value['snapshots']), 'mode': 'report-only', 'evidence_trust': 'unverified',
            'official_acceptance': False, 'provider_invoked': False}, sort_keys=True))
        return 0
    if args.command in ('inspect', 'intake'):
        value = context.load(args.id)
        if args.command == 'inspect':
            print(json.dumps({'assessment_id': args.id, 'assessment': value,
                'raw_sources_reverified': True, 'native_metadata_rechecked_now': False}, sort_keys=True))
        else:
            with closing(ResultLedger(private_directory(context.root / 'ledger'))) as ledger:
                value = ledger.admit(value['repository'], value['snapshots'], origin=value['input_origin'],
                                     assessment_id=args.id, at=value['assessed_at'])
            print(json.dumps(value, sort_keys=True))
        return 0
    if args.command == 'records':
        with closing(ResultLedger(private_directory(context.root / 'ledger'))) as ledger:
            value = ledger.records(origin=args.origin, domain=args.domain, limit=args.limit,
                                   offset=args.offset, realm=identity(args.realm) if args.realm else None)
        print(json.dumps(value, sort_keys=True))
        return 0
    if args.command == 'project':
        projection_id, value = indices.persist(context, settings, domain=args.domain, origin=args.origin,
            realm=indices.realm_key(args.scm, args.service), at=args.at, profile=args.event_profile,
            main_branch=args.main_branch)
        print(json.dumps({'projection_id': projection_id, 'domain': value['domain'],
            'origin': value['origin'], 'realm': value['realm'], 'source_count': len(value['membership']),
            'reported_summary': value['reported_index']['summary'], 'effective_summary': value['effective_index']['summary'],
            'published': False, 'official_acceptance': False}, sort_keys=True))
        return 0
    value = indices.inspect(context, settings, args.id)
    print(json.dumps({'projection_id': args.id, 'projection': value, 'raw_sources_reverified': True,
                     'native_metadata_rechecked_now': False}, sort_keys=True))
    return 0


def run(arguments, instance_root, settings):
    try:
        return _run(arguments, instance_root, settings)
    except ValidationError:
        raise ValueError('invalid_general_result') from None
    except sqlite3.Error:
        raise ValueError('result_ledger_state_unavailable') from None
    except zipfile.BadZipFile:
        raise ValueError('invalid_ci_result_archive') from None
