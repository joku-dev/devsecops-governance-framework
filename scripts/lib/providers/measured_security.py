"""Native measured-evidence bindings, extracted from frozen V1 6b557fefe295b58272d2271326576ca3a3687197.

Source: scripts/lib/measured_security.py. Only explicit native normalization is exposed;
shared control decisions live in lib.measurement_logic. No source CLI dispatch.
"""
from lib.measurement_logic import decode_json

from collections import Counter

from datetime import datetime

import hashlib

import json

from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from lib.portable.contracts import ROOT

SERVICES = ('ha-sync', 'query-api', 'semantic-enrichment', 'world-model-chat', 'neo4j')

SEVERITIES = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN', 'INFO')

REPOSITORY = 'joku-dev/ha-CPsWMS'

WORKFLOW = '.github/workflows/l1-measured-evidence.yml'

def counts(findings):
    counter = Counter(v['severity'] for v in findings)
    return {s: counter[s] for s in SEVERITIES}

def check_run(run, repository, run_id):
    if (repository != REPOSITORY or run['repository']['full_name'] != repository
            or str(run['id']) != str(run_id) or run['head_branch'] != 'main'
            or run['event'] != 'push' or run['status'] != 'completed'
            or run['conclusion'] != 'success' or run['path'] != WORKFLOW):
        raise ValueError('Only successful main push runs of L1 Measured Evidence are admitted')

def normalize(run, report, bundles):
    repository = run['repository']['full_name']
    check_run(run, repository, run['id'])
    expected = {'repository': repository, 'commit': run['head_sha'], 'run_id': str(run['id']),
                'attempt': str(run['run_attempt']), 'event': 'push'}
    if any(report['context'].get(k) != v for k, v in expected.items()):
        raise ValueError('Coverage/run context mismatch')
    if (report.get('report_type') != 'l1-measured-evidence-coverage'
            or report.get('evidence_errors') != {} or report.get('official_compliance_result') is not False
            or report.get('enforcement') != 'report-only' or report.get('production_approval') is not False):
        raise ValueError('Incomplete or incompatible coverage report')
    images, all_findings = {}, []
    for service in SERVICES:
        files, artifact = bundles[service]
        binding = artifact['workflow_run']
        if (artifact['name'] != 'l1-image-' + service or artifact['expired']
                or str(binding['id']) != str(run['id']) or binding['head_sha'] != run['head_sha']
                or binding['head_branch'] != 'main'
                or binding['repository_id'] != run['repository']['id']):
            raise ValueError('Artifact/run mismatch')
        manifest = decode_json(files['manifest.json'])
        if any(manifest['context'].get(k) != v for k, v in expected.items()):
            raise ValueError('Image manifest context mismatch')
        for name in ('subject.json', 'vulnerabilities.json', 'vulnerabilities.execution.json'):
            record = manifest['files'][name]
            if record['sha256'] != hashlib.sha256(files[name]).hexdigest() or record['bytes'] != len(files[name]):
                raise ValueError('Changed raw evidence: ' + name)
        subject = decode_json(files['subject.json'])
        scan = decode_json(files['vulnerabilities.json'])
        execution = decode_json(files['vulnerabilities.execution.json'])
        if (subject['service'] != service or subject['commit'] != run['head_sha']
                or scan['Metadata']['ImageID'] != subject['image_id']
                or report['images'][service]['image_id'] != subject['image_id']
                or execution['exit_code'] != 0 or not scan.get('Results')):
            raise ValueError('Scan/image identity or execution mismatch')
        findings = []
        for result in scan['Results']:
            for item in result.get('Vulnerabilities', []):
                if item['Severity'] not in SEVERITIES:
                    raise ValueError('Unsupported severity')
                findings.append({'id': item['VulnerabilityID'], 'severity': item['Severity'],
                    'package': item['PkgName'], 'installed_version': item['InstalledVersion'],
                    'fixed_version': item.get('FixedVersion') or ''})
        all_findings.extend(findings)
        images[service] = {'image_id': subject['image_id'], 'counts': counts(findings),
            'findings': [v for v in findings if v['severity'] in ('HIGH', 'CRITICAL')],
            'scan_sha256': hashlib.sha256(files['vulnerabilities.json']).hexdigest(),
            'manifest_sha256': hashlib.sha256(files['manifest.json']).hexdigest(),
            'artifact_id': str(artifact['id']), 'artifact_digest': artifact.get('digest'),
            'archive_digest_verified': False}
    total = counts(all_findings)
    if any(report['vulnerability_severities'].get(s, 0) != total[s] for s in SEVERITIES):
        raise ValueError('Coverage/raw scan count mismatch')
    result = {'schema_version': '1.0.0', 'result_type': 'measured-container-security',
        'repository_id': repository, 'run': {'id': str(run['id']), 'attempt': run['run_attempt'],
            'commit': run['head_sha'], 'branch': 'main', 'event': 'push',
            'created_at': run['created_at'], 'updated_at': run['updated_at']},
        'enforcement': 'report-only', 'official_compliance_result': False, 'risk_acceptance': False,
        'verification': 'github_run_context_and_raw_file_hashes_and_image_binding',
        'independent_attestation': False, 'detail_severities': ['CRITICAL', 'HIGH'],
        'counts': total, 'unique_cves': {s: len({v['id'] for v in all_findings if v['severity'] == s}) for s in SEVERITIES},
        'tests_passed': report['test_summary']['pass'], 'images': images}
    validate_snapshot(result)
    return result

def validate_snapshot(item):
    schema = decode_json((ROOT / 'schemas/measured-container-security.schema.json').read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    for s in SEVERITIES:
        if item['counts'][s] != sum(i['counts'][s] for i in item['images'].values()):
            raise ValueError('Snapshot total mismatch')
        if s in ('CRITICAL', 'HIGH'):
            findings = [v for image in item['images'].values() for v in image['findings'] if v['severity'] == s]
            if len(findings) != item['counts'][s] or len({v['id'] for v in findings}) != item['unique_cves'][s]:
                raise ValueError('Snapshot details mismatch')
            for image in item['images'].values():
                if sum(v['severity'] == s for v in image['findings']) != image['counts'][s]:
                    raise ValueError('Image detail count mismatch')
