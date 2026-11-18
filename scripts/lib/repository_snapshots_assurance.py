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
import yaml
from jsonschema import Draft202012Validator, FormatChecker
_DEFAULT_ROOT = object()
PROFILE_ID = 'control-evidence-assurance-v1'
TRUST_LEVELS = ('unverified', 'integrity_verified', 'provenance_verified', 'attested')
RESULTS = ('pass', 'fail', 'not_evaluated')

class AssuranceSnapshots:

    def __init__(self, root, *, validator_class, peers=None):
        self.root = root
        self.validator_class = validator_class
        self.peers = peers
        self.profile_path = self.root / 'model' / 'evidence' / 'control-evidence-assurance-profile.yaml'
        self.policy_path = self.root / 'model' / 'evidence' / 'evidence-freshness-policies.yaml'
        self.evidence_types_path = self.root / 'model' / 'evidence' / 'evidence-types.yaml'
        self.schema_path = self.root / 'schemas' / 'control-evidence-assurance.schema.json'
        self.result_root = self.root / 'status' / 'control-evidence-assurance'

    def canonical_digest(self, value: object) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def assurance_binding(self, item: dict) -> str:
        return self.canonical_digest({key: value for key, value in item.items() if key != 'assurance_binding'})

    def load_profile(self) -> dict:
        profile = yaml.safe_load(self.profile_path.read_text(encoding='utf-8'))
        expected = {f'DSCB-L1-REQ-{number:03}' for number in range(1, 17)}
        actual = [row.get('control_id') for row in profile.get('controls', [])]
        if profile.get('profile_id') != PROFILE_ID or set(actual) != expected or len(actual) != 16:
            raise ValueError('Control assurance profile must map every L1 control exactly once')
        policies = yaml.safe_load(self.policy_path.read_text(encoding='utf-8'))
        known_policies = {row['id'] for row in policies.get('policies', [])}
        unknown = {row.get('freshness_policy') for row in profile['controls']} - known_policies
        if unknown:
            raise ValueError(f'Unknown assurance freshness policies: {sorted(unknown)}')
        evidence_types = yaml.safe_load(self.evidence_types_path.read_text(encoding='utf-8'))
        type_rows = {row['id']: row for row in evidence_types.get('evidence_types', [])}
        known_types = set(type_rows)
        unknown_types = {row.get('evidence_type') for row in profile['controls']} - known_types
        if unknown_types:
            raise ValueError(f'Unknown assurance evidence types: {sorted(unknown_types)}')
        for row in profile['controls']:
            if row['control_id'] not in type_rows[row['evidence_type']].get('supports_requirements', []):
                raise ValueError(f"Evidence type {row['evidence_type']} does not support {row['control_id']}")
            if row.get('typed_evidence_type') not in (None, 'sbom', 'vulnerability_scan'):
                raise ValueError(f"Unsupported typed evidence projection: {row['typed_evidence_type']}")
        return profile

    def validate_assurance(self, item: dict) -> None:
        schema = json.loads(self.schema_path.read_text(encoding='utf-8'))
        self.validator_class(schema, format_checker=FormatChecker()).validate(item)
        if item['assurance_binding'] != self.assurance_binding(item):
            raise ValueError('Control assurance binding changed')
        if {row['control_id'] for row in item['controls']} != {f'DSCB-L1-REQ-{n:03}' for n in range(1, 17)}:
            raise ValueError('Control assurance must contain all L1 controls')
        controls = item['controls']
        expected = {'total_controls': 16, 'coverage': {key: Counter((row['coverage'] for row in controls))[key] for key in ('complete', 'partial', 'missing')}, 'trust_levels': {key: Counter((row['effective_level'] for row in controls))[key] for key in TRUST_LEVELS}, 'freshness': {key: Counter((row['freshness']['result'] for row in controls))[key] for key in RESULTS}}
        if item['summary'] != expected:
            raise ValueError('Control assurance summary differs from controls')
        for control in controls:
            missing = [row for row in control['evidence'] if row['status'] == 'missing']
            if (control['coverage'] == 'complete') != (not missing):
                raise ValueError(f"Control assurance coverage mismatch: {control['control_id']}")
            if missing and control['effective_level'] != 'unverified':
                raise ValueError(f"Missing evidence did not downgrade control Trust: {control['control_id']}")
            if missing:
                dimensions = ('content_integrity', 'provenance', 'replay', 'custody', 'attestation')
                if any((control[key] != 'not_evaluated' for key in dimensions)):
                    raise ValueError(f"Missing evidence produced a positive Trust dimension: {control['control_id']}")
                if control['freshness']['result'] != 'not_evaluated':
                    raise ValueError(f"Missing evidence produced positive Freshness: {control['control_id']}")

    def validate_assurance_source(self, item: dict, repository_root: Path=_DEFAULT_ROOT) -> None:
        if repository_root is _DEFAULT_ROOT:
            repository_root = self.root
        'Verify that a stored assurance still points to its exact measured source.'
        source_path = repository_root / item['source_assessment']['source_file']
        try:
            source_path.resolve().relative_to(repository_root.resolve())
        except ValueError as exc:
            raise ValueError('Control assurance source escapes repository root') from exc
        if not source_path.is_file() or source_path.is_symlink():
            raise ValueError('Control assurance measured source is missing or unsafe')
        measured = json.loads(source_path.read_text(encoding='utf-8'))
        validate_snapshot = self.peers.measured.validate_snapshot
        validate_snapshot(measured)
        expected = item['source_assessment']
        if measured['repository_id'] != item['repository_id'] or measured['reference_baseline'] != item['reference_baseline'] or measured['run'] != item['run'] or (measured['result_type'] != expected['result_type']) or (measured['profile'] != expected['profile']) or (measured['evidence_binding'] != expected['evidence_binding']):
            raise ValueError('Control assurance differs from its measured source')

    def load_snapshots(self, root: Path) -> list[dict]:
        items = []
        for path in sorted(root.rglob('*.json')) if root.exists() else []:
            item = json.loads(path.read_text(encoding='utf-8'))
            self.validate_assurance(item)
            expected = item['repository_id'].replace('/', '__') + f"/run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
            if path.is_symlink() or path.relative_to(root).as_posix() != expected:
                raise ValueError('Control assurance path/identity mismatch')
            items.append(item)
        return sorted(items, key=lambda row: (datetime.fromisoformat(row['run']['created_at'].replace('Z', '+00:00')), int(row['run']['id']), row['run']['attempt']))
