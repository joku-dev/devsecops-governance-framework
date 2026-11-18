"""Original snapshot-validation decisions over explicit retained repository data.

Frozen technical reference: V1 6b557f. No provider calls, snapshot publication,
Trust elevation or operating acceptance are performed by these validators.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from jsonschema import Draft202012Validator, FormatChecker
REPOSITORY = 'joku-dev/ha-CPsWMS'
BASELINE = 'l1-baseline-v1.1.3'

class StagingSnapshots:

    def __init__(self, root, *, validator_class, peers=None):
        self.root = root
        self.validator_class = validator_class
        self.peers = peers
        self.schema = self.root / 'schemas/staging-deployment-result.schema.json'
        self.result_root = self.root / 'status/staging-deployment-results'

    def digest(self, raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    def binding(self, item: dict) -> str:
        payload = {key: value for key, value in item.items() if key != 'evidence_binding'}
        return self.digest(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode())

    def validate_snapshot(self, item: dict) -> None:
        schema = json.loads(self.schema.read_text(encoding='utf-8'))
        self.validator_class(schema, format_checker=FormatChecker()).validate(item)
        if item['evidence_binding'] != self.binding(item):
            raise ValueError('Staging evidence binding changed')
        expected = {'DSCB-L1-REQ-013': 'measured', 'DSCB-L1-REQ-014': 'measured', 'DSCB-L1-REQ-016': 'partial'}
        actual = {row['control_id']: row['assessment'] for row in item['controls']}
        if actual != expected or len(item['controls']) != len(actual):
            raise ValueError('Staging control projection changed')
        if not all(item['security_boundaries'].values()):
            raise ValueError('Required staging security boundary failed')

    def load_snapshots(self, root: Path) -> list[dict]:
        items = []
        for path in sorted(root.rglob('*.json')) if root.exists() else []:
            item = json.loads(path.read_text(encoding='utf-8'))
            self.validate_snapshot(item)
            if path.is_symlink() or path.relative_to(self.root).as_posix() != item['source_file']:
                raise ValueError('Staging snapshot path/identity mismatch')
            items.append(item)
        return sorted(items, key=lambda row: datetime.fromisoformat(row['deployment']['finished_at'].replace('Z', '+00:00')))
