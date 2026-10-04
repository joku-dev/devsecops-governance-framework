"""Read-only, validated consumer case summary for the presentation layer."""
from pathlib import Path
from jsonschema import ValidationError

from lib.governance_lifecycle.consumer_acceptance import validate
from lib.governance_lifecycle.consumer_actions import load_context


def load_consumer_case(root: Path):
    try:
        index = validate(root)
        _, _, receipts, actions = load_context(root)
    except (ValueError, OSError, ValidationError):
        return {'available': False}
    timeline = []
    for folder, records in (('observations', receipts), ('actions', actions)):
        for record in records:
            body = record.get('request', {}).get('body', {})
            suffix = record['transaction_id'].split(':', 1)[1]
            timeline.append({
                'recorded_at': record['recorded_at'],
                'kind': body.get('kind', 'observation'),
                'status': body.get('progress', record.get('criterion', {}).get('status', '')),
                'outcome': record['outcome'],
                'source_file': f"governance/consumer-lifecycle/{folder}/transactions/{record['sequence']:08d}-{suffix}.json",
            })
    return {
        'available': True, 'repository_id': index['scope']['repository_id'],
        'rule_id': index['scope']['rule_id'], 'finding_state': index['finding_state'],
        'effective': index['operating_acceptance']['effective'],
        'as_of': index['as_of'], 'counts': index['counts'],
        'timeline': sorted(timeline, key=lambda item: item['recorded_at']),
    }
