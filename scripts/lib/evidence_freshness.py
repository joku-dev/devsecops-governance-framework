"""Neutral explicit-context logic extracted from frozen V1 6b557fefe295b58272d2271326576ca3a3687197.

Legacy storage and source CLI dispatch are deliberately excluded.
"""
from datetime import datetime
from pathlib import Path
import yaml

def load_freshness_policy(path: Path, policy_id: str) -> dict:
    policy_set = yaml.safe_load(path.read_text(encoding='utf-8'))
    policy = next((item for item in policy_set.get('policies', []) if item.get('id') == policy_id), None)
    if policy is None:
        raise ValueError(f'Unknown evidence freshness policy: {policy_id}')
    return {**policy, 'policy_set_id': policy_set['policy_set_id'], 'policy_version': policy_set['version'], 'policy_status': policy_set['status'], 'enforcement': policy_set['enforcement'], 'defaults': policy_set['defaults']}

def _parse_timestamp(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None

def evaluate_freshness(policy: dict, *, produced_at: str | None, evaluated_at: str, subject_bound: bool | None=None) -> dict:
    defaults = policy['defaults']
    mode = policy.get('evaluation_mode')
    evidence_refs = [policy['subject_claim']] if mode == 'subject_bound' else [policy.get('produced_at_claim', 'trust.capture.produced_at'), policy.get('evaluated_at_claim', 'trust.verified_at')]
    check = {'id': 'freshness_evaluated', 'result': defaults['missing_metadata_result'], 'evidence_refs': evidence_refs, 'policy_id': policy['id'], 'policy_version': policy['policy_version'], 'policy_status': policy['policy_status'], 'produced_at': produced_at, 'evaluated_at': evaluated_at, 'maximum_age_seconds': policy.get('maximum_age_seconds'), 'finding_effect': defaults['finding_effect'], 'reason': 'Required freshness timestamps are missing or invalid.'}
    if mode == 'subject_bound':
        if subject_bound is not None:
            check['result'] = 'pass' if subject_bound else 'fail'
            check['reason'] = 'Evidence is bound to the centrally verified immutable subject.' if subject_bound else 'Evidence is not bound to the centrally verified immutable subject.'
        return check
    produced = _parse_timestamp(produced_at)
    evaluated = _parse_timestamp(evaluated_at)
    if mode != 'max_age' or produced is None or evaluated is None:
        return check
    age_seconds = int((evaluated - produced).total_seconds())
    check['age_seconds'] = age_seconds
    maximum_age = policy['maximum_age_seconds']
    if age_seconds < 0:
        check['result'] = defaults['future_timestamp_result']
        check['reason'] = 'Evidence production time is later than the verification time.'
    elif age_seconds > maximum_age:
        check['result'] = defaults['expired_result']
        check['reason'] = f'Evidence age {age_seconds}s exceeds the provisional maximum {maximum_age}s.'
    else:
        check['result'] = 'pass'
        check['reason'] = f'Evidence age {age_seconds}s is within the provisional maximum {maximum_age}s.'
    return check
