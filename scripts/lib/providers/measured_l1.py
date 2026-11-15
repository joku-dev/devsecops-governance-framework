"""Native measured-evidence bindings, extracted from frozen V1 6b557fefe295b58272d2271326576ca3a3687197.

Source: scripts/lib/measured_l1.py. Only explicit native normalization is exposed;
shared control decisions live in lib.measurement_logic. No source CLI dispatch.
"""
from lib.measurement_logic import decode_json, evaluate as evaluate_controls

from collections import Counter

from datetime import datetime

import hashlib

import json

from pathlib import Path

import re

import xml.etree.ElementTree as ET

from jsonschema import Draft202012Validator, FormatChecker

from lib.providers.measured_security import ROOT, SERVICES, REPOSITORY, check_run, normalize as security_normalize

PROFILE = 'ha-cpswms-l1-measured-v2'

LEGACY_PROFILE = 'ha-cpswms-l1-measured-v1'

BASELINE = 'l1-baseline-v1.1.3'

MAX_JUNIT_BYTES = 32 * 1024 * 1024

STATES = ('measured', 'partial', 'findings', 'gap')

LEGACY_FILES = {
    'source': ('junit.xml', 'tests.execution.json', 'bandit.json', 'bandit.execution.json',
               'ruff.json', 'ruff.execution.json', 'installed-tools.log'),
    'platform': ('commit.json', 'pulls.json', 'protection.json', 'rules.json', 'environments.json', 'run.json'),
    'runtime': ('junit.xml', 'runtime-tests.execution.json', 'deployment.json', 'query-api.log', 'neo4j.log'),
}

IMAGE_FILES = ('subject.json', 'image-metadata.json', 'sbom.cyclonedx.json', 'vulnerabilities.json',
               'build.execution.json', 'sbom.execution.json', 'vulnerabilities.execution.json',
               'archive.execution.json', 'trivy-version.log')

LEGACY_FILES.update({'image-' + s: IMAGE_FILES for s in SERVICES})

DEPENDENCY_PROFILES = ('ha-sync', 'query-api', 'semantic-enrichment', 'world-model-chat', 'application', 'ci')

DEPENDENCY_FILES = (
    'dependency-locks.json',
    'dependency-sbom-application.cyclonedx.json', 'dependency-sbom-application.execution.json',
    'dependency-sbom-ci.cyclonedx.json', 'dependency-sbom-ci.execution.json',
    'dependency-audit.json', 'dependency-audit.execution.json',
    *(f'dependency-files/{name}.{suffix}' for name in DEPENDENCY_PROFILES for suffix in ('in', 'lock')),
)

FILES = {name: tuple(value) for name, value in LEGACY_FILES.items()}

FILES['source'] += DEPENDENCY_FILES

FILES['platform'] += ('rulesets.json', 'ruleset-details.json')

REQUIRED_CHECKS = {
    'validate-ubuntu', 'validate-debian', 'DevSecOps Governance',
    'Architecture Runtime Governance', 'L1 coverage report',
}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def artifact_binding(artifact, run, name):
    binding = artifact['workflow_run']
    if (artifact['name'] != name or artifact['expired'] or str(binding['id']) != str(run['id'])
            or binding['head_sha'] != run['head_sha'] or binding['head_branch'] != 'main'
            or binding['repository_id'] != run['repository']['id']):
        raise ValueError('Artifact/run binding mismatch: ' + name)

def raw_record(raw, artifact_id, verification):
    return {'sha256': digest(raw), 'bytes': len(raw), 'artifact_id': str(artifact_id), 'verification': verification}

def cases(raw):
    if len(raw) > MAX_JUNIT_BYTES:
        raise ValueError('JUnit evidence exceeds size limit')
    text = raw.decode('utf-8-sig')  # Producer JUnit is UTF-8; reject alternate encodings.
    if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD/entity declarations are not test evidence')
    result = []
    for case in ET.fromstring(text).iter('testcase'):  # nosec B314: DTD/entities and size are rejected above.
        state = next((s for s in ('error', 'failure', 'skipped') if case.find(s) is not None), 'pass')
        result.append({'class': case.get('classname', ''), 'name': case.get('name', ''), 'status': state})
    if not result:
        raise ValueError('Empty JUnit is not test evidence')
    return result

def locked_packages(raw):
    text = raw.decode('utf-8')
    packages = {}
    matches = list(re.finditer(
        r'(?m)^([A-Za-z0-9_.-]+)==([^\s\\]+)(.*?)(?=^[A-Za-z0-9_.-]+==|\Z)',
        text, re.DOTALL))
    for match in matches:
        name, version, block = match.groups()
        if '--hash=sha256:' not in block:
            raise ValueError('Unhashed dependency lock entry: ' + name)
        packages[name.lower().replace('_', '-')] = version
    if not packages:
        raise ValueError('Dependency lock has no exact pins')
    return packages

