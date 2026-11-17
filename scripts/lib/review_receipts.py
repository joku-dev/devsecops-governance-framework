"""Allowlisted receipt projection and idempotence; native freshness is checked by the application."""
import json
from lib.review_metadata import digest, parse_usage, validate_receipt, summarize_review_usage
from lib.review_planning import check_results
from lib.result_bytes import strict_json

MAX_RECEIPT = 2 * 1024**2
MAX_LOG = 16 * 1024**2
MAX_EVENTS = 10000


def build_receipt(plan, results, recorded_at, receipt_schema, results_schema):
    if plan.get('selection_mode') != 'working_tree' or not plan.get('base_commit'):
        raise ValueError('receipt_full_branch_with_base_required')
    report = check_results(plan, results, results_schema)
    value = {'schema_version': '1.0.0', 'plan_digest': plan['plan_digest'], 'results_digest': digest(results),
        'head_commit': plan['head_commit'], 'base_commit': plan['base_commit'], 'changed_paths': plan['changed_files'],
        'roles': [{**{k: row[k] for k in ('role_id', 'status', 'execution_kind')},
            'execution_declared': row['status'] in ('completed', 'failed') and bool(row['executor'].strip() and row['provider'].strip())} for row in results['reviews']],
        'validations': [{k: row[k] for k in ('command', 'status')} for row in results['validations']],
        'finding_counts': {state: {severity: sum(f['status'] == state and f['severity'] == severity for f in report['findings'])
            for severity in ('low', 'medium', 'high', 'critical')} for state in ('open', 'resolved')},
        'eligible_for_human_review': report['eligible_for_human_review'], 'evidence_kind': report['evidence_kind'],
        'independent_human_approval': False, 'recorded_at': recorded_at}
    value['receipt_id'] = digest({k: value[k] for k in ('plan_digest', 'results_digest')})
    value['receipt_digest'] = digest(value); validate_receipt(value, receipt_schema)
    if len(receipt_bytes(value)) > MAX_RECEIPT: raise ValueError('review_receipt_byte_budget')
    return value


def receipt_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def stable_projection(value):
    return {k: v for k, v in value.items() if k not in ('recorded_at', 'receipt_digest')}


def choose_receipt(candidate, before, schema):
    validate_receipt(candidate, schema)
    if before is None: return candidate, receipt_bytes(candidate), True
    if not isinstance(before, bytes) or len(before) > MAX_RECEIPT: raise ValueError('review_receipt_byte_budget')
    existing = strict_json(before); validate_receipt(existing, schema)
    if stable_projection(existing) != stable_projection(candidate): raise ValueError('existing_receipt_belongs_to_different_review')
    return existing, before, False


def usage_projection(before, receipt, schema):
    if before is None: before = b''
    if not isinstance(before, bytes) or len(before) > MAX_LOG: raise ValueError('review_usage_byte_budget')
    validate_receipt(receipt, schema); events = parse_usage(before, schema, max_events=MAX_EVENTS)
    for event in events:
        if event['receipt_id'] == receipt['receipt_id']:
            if stable_projection(event) != stable_projection(receipt): raise ValueError('conflicting_review_receipt_projection')
            return before, False
    if len(events) >= MAX_EVENTS: raise ValueError('review_usage_event_budget')
    # Preserve every existing byte and separate a valid unterminated final event.
    separator = b'\n' if before and not before.endswith(b'\n') else b''
    after = before + separator + (json.dumps(receipt, sort_keys=True) + '\n').encode()
    if len(after) > MAX_LOG: raise ValueError('review_usage_byte_budget')
    return after, True


def usage_summary(raw, schema):
    if len(raw) > MAX_LOG: raise ValueError('review_usage_byte_budget')
    return summarize_review_usage(parse_usage(raw, schema, max_events=MAX_EVENTS), schema)


def export_result(receipt, appended):
    return {'receipt_id': receipt['receipt_id'], 'head_commit': receipt['head_commit'],
        'eligible_for_human_review': receipt['eligible_for_human_review'], 'usage_appended': appended}
