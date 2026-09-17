"""Read-only presentation model. Existing indexes own official result selection."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import json
import shutil

from lib.measured_security import load_snapshots
from lib.viewer_technical import project_technical
from lib.measured_security_view import assessment


def project(devsecops, architecture, snapshots):
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
    for repo in repositories.values():
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
                   load_snapshots(root / 'status/measured-security-results'))
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