def dependency_observation(source_files, source):
    record = source['dependency-locks.json']
    if record.get('python') != '3.12' or set(record.get('locks', {})) != set(DEPENDENCY_PROFILES):
        raise ValueError('Dependency lock profiles are incomplete')
    packages = {}
    profiles = {}
    for name in DEPENDENCY_PROFILES:
        item = record['locks'][name]
        input_name = f'dependency-files/{name}.in'
        lock_name = f'dependency-files/{name}.lock'
        if (item.get('evidence_input') != input_name or item.get('evidence_lock') != lock_name
                or digest(source_files[input_name]) != item.get('input_sha256')
                or digest(source_files[lock_name]) != item.get('lock_sha256')
                or item.get('hashes_required') is not True):
            raise ValueError('Dependency lock byte binding invalid: ' + name)
        packages[name] = locked_packages(source_files[lock_name])
        if len(packages[name]) != item.get('package_count'):
            raise ValueError('Dependency lock package count mismatch: ' + name)
        profiles[name] = {
            'package_count': len(packages[name]),
            'input_sha256': item['input_sha256'],
            'lock_sha256': item['lock_sha256'],
        }
    for service in DEPENDENCY_PROFILES[:4]:
        if not set(packages[service].items()).issubset(set(packages['application'].items())):
            raise ValueError('Application dependency inventory omits ' + service)
    if not set(packages['application'].items()).issubset(set(packages['ci'].items())):
        raise ValueError('CI dependency inventory omits application packages')
    components = {}
    for profile in ('application', 'ci'):
        sbom = source[f'dependency-sbom-{profile}.cyclonedx.json']
        execution = source[f'dependency-sbom-{profile}.execution.json']
        if (sbom.get('bomFormat') != 'CycloneDX'
                or len(sbom.get('components', [])) < len(packages[profile])
                or execution.get('exit_code') != 0):
            raise ValueError('Dependency SBOM invalid: ' + profile)
        components[profile] = len(sbom['components'])
    audit = source['dependency-audit.json']
    audit_execution = source['dependency-audit.execution.json']
    if (not isinstance(audit.get('dependencies'), list)
            or audit_execution.get('exit_code') not in (0, 1)):
        raise ValueError('Dependency audit invalid')
    vulnerabilities = [finding for dependency in audit['dependencies'] for finding in dependency.get('vulns', [])]
    return {
        'python': '3.12',
        'resolver': record.get('resolver'),
        'profiles': profiles,
        'application_sbom_components': components['application'],
        'ci_sbom_components': components['ci'],
        'vulnerability_count': len(vulnerabilities),
        'execution_ok': True,
    }

def main_ruleset(platform):
    listing = platform['rulesets.json']
    details = platform['ruleset-details.json']
    if listing.get('http_status') != 200 or not isinstance(listing.get('data'), list) or not isinstance(details, list):
        return None
    by_id = {row.get('data', {}).get('id'): row for row in details}
    for summary in listing['data']:
        ruleset_id = summary.get('id')
        response = by_id.get(ruleset_id, {})
        if response.get('http_status') != 200:
            continue
        detail = response.get('data', {})
        includes = set(detail.get('conditions', {}).get('ref_name', {}).get('include', []))
        rules = {rule.get('type'): rule for rule in detail.get('rules', [])}
        checks = {item.get('context') for item in rules.get('required_status_checks', {}).get(
            'parameters', {}).get('required_status_checks', [])}
        required_rules = {'deletion', 'non_fast_forward', 'pull_request', 'required_status_checks'}
        if (detail.get('enforcement') == 'active'
                and ('refs/heads/main' in includes or '~DEFAULT_BRANCH' in includes)
                and not detail.get('bypass_actors') and required_rules.issubset(rules)
                and REQUIRED_CHECKS.issubset(checks)):
            return {
                'id': ruleset_id,
                'name': detail.get('name'),
                'required_checks': sorted(checks),
                'required_approvals': rules['pull_request'].get('parameters', {}).get(
                    'required_approving_review_count'),
            }
    return None

NATIVE_LABELS = {'scm_api': 'GitHub API', 'ci': 'GitHub Actions', 'artifacts': 'GitHub Artifacts'}


def evaluate(observed, refs):
    return evaluate_controls(observed, refs, services=SERVICES, labels=NATIVE_LABELS)

