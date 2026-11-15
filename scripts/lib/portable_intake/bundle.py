"""One bounded bundle contract for local, CI and VM intake."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import shutil

from lib.portable.contracts import ROOT, canonical_digest, execution_key, repository_key, validate
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib.portable.runtime import baseline, evaluate, file_digest, gate, prepare_evidence, read_json, source_digest
from lib.evidence_trust import derive_effective_level, load_freshness_policy
from lib.consumer_intake_store import atomic_json
from lib.safe_archive import safe_extract_zip

VERSION = '2.0.0'
MAX_FILE = 256 * 1024 ** 2
MAX_TOTAL = 512 * 1024 ** 2
ROLES = {'context', 'result', 'input', 'artifact', 'sbom', 'vulnerability_scan'}


def require_storage(root, policy):
    """Reserve the whole archive/unpacked/staged-copy budget before acquisition."""
    raw=Path(root)/'raw'
    used=sum(p.stat().st_size for p in raw.rglob('*') if p.is_file()) if raw.exists() else 0
    limit=policy.get('storage_budget_bytes',2*1024**3)
    reserve=policy.get('storage_reserve_bytes',8*1024**3)
    if used+2*MAX_TOTAL>limit or shutil.disk_usage(root).free<reserve+4*MAX_TOTAL:
        from lib.provider_errors import AccessFailure
        raise AccessFailure('storage_budget_exhausted')


def verifier_digest():
    paths=[*(p for p in sorted((ROOT/'scripts/lib/portable_intake').glob('*.py')) if p.name not in ('assurance.py','operations.py','transport.py')),
           *sorted((ROOT/'schemas').glob('portable-intake-*-v2.schema.json')),
           ROOT/'scripts/intake_portable_evidence.py',ROOT/'scripts/lib/consumer_intake_store.py',
           ROOT/'scripts/lib/provider_errors.py',ROOT/'scripts/lib/secure_http.py',
           ROOT/'scripts/lib/private_credentials.py',ROOT/'scripts/lib/safe_archive.py',
           ROOT/'scripts/lib/evidence_trust.py',ROOT/'model/evidence/evidence-trust-model.yaml',
           ROOT/'model/evidence/evidence-freshness-policies.yaml']
    return canonical_digest({'evaluation_runtime':source_digest(),
                             'files':{str(p.relative_to(ROOT)):file_digest(p) for p in paths}})


def validate_v2(kind, value):
    try:
        Draft202012Validator(read_json(ROOT / f'schemas/portable-intake-{kind}-v2.schema.json'),
                             format_checker=FormatChecker()).validate(value)
    except ValidationError:
        raise ValueError('invalid_portable_intake_' + kind) from None
    return value


def safe_path(root, name):
    root = Path(root)
    if root.is_symlink():
        raise ValueError('unsafe_bundle_root')
    root = root.resolve()
    path = PurePosixPath(name)
    if (not isinstance(name, str) or not name or name != str(path) or path.is_absolute()
            or any(part in ('..', '.') for part in path.parts) or '\\' in name or ':' in name
            or any(ord(c) < 32 for c in name)):
        raise ValueError('unsafe_bundle_path')
    target = root / name
    parents = [root.joinpath(*path.parts[:i]) for i in range(1,len(path.parts))]
    if (target.is_symlink() or any(p.is_symlink() for p in parents)
            or not target.resolve().is_relative_to(root) or not target.is_file()):
        raise ValueError('missing_or_unsafe_bundle_member')
    return target


def export_bundle(assessment, checkout, destination):
    """Preserve bytes and original subject identities. Never assert provider provenance."""
    assessment, checkout, destination = map(Path, (assessment, checkout, destination))
    result = validate('result', read_json(safe_path(assessment, 'result.json')))
    context = read_json(safe_path(assessment, 'context.json'))
    if result['context'] != context:
        raise ValueError('result_context_mismatch')
    sources = [(name, safe_path(assessment, filename), filename, None) for name, filename in
               [('context', 'context.json'), ('result', 'result.json'), ('input', 'evaluation-input.json')]]
    for subject in result['subjects']:
        source = safe_path(checkout, subject['path'])
        if file_digest(source) != subject['sha256'] or source.stat().st_size != subject['size']:
            raise ValueError('subject_changed_after_evaluation')
        sources.append((subject['role'], source, 'subjects/' + subject['role'] + '/' + source.name, subject['path']))
    if {row[0] for row in sources} != ROLES or len(sources) != len(ROLES):
        raise ValueError('missing_or_duplicate_bundle_role')
    if sum(row[1].stat().st_size for row in sources) > MAX_TOTAL:
        raise ValueError('bundle_size_limit')
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    files = []
    for role, source, name, original in sources:
        if source.stat().st_size > MAX_FILE:
            raise ValueError('bundle_member_size_limit')
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as incoming, target.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        files.append({'role': role, 'path': name, 'subject_path': original,
                      'sha256': file_digest(target), 'size': target.stat().st_size})
    manifest = {'schema_version': VERSION, 'execution_key': execution_key(context),
                'repository_key': repository_key(context['scm']), 'files': files}
    validate_v2('bundle', manifest)
    atomic_json(destination / 'bundle.json', manifest)
    return manifest


def unpack(archive, destination):
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    safe_extract_zip(Path(archive), destination, max_members=32, max_member_bytes=MAX_FILE,
                     max_total_bytes=MAX_TOTAL)
    return destination


def timestamp(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('time_requires_timezone')
    return stamp.astimezone(timezone.utc)


def validate_policy(policy):
    """Trusted operator input, never accepted from inside a downloaded bundle."""
    validate_v2('policy', policy)
    freshness=load_freshness_policy(ROOT/'model/evidence/evidence-freshness-policies.yaml','freshness-governance-result-24h')
    if (policy.get('schema_version') != VERSION or policy.get('runtime_source_digest') != source_digest()
            or policy.get('baseline_digest') != baseline(baseline_id=policy.get('baseline_id'))[1]['digest']
            or type(policy.get('max_age_seconds')) is not int or not 1 <= policy['max_age_seconds'] <= freshness['maximum_age_seconds']
            or type(policy.get('future_skew_seconds')) is not int or policy['future_skew_seconds'] != 0
            or policy.get('max_severity') not in ('none', 'info', 'low', 'medium', 'high', 'critical')):
        raise ValueError('unsupported_verification_policy')
    repository_key(policy['scm'])
    from lib.portable.contracts import endpoint
    endpoint(policy['ci']['instance'])
    return policy


def verify_bundle(root, policy, *, opa, at, history=None, observation=None):
    """Pure verification apart from explicit file/tool reads; does not consume replay state.

    An observation is a collector-owned object, never JSON loaded from the bundle.
    Local imports can prove integrity only. Caller commits a receipt transactionally.
    """
    root = Path(root)
    validate_policy(policy)
    evaluated_at = timestamp(at)
    manifest = read_json(safe_path(root, 'bundle.json'))
    validate_v2('bundle', manifest)
    if set(manifest) != {'schema_version', 'execution_key', 'repository_key', 'files'} or manifest['schema_version'] != VERSION:
        raise ValueError('unsupported_bundle_contract')
    files = manifest['files']
    if (not isinstance(files, list) or len(files) != len(ROLES) or {row['role'] for row in files} != ROLES
            or len({row['path'].casefold() for row in files}) != len(files)
            or any(set(row) != {'role','path','subject_path','sha256','size'} for row in files)):
        raise ValueError('ambiguous_bundle_manifest')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('unsafe_bundle_member')
        if path.is_file():
            actual.add(str(path.relative_to(root)))
    if actual != {'bundle.json', *(row['path'] for row in files)}:
        raise ValueError('bundle_file_set_mismatch')
    if sum(safe_path(root, row['path']).stat().st_size for row in files) > MAX_TOTAL:
        raise ValueError('bundle_size_limit')
    for row in files:
        path = safe_path(root, row['path'])
        if (type(row['size']) is not int or row['size'] > MAX_FILE or path.stat().st_size != row['size']
                or file_digest(path) != row['sha256']):
            raise ValueError('bundle_digest_mismatch')
    members = {row['role']: row for row in files}
    context = validate('context', read_json(root / members['context']['path']))
    result = validate('result', read_json(root / members['result']['path']))
    document = read_json(root / members['input']['path'])
    # The runtime CLI preserves payload and subject bindings in one envelope.
    # Earlier programmatic exporters supplied the payload directly. Retain both
    # byte-preserving forms, validating every envelope binding before derivation.
    if not isinstance(document, dict):
        raise ValueError('invalid_evaluation_input')
    if 'payload' in document or 'subjects' in document:
        if (set(document) != {'payload', 'subjects'}
                or not isinstance(document['payload'], dict)
                or document['subjects'] != result['subjects']):
            raise ValueError('evaluation_input_subject_binding_mismatch')
        payload = document['payload']
    else:
        payload = document
    if result['context'] != context or canonical_digest(context) != result['context_digest']:
        raise ValueError('result_context_mismatch')
    key = execution_key(context)
    if key != manifest['execution_key'] or repository_key(context['scm']) != manifest['repository_key']:
        raise ValueError('bundle_identity_mismatch')
    if (repository_key(context['scm']) != repository_key(policy['scm'])
            or context['scm']['path'] != policy['scm']['path']
            or context['scm']['url'] != policy['scm']['url']
            or context['ci']['provider'] != policy['ci']['provider']
            or context['ci']['instance'] != policy['ci']['instance']
            or context['governance']['baseline_id'] != policy['baseline_id']
            or context['governance']['baseline_digest'] != policy['baseline_digest']
            or context['governance']['runtime_source_digest'] != policy['runtime_source_digest']):
        raise ValueError('bundle_policy_binding_mismatch')
    subjects = {row['role']: row for row in result['subjects']}
    if set(subjects) != {'artifact','sbom','vulnerability_scan'} or len(result['subjects']) != 3:
        raise ValueError('ambiguous_subjects')
    for role, subject in subjects.items():
        member = members[role]
        if (subject['path'] != member['subject_path'] or subject['size'] != member['size']
                or subject['sha256'] != member['sha256']):
            raise ValueError('subject_binding_mismatch')
        # Validate original paths even though they are not used to open a bundle file.
        original = PurePosixPath(subject['path'])
        if (str(original) != subject['path'] or original.is_absolute() or '..' in original.parts
                or '\\' in subject['path'] or ':' in subject['path']):
            raise ValueError('unsafe_original_subject_path')
    # Derive critical facts again from bytes and context, then use the same evaluator.
    derived, _ = prepare_evidence(context, root, *(members[r]['path'] for r in ('artifact','sbom','vulnerability_scan')),
                                 governance_input=payload)
    if derived != payload:
        raise ValueError('normalized_input_does_not_match_files')
    expected = evaluate(context, payload, result['subjects'], opa=opa, mode=result['requested_enforcement'],
                        max_severity=policy['max_severity'], at=result['generated_at'])
    if result != expected:
        raise ValueError('assessment_recomputation_mismatch')
    digest = canonical_digest(manifest)
    previous = (history or {}).get(key)
    replay = 'new' if previous is None else 'duplicate' if previous == digest else 'conflict'
    age = (evaluated_at - timestamp(result['generated_at'])).total_seconds()
    fresh = -policy['future_skew_seconds'] <= age <= policy['max_age_seconds']
    observed = observation.checks(context, manifest, policy, evaluated_at, result['generated_at']) if observation else {}
    checks = {'subject_identity_complete': True, 'content_digest_verified': True,
              'producer_run_resolved': False, 'commit_matches_run': False, 'artifact_belongs_to_run': False,
              'baseline_ref_resolved': True, 'freshness_evaluated': fresh,
              'replay_key_unique': replay == 'new', 'custody_recorded': False}
    if set(observed) - {'producer_run_resolved','commit_matches_run','artifact_belongs_to_run','custody_recorded','freshness_evaluated'}:
        raise ValueError('unsupported_native_assertion')
    checks.update(observed)
    checks['freshness_evaluated'] = fresh and checks['freshness_evaluated']
    # Synthetic evidence and incomplete native closure never acquire producer assurance.
    if context['synthetic']:
        checks['producer_run_resolved'] = False
    trust = derive_effective_level([{'id': k, 'result': 'pass' if v else 'fail'} for k,v in checks.items()])
    receipt = {'schema_version': VERSION, 'execution_key': key, 'repository_key': manifest['repository_key'],
            'bundle_digest': digest, 'evaluated_at': evaluated_at.isoformat(),
            'decision': result['decision'], 'execution': result['execution'], 'trust': trust,
            'freshness': 'fresh' if fresh else 'stale_or_future', 'replay': replay, 'checks': checks,
            'candidate_eligible': trust == 'provenance_verified' and result['execution'] == 'complete'
                                  and gate(result, 'report-only') == 0,
            'official_acceptance': False, 'blocks_merge': None,
            'verifier':{'version':VERSION,'source_digest':verifier_digest()},
            'producer': context, 'collector': {'kind':'local' if observation is None else observation.kind}}
    return validate_v2('receipt',receipt)
