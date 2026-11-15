"""Explicit full-archive acquisition for the retained native typed image profile.

Selected JSON is sufficient for measured coverage. Typed archive verification
additionally reads every archived configuration and layer, without running images.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
import zipfile

from jsonschema import Draft202012Validator, FormatChecker

from lib.consumer_intake_store import atomic_json
from lib.measurement_logic import decode_json
from lib.portable.contracts import ROOT
from lib.portable_intake.bundle import safe_path
from lib.provider_errors import AccessFailure
from lib.providers.context import NoRedirect
from lib.providers.measured_capture import credential_reader, storage_url
from lib.providers.measured_l1 import artifact_binding
from lib.providers.measured_security import REPOSITORY, SERVICES, check_run, normalize
from lib.providers.typed_containers import (PROFILE, NAMES, VULNERABILITY_NAMES, MAX_IMAGE,
                                           verify_bundle, _baseline_workflow_matches)

MAX_ZIP = 1024**3
MAX_SMALL = 32 * 1024**2
DEFAULT_BUDGET = 2 * 1024**3
DEFAULT_RESERVE = 8 * 1024**3


def verification_clock():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def sha256_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def space(root, needed, reserve):
    if shutil.disk_usage(root).free < reserve + needed:
        raise ValueError('typed_evidence_storage_reserve_exhausted')


def private_root(root):
    root = Path(root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('unsafe_typed_bundle_root')
    return root


def extract(archive_path, destination, names, accounting, *, budget, reserve):
    destination.mkdir(mode=0o700, exist_ok=False)
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or len({row.filename for row in infos}) != len(infos):
            raise ValueError('typed_archive_member_limit_or_duplicate')
        for name in names:
            matches = [row for row in infos if row.filename == name]
            limit = MAX_IMAGE if name == 'image.tar' else MAX_SMALL
            if (len(matches) != 1 or matches[0].is_dir() or matches[0].file_size > limit
                    or matches[0].flag_bits & 1 or stat.S_ISLNK(matches[0].external_attr >> 16)
                    or matches[0].compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('unsafe_or_missing_typed_archive_member')
            if accounting['bytes'] + matches[0].file_size > budget:
                raise ValueError('typed_evidence_storage_budget_exhausted')
            space(destination, matches[0].file_size, reserve)
            with archive.open(matches[0]) as incoming, (destination / name).open('xb') as outgoing:
                total = 0
                while chunk := incoming.read(1024**2):
                    total += len(chunk)
                    if total > limit or total > matches[0].file_size:
                        raise ValueError('typed_archive_member_size_changed')
                    outgoing.write(chunk)
            if total != matches[0].file_size:
                raise ValueError('typed_archive_member_incomplete')
            (destination / name).chmod(0o600)
            accounting['bytes'] += total
            if name.endswith('.json'):
                decode_json((destination / name).read_bytes())


def manifest(root, expected_sha256, *, budget):
    root = private_root(root)
    path = safe_path(root, 'capture.json')
    if path.stat().st_size > MAX_SMALL or sha256_file(path) != expected_sha256:
        raise ValueError('typed_capture_manifest_changed')
    value = decode_json(path.read_bytes())
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'kind', 'run', 'baseline_run', 'archives'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['kind'] != 'native-typed-container-capture'
            or set(value['archives']) != {'coverage', *SERVICES}):
        raise ValueError('invalid_typed_capture_manifest')
    run = value['run']
    check_run(run, REPOSITORY, run['id'])
    if run['html_url'] != f"https://github.com/{REPOSITORY}/actions/runs/{run['id']}":
        raise ValueError('typed_native_run_url_mismatch')
    total = 0
    for group, row in value['archives'].items():
        if not isinstance(row, dict) or set(row) != {'path', 'sha256', 'bytes', 'artifact'}:
            raise ValueError('invalid_typed_archive_record')
        expected_name = 'l1-control-coverage' if group == 'coverage' else 'l1-image-' + group
        artifact_binding(row['artifact'], run, expected_name)
        artifact_id = str(row['artifact']['id'])
        if not re.fullmatch('[1-9][0-9]*', artifact_id):
            raise ValueError('invalid_typed_native_artifact_id')
        if row['path'] != 'archives/' + group + '.zip':
            raise ValueError('invalid_typed_archive_path')
        archive = safe_path(root, row['path'])
        size = archive.stat().st_size
        if (not 0 < size <= MAX_ZIP or type(row['bytes']) is not int
                or size != row['bytes'] or row['artifact']['size_in_bytes'] != size
                or not re.fullmatch('[a-f0-9]{64}', row['sha256'])
                or sha256_file(archive) != row['sha256']):
            raise ValueError('typed_archive_bytes_changed')
        digest = row['artifact'].get('digest')
        if digest is not None and digest != 'sha256:' + row['sha256']:
            raise ValueError('typed_native_archive_digest_mismatch')
        url = row['artifact'].get('archive_download_url')
        if url != f'https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip':
            raise ValueError('typed_native_artifact_url_mismatch')
        total += size
    if total > budget:
        raise ValueError('typed_evidence_storage_budget_exhausted')
    return value, total


def snapshot(run, artifact, trust):
    """Original V1 typed-result wire payload, without its old filesystem writer."""
    return {'schema_version': '1.0.0', 'result_type': 'typed-evidence-trust',
        'repository_id': REPOSITORY, 'evidence_type': trust['capture']['evidence_type'],
        'generated_at': run.get('updated_at') or run['created_at'],
        'pipeline': {'pipeline_name': run['name'], 'pipeline_run_id': str(run['id']),
            'pipeline_url': run['html_url'], 'event': run['event'], 'status': 'success',
            'run_attempt': run['run_attempt']},
        'repository': {'branch': run['head_branch'], 'commit_id': run['head_sha']},
        'source_artifact': {'name': artifact['name'], 'artifact_id': str(artifact['id']),
            'size_bytes': artifact['size_in_bytes'], 'archive_download_url': artifact['archive_download_url'],
            'archive_sha256': artifact['verified_zip_sha256']}, 'trust': trust}


def copy_bundle(root, expected_sha256, destination, *, budget=DEFAULT_BUDGET, reserve=DEFAULT_RESERVE):
    """Snapshot untrusted operator files before any verification or intake."""
    if not 0 < budget <= 16 * 1024**3 or reserve < DEFAULT_RESERVE:
        raise ValueError('invalid_typed_storage_limits')
    value, total = manifest(root, expected_sha256, budget=budget)
    destination = private_root(destination)
    space(destination.parent, total + MAX_SMALL, reserve)
    destination.mkdir(mode=0o700, exist_ok=False)
    (destination / 'archives').mkdir(mode=0o700)
    rows = [('capture.json', MAX_SMALL), *((row['path'], row['bytes']) for row in value['archives'].values())]
    for name, limit in rows:
        source = safe_path(root, name)
        descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError('unsafe_typed_copy_source')
            with os.fdopen(descriptor, 'rb') as incoming, (destination / name).open('xb') as outgoing:
                descriptor = -1
                copied = 0
                while chunk := incoming.read(1024**2):
                    copied += len(chunk)
                    if copied > limit:
                        raise ValueError('typed_copy_source_size_changed')
                    outgoing.write(chunk)
            (destination / name).chmod(0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    manifest(destination, expected_sha256, budget=budget)


def verify(root, expected_sha256, at, *, budget=DEFAULT_BUDGET, reserve=DEFAULT_RESERVE):
    if not 0 < budget <= 16 * 1024**3 or reserve < DEFAULT_RESERVE:
        raise ValueError('invalid_typed_storage_limits')
    stamp = datetime.fromisoformat(at.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('explicit_typed_timezone_required')
    value, raw_bytes = manifest(root, expected_sha256, budget=budget)
    run = value['run']
    accounting = {'bytes': raw_bytes}
    # Work files stay on the instance's filesystem so reserve accounting is real.
    with tempfile.TemporaryDirectory(prefix='.typed-verify-', dir=Path(root).parent) as directory:
        base = Path(directory)
        coverage = value['archives']['coverage']
        extract(safe_path(root, coverage['path']), base / 'coverage',
            ('l1-coverage.json', 'typed-evidence-manifest.json'), accounting, budget=budget, reserve=reserve)
        report = decode_json((base / 'coverage/l1-coverage.json').read_bytes())
        declaration = decode_json((base / 'coverage/typed-evidence-manifest.json').read_bytes())
        names = NAMES if declaration.get('profile') == PROFILE else VULNERABILITY_NAMES
        bundles, paths = {}, {}
        for service in SERVICES:
            row = value['archives'][service]
            path = base / service
            extract(safe_path(root, row['path']), path, ('manifest.json', *names),
                accounting, budget=budget, reserve=reserve)
            raw = {name: (path / name).read_bytes() for name in
                   ('manifest.json', 'subject.json', 'vulnerabilities.json', 'vulnerabilities.execution.json')}
            artifact = {**row['artifact'], 'verified_zip_sha256': row['sha256']}
            bundles[service], paths[service] = (raw, artifact), path
        coverage_artifact = {**coverage['artifact'], 'verified_zip_sha256': coverage['sha256']}
        trusts = verify_bundle(run, report, declaration, bundles, paths, at,
            coverage_artifact=coverage_artifact, baseline_run=value['baseline_run'])
        for trust in trusts.values():
            trust['capture']['source']['artifact_digest'] = coverage['sha256']
        snapshots = {kind: snapshot(run, coverage_artifact, trust) for kind, trust in trusts.items()}
        validator = Draft202012Validator(decode_json((ROOT / 'schemas/typed-evidence-result.schema.json').read_bytes()),
                                         format_checker=FormatChecker())
        for item in snapshots.values():
            validator.validate(item)
        return {'repository': {'provider': 'github', 'instance': 'https://github.com',
            'native_id': str(run['repository']['id']), 'path': REPOSITORY},
            'execution': {'provider': 'github-actions', 'instance': 'https://api.github.com',
                'run_id': str(run['id']), 'attempt': run['run_attempt'], 'event': run['event'],
                'branch': run['head_branch'], 'commit': run['head_sha'], 'workflow': run['path'],
                'produced_at': run['updated_at']},
            'snapshots': snapshots, 'measured_containers': normalize(run, report, bundles),
            'verified_archive_bytes': raw_bytes, 'verified_material_bytes': accounting['bytes'] - raw_bytes}


def download(reader, repository, artifact, destination, *, reserve):
    expected_size = artifact['size_in_bytes']
    if type(expected_size) is not int or not 0 < expected_size <= MAX_ZIP:
        raise ValueError('typed_native_archive_size_limit')
    space(destination.parent, expected_size, reserve)
    route = f"/repos/{repository}/actions/artifacts/{artifact['id']}/zip"
    request = Request(reader.url(route), headers=reader.headers)
    try:
        response = build_opener(NoRedirect).open(request, timeout=40)
    except HTTPError as error:
        if error.code != 302:
            raise AccessFailure('typed_artifact_unavailable', error.code >= 500) from None
        location = storage_url(error.headers['Location'])
    else:
        response.close()
        raise ValueError('typed_artifact_redirect_required')
    if reader.calls >= reader.budget:
        raise AccessFailure('request_budget_exhausted', True)
    reader.calls += 1
    total = 0
    with build_opener(NoRedirect).open(Request(location), timeout=120) as incoming, destination.open('xb') as outgoing:
        if incoming.status != 200 or int(incoming.headers['Content-Length']) != expected_size:
            raise ValueError('typed_download_size_mismatch')
        while chunk := incoming.read(1024**2):
            total += len(chunk)
            if total > expected_size:
                raise ValueError('typed_download_size_mismatch')
            outgoing.write(chunk)
    destination.chmod(0o600)
    if total != expected_size:
        raise ValueError('typed_download_incomplete')
    return {'sha256': sha256_file(destination), 'bytes': total}


def capture(repository, run_id, credential_file, destination, *, request_budget=100,
            storage_budget=DEFAULT_BUDGET, reserve=DEFAULT_RESERVE):
    if not 0 < storage_budget <= 16 * 1024**3 or reserve < DEFAULT_RESERVE:
        raise ValueError('invalid_typed_storage_limits')
    if repository != REPOSITORY or not re.fullmatch('[1-9][0-9]*', str(run_id)):
        raise ValueError('unsupported_typed_repository_or_run')
    destination = private_root(destination)
    if destination.exists():
        raise ValueError('fresh_typed_capture_directory_required')
    reader = credential_reader(credential_file, repository, request_budget)
    run = reader.get(f'/repos/{repository}/actions/runs/{run_id}')
    check_run(run, repository, run_id)
    listing = reader.get(f'/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100')
    if listing['total_count'] != len(listing['artifacts']):
        raise ValueError('typed_artifact_list_truncated')
    selected = {}
    for group in ('coverage', *SERVICES):
        name = 'l1-control-coverage' if group == 'coverage' else 'l1-image-' + group
        matches = [item for item in listing['artifacts'] if item['name'] == name]
        if len(matches) != 1:
            raise ValueError('typed_artifact_identity_ambiguous')
        artifact_binding(matches[0], run, name)
        selected[group] = matches[0]
    if (any(type(item['size_in_bytes']) is not int or not 0 < item['size_in_bytes'] <= MAX_ZIP
            for item in selected.values()) or sum(item['size_in_bytes'] for item in selected.values()) > storage_budget):
        raise ValueError('typed_evidence_storage_budget_exhausted')
    baseline = None
    lookup = 'same_run_reference'
    if len(_baseline_workflow_matches(run)) != 1:
        lookup = 'no_unique_paired_run'
        try:
            paired = reader.get(f'/repos/{repository}/actions/workflows/devsecops-baseline.yml/runs'
                f"?head_sha={run['head_sha']}&branch=main&event=push&per_page=100")
            if paired['total_count'] == len(paired['workflow_runs']) == 1:
                baseline = paired['workflow_runs'][0]
                lookup = 'paired_run_observed'
        except AccessFailure:
            lookup = 'paired_lookup_unavailable'
    destination.mkdir(mode=0o700)
    (destination / 'archives').mkdir(mode=0o700)
    archives = {}
    try:
        for group, artifact in selected.items():
            relative = 'archives/' + group + '.zip'
            record = download(reader, repository, artifact, destination / relative, reserve=reserve)
            archives[group] = {**record, 'path': relative, 'artifact': deepcopy(artifact)}
        after = reader.get(f'/repos/{repository}/actions/runs/{run_id}')
        check_run(after, repository, run_id)
        if (any(after.get(key) != run.get(key) for key in ('id', 'head_sha', 'run_attempt', 'status', 'conclusion'))
                or after['repository']['id'] != run['repository']['id']):
            raise ValueError('typed_run_changed_during_capture')
        value = {'schema_version': 1, 'kind': 'native-typed-container-capture', 'run': run,
                 'baseline_run': baseline, 'archives': archives}
        atomic_json(destination / 'capture.json', value)
        sha = sha256_file(destination / 'capture.json')
        at = verification_clock()
        normalized = verify(destination, sha, at, budget=storage_budget, reserve=reserve)
        return normalized, sha, {'native_metadata_rechecked': True, 'requests': reader.calls,
            'whole_archives_downloaded': True, 'baseline_lookup': lookup, 'verified_at': at}
    except (HTTPError, URLError, OSError, zipfile.BadZipFile):
        raise AccessFailure('typed_capture_failed', True) from None