def normalize(run, report_raw, report_artifact, bundles, traceability_raw):
    check_run(run, run['repository']['full_name'], run['id'])
    artifact_binding(report_artifact, run, 'l1-control-coverage')
    report = decode_json(report_raw)
    expected = {'repository': REPOSITORY, 'commit': run['head_sha'], 'run_id': str(run['id']),
                'attempt': str(run['run_attempt']), 'event': 'push'}
    if (any(report['context'].get(k) != v for k, v in expected.items()) or report.get('reference_baseline') != BASELINE
            or report.get('report_type') != 'l1-measured-evidence-coverage' or report.get('evidence_errors') != {}
            or report.get('enforcement') != 'report-only' or report.get('official_compliance_result') is not False
            or report.get('production_approval') is not False):
        raise ValueError('Incompatible coverage context or contract')
    producer_ids = [r['control_id'] for r in report['controls']]
    if sorted(producer_ids) != [f'DSCB-L1-REQ-{n:03}' for n in range(1, 17)]:
        raise ValueError('Incomplete or duplicate producer controls')
    sources = {'report/l1-coverage.json': raw_record(report_raw, report_artifact['id'], 'github_artifact_context'),
               'repository/quality/traceability.json': raw_record(traceability_raw, 'repository', 'git_commit_content')}
    parsed = {}
    for name, required in FILES.items():
        files, artifact = bundles[name]
        artifact_binding(artifact, run, 'l1-' + name)
        manifest = decode_json(files['manifest.json'])
        if any(manifest['context'].get(k) != v for k, v in expected.items()):
            raise ValueError('Manifest context mismatch: ' + name)
        sources[name + '/manifest.json'] = raw_record(files['manifest.json'], artifact['id'], 'github_artifact_context')
        for filename in required:
            raw = files[filename]; record = manifest['files'][filename]
            if digest(raw) != record['sha256'] or len(raw) != record['bytes']:
                raise ValueError('Raw evidence hash/size mismatch: ' + name + '/' + filename)
            sources[name + '/' + filename] = raw_record(raw, artifact['id'], 'manifest_sha256')
        parsed[name] = {n: decode_json(files[n]) for n in required if n.endswith('.json')}
    scans = security_normalize(run, report, {s: bundles['image-' + s] for s in SERVICES})
    images = {}; component_count = 0
    for s in SERVICES:
        data = parsed['image-' + s]; subject = data['subject.json']; sbom = data['sbom.cyclonedx.json']
        component = sbom.get('metadata', {}).get('component', {})
        properties = {p.get('name'): p.get('value') for p in component.get('properties', [])}
        if (sbom.get('bomFormat') != 'CycloneDX' or not sbom.get('components') or component.get('type') != 'container'
                or properties.get('aquasecurity:trivy:ImageID') != subject['image_id']
                or data['image-metadata.json']['Id'] != subject['image_id']
                or not re.fullmatch(r'[a-f0-9]{64}', subject['archive_sha256'])
                or not re.search(r'@sha256:[a-f0-9]{64}$', subject.get('python_base') or subject.get('external_image') or '')
                or any(data[n + '.execution.json']['exit_code'] != 0 for n in ('build', 'sbom', 'vulnerabilities', 'archive'))):
            raise ValueError('SBOM/image/build binding invalid: ' + s)
        component_count += len(sbom['components'])
        images[s] = {'image_id': subject['image_id'], 'archive_sha256_declared': subject['archive_sha256']}
    tests = {}; all_cases = []
    for name, execution in [('source', 'tests'), ('runtime', 'runtime-tests')]:
        found = cases(bundles[name][0]['junit.xml']); all_cases.extend(found)
        totals = Counter(c['status'] for c in found)
        tests[name] = {'passed': totals['pass'], 'failed': totals['failure'] + totals['error'],
                       'skipped': totals['skipped'], 'execution_ok': parsed[name][execution + '.execution.json']['exit_code'] == 0}
    if dict(Counter(c['status'] for c in all_cases)) != report['test_summary']:
        raise ValueError('Producer test counts disagree with raw JUnit')
    trace = decode_json(traceability_raw); linked = []
    for req in trace['requirements']:
        matched = [c for c in all_cases if c['class'].startswith(req['test_class_prefix']) and c['name'].startswith(req.get('test_name_prefix', ''))]
        linked.append({'id': req['id'], 'cases': len(matched), 'passed': bool(matched) and all(c['status'] == 'pass' for c in matched)})
    source = parsed['source']; bandit = source['bandit.json']; ruff = source['ruff.json']
    static = {'bandit': len(bandit['results']), 'ruff': len(ruff), 'execution_ok': not bool(bandit.get('errors')) and all(source[n + '.execution.json']['exit_code'] in (0, 1) for n in ('bandit', 'ruff'))}
    if {k: static[k] for k in ('bandit', 'ruff')} != report['static_analysis']:
        raise ValueError('Producer SAST counts disagree with raw reports')
    dependencies = dependency_observation(bundles['source'][0], source)
    producer_dependencies = report.get('dependency_inventory') or {}
    if (producer_dependencies.get('packages') != {
            name: value['package_count'] for name, value in dependencies['profiles'].items()}
            or producer_dependencies.get('sbom_components') != {
                'application': dependencies['application_sbom_components'],
                'ci': dependencies['ci_sbom_components']}
            or producer_dependencies.get('resolver') != dependencies['resolver']
            or report.get('dependency_vulnerability_count') != dependencies['vulnerability_count']):
        raise ValueError('Producer dependency inventory disagrees with raw evidence')
    platform = parsed['platform']; commit = platform['commit.json']; platform_run = platform['run.json']
    if platform_run['http_status'] == 200 and (str(platform_run['data']['id']) != str(run['id']) or platform_run['data']['head_sha'] != run['head_sha']):
        raise ValueError('Platform run identity mismatch')
    if commit['http_status'] == 200 and commit['data']['sha'] != run['head_sha']:
        raise ValueError('Platform commit identity mismatch')
    ruleset = main_ruleset(platform)
    if report.get('main_ruleset') != ruleset:
        raise ValueError('Producer main ruleset assessment disagrees with raw API evidence')
    deployment = parsed['runtime']['deployment.json']
    deployed = deployment['containers']
    portable_runtime = all(
        set(('runtime_image_id', 'build_config_digest', 'archive_tag')) <= set(container)
        for container in deployed
    )
    portable_binding_valid = (
        portable_runtime
        and {container['build_config_digest'] for container in deployed}
            == {images[s]['image_id'] for s in ('query-api', 'neo4j')}
        and {container['archive_tag'] for container in deployed}
            == {parsed['image-' + s]['subject.json']['archive_tag'] for s in ('query-api', 'neo4j')}
        and all(re.fullmatch(r'sha256:[a-f0-9]{64}', container['runtime_image_id']) for container in deployed)
        and len({container['runtime_image_id'] for container in deployed}) == len(deployed)
    )
    if (deployment['commit'] != run['head_sha'] or str(deployment['run_id']) != str(run['id'])
            or len(deployed) != 2 or not portable_binding_valid
            or any(c['environment'] != 'ephemeral-ci' for c in deployed)):
        raise ValueError('Runtime images/context do not match scanned CI images')
    observed = {'tests': tests, 'traceability': {'requirements': len(linked), 'matched': sum(r['passed'] for r in linked), 'links': linked},
        'static_analysis': static, 'component_count': component_count,
        'dependency_inventory': dependencies, 'vulnerability_counts': scans['counts'],
        'platform': {'author_identified': commit['http_status'] == 200 and bool((commit['data'].get('author') or {}).get('id')),
                     'protection_http': platform['protection.json']['http_status'], 'rules_http': platform['rules.json']['http_status'],
                     'rulesets_http': platform['rulesets.json']['http_status'], 'main_ruleset': ruleset,
                     'environments_http': platform['environments.json']['http_status']}, 'images': images}
    rows = evaluate(observed, sources)
    result = {'schema_version': '1.0.0', 'result_type': 'measured-l1-assessment', 'profile': PROFILE,
        'repository_id': REPOSITORY, 'reference_baseline': BASELINE, 'run': scans['run'], 'enforcement': 'report-only',
        'official_compliance_result': False, 'production_approval': False, 'risk_acceptance': False,
        'verification': {'selected_raw_files_verified': True, 'archive_digest_verified': False, 'independent_attestation': False},
        'sources': sources, 'observations': observed, 'controls': rows,
        'summary': {s: sum(r['assessment'] == s for r in rows) for s in STATES}}
    result['evidence_binding'] = binding(result)
    validate_snapshot(result)
    return result

