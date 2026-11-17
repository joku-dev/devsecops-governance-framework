"""Explicit-context verification extracted from frozen V1 6b557fefe295b58272d2271326576ca3a3687197.

No source CLI dispatch or native acquisition is included here.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
from lib.artifact_integrity import digest_file, verify_docker_archive, MAX_IMAGE
from lib.evidence_verification import build_typed_trust_capture, canonical_sha256, verify_trust_capture
from lib.evidence_freshness import load_freshness_policy
from lib.providers.measured_security import ROOT, SERVICES, REPOSITORY, normalize
CUSTODY_TRANSFORMATIONS=('download_github_actions_artifacts','verify_zip_metadata_and_sha256',
    'extract_selected_members','verify_subject_hashes','normalize_typed_evidence')

def verify_native_trust(trust, **context):
    return verify_trust_capture(trust, root=ROOT, custody_transformations=CUSTODY_TRANSFORMATIONS, **context)

LEGACY_PROFILE = 'ha-cpswms-container-trust-v1'

PROFILE = 'ha-cpswms-container-evidence-v2'

VULNERABILITY_NAMES = ('subject.json', 'vulnerabilities.json', 'vulnerabilities.execution.json', 'archive.execution.json', 'trivy-version.log', 'trivy-version.execution.json', 'image.tar')

SBOM_NAMES = ('subject.json', 'sbom.cyclonedx.json', 'sbom.execution.json', 'archive.execution.json', 'trivy-version.log', 'trivy-version.execution.json', 'image.tar')

NAMES = tuple(dict.fromkeys((*VULNERABILITY_NAMES, *SBOM_NAMES)))

def _baseline_workflow_matches(run):
    """Return the single pinned L1 workflow reference from an authoritative run."""
    matches = []
    for workflow in run.get('referenced_workflows', []):
        path = workflow.get('path', '')
        ref = workflow.get('ref', '')
        sha = workflow.get('sha', '')
        if 'devsecops-baseline-l1-' in path:
            matches.append({'workflow_ref': ref, 'workflow_path': path, 'workflow_sha': sha})
    return matches

def _paired_baseline_context_matches(run, baseline_run):
    """Require a successful protected-main baseline run for the exact producer commit."""
    producer_repository = run.get('repository', {})
    baseline_repository = baseline_run.get('head_repository', {})
    return baseline_run.get('path') == '.github/workflows/devsecops-baseline.yml' and baseline_run.get('event') == 'push' and (baseline_run.get('head_branch') == 'main') and (baseline_run.get('head_sha') == run.get('head_sha')) and (baseline_run.get('status') == 'completed') and (baseline_run.get('conclusion') == 'success') and (str(baseline_repository.get('id', '')) == str(producer_repository.get('id', '')))

def resolve_baseline(run, report, baseline_run=None):
    """Bind the report baseline to a same-run or exact-commit paired workflow reference."""
    expected = report.get('reference_baseline')
    matches = _baseline_workflow_matches(run)
    baseline_context = None
    if len(matches) != 1 and baseline_run and _paired_baseline_context_matches(run, baseline_run):
        matches = _baseline_workflow_matches(baseline_run)
        if len(matches) == 1:
            baseline_context = {'run_id': str(baseline_run.get('id', '')), 'run_attempt': str(baseline_run.get('run_attempt', '')), 'workflow_path': baseline_run.get('path', ''), 'event': baseline_run.get('event', ''), 'branch': baseline_run.get('head_branch', ''), 'commit_id': baseline_run.get('head_sha', ''), 'status': baseline_run.get('status', ''), 'conclusion': baseline_run.get('conclusion', ''), 'url': baseline_run.get('html_url', '')}
    if len(matches) != 1:
        return {'baseline_ref': expected, 'workflow_ref': '', 'workflow_path': '', 'workflow_sha': '', 'baseline_run': None, 'evidence_refs': []}
    match = matches[0]
    evidence_refs = ['baseline_run.id', 'baseline_run.head_sha', 'baseline_run.referenced_workflows[].ref', 'baseline_run.referenced_workflows[].sha'] if baseline_context else ['run.referenced_workflows[].ref', 'run.referenced_workflows[].sha']
    return {'baseline_ref': expected, **match, 'baseline_run': baseline_context, 'evidence_refs': evidence_refs}

def build_custody_record(run, coverage_artifact, bundles, subjects, observations, verified_at):
    artifacts = {'l1-control-coverage': coverage_artifact}
    artifacts.update({artifact['name']: artifact for _, artifact in bundles.values()})
    raw_artifacts = {name: {'artifact_id': str(item['id']), 'sha256': item.get('verified_zip_sha256', '')} for name, item in sorted(artifacts.items())}
    raw_digest = canonical_sha256(raw_artifacts)
    normalized_digest = canonical_sha256({'profile': observations['profile'], 'repository_id': run['repository']['full_name'], 'commit_id': run['head_sha'], 'run_id': str(run['id']), 'subjects': subjects, 'observations': observations})
    return {'collector': 'central-ha-container-trust-intake', 'collected_at': verified_at, 'raw_digest': raw_digest, 'raw_artifacts': raw_artifacts, 'normalized_digest': normalized_digest, 'transformations': ['download_github_actions_artifacts', 'verify_zip_metadata_and_sha256', 'extract_selected_members', 'verify_subject_hashes', 'normalize_typed_evidence']}

def verify_bundle(run, report, declaration, bundles, paths, verified_at, coverage_artifact=None, baseline_run=None):
    """Return separately verified vulnerability and SBOM Trust records."""
    measured = normalize(run, report, bundles)
    expected_context = {'repository': REPOSITORY, 'commit': run['head_sha'], 'run_id': str(run['id']), 'attempt': str(run['run_attempt']), 'event': 'push'}
    profile = declaration.get('profile')
    if profile not in {LEGACY_PROFILE, PROFILE} or declaration.get('enforcement') != 'report-only' or declaration.get('context') != expected_context or (set(declaration.get('images', {})) != set(SERVICES)):
        raise ValueError('Incomplete typed container declaration')
    names = NAMES if profile == PROFILE else VULNERABILITY_NAMES
    subjects_by_type = {'vulnerability_scan': [], 'sbom': []}
    paths_by_type = {'vulnerability_scan': {}, 'sbom': {}}
    vulnerability_images, sbom_images, produced_times, versions, spec_versions = ([], [], [], set(), set())
    for service in SERVICES:
        raw, artifact = bundles[service]
        manifest = json.loads(raw['manifest.json'])
        subject = json.loads(raw['subject.json'])
        for name in names:
            path = paths[service] / name
            record = manifest['files'][name]
            if path.stat().st_size != record['bytes'] or digest_file(path) != record['sha256']:
                raise ValueError('Image evidence digest mismatch: ' + service + '/' + name)
            sid = service.replace('-', '_') + '_' + name.replace('.', '_').replace('-', '_')
            entry = {'id': sid, 'evidence_ref': f"artifact:{artifact['id']}/{name}", 'algorithm': 'sha256', 'digest': record['sha256'], 'size_bytes': record['bytes']}
            if name in VULNERABILITY_NAMES:
                subjects_by_type['vulnerability_scan'].append(entry)
                paths_by_type['vulnerability_scan'][sid] = path
            if name in SBOM_NAMES:
                subjects_by_type['sbom'].append(entry)
                paths_by_type['sbom'][sid] = path
        if manifest['files']['image.tar']['sha256'] != subject['archive_sha256']:
            raise ValueError('Image archive subject digest mismatch')
        for name in ('archive', 'vulnerabilities', 'trivy-version'):
            execution = json.loads((paths[service] / (name + '.execution.json')).read_text())
            if execution['exit_code'] != 0 or execution.get('execution_ok') is not True:
                raise ValueError('Failed image evidence command')
        scan_command = json.loads(raw['vulnerabilities.execution.json'])['command']
        if scan_command[:2] != ['trivy', 'image'] or scan_command[-1] != subject['image_id'] or '--image-src' not in scan_command or (scan_command[scan_command.index('--image-src') + 1] != 'docker'):
            raise ValueError('Scan command is not bound to the archived image')
        version_lines = (paths[service] / 'trivy-version.log').read_text().splitlines()
        version = next((line.split(':', 1)[1].strip() for line in version_lines if line.startswith('Version:')), '')
        if not version:
            raise ValueError('Missing Trivy version')
        versions.add(version)
        layers = verify_docker_archive(paths[service] / 'image.tar', subject['image_id'], run['head_sha'])
        produced_times.append(manifest['context']['observed_at'])
        common_image = {'service': service, 'image_id': subject['image_id'], 'artifact_id': str(artifact['id']), 'artifact_name': artifact['name'], 'artifact_archive_sha256': artifact['verified_zip_sha256'], 'archive_sha256': subject['archive_sha256'], 'archive_digest_verified': True, 'image_layers_verified': layers}
        vulnerability_images.append({**common_image, 'counts': measured['images'][service]['counts']})
        expected_declaration = {'artifact_name': 'l1-image-' + service, 'image_id': subject['image_id'], 'archive_sha256': subject['archive_sha256']}
        if profile == PROFILE:
            sbom_execution = json.loads((paths[service] / 'sbom.execution.json').read_text())
            if sbom_execution['exit_code'] != 0 or sbom_execution.get('execution_ok') is not True:
                raise ValueError('Failed SBOM evidence command')
            command = sbom_execution['command']
            if command[:2] != ['trivy', 'image'] or command[-1] != subject['image_id'] or '--image-src' not in command or (command[command.index('--image-src') + 1] != 'docker') or ('--format' not in command) or (command[command.index('--format') + 1] != 'cyclonedx'):
                raise ValueError('SBOM command is not bound to the archived image')
            sbom = json.loads((paths[service] / 'sbom.cyclonedx.json').read_text())
            component = sbom.get('metadata', {}).get('component', {})
            properties = {item.get('name'): item.get('value') for item in component.get('properties', [])}
            components = sbom.get('components', [])
            if sbom.get('bomFormat') != 'CycloneDX' or not sbom.get('specVersion') or (not components) or (component.get('type') != 'container') or (properties.get('aquasecurity:trivy:ImageID') != subject['image_id']):
                raise ValueError('SBOM format, contents or image binding is invalid')
            spec_versions.add(sbom['specVersion'])
            sbom_sha256 = manifest['files']['sbom.cyclonedx.json']['sha256']
            expected_declaration.update({'sbom_sha256': sbom_sha256, 'sbom_component_count': len(components)})
            sbom_images.append({**common_image, 'sbom_sha256': sbom_sha256, 'sbom_digest_verified': True, 'component_count': len(components)})
        if declaration['images'][service] != expected_declaration:
            raise ValueError('Container declaration differs from image evidence')
    if len(versions) != 1:
        raise ValueError('Mixed scanner versions')
    counts = measured['counts']
    severity = next((s.lower() for s in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'UNKNOWN') if counts[s]), 'none')
    observations = {'profile': profile, 'scanner': {'name': 'trivy', 'version': next(iter(versions))}, 'finding_count': sum(counts.values()), 'observed_max_severity': severity, 'declared_max_severity': severity, 'severity_consistent': True, 'subject_binding': {'mode': 'co_collected', 'scanner_attested': False}, 'container_images': vulnerability_images, 'independent_attestation': False}
    produced_at = min(produced_times, key=lambda value: datetime.fromisoformat(value.replace('Z', '+00:00')))
    trust = build_typed_trust_capture(evidence_type='vulnerability_scan', governance_domain='devsecops', collector_id='central-ha-container-collector', collector_version='0.2.0', source_provider='ci_artifact', repository_id=REPOSITORY, commit_id=run['head_sha'], workflow_name=run['name'], run_id=str(run['id']), run_attempt=run['run_attempt'], artifact_name='l1-control-coverage', source_uri=run['html_url'], produced_at=produced_at, captured_at=verified_at, subjects=subjects_by_type['vulnerability_scan'], observations=observations)
    baseline_resolution = resolve_baseline(run, report, baseline_run=baseline_run)
    observations['baseline_resolution'] = baseline_resolution
    observations['governance_baseline'] = {'ref': baseline_resolution.get('workflow_ref'), 'sha': baseline_resolution.get('workflow_sha')}
    if coverage_artifact is None:
        coverage_artifact = {'id': 'missing', 'name': 'l1-control-coverage'}
    vulnerability_custody = build_custody_record(run, coverage_artifact, bundles, subjects_by_type['vulnerability_scan'], observations, verified_at)
    trusts = {'vulnerability_scan': verify_native_trust(trust, repository_id=REPOSITORY, commit_id=run['head_sha'], run_id=str(run['id']), artifact_name='l1-control-coverage', subject_paths=paths_by_type['vulnerability_scan'], verified_at=verified_at, freshness_policy=load_freshness_policy(ROOT / 'model/evidence/evidence-freshness-policies.yaml', 'freshness-vulnerability-scan-24h'), produced_at=produced_at, baseline={'ref': baseline_resolution.get('workflow_ref'), 'sha': baseline_resolution.get('workflow_sha'), 'evidence_refs': baseline_resolution.get('evidence_refs', [])}, baseline_ref=baseline_resolution.get('baseline_ref'), custody_record=vulnerability_custody, verifier_id='central-ha-container-trust-intake/v3')}
    if profile == PROFILE:
        if len(spec_versions) != 1:
            raise ValueError('Mixed CycloneDX versions')
        sbom_observations = {'profile': PROFILE, 'generator': {'name': 'trivy', 'version': next(iter(versions))}, 'format': {'name': 'CycloneDX', 'version': next(iter(spec_versions))}, 'component_count': sum((image['component_count'] for image in sbom_images)), 'subject_binding': {'mode': 'co_collected', 'producer_attested': False}, 'container_images': sbom_images, 'independent_attestation': False}
        sbom_observations['baseline_resolution'] = baseline_resolution
        sbom_trust = build_typed_trust_capture(evidence_type='sbom', governance_domain='devsecops', collector_id='central-ha-container-sbom-collector', collector_version='0.1.0', source_provider='ci_artifact', repository_id=REPOSITORY, commit_id=run['head_sha'], workflow_name=run['name'], run_id=str(run['id']), run_attempt=run['run_attempt'], artifact_name='l1-control-coverage', source_uri=run['html_url'], produced_at=produced_at, captured_at=verified_at, subjects=subjects_by_type['sbom'], observations=sbom_observations)
        sbom_custody = build_custody_record(run, coverage_artifact, bundles, subjects_by_type['sbom'], sbom_observations, verified_at)
        trusts['sbom'] = verify_native_trust(sbom_trust, repository_id=REPOSITORY, commit_id=run['head_sha'], run_id=str(run['id']), artifact_name='l1-control-coverage', subject_paths=paths_by_type['sbom'], verified_at=verified_at, freshness_policy=load_freshness_policy(ROOT / 'model/evidence/evidence-freshness-policies.yaml', 'freshness-sbom-subject-bound'), produced_at=produced_at, freshness_subject_bound=True, baseline={'ref': baseline_resolution.get('workflow_ref'), 'sha': baseline_resolution.get('workflow_sha'), 'evidence_refs': baseline_resolution.get('evidence_refs', [])}, baseline_ref=baseline_resolution.get('baseline_ref'), custody_record=sbom_custody, verifier_id='central-ha-container-sbom-intake/v2')
    return trusts
