"""Private, source-backed complete result indices; no public status publication."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile

from lib import results_projection
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.evidence_verification import project_trust, promote_effective_level
from lib.portable.contracts import ROOT, canonical_digest, endpoint, repository_key
from lib.provider_ports import result_index_profile
from lib.result_assessments import identity, strict_json
from lib.result_ledger import replay_key
from lib.result_snapshot_store import ResultLedger, explicit_time
from lib.supplement_application import safe_bytes, write_lock
from lib.typed_evidence_application import load as load_typed
from lib.typed_result_ledger import TypedLedger

MAX_PROJECT = 128 * 1024**2
MAX_RECORDS = 10000
DOMAINS = ('devsecops', 'architecture', 'typed')
FOLDERS = {'devsecops': 'results', 'architecture': 'architecture-results', 'typed': 'typed-evidence-results'}
INDEX_SCHEMAS = {'devsecops': 'governance-results-index.schema.json',
                 'architecture': 'architecture-results-index.schema.json',
                 'typed': 'typed-evidence-results-index.schema.json'}


def realm_key(provider, service):
    if not isinstance(provider, str) or not provider or len(provider) > 64:
        raise ValueError('invalid_result_scope_provider')
    return canonical_digest({'provider': provider, 'instance': endpoint(service)})


def source_rows(context, *, domain, origin, realm):
    rows = []; size = 0
    if domain == 'typed':
        root = private_directory(context.instance_root / 'state/typed')
        ledger = TypedLedger(private_directory(root / 'ledger'))
    else:
        ledger = ResultLedger(private_directory(context.root / 'ledger'))
    with closing(ledger):
        ledger.db.execute('BEGIN')
        offset = 0
        while True:
            if domain == 'typed':
                page = ledger.projection(limit=1000, offset=offset)
            else:
                page = ledger.records(origin=origin, domain=domain, realm=realm, limit=1000, offset=offset)
            for row in page['records']:
                descriptor = row['repository']
                if row['origin'] != origin or realm_key(descriptor['provider'], descriptor['instance']) != realm:
                    continue
                if repository_key(descriptor) != row['repository_key'] or descriptor['path'] != row['payload']['repository_id']:
                    raise ValueError('result_projection_native_subject_changed')
                size += len(json.dumps(row['payload']).encode())
                if len(rows) >= MAX_RECORDS or size > MAX_PROJECT:
                    raise ValueError('result_projection_source_limit')
                rows.append(row)
            offset += 1000
            if offset >= page['record_count']: break
    return sorted(rows, key=lambda row: (row['repository_key'], row['identity']))


def same_stored_payload(expected, stored):
    """Only the original ledger replay transformation may alter a source result."""
    expected = deepcopy(expected)
    if isinstance(expected.get('trust'), dict):
        observed = stored.get('trust')
        if not isinstance(observed, dict): raise ValueError('result_ledger_report_differs_from_source')
        checks = [check for check in observed.get('checks', []) if check.get('id') == 'replay_key_unique']
        if len(checks) != 1: raise ValueError('result_ledger_replay_check_changed')
        check = checks[0]
        if (check.get('result') not in ('pass', 'fail', 'not_evaluated')
                or check.get('finding_effect') != 'report_only'
                or check.get('evidence_refs') != ['trust.capture.source', 'trust.capture.subjects']
                or check.get('replay_key') != replay_key(expected['trust'])):
            raise ValueError('result_ledger_replay_check_changed')
        if (replay_key(expected['trust']) is None and check['result'] != 'not_evaluated'
                and not (check['result'] == 'fail' and check.get('related_native_repository_keys'))):
            raise ValueError('result_ledger_replay_check_changed')
        original_checks = expected['trust'].get('checks', [])
        without_replay = lambda values: [item for item in values if item.get('id') != 'replay_key_unique']
        if without_replay(original_checks) != without_replay(observed.get('checks', [])):
            raise ValueError('result_ledger_proof_checks_changed')
        expected['trust']['checks'] = deepcopy(observed['checks'])
        expected['trust']['effective_level'] = promote_effective_level(
            expected['trust'].get('effective_level', 'unverified'), expected['trust']['checks'], root=ROOT)
    if expected != stored: raise ValueError('result_ledger_report_differs_from_source')


def verify_row(context, row, domain, settings):
    if domain == 'typed':
        key = ('typed', identity(row['assessment_id']))
        if key not in context.loaded:
            context.remember(key, load_typed(context.instance_root / 'state/typed', row['assessment_id'], settings))
        proof = context.loaded[key]
        repository = proof['verification']['repository']
        expected = proof['verification']['snapshots'][row['evidence_type']]
    else:
        proof = context.load(row['assessment_id'])
        repository = proof['repository']; expected = proof['snapshots'][domain]
    if row['origin'] != proof['input_origin'] or repository != row['repository']:
        raise ValueError('result_projection_source_origin_changed')
    same_stored_payload(expected, row['payload'])


def membership(row):
    return {'repository_key': row['repository_key'], 'identity': row['identity'],
            'assessment_id': row['assessment_id'], 'payload_digest': row['payload_digest'],
            'repository_descriptor_digest': canonical_digest(row['repository'])}


def build(context, settings, *, domain, origin, realm, at, profile, main_branch, material, selected=None):
    explicit_time(at)
    if domain not in DOMAINS or origin not in ('operator_bundle', 'native_reader'):
        raise ValueError('invalid_result_projection_scope')
    rows = source_rows(context, domain=domain, origin=origin, realm=identity(realm))
    if selected is not None:
        by_id = {(row['repository_key'], row['identity']): row for row in rows}
        matched = []
        for item in selected:
            row = by_id.get((item['repository_key'], item['identity']))
            if row is None or membership(row) != item: raise ValueError('result_projection_membership_changed')
            matched.append(row)
        rows = matched
    files = {}; namespaces = {}
    for row in rows:
        verify_row(context, row, domain, settings)
        key = identity(row['repository_key']); record_id = identity(row['identity'])
        name = f'status/{FOLDERS[domain]}/{key}/{record_id}.json'
        if name in files: raise ValueError('duplicate_result_projection_target')
        raw = (json.dumps(row['payload'], sort_keys=True, indent=2) + '\n').encode()
        reserve(material, len(raw))
        path = material / name; path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        path.write_bytes(raw); path.chmod(0o600)
        for parent in path.parents:
            if parent == material: break
            parent.chmod(0o700)
        files[name] = hashlib.sha256(raw).hexdigest()
        descriptors = namespaces.setdefault(key, [])
        if row['repository'] not in descriptors: descriptors.append(row['repository'])
    policy = result_index_profile(profile, main_branch)
    builder = {'devsecops': results_projection.devsecops_index,
               'architecture': results_projection.architecture_index,
               'typed': results_projection.typed_index}[domain]
    reported = builder(material, at, **policy)
    def effective_trust(value):
        projected = project_trust(value)
        return {**projected, 'effective_level': 'unverified'} if origin == 'operator_bundle' else projected
    effective = builder(material, at, **policy, trust_projection=effective_trust)
    from lib.result_assessments import require_schema
    require_schema(reported, INDEX_SCHEMAS[domain]); require_schema(effective, INDEX_SCHEMAS[domain])
    return {'schema_version': 1, 'kind': 'private-result-index-projection', **context.binding,
        'generated_at': at, 'domain': domain, 'origin': origin, 'realm': realm,
        'event_profile': profile, 'main_branch': main_branch, 'membership': [membership(row) for row in rows],
        'namespace_descriptors': namespaces, 'files': files, 'reported_index': reported, 'effective_index': effective,
        'raw_sources_reverified': True, 'native_metadata_rechecked_now': False,
        'mode': 'report-only', 'evidence_trust': 'unverified', 'official_acceptance': False,
        'production_approval': False, 'risk_acceptance': False, 'authority_transferred': False,
        'published': False}


def persist(context, settings, **parameters):
    projections = private_directory(context.root / 'projections')
    with tempfile.TemporaryDirectory(prefix='.projection-', dir=projections) as temporary:
        staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
        value = build(context, settings, material=staged, **parameters)
        raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
        if len(raw) > MAX_PROJECT: raise ValueError('result_projection_output_limit')
        from lib.result_assessments import require_schema
        require_schema(value, 'axiom-v2-result-projection.schema.json')
        context.assert_current(); projection_id = canonical_digest(value)
        reserve(staged, len(raw)); atomic_json(staged / 'projection.json', value)
        with write_lock(context.root):
            target = projections / projection_id
            if target.is_symlink(): raise ValueError('unsafe_result_projection_target')
            if target.exists():
                existing = inspect(context, settings, projection_id)
                if existing != value: raise ValueError('immutable_result_projection_conflict')
            else:
                staged.rename(target)
        return projection_id, value


def inspect(context, settings, projection_id):
    root = context.root / 'projections' / identity(projection_id)
    value = strict_json(safe_bytes(root / 'projection.json', limit=MAX_PROJECT))
    from lib.result_assessments import require_schema
    require_schema(value, 'axiom-v2-result-projection.schema.json')
    if canonical_digest(value) != projection_id: raise ValueError('result_projection_identity_changed')
    if any(value[key] != expected for key, expected in context.binding.items()):
        raise ValueError('result_projection_node_runtime_or_source_changed')
    for name, expected in value['files'].items():
        if (not isinstance(name, str) or '..' in Path(name).parts or Path(name).is_absolute()
                or not name.startswith('status/' + FOLDERS[value['domain']] + '/')):
            raise ValueError('unsafe_result_projection_member')
        if hashlib.sha256(safe_bytes(root / name, limit=16*1024**2)).hexdigest() != expected:
            raise ValueError('result_projection_retained_file_changed')
    with tempfile.TemporaryDirectory(prefix='.projection-replay-', dir=context.root) as temporary:
        rebuilt = build(context, settings, domain=value['domain'], origin=value['origin'], realm=value['realm'],
            at=value['generated_at'], profile=value['event_profile'], main_branch=value['main_branch'],
            material=Path(temporary), selected=value['membership'])
    if rebuilt != value: raise ValueError('result_projection_differs_from_sources')
    return value