def binding(item):
    return digest(json.dumps({'profile': item['profile'], 'run': item['run'], 'sources': item['sources']}, sort_keys=True, separators=(',', ':')).encode())

def validate_snapshot(item):
    schema = decode_json((ROOT / 'schemas/measured-l1-assessment.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    if item['evidence_binding'] != binding(item):
        raise ValueError('Evidence binding changed')
    if item['controls'] != evaluate(item['observations'], item['sources']):
        raise ValueError('Assessment differs from measured observations')
    if item['summary'] != {s: sum(r['assessment'] == s for r in item['controls']) for s in STATES}:
        raise ValueError('Assessment summary mismatch')
    profile = item['profile']
    files = FILES if profile == PROFILE else LEGACY_FILES
    if profile == PROFILE and ('dependency_inventory' not in item['observations']
                               or 'main_ruleset' not in item['observations']['platform']):
        raise ValueError('Current measured profile lacks dependency or ruleset observations')
    required_refs = {'report/l1-coverage.json', 'repository/quality/traceability.json'}
    required_refs.update(n + '/' + f for n, fs in files.items() for f in ('manifest.json', *fs))
    if set(item['sources']) != required_refs:
        raise ValueError('Incomplete or unexpected verified sources')
    for row in item['controls']:
        if not set(row['evidence_refs']) <= set(item['sources']):
            raise ValueError('Unresolved control evidence')
