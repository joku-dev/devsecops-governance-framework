"""VM consumer pilot: discover, verify, propose, and project accepted Git state."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

from lib.consumer_github import AccessFailure, git_environment
from lib.consumer_intake_store import atomic_json, disk_ready, lock

CENTRAL = 'joku-dev/devsecops-governance-framework'
CONSUMER = 'joku-dev/ha-CPsWMS'
WORKFLOW = '.github/workflows/devsecops-baseline.yml'
BASELINE = 'l1-baseline-v1.1.3'
ARTIFACT = 'devsecops-pipeline-evidence'
GENERATORS = ('generate_repository_results_index.py', 'generate_intake_health.py',
              'generate_multi_consumer_readiness.py', 'generate_governance_graph.py',
              'generate_replay_triage_report.py', 'generate_blocking_readiness.py',
              'generate_blocking_mode_alignment.py', 'generate_status_viewer.py')


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def owner(root, repository=CONSUMER, domain='devsecops'):
    value = json.loads((Path(root) / 'config/consumer-intake-routing.json').read_text())
    if value.get('schema_version') != 1 or value.get('default_owner') != 'github-actions':
        raise ValueError('Invalid intake routing contract')
    routes = value['routes']
    keys = [(row['repository'], row['domain']) for row in routes]
    if len(set(keys)) != len(keys) or any(row['owner'] not in {'github-actions', 'vm'} for row in routes):
        raise ValueError('Invalid or duplicate intake route')
    return next((row['owner'] for row in routes if (row['repository'], row['domain']) == (repository, domain)),
                value['default_owner'])


def fingerprints(root):
    """Closed dependency set. Documentation/status changes do not authorize new code."""
    root = Path(root)
    names = ['scripts', 'schemas', 'model', 'policies', 'architecture', 'releases', 'pipeline-baseline',
             '.github/workflows', '.agents', 'docs/governance/source-documents', 'docs/foundation']
    paths = [path for name in names for path in (root / name).rglob('*') if path.is_file()
             and '__pycache__' not in path.parts and path.suffix != '.pyc']
    paths += list(root.glob('requirements*'))
    result = {}
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError('Symlink in executable dependency set')
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def compatible(installed, staging):
    if fingerprints(installed) != fingerprints(staging):
        raise AccessFailure('application_update_required')


def command(args, cwd, *, token=None, timeout=1800):
    env = git_environment(token) if token else dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    try:
        result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise AccessFailure('operation_timeout', True) from None
    if result.returncode:
        # Private command output can contain source URLs or credentials: expose codes only.
        raise AccessFailure('source_fetch_failed', True) if args[:2] == ['git', 'fetch'] else AccessFailure('validation_or_command_failed')
    return result.stdout.decode('utf-8')


def stage(root, destination, sha, token):
    if not re.fullmatch('[a-f0-9]{40}', sha):
        raise ValueError('Expected immutable central commit')
    destination.mkdir()
    command(['git', 'init', '-q'], destination)
    command(['git', 'remote', 'add', 'origin', f'https://github.com/{CENTRAL}.git'], destination)
    command(['git', 'fetch', '--depth=1', 'origin', sha], destination, token=token)
    command(['git', 'checkout', '--detach', '-q', sha], destination)
    compatible(root, destination)
    return destination


def appropriate(run):
    return (run.get('repository', {}).get('full_name') == CONSUMER and run.get('head_branch') == 'main'
            and run.get('event') == 'push' and run.get('path', '').split('@')[0] == WORKFLOW
            and int(run.get('run_attempt', 0)) > 0)


def discover(store, api):
    if store.get('poll_after', 0) > time.time():
        return
    prefix = f'/repos/{CONSUMER}/actions/workflows/devsecops-baseline.yml/runs?branch=main&event=push'
    started = store.get('discovery_started')
    if not started:
        # Bootstrap only the newest completed run and active runs; no historic backfill.
        found = False
        for runs in api.pages(prefix, 'workflow_runs'):
            for run in runs:
                if not appropriate(run):
                    continue
                if run['status'] != 'completed' or not found:
                    store.discover(CONSUMER, run)
                if run['status'] == 'completed':
                    found = True
            if found:
                break
        store.put('discovery_started', now())
        store.put('shadow_started', time.time())
    else:
        since = datetime.fromisoformat(started.replace('Z', '+00:00')) - timedelta(hours=1)
        until = datetime.now(timezone.utc)
        discover_window(store, api, prefix, since, until)
        # Commit the watermark only after all pages/windows have succeeded.
        store.put('discovery_started', now())
    # Reruns retain the old created_at; poll known active/recent IDs independently.
    for run_id in sorted({job['run_id'] for job in store.jobs()}):
        current = api.request('GET', f'/repos/{CONSUMER}/actions/runs/{run_id}')
        if appropriate(current):
            store.discover(CONSUMER, current)
    store.put('central_head', api.request('GET', f'/repos/{CENTRAL}/commits/main')['sha'])
    store.put('last_poll', now())
    store.put('poll_error', None)
    store.put('poll_failures', 0)
    store.put('poll_after', 0)


def discover_window(store, api, prefix, start, end):
    window = quote(start.strftime('%Y-%m-%dT%H:%M:%SZ') + '..' + end.strftime('%Y-%m-%dT%H:%M:%SZ'), safe='')
    endpoint = prefix + '&created=' + window
    first = api.request('GET', endpoint + '&per_page=100&page=1')
    if first['total_count'] > 1000:
        if (end - start).total_seconds() <= 1:
            raise AccessFailure('discovery_window_overflow')
        middle = start + (end - start) / 2
        discover_window(store, api, prefix, start, middle)
        discover_window(store, api, prefix, middle, end)
        return
    for runs in api.pages(endpoint, 'workflow_runs'):
        for run in runs:
            if appropriate(run):
                store.discover(CONSUMER, run)


def identity(snapshot):
    source = snapshot.get('trust', {}).get('capture', {}).get('source', {})
    return snapshot['repository_id'], str(snapshot['pipeline']['pipeline_run_id']), int(source.get('run_attempt', 1))


def comparison(snapshot):
    """Meaningful shadow comparison excludes collection-time and operator observations."""
    subjects = snapshot.get('trust', {}).get('capture', {}).get('subjects', [])
    return {'identity': identity(snapshot), 'commit': snapshot['repository']['commit_id'],
            'verdict': snapshot['overall_status'], 'checks': snapshot['checks'],
            'baseline': snapshot['governance_baseline_ref'],
            'digests': sorted((s['id'], s['digest']) for s in subjects)}


def accepted_snapshots(staging):
    values = []
    for path in (Path(staging) / 'status/results').rglob('*.json'):
        if path.is_symlink() or not path.resolve().is_relative_to(Path(staging).resolve()):
            raise AccessFailure('invalid_accepted_path')
        values.append((path.relative_to(staging).as_posix(), json.loads(path.read_text())))
    return values


def validate_snapshot(root, snapshot, job):
    from jsonschema import Draft202012Validator, ValidationError
    try:
        Draft202012Validator(json.loads((root / 'schemas/evidence-trust-record.schema.json').read_text())).validate(snapshot['trust'])
    except (ValidationError, KeyError):
        raise AccessFailure('snapshot_schema_invalid') from None
    source = snapshot['trust']['capture']['source']
    if (identity(snapshot) != (CONSUMER, str(job['run_id']), job['attempt'])
            or snapshot['repository']['commit_id'] != json.loads(job['payload'])['head_sha']
            or snapshot['repository']['branch'] != 'main' or snapshot['pipeline']['event'] != 'push'
            or snapshot['governance_baseline_ref'] != BASELINE
            or source['repository_id'] != CONSUMER or source['artifact_name'] != ARTIFACT
            or source['commit_id'] != snapshot['repository']['commit_id']):
        raise AccessFailure('snapshot_context_mismatch')
    # A failed governance verdict is valid evidence. Failed integrity/provenance is not.
    checks = snapshot['trust'].get('checks', {})
    values = checks.values() if isinstance(checks, dict) else checks
    if any(isinstance(check, dict) and check.get('result') == 'fail' for check in values):
        raise AccessFailure('evidence_verification_failed')
    outcomes = {check['id']: check['result'] for check in values}
    required = {'subject_identity_complete', 'content_digest_verified', 'producer_run_resolved',
                'commit_matches_run', 'artifact_belongs_to_run', 'baseline_ref_resolved', 'custody_recorded'}
    if any(outcomes.get(check) != 'pass' for check in required):
        raise AccessFailure('evidence_provenance_unverified')


def collect(store, staging, api, job):
    if not disk_ready(store.root):
        raise AccessFailure('capacity_paused')
    run = api.request('GET', f'/repos/{CONSUMER}/actions/runs/{job["run_id"]}', cache=False)
    if not appropriate(run) or run['run_attempt'] != job['attempt'] or run['status'] != 'completed':
        raise AccessFailure('run_attempt_changed')
    artifacts = [row for page in api.pages(f'/repos/{CONSUMER}/actions/runs/{job["run_id"]}/artifacts', 'artifacts') for row in page]
    selected = [item for item in artifacts if item['name'] == ARTIFACT]
    if len(selected) != 1 or selected[0].get('expired'):
        raise AccessFailure('artifact_missing_or_expired')
    raw_used = sum(path.stat().st_size for path in (store.root / 'raw').rglob('*') if path.is_file())
    if raw_used + sum(row.get('size_in_bytes', 0) for row in artifacts) > 1024 ** 3:
        raise AccessFailure('cache_budget_exceeded')
    key = f'{job["run_id"]}-{job["attempt"]}'
    raw = store.root / 'raw' / key
    output = store.root / 'verified' / key
    output.mkdir(parents=True, exist_ok=True)
    failure_record = store.root / 'errors' / (key + '.json')
    failure_record.unlink(missing_ok=True)
    env = {**os.environ, 'GH_RESULT_INTAKE_TOKEN': api.token(), 'PYTHONDONTWRITEBYTECODE': '1',
           'AXIOM_INTAKE_FAILURE_RECORD': str(failure_record)}
    args = [sys.executable, str(staging / 'scripts/intake_github_actions_run.py'),
            '--repository-id', CONSUMER, '--run-id', str(job['run_id']),
            '--expected-run-attempt', str(job['attempt']), '--governance-baseline-ref', BASELINE,
            '--archive-directory', str(raw), '--snapshot-directory', str(output)]
    try:
        result = subprocess.run(args, cwd=staging, env=env, capture_output=True, timeout=600, check=False)
    except subprocess.TimeoutExpired:
        raise AccessFailure('collection_timeout', True) from None
    if result.returncode:
        if failure_record.is_file():
            failure = json.loads(failure_record.read_text())
            raise AccessFailure(failure['code'], failure['retryable'], failure['delay'])
        # Probe the source again to distinguish retryable API failure from invalid input.
        api.request('GET', f'/repos/{CONSUMER}/actions/runs/{job["run_id"]}', cache=False)
        raise AccessFailure('normalization_failed')
    snapshots = list(output.rglob('*.json'))
    if len(snapshots) != 1:
        raise AccessFailure('snapshot_count_mismatch')
    snapshot = json.loads(snapshots[0].read_text())
    validate_snapshot(staging, snapshot, job)
    relative = 'status/results/' + snapshots[0].relative_to(output).as_posix()
    store.update(job, state='verified', snapshot=json.dumps(snapshot), snapshot_path=relative, error=None)
    store.put('last_success', now())
    return snapshot


def summarize(snapshot):
    return {'run_id': snapshot['pipeline']['pipeline_run_id'],
            'attempt': identity(snapshot)[2], 'produced_at': snapshot['generated_at'],
            'governance_status': snapshot['overall_status'],
            'evidence_trust': snapshot.get('trust', {}).get('effective_level', 'unverified'),
            'source_url': snapshot['pipeline']['pipeline_url']}


def sync_accepted(store, staging, sha):
    if store.get('accepted_commit') == sha:
        return
    command([sys.executable, 'scripts/validate_governance_repo.py'], staging)
    index = json.loads((staging / 'status/repository-results-index.json').read_text())
    row = next((row for row in index['repositories'] if row['repository_id'] == CONSUMER), None)
    latest = None
    if row and row.get('latest_result'):
        source = row['latest_result']['source_file']
        path = staging / source
        if (not source.startswith('status/results/') or '..' in Path(source).parts
                or path.is_symlink() or not path.resolve().is_relative_to(staging.resolve())):
            raise AccessFailure('invalid_accepted_path')
        latest = summarize(json.loads(path.read_text()))
    accepted = {'source_commit': sha, 'synced_at': now(), 'latest': latest}
    # One atomic generation contains all accepted details and its exact commit.
    atomic_json(store.root / 'accepted' / (sha + '.json'), accepted)
    store.put('accepted', accepted)
    store.put('accepted_commit', sha)
    compare_jobs(store, staging)


def shadow_ready(store):
    return time.time() - store.get('shadow_started', time.time()) >= 24 * 3600 and bool(store.get('shadow_match'))


def project(store, directory, mode):
    with lock(store.root / 'projection.lock', blocking=True):
        return _project(store, directory, mode)


def _project(store, directory, mode):
    # Explicit projection allowlist: no queue payloads, paths, secrets, HTTP caches or raw logs.
    rows = []
    for job in store.jobs():
        entry = {'run_id': str(job['run_id']), 'attempt': job['attempt'], 'state': job['state'], 'error': job['error']}
        if job['snapshot']:
            entry.update(summarize(json.loads(job['snapshot'])))
        rows.append(entry)
    result = {'schema_version': 1, 'configured': True, 'repository': CONSUMER, 'domain': 'devsecops',
              'mode': mode, 'generated_at': now(), 'last_poll': store.get('last_poll'),
              'last_success': store.get('last_success'), 'poll_error': store.get('poll_error'),
              'sync_error': store.get('sync_error'), 'accepted': store.get('accepted'),
              'shadow_ready': shadow_ready(store), 'jobs': list(reversed(rows))[:100],
              'queue_count': len(rows), 'batch': None}
    batch = store.active_batch()
    if batch:
        result['batch'] = {key: batch[key] for key in ('id', 'state', 'pr', 'url')}
    atomic_json(Path(directory) / 'consumers.json', result, mode=0o640)
    return result


def process(store, installed, reader, publisher=None, mode='shadow', limit=25):
    store.recover()
    sha = reader.request('GET', f'/repos/{CENTRAL}/commits/main', cache=False)['sha']
    if (store.get('accepted_commit') == sha and not store.jobs('queued')
            and not store.jobs('verified') and not store.jobs('accepted_pending_sync') and not store.active_batch()):
        return
    if shutil.disk_usage(store.root).free < 9 * 1024 ** 3:
        raise AccessFailure('capacity_paused', True, 900)
    with tempfile.TemporaryDirectory(prefix='stage-', dir=store.root) as temporary:
        staging = stage(installed, Path(temporary) / 'repository', sha, reader.token())
        sync_accepted(store, staging, sha)
        store.put('sync_error', None)
        for _ in range(min(limit, 25)):
            job = store.claim()
            if not job:
                break
            try:
                collect(store, staging, reader, job)
            except AccessFailure as error:
                if error.code == 'capacity_paused':
                    store.update(job, state='queued', next_at=time.time() + 900, error=error.code)
                    break
                store.failure(job, error.code, error.retryable, error.delay)
            except (ValueError, OSError, KeyError):
                store.failure(job, 'invalid_snapshot_or_local_state')
        # Compare against accepted state even when main itself did not change.
        compare_jobs(store, staging)
        if mode == 'publish':
            if owner(staging) != 'vm' or not shadow_ready(store):
                raise AccessFailure('handoff_required')
            if publisher is None:
                raise AccessFailure('publisher_credentials_missing')
            from lib.consumer_publisher import publish
            publish(store, staging, reader, publisher, sha)


def compare_jobs(store, staging):
    # Use the same comparison path without rewriting accepted timestamps.
    snapshots = accepted_snapshots(staging)
    for job in (row for row in store.jobs() if row['state'] in {'verified', 'accepted_pending_sync'}):
        snapshot = json.loads(job['snapshot'])
        existing = next((value for _, value in snapshots if identity(value) == identity(snapshot)), None)
        if not existing:
            continue
        matches = comparison(snapshot) == comparison(existing)
        store.update(job, state='accepted' if matches else 'held', error=None if matches else 'shadow_mismatch')
        produced = datetime.fromisoformat(json.loads(job['payload'])['created_at'].replace('Z', '+00:00')).timestamp()
        if matches and produced > store.get('shadow_started', time.time()):
            store.put('shadow_match', {'run_id': job['run_id'], 'attempt': job['attempt'], 'at': now()})
