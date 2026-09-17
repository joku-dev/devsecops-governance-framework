"""Fixed ha-CPsWMS profile: verify all five Docker archives without executing them."""
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

from lib.evidence_trust import build_typed_trust_capture, verify_trust_capture, load_freshness_policy
from lib.measured_security import ROOT, SERVICES, REPOSITORY, normalize

PROFILE = 'ha-cpswms-container-trust-v1'
NAMES = ('subject.json', 'vulnerabilities.json', 'vulnerabilities.execution.json',
         'archive.execution.json', 'trivy-version.log', 'trivy-version.execution.json', 'image.tar')
MAX_IMAGE = 2 * 1024**3


def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_docker_archive(path, image_id, commit=None):
    """Match config digest and every uncompressed layer to Docker's immutable image ID."""
    with tarfile.open(path, 'r:') as archive:
        members = archive.getmembers()
        if len(members) > 20000:
            raise ValueError('Too many image archive members')
        files = {}
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or member.issym() or member.islnk():
                raise ValueError('Unsafe image archive member')
            if member.isdir():
                continue
            if not member.isfile() or member.name in files or member.size > MAX_IMAGE:
                raise ValueError('Duplicate, oversized or unsupported image member')
            files[member.name] = member
        def read(name, limit=8 * 1024**2):
            member = files.get(name)
            if member is None or member.size > limit:
                raise ValueError('Missing or oversized image metadata')
            with archive.extractfile(member) as stream:
                return stream.read(limit + 1)
        manifest = json.loads(read('manifest.json'))
        if not isinstance(manifest, list) or len(manifest) != 1:
            raise ValueError('Expected exactly one Docker image')
        config_bytes = read(manifest[0]['Config'])
        if 'sha256:' + hashlib.sha256(config_bytes).hexdigest() != image_id:
            raise ValueError('Archive config does not match scanned image ID')
        config = json.loads(config_bytes)
        if commit is not None and config.get('config', {}).get('Labels', {}).get('org.opencontainers.image.revision') != commit:
            raise ValueError('Archive revision label differs from source commit')
        layers, diff_ids = manifest[0]['Layers'], config['rootfs']['diff_ids']
        if not layers or len(layers) != len(diff_ids) or len(set(layers)) != len(layers):
            raise ValueError('Invalid image layer binding')
        for name, expected in zip(layers, diff_ids):
            if name not in files:
                raise ValueError('Missing image layer')
            with archive.extractfile(files[name]) as stream:
                actual = 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('Archive layer does not match image config')
        return len(layers)


def verify_bundle(run, report, declaration, bundles, paths, verified_at):
    """Trust uses producer digests; central hashing is independent of those assertions."""
    measured = normalize(run, report, bundles)
    expected_context = {'repository': REPOSITORY, 'commit': run['head_sha'],
                        'run_id': str(run['id']), 'attempt': str(run['run_attempt']), 'event': 'push'}
    if (declaration.get('profile') != PROFILE or declaration.get('enforcement') != 'report-only'
            or declaration.get('context') != expected_context
            or set(declaration.get('images', {})) != set(SERVICES)):
        raise ValueError('Incomplete typed container declaration')
    subjects, subject_paths, images, produced_times, versions = [], {}, [], [], set()
    for service in SERVICES:
        raw, artifact = bundles[service]
        manifest = json.loads(raw['manifest.json'])
        subject = json.loads(raw['subject.json'])
        declared = declaration['images'][service]
        if declared != {'artifact_name': 'l1-image-' + service, 'image_id': subject['image_id'],
                        'archive_sha256': subject['archive_sha256']}:
            raise ValueError('Container declaration differs from image evidence')
        for name in NAMES:
            path = paths[service] / name
            record = manifest['files'][name]
            if path.stat().st_size != record['bytes'] or digest_file(path) != record['sha256']:
                raise ValueError('Image evidence digest mismatch: ' + service + '/' + name)
            sid = service.replace('-', '_') + '_' + name.replace('.', '_').replace('-', '_')
            subjects.append({'id': sid, 'evidence_ref': f'artifact:{artifact["id"]}/{name}',
                             'algorithm': 'sha256', 'digest': record['sha256'], 'size_bytes': record['bytes']})
            subject_paths[sid] = path
        if manifest['files']['image.tar']['sha256'] != subject['archive_sha256']:
            raise ValueError('Image archive subject digest mismatch')
        for name in ('archive', 'vulnerabilities', 'trivy-version'):
            execution = json.loads((paths[service] / (name + '.execution.json')).read_text())
            if execution['exit_code'] != 0 or execution.get('execution_ok') is not True:
                raise ValueError('Failed image evidence command')
        scan_command = json.loads(raw['vulnerabilities.execution.json'])['command']
        if (scan_command[:2] != ['trivy', 'image'] or scan_command[-1] != subject['image_id']
                or '--image-src' not in scan_command or scan_command[scan_command.index('--image-src') + 1] != 'docker'):
            raise ValueError('Scan command is not bound to the archived image')
        version_lines = (paths[service] / 'trivy-version.log').read_text().splitlines()
        version = next((line.split(':', 1)[1].strip() for line in version_lines if line.startswith('Version:')), '')
        if not version:
            raise ValueError('Missing Trivy version')
        versions.add(version)
        layers = verify_docker_archive(paths[service] / 'image.tar', subject['image_id'], run['head_sha'])
        produced_times.append(manifest['context']['observed_at'])
        images.append({'service': service, 'image_id': subject['image_id'],
                       'artifact_id': str(artifact['id']), 'artifact_name': artifact['name'],
                       'artifact_archive_sha256': artifact['verified_zip_sha256'],
                       'archive_sha256': subject['archive_sha256'], 'archive_digest_verified': True,
                       'image_layers_verified': layers, 'counts': measured['images'][service]['counts']})
    if len(versions) != 1:
        raise ValueError('Mixed scanner versions')
    counts = measured['counts']
    severity = next((s.lower() for s in ('CRITICAL','HIGH','MEDIUM','LOW','INFO','UNKNOWN') if counts[s]), 'none')
    observations = {'profile': PROFILE, 'scanner': {'name': 'trivy', 'version': next(iter(versions))},
                    'finding_count': sum(counts.values()), 'observed_max_severity': severity,
                    'declared_max_severity': severity, 'severity_consistent': True,
                    'subject_binding': {'mode': 'co_collected', 'scanner_attested': False},
                    'container_images': images, 'independent_attestation': False}
    produced_at = min(produced_times, key=lambda value: datetime.fromisoformat(value.replace('Z', '+00:00')))
    trust = build_typed_trust_capture(evidence_type='vulnerability_scan', governance_domain='devsecops',
        collector_id='central-ha-container-collector', collector_version='0.1.0', source_provider='ci_artifact',
        repository_id=REPOSITORY, commit_id=run['head_sha'], workflow_name=run['name'], run_id=str(run['id']),
        run_attempt=run['run_attempt'], artifact_name='l1-control-coverage', source_uri=run['html_url'],
        produced_at=produced_at, captured_at=verified_at, subjects=subjects, observations=observations)
    return verify_trust_capture(trust, repository_id=REPOSITORY, commit_id=run['head_sha'], run_id=str(run['id']),
        artifact_name='l1-control-coverage', subject_paths=subject_paths, verified_at=verified_at,
        freshness_policy=load_freshness_policy(ROOT/'model/evidence/evidence-freshness-policies.yaml', 'freshness-vulnerability-scan-24h'),
        produced_at=produced_at, verifier_id='central-ha-container-trust-intake/v1')
