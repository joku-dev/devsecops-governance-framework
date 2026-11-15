"""Bounded GitHub Actions reads for the retained native V1 result contract.

All authenticated requests stay on the explicitly configured repository/API.
Artifact storage redirects receive no credentials. Captured archives and API
metadata can subsequently be replayed without a network request.
"""
from copy import deepcopy
from pathlib import Path
import json
import re
import tempfile
from urllib.parse import quote

from lib import ci_bundle_storage as storage
from lib import native_result_logic as logic
from lib.consumer_intake_store import atomic_json
from lib.evidence_freshness import load_freshness_policy
from lib.evidence_verification import (build_typed_trust_capture, digest_subject,
    verify_trust_capture, promote_effective_level)
from lib.portable.contracts import ROOT
from lib.private_credentials import check_private_file
from lib.provider_errors import AccessFailure
from lib.providers.transports import Reader
from lib.providers.typed_capture import download, verification_clock
from lib.result_bytes import strict_json
from lib.result_ledger import apply_replay_assessment
from lib.result_snapshot_store import explicit_time
from lib.result_bytes import safe_bytes

PROVIDER = 'github-actions'
REPO = r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'
NUMERIC = r'[1-9][0-9]*'
MAX_MANIFEST = 16 * 1024**2


def credential_reader(path, repository, budget):
    if (not isinstance(repository, str) or not re.fullmatch(REPO, repository)
            or any(part in ('.', '..') for part in repository.split('/'))
            or type(budget) is not int or not 1 <= budget <= 2000):
        raise ValueError('invalid_native_result_reader_scope')
    check_private_file(path)
    value = strict_json(safe_bytes(Path(path).resolve(), limit=1024**2))
    if (set(value) != {'schema_version', 'provider', 'instance', 'repository', 'token'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1 or value['provider'] != PROVIDER
            or value['instance'] != 'https://api.github.com' or value['repository'] != repository
            or not isinstance(value['token'], str) or not value['token'].strip()
            or any(ord(c) < 32 for c in value['token'])):
        raise ValueError('native_result_reader_binding_mismatch')
    return Reader(value['instance'], value['token'], budget=budget)


def check_run(run, repository, run_id, attempt):
    if (not isinstance(run, dict) or str(run.get('id')) != str(run_id)
            or not re.fullmatch(NUMERIC, str(run_id))
            or type(attempt) is not int or attempt < 1
            or type(run.get('run_attempt')) is not int or run['run_attempt'] != attempt or run.get('status') != 'completed'
            or not isinstance(run.get('conclusion'), str) or not run['conclusion']
            or not re.fullmatch('[0-9a-f]{40}', run.get('head_sha', ''))
            or run.get('html_url') != f'https://github.com/{repository}/actions/runs/{run_id}'
            or run.get('repository', {}).get('full_name') != repository
            or type(run['repository'].get('id')) is not int or run['repository']['id'] < 1
            or any(not isinstance(run.get(key), str) or not run[key]
                   for key in ('name', 'head_branch', 'event'))):
        raise ValueError('native_result_run_binding_mismatch')
    explicit_time(run.get('created_at')); explicit_time(run.get('updated_at'))


def baseline(run):
    for workflow in run.get('referenced_workflows', []):
        ref, sha = workflow.get('ref', ''), workflow.get('sha', '')
        tag = ref.removeprefix('refs/tags/') if ref.startswith('refs/tags/') else ''
        if 'baseline' in tag and isinstance(sha, str) and re.fullmatch('[a-fA-F0-9]{40}', sha):
            return {'ref': ref, 'sha': sha.lower()}
    return None


def inferred_baseline(run):
    for workflow in run.get('referenced_workflows', []):
        ref, path = workflow.get('ref', ''), workflow.get('path', '')
        if ref.startswith('refs/tags/') and 'baseline' in ref.removeprefix('refs/tags/'):
            return ref.removeprefix('refs/tags/')
        match = re.search(r'devsecops-baseline-l1-(v[0-9]+(?:\.[0-9]+)+)\.yml@([^/]+)$', path)
        if match: return match.group(2)
    return 'unknown'


def check_artifact(artifact, run, repository):
    identifier = str(artifact.get('id', ''))
    binding = artifact.get('workflow_run', {})
    if (not re.fullmatch(NUMERIC, identifier) or artifact.get('expired') is not False
            or type(artifact.get('size_in_bytes')) is not int
            or not 0 < artifact['size_in_bytes'] <= 1024**3
            or str(binding.get('id')) != str(run['id'])
            or binding.get('repository_id') != run['repository']['id']
            or binding.get('head_sha') != run['head_sha']
            or binding.get('head_branch') != run['head_branch']
            or artifact.get('archive_download_url') !=
                f'https://api.github.com/repos/{repository}/actions/artifacts/{identifier}/zip'):
        raise ValueError('native_result_artifact_binding_mismatch')


def selected(artifacts, name, run, repository, *, required=True):
    matches = [item for item in artifacts if item.get('name') == name]
    if not matches and not required: return None
    if len(matches) != 1: raise ValueError('native_result_artifact_missing_or_ambiguous')
    check_artifact(matches[0], run, repository)
    return matches[0]


def parameters(value, domain):
    if (domain not in ('devsecops', 'architecture') or not isinstance(value, dict)
            or set(value) != {'artifact_name', 'baseline_level', 'baseline_ref', 'governance_repository', 'notes'}
            or any(not isinstance(v, str) or len(v) > 4096 or any(ord(c) < 32 for c in v)
                   for v in value.values()) or not value['artifact_name']
            or not value['governance_repository'] or not value['baseline_level']):
        raise ValueError('invalid_native_result_parameters')
    return value


def listing(reader, path, field, *, limit=25):
    rows = list(reader.pages(path, field, limit=limit))
    identifiers = [str(item.get('id')) for item in rows]
    if len(set(identifiers)) != len(rows) or any(not re.fullmatch(NUMERIC, key) for key in identifiers):
        raise ValueError('native_result_list_identity_ambiguous')
    return rows


def check_jobs(jobs, run):
    for job in jobs:
        if (job.get('run_id') != run['id'] or job.get('run_attempt') != run['run_attempt']
                or job.get('head_sha') != run['head_sha']):
            raise ValueError('native_result_job_binding_mismatch')


def protection(reader, repository, branch):
    try:
        value = reader.get(f'/repos/{repository}/branches/{quote(branch, safe="")}')
    except AccessFailure as error:
        if error.code in ('request_budget_exhausted', 'rate_limited'): raise
        if re.fullmatch(r'http_[0-9]{3}', error.code):
            return None, {'status': 'unavailable', 'http_status': int(error.code[5:])}
        return None, {'status': 'unavailable', 'error_type': 'provider_read_failed'}
    if not isinstance(value, dict) or not isinstance(value.get('protected'), bool):
        return None, {'status': 'unavailable', 'error_type': 'invalid_response'}
    return value['protected'], {'status': 'protected' if value['protected'] else 'unprotected'}


def capture(repository, run_id, attempt, credential, destination, *, domain, options,
            request_budget=100, storage_budget=storage.DEFAULT_BUDGET):
    parameters(options, domain)
    if type(storage_budget) is not int or not 0 < storage_budget <= storage.MAX_BUDGET:
        raise ValueError('invalid_native_result_storage_budget')
    if not re.fullmatch(NUMERIC, str(run_id)): raise ValueError('invalid_native_result_run_id')
    destination = Path(destination)
    if destination.exists() or destination.is_symlink(): raise ValueError('fresh_native_result_capture_required')
    reader = credential_reader(credential, repository, request_budget)
    route = f'/repos/{repository}/actions/runs/{run_id}'
    run = reader.get(route); check_run(run, repository, run_id, attempt)
    jobs_route = f'{route}/attempts/{attempt}/jobs'
    jobs = listing(reader, jobs_route, 'jobs') if domain == 'devsecops' else []
    check_jobs(jobs, run)
    artifacts = listing(reader, route + '/artifacts', 'artifacts')
    primary = selected(artifacts, options['artifact_name'], run, repository)
    if primary['size_in_bytes'] > storage_budget:
        raise ValueError('native_result_storage_budget_exhausted')
    companion = selected(artifacts, 'devsecops-governance-run-input', run, repository,
                         required=False) if domain == 'devsecops' else None
    # Downloading an optional companion even when the primary contains its input
    # would change the original source identity. Decide after bounded extraction.
    storage.reserve(destination.parent, primary['size_in_bytes'])
    destination.mkdir(mode=0o700)
    archives = {}
    with tempfile.TemporaryDirectory(prefix='.native-material-', dir=destination.parent) as temporary:
        primary_path = destination / 'artifact.zip'
        record = download(reader, repository, primary, primary_path, reserve=storage.RESERVE)
        if primary.get('digest') not in (None, 'sha256:' + record['sha256']):
            raise ValueError('native_result_archive_digest_mismatch')
        material = Path(temporary) / 'primary'; material.mkdir(mode=0o700)
        files = storage.extract_archive(primary_path, material, raw_bytes=record['bytes'], budget=storage_budget)
        consumed = record['bytes'] + sum(row['bytes'] for row in files.values())
        archives['primary'] = {**record, 'path': 'artifact.zip', 'artifact': primary}
        if (domain == 'devsecops' and logic.optional_json(material, 'governance-run-input.json')[1] is None
                and companion is not None):
            if consumed + companion['size_in_bytes'] > storage_budget:
                raise ValueError('native_result_storage_budget_exhausted')
            record = download(reader, repository, companion, destination / 'governance-run-input.zip', reserve=storage.RESERVE)
            if companion.get('digest') not in (None, 'sha256:' + record['sha256']):
                raise ValueError('native_result_archive_digest_mismatch')
            archives['companion'] = {**record, 'path': 'governance-run-input.zip', 'artifact': companion}
    protected, lookup = protection(reader, repository, run['head_branch'])
    after = reader.get(route); check_run(after, repository, run_id, attempt)
    if (after != run or listing(reader, route + '/artifacts', 'artifacts') != artifacts
            or (domain == 'devsecops' and listing(reader, jobs_route, 'jobs') != jobs)):
        raise ValueError('native_result_run_changed_during_capture')
    at = verification_clock()
    value = {'schema_version': 1, 'kind': 'native-general-result-capture', 'provider': PROVIDER,
        'repository_id': repository, 'domain': domain, 'parameters': deepcopy(options),
        'run': run, 'jobs': jobs, 'artifacts': artifacts, 'branch_protected': protected,
        'branch_protection_lookup': lookup, 'archives': archives, 'verified_at': at}
    raw_size = sum(row['bytes'] for row in archives.values())
    metadata_size = len(json.dumps(value, sort_keys=True, indent=2).encode()) + 1
    if metadata_size > MAX_MANIFEST or raw_size + metadata_size > storage_budget:
        raise ValueError('native_result_capture_metadata_budget')
    storage.reserve(destination, metadata_size); atomic_json(destination / 'capture.json', value)
    sha = storage.hash_file(destination / 'capture.json', MAX_MANIFEST)['sha256']
    normalized = verify(destination, sha, budget=storage_budget)
    return normalized, sha, {'native_metadata_rechecked': True, 'requests': reader.calls,
                           'whole_archives_downloaded': True, 'verified_at': at}


def verify(root, expected_sha256, *, budget):
    root = Path(root)
    manifest_path = root / 'capture.json'
    if storage.hash_file(manifest_path, MAX_MANIFEST)['sha256'] != expected_sha256:
        raise ValueError('native_result_manifest_changed')
    value = strict_json(safe_bytes(manifest_path, limit=MAX_MANIFEST))
    required = {'schema_version', 'kind', 'provider', 'repository_id', 'domain', 'parameters',
        'run', 'jobs', 'artifacts', 'branch_protected', 'branch_protection_lookup', 'archives', 'verified_at'}
    if (set(value) != required or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'native-general-result-capture' or value['provider'] != PROVIDER
            or not isinstance(value['repository_id'], str) or not re.fullmatch(REPO, value['repository_id'])
            or not isinstance(value['archives'], dict) or not {'primary'} <= set(value['archives']) <= {'primary', 'companion'}
            or not isinstance(value['jobs'], list) or not isinstance(value['artifacts'], list)
            or (value['branch_protected'] is not None and type(value['branch_protected']) is not bool)
            or not isinstance(value['branch_protection_lookup'], dict)):
        raise ValueError('invalid_native_result_manifest')
    parameters(value['parameters'], value['domain']); explicit_time(value['verified_at'])
    run = value['run']; repository = value['repository_id']
    check_run(run, repository, run['id'], run['run_attempt'])
    check_jobs(value['jobs'], run)
    archives = value['archives']; total = manifest_path.stat().st_size
    for group, record in archives.items():
        if (not isinstance(record, dict) or set(record) != {'sha256', 'bytes', 'path', 'artifact'}
                or record['path'] != ('artifact.zip' if group == 'primary' else 'governance-run-input.zip')):
            raise ValueError('invalid_native_result_archive_record')
        check_artifact(record['artifact'], run, repository)
        name = value['parameters']['artifact_name'] if group == 'primary' else 'devsecops-governance-run-input'
        if selected(value['artifacts'], name, run, repository) != record['artifact']:
            raise ValueError('native_result_archive_metadata_changed')
        actual = storage.hash_file(root / record['path'], 1024**3)
        if (actual != {key: record[key] for key in ('sha256', 'bytes')}
                or actual['bytes'] != record['artifact']['size_in_bytes']
                or record['artifact'].get('digest') not in (None, 'sha256:' + actual['sha256'])):
            raise ValueError('native_result_archive_bytes_changed')
        total += actual['bytes']
    if total > budget: raise ValueError('native_result_storage_budget_exhausted')
    if {p.name for p in root.iterdir()} != {'capture.json', *(row['path'] for row in archives.values())}:
        raise ValueError('undeclared_native_result_capture_file')
    with tempfile.TemporaryDirectory(prefix='.native-replay-', dir=root.parent) as temporary:
        material = {}
        for group, record in archives.items():
            path = Path(temporary) / group; path.mkdir(mode=0o700)
            files = storage.extract_archive(root / record['path'], path, raw_bytes=total, budget=budget)
            total += sum(row['bytes'] for row in files.values()); material[group] = path
        snapshot = normalize(value, root, material)
    return {'repository': {'provider': 'github', 'instance': 'https://api.github.com',
        'native_id': str(run['repository']['id']), 'path': repository, 'url': f'https://github.com/{repository}'},
        'snapshots': {value['domain']: snapshot}, 'verified_at': value['verified_at']}


def normalize(value, root, material):
    domain, options, run = value['domain'], value['parameters'], value['run']
    artifact = value['archives']['primary']['artifact']; primary = material['primary']
    paths, subjects = {}, []
    def add(key, path, ref):
        paths[key] = path; subjects.append(digest_subject(key, path, ref))
    common = {'repository_id': value['repository_id'], 'run': run,
        'branch_protected': value['branch_protected'], 'branch_protection_lookup': value['branch_protection_lookup'],
        'notes': options['notes'], 'governance_repository': options['governance_repository']}
    baseline_ref = options['baseline_ref'] or inferred_baseline(run)
    if domain == 'devsecops':
        report_path = logic.find_report(primary)
        report = logic.normalize_governance_report(logic.load_json(report_path), report_path)
        governance_input, input_path = logic.optional_json(primary, 'governance-run-input.json')
        companion = value['archives'].get('companion')
        if companion is not None:
            if input_path is not None: raise ValueError('native_result_unnecessary_companion')
            governance_input, input_path = logic.optional_json(material['companion'], 'governance-run-input.json')
            if input_path is None: raise ValueError('native_result_companion_input_missing')
        pipeline, pipeline_path = logic.optional_json(primary, 'pipeline-evidence.json')
        add('control_evaluation_report', report_path, 'downloaded_artifact.control_evaluation_report_sha256')
        if input_path is not None and companion is None:
            add('governance_run_input', input_path, 'downloaded_artifact.governance_run_input_sha256')
        if pipeline_path is not None: add('pipeline_evidence', pipeline_path, 'downloaded_artifact.pipeline_evidence_sha256')
        add('artifact_archive', root / 'artifact.zip', 'trust.capture.subjects.artifact_archive')
        names = {row['name'] for row in value['artifacts']}
        arguments = {'baseline_level': options['baseline_level'], 'governance_baseline_ref': baseline_ref,
            'jobs': value['jobs'], 'report': report, 'governance_input': governance_input,
            'report_sha256': logic.compute_sha256(report_path),
            'governance_input_sha256': logic.compute_sha256(input_path) if input_path else None,
            'pipeline_evidence_sha256': logic.compute_sha256(pipeline_path) if pipeline_path else None,
            'artifacts': value['artifacts'], 'selected_artifact': artifact,
            'governance_input_artifact': companion['artifact'] if companion else None,
            'governance_input_artifact_archive_sha256': companion['sha256'] if companion else None,
            'artifact_names': names, 'evidence': logic.evidence_flags_from_artifacts(pipeline, primary, governance_input,
                names, report_path.name == 'control-evaluation-report.json' or options['artifact_name'] == 'governance-control-evaluation'),
            'evidence_context_payload': logic.evidence_context(pipeline, governance_input, report)}
    else:
        if set(value['archives']) != {'primary'}: raise ValueError('unexpected_architecture_companion')
        report, report_path = logic.optional_json(primary, 'architecture-governance-report.json')
        release_input, input_path = logic.optional_json(primary, 'architecture-release-input.json')
        if report_path is None or input_path is None: raise ValueError('native_architecture_material_missing')
        add('architecture_governance_report', report_path, 'artifact_metadata.architecture_governance_report_sha256')
        add('architecture_release_input', input_path, 'artifact_metadata.architecture_release_input_sha256')
        add('artifact_archive', root / 'artifact.zip', 'artifact_metadata.artifact_archive_sha256')
        digests = {row['id']: row['digest'] for row in subjects}
        arguments = {'architecture_baseline_ref': options['baseline_ref'], 'report': report, 'release_input': release_input,
            'artifact_metadata': {'artifact_name': options['artifact_name'], 'artifact_size_bytes': artifact['size_in_bytes'],
                'architecture_governance_report_sha256': digests['architecture_governance_report'],
                'architecture_release_input_sha256': digests['architecture_release_input'],
                'artifact_archive_sha256': digests['artifact_archive']}}
    at = value['verified_at']
    trust = build_typed_trust_capture(evidence_type='governance_result', governance_domain=domain,
        collector_id='central-governance-intake', collector_version='0.1.0', source_provider='github_actions',
        repository_id=value['repository_id'], commit_id=run['head_sha'], workflow_name=run['name'], run_id=str(run['id']),
        run_attempt=run['run_attempt'], artifact_name=options['artifact_name'], source_uri=artifact['archive_download_url'],
        produced_at=run['updated_at'], captured_at=at, subjects=subjects)
    extras = {}
    if domain == 'devsecops':
        if artifact.get('digest'): trust['capture']['source']['artifact_digest'] = artifact['digest'].removeprefix('sha256:')
        resolved = baseline(run)
        trust['capture']['observations'] = {'governance_baseline': resolved or {'ref': None, 'sha': None}}
        extras = {'baseline': resolved, 'baseline_ref': baseline_ref}
    policy = load_freshness_policy(ROOT / 'model/evidence/evidence-freshness-policies.yaml', 'freshness-governance-result-24h')
    trust = verify_trust_capture(trust, repository_id=value['repository_id'], commit_id=run['head_sha'], run_id=str(run['id']),
        artifact_name=options['artifact_name'], subject_paths=paths, verified_at=at, freshness_policy=policy,
        produced_at=run['updated_at'], root=ROOT, verifier_id='central-governance-intake/v1', **extras)
    trust = apply_replay_assessment(trust, [])
    if domain == 'devsecops':
        trust['effective_level'] = promote_effective_level(trust['effective_level'], trust['checks'], root=ROOT)
    return getattr(logic, domain + '_snapshot')(**common, **arguments, trust=trust)
