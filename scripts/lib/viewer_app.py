"""Read-only presentation model. Existing indexes own official result selection."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import json
import shutil

from jsonschema import Draft202012Validator, FormatChecker

from lib.measured_security import load_snapshots
from lib.measured_l1 import load_snapshots as load_l1_snapshots
from lib.control_evidence_assurance import load_snapshots as load_assurance_snapshots
from lib.staging_deployment import load_snapshots as load_staging_snapshots
from lib.consolidated_l1 import load_snapshots as load_consolidated_l1_snapshots
from lib.viewer_technical import project_technical
from lib.measured_security_view import assessment
from lib.viewer_experience import load_consumer_case


def load_repository_security(root: Path):
    report_path = root / 'generated/reports/governance-repository-security.json'
    schema_path = root / 'schemas/governance-repository-security-report.schema.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(report)
    return {
        key: report[key]
        for key in (
            'repository_id', 'observed_at', 'profile_version', 'enforcement',
            'overall_status', 'summary', 'risk_statement', 'criteria',
            'next_steps', 'decision_boundary',
        )
    } | {
        'source_file': 'generated/reports/governance-repository-security.json',
        'human_report': 'generated/reports/governance-repository-security.md',
    }


def project(devsecops, architecture, snapshots, l1_snapshots=(), assurance_snapshots=(),
            staging_snapshots=(), consolidated_l1_snapshots=()):
    repositories = {}
    for domain, index in [('devsecops', devsecops), ('architecture', architecture)]:
        for row in index['repositories']:
            repo = repositories.setdefault(row['repository_id'], {
                'id': row['repository_id'], 'devsecops': None, 'architecture': None,
                'security': None, 'security_history': [],
            })
            # Never infer latest from history: manual/PR runs are not authoritative.
            repo[domain] = row.get('latest_result')
    grouped = defaultdict(list)
    for item in snapshots:
        grouped[item['repository_id']].append(item)
    for name, items in grouped.items():
        repo = repositories.setdefault(name, {'id': name, 'devsecops': None, 'architecture': None})
        ordered = sorted(items, key=lambda s: (datetime.fromisoformat(s['run']['created_at'].replace('Z', '+00:00')), int(s['run']['id']), s['run']['attempt']))
        repo['security'] = ordered[-1]
        repo['security_history'] = [
            {k: s[k] for k in ('run', 'counts', 'tests_passed')} for s in reversed(ordered)
        ]
    for item in l1_snapshots:
        repo = repositories.setdefault(item['repository_id'], {'id': item['repository_id'], 'devsecops': None, 'architecture': None, 'security': None, 'security_history': []})
        repo.setdefault('l1_history', []).append(item)
    for item in assurance_snapshots:
        repo = repositories.setdefault(item['repository_id'], {'id': item['repository_id'], 'devsecops': None, 'architecture': None, 'security': None, 'security_history': []})
        repo.setdefault('control_assurance_history', []).append(item)
    for item in staging_snapshots:
        repo = repositories.setdefault(item['repository_id'], {
            'id': item['repository_id'], 'devsecops': None, 'architecture': None,
            'security': None, 'security_history': [],
        })
        repo.setdefault('staging_deployment_history', []).append(item)
    for item in consolidated_l1_snapshots:
        repo = repositories.setdefault(item['repository_id'], {
            'id': item['repository_id'], 'devsecops': None, 'architecture': None,
            'security': None, 'security_history': [],
        })
        repo.setdefault('consolidated_l1_history', []).append(item)
    for repo in repositories.values():
        history = sorted(repo.get('l1_history', []), key=lambda s: (datetime.fromisoformat(s['run']['created_at'].replace('Z', '+00:00')), int(s['run']['id']), s['run']['attempt']), reverse=True)
        base_assessment = history[0] if history else None
        consolidated_history = sorted(
            repo.get('consolidated_l1_history', []),
            key=lambda s: (datetime.fromisoformat(s['run']['created_at'].replace('Z', '+00:00')),
                           int(s['run']['id']), s['run']['attempt']), reverse=True)
        matching_consolidated = next((item for item in consolidated_history
            if base_assessment and item['run'] == base_assessment['run']), None)
        repo['l1_assessment'] = matching_consolidated or base_assessment
        repo['l1_consolidated_assessment'] = matching_consolidated
        repo['l1_history'] = [{'run': s['run'], 'summary': s['summary']} for s in history]
        repo['l1_consolidated_history'] = [
            {'run': s['run'], 'summary': s['summary'], 'verified_at': s['verified_at']}
            for s in consolidated_history]
        assurance_history = sorted(repo.get('control_assurance_history', []), key=lambda s: (datetime.fromisoformat(s['run']['created_at'].replace('Z', '+00:00')), int(s['run']['id']), s['run']['attempt']), reverse=True)
        repo['control_assurance'] = assurance_history[0] if assurance_history else None
        repo['control_assurance_history'] = [
            {'run': s['run'], 'summary': s['summary'], 'verified_at': s['verified_at']} for s in assurance_history
        ]
        staging_history = sorted(
            repo.get('staging_deployment_history', []),
            key=lambda s: datetime.fromisoformat(s['deployment']['finished_at'].replace('Z', '+00:00')),
            reverse=True,
        )
        repo['staging_deployment'] = staging_history[0] if staging_history else None
        repo['staging_deployment_history'] = [
            {
                'deployed_subject': s['deployed_subject'],
                'deployment': s['deployment'],
                'tests': s['tests'],
                'trust': s['trust'],
                'source_file': s['source_file'],
            }
            for s in staging_history
        ]
        groups = {}
        current = repo.get('security')
        if current:
            for service, image in current['images'].items():
                for finding in image['findings']:
                    key = tuple(finding[k] for k in ('severity', 'id', 'package', 'installed_version', 'fixed_version'))
                    group = groups.setdefault(key, {**finding, 'images': [], 'occurrences': 0,
                                                   'assessment': assessment(finding['package'])})
                    group['occurrences'] += 1
                    if service not in group['images']:
                        group['images'].append(service)
        repo['findings'] = sorted(groups.values(), key=lambda f: (f['severity'] != 'CRITICAL', f['id'], f['package']))
    return {'version': 1, 'repositories': sorted(repositories.values(), key=lambda r: (r['id'] != 'joku-dev/ha-CPsWMS', r['id']))}


def build(root: Path, technical_html=None):
    def read(name):
        return json.loads((root / 'status' / name).read_text(encoding='utf-8'))
    data = project(read('repository-results-index.json'), read('architecture-results-index.json'),
                   load_snapshots(root / 'status/measured-security-results'),
                   load_l1_snapshots(root / 'status/measured-l1-results'),
                   load_assurance_snapshots(root / 'status/control-evidence-assurance'),
                   load_staging_snapshots(root / 'status/staging-deployment-results'),
                   load_consolidated_l1_snapshots(root / 'status/consolidated-l1-results'))
    data['repository_security'] = load_repository_security(root)
    data['consumer_case'] = load_consumer_case(root)
    if technical_html is None:
        legacy = root / 'generated/viewer/status-viewer.html'
        technical_html = legacy.read_text(encoding='utf-8') if legacy.exists() else ''
    data['technical'] = project_technical(technical_html)
    target = root / 'generated/viewer/app'
    target.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'app.css', 'app.js', 'technical.js', 'technical.css'):
        shutil.copyfile(root / 'apps/governance-viewer' / name, target / name)
    (target / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return data
