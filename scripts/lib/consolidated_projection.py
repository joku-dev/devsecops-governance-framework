"""Neutral explicit-context logic extracted from frozen V1 6b557fefe295b58272d2271326576ca3a3687197.

Legacy storage and source CLI dispatch are deliberately excluded.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from lib.staging_projection import validate_snapshot as validate_staging
STATES=("measured","partial","findings","gap")
STAGING_CONTROLS={"DSCB-L1-REQ-013","DSCB-L1-REQ-014","DSCB-L1-REQ-016"}

def binding(item: dict) -> str:
    payload = {key: value for key, value in item.items() if key != 'evidence_binding'}
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()

def _same_subject(measured: dict, staging: dict) -> bool:
    subject = staging['deployed_subject']
    return measured['repository_id'] == staging['repository_id'] and measured['reference_baseline'] == staging['reference_baseline'] and (measured['run']['commit'] == subject['commit']) and (measured['run']['id'] == subject['source_run_id']) and (measured['run']['attempt'] == subject['source_attempt'])

def build_consolidated(measured: dict, staging: dict, *, root: Path, profile: str, measured_source_file: str, staging_source_file: str) -> dict:
    validate_staging(staging, root=root)
    if not _same_subject(measured, staging):
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
    result = {'schema_version': '1.0.0', 'result_type': 'consolidated-l1-assessment', 'profile': profile, 'repository_id': measured['repository_id'], 'reference_baseline': measured['reference_baseline'], 'run': deepcopy(measured['run']), 'verified_at': staging['verified_at'], 'enforcement': 'report-only', 'official_compliance_result': False, 'production_approval': False, 'risk_acceptance': False, 'source_assessments': {'measured': {'source_file': measured_source_file, 'profile': measured['profile'], 'evidence_binding': measured['evidence_binding']}, 'staging': {'source_file': staging_source_file, 'evidence_binding': staging['evidence_binding'], 'effective_level': staging['trust']['effective_level'], 'freshness': staging['trust']['freshness'], 'replay': staging['trust']['replay']}}, 'controls': controls, 'summary': {state: Counter((row['assessment'] for row in controls))[state] for state in STATES}}
    result['evidence_binding'] = binding(result)
    validate_snapshot(result, root=root)
    return result

def validate_snapshot(item: dict, *, root: Path) -> None:
    schema = json.loads((root / 'schemas/consolidated-l1-assessment.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    if item['evidence_binding'] != binding(item):
        raise ValueError('Consolidated L1 evidence binding changed')
    controls = item['controls']
    if {row['control_id'] for row in controls} != {f'DSCB-L1-REQ-{number:03}' for number in range(1, 17)} or len(controls) != 16:
        raise ValueError('Consolidated L1 assessment must contain all controls exactly once')
    expected = {state: Counter((row['assessment'] for row in controls))[state] for state in STATES}
    if item['summary'] != expected:
        raise ValueError('Consolidated L1 summary differs from controls')
