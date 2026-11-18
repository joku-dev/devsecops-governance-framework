"""Original snapshot-validation decisions over explicit retained repository data.

Frozen technical reference: V1 6b557f. No provider calls, snapshot publication,
Trust elevation or operating acceptance are performed by these validators.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
_DEFAULT_ROOT = object()
STATES = ('measured', 'partial', 'findings', 'gap')
PROFILE = 'ha-cpswms-l1-consolidated-v1'
STAGING_CONTROLS = {'DSCB-L1-REQ-013', 'DSCB-L1-REQ-014', 'DSCB-L1-REQ-016'}

class ConsolidatedSnapshots:

    def __init__(self, root, *, validator_class, peers=None):
        self.root = root
        self.validator_class = validator_class
        self.peers = peers
        self.schema = self.root / 'schemas/consolidated-l1-assessment.schema.json'
        self.result_root = self.root / 'status/consolidated-l1-results'

    def binding(self, item: dict) -> str:
        payload = {key: value for key, value in item.items() if key != 'evidence_binding'}
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _same_subject(self, measured: dict, staging: dict) -> bool:
        subject = staging['deployed_subject']
        return measured['repository_id'] == staging['repository_id'] and measured['reference_baseline'] == staging['reference_baseline'] and (measured['run']['commit'] == subject['commit']) and (measured['run']['id'] == subject['source_run_id']) and (measured['run']['attempt'] == subject['source_attempt'])

    def build_consolidated(self, measured: dict, staging: dict, *, measured_source_file: str, staging_source_file: str) -> dict:
        self.peers.measured.validate_snapshot(measured)
        self.peers.staging.validate_snapshot(staging)
        if not self._same_subject(measured, staging):
            raise ValueError('Staging deployment does not match the measured run exactly')
        staging_rows = {row['control_id']: row for row in staging['controls']}
        if set(staging_rows) != STAGING_CONTROLS:
            raise ValueError('Staging supplement has an unexpected control scope')
        controls = []
        for source in measured['controls']:
            row = deepcopy(source)
            supplement = staging_rows.get(row['control_id'])
            if supplement:
                row['assessment'] = supplement['assessment']
                row['observation'] = supplement['observation']
                row['remaining'] = supplement['remaining']
                row['tools'] = sorted(set([*row['tools'], 'Staging deployment evidence']))
                row['evidence_refs'] = [*('measured:' + ref for ref in source['evidence_refs']), *('staging:' + ref for ref in supplement['evidence_refs'])]
            else:
                row['evidence_refs'] = ['measured:' + ref for ref in row['evidence_refs']]
            controls.append(row)
        result = {'schema_version': '1.0.0', 'result_type': 'consolidated-l1-assessment', 'profile': PROFILE, 'repository_id': measured['repository_id'], 'reference_baseline': measured['reference_baseline'], 'run': deepcopy(measured['run']), 'verified_at': staging['verified_at'], 'enforcement': 'report-only', 'official_compliance_result': False, 'production_approval': False, 'risk_acceptance': False, 'source_assessments': {'measured': {'source_file': measured_source_file, 'profile': measured['profile'], 'evidence_binding': measured['evidence_binding']}, 'staging': {'source_file': staging_source_file, 'evidence_binding': staging['evidence_binding'], 'effective_level': staging['trust']['effective_level'], 'freshness': staging['trust']['freshness'], 'replay': staging['trust']['replay']}}, 'controls': controls, 'summary': {state: Counter((row['assessment'] for row in controls))[state] for state in STATES}}
        result['evidence_binding'] = self.binding(result)
        self.validate_snapshot(result)
        return result

    def validate_snapshot(self, item: dict) -> None:
        schema = json.loads(self.schema.read_text(encoding='utf-8'))
        self.validator_class(schema, format_checker=FormatChecker()).validate(item)
        if item['evidence_binding'] != self.binding(item):
            raise ValueError('Consolidated L1 evidence binding changed')
        controls = item['controls']
        if {row['control_id'] for row in controls} != {f'DSCB-L1-REQ-{number:03}' for number in range(1, 17)} or len(controls) != 16:
            raise ValueError('Consolidated L1 assessment must contain all controls exactly once')
        expected = {state: Counter((row['assessment'] for row in controls))[state] for state in STATES}
        if item['summary'] != expected:
            raise ValueError('Consolidated L1 summary differs from controls')

    def validate_sources(self, item: dict, repository_root: Path=_DEFAULT_ROOT) -> None:
        if repository_root is _DEFAULT_ROOT:
            repository_root = self.root
        sources = item['source_assessments']
        loaded = {}
        for name in ('measured', 'staging'):
            path = repository_root / sources[name]['source_file']
            try:
                path.resolve().relative_to(repository_root.resolve())
            except ValueError as exc:
                raise ValueError('Consolidated L1 source escapes repository root') from exc
            if not path.is_file() or path.is_symlink():
                raise ValueError('Consolidated L1 source is missing or unsafe')
            loaded[name] = json.loads(path.read_text(encoding='utf-8'))
        expected = self.build_consolidated(loaded['measured'], loaded['staging'], measured_source_file=sources['measured']['source_file'], staging_source_file=sources['staging']['source_file'])
        if expected != item:
            raise ValueError('Consolidated L1 assessment differs from its exact sources')

    def load_snapshots(self, root: Path) -> list[dict]:
        items = []
        for path in sorted(root.rglob('*.json')) if root.exists() else []:
            item = json.loads(path.read_text(encoding='utf-8'))
            self.validate_snapshot(item)
            expected = item['repository_id'].replace('/', '__') + f"/run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
            if path.is_symlink() or path.relative_to(root).as_posix() != expected:
                raise ValueError('Consolidated L1 snapshot path/identity mismatch')
            items.append(item)
        return sorted(items, key=lambda row: (datetime.fromisoformat(row['run']['created_at'].replace('Z', '+00:00')), int(row['run']['id']), row['run']['attempt']))
