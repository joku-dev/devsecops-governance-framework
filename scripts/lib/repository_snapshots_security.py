"""Original snapshot-validation decisions over explicit retained repository data.

Frozen technical reference: V1 6b557f. No provider calls, snapshot publication,
Trust elevation or operating acceptance are performed by these validators.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
SERVICES = ('ha-sync', 'query-api', 'semantic-enrichment', 'world-model-chat', 'neo4j')
SEVERITIES = ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN', 'INFO')
REPOSITORY = 'joku-dev/ha-CPsWMS'
WORKFLOW = '.github/workflows/l1-measured-evidence.yml'

class SecuritySnapshots:

    def __init__(self, root, *, validator_class, peers=None):
        self.root = root
        self.validator_class = validator_class
        self.peers = peers

    def validate_snapshot(self, item):
        schema = json.loads((self.root / 'schemas/measured-container-security.schema.json').read_text())
        self.validator_class(schema, format_checker=FormatChecker()).validate(item)
        for s in SEVERITIES:
            if item['counts'][s] != sum((i['counts'][s] for i in item['images'].values())):
                raise ValueError('Snapshot total mismatch')
            if s in ('CRITICAL', 'HIGH'):
                findings = [v for image in item['images'].values() for v in image['findings'] if v['severity'] == s]
                if len(findings) != item['counts'][s] or len({v['id'] for v in findings}) != item['unique_cves'][s]:
                    raise ValueError('Snapshot details mismatch')
                for image in item['images'].values():
                    if sum((v['severity'] == s for v in image['findings'])) != image['counts'][s]:
                        raise ValueError('Image detail count mismatch')

    def load_snapshots(self, root):
        items = []
        for path in root.rglob('*.json') if root.exists() else []:
            item = json.loads(path.read_text())
            self.validate_snapshot(item)
            items.append(item)
        return sorted(items, key=lambda i: (datetime.fromisoformat(i['run']['created_at'].replace('Z', '+00:00')), int(i['run']['id']), i['run']['attempt']))
