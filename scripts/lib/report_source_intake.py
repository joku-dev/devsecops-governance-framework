"""Original V1 source-report semantics with explicit inert data and UTC."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
from lib.report_data import report_time
from lib import report_lineage, report_source_replacement
from lib.explicit_requirements import extract_explicit_requirements
from lib.source_document_text import SourceDocumentExtractionError, line_for_markdown_parser

def rel(data, path): return data.relative(path)
def read_text(data, path): return data.raw(path).decode('utf-8', errors='ignore')
def sha256(data, path): return hashlib.sha256(data.raw(path)).hexdigest()

def load_json(data, path): return data.json(path)
def load_yaml(data, path): return data.yaml(path)


ACTIVE_STATUSES = {'intake', 'review', 'approved'}

CLOSED_STATUSES = {'superseded', 'retired'}

TRACKING_ROLES = {'source_document_intake', 'governance_change_impact'}

def operational_artifacts(artifacts: list[dict]) -> list[dict]:
    return [artifact for artifact in artifacts if artifact.get('role') not in TRACKING_ROLES]

def similarity_assessment(document: dict) -> str:
    return document.get('similarity_assessment', {}).get('assessment', 'not_recorded')

def is_replacement_candidate(document: dict) -> bool:
    assessment = similarity_assessment(document)
    return bool(document.get('candidate_replacement_for')) or assessment in {'possible_duplicate', 'replacement_candidate', 'supersedes_existing'}

def review_state(document: dict) -> str:
    status = document.get('status')
    if status == 'candidate' and is_replacement_candidate(document):
        return 'candidate_replacement_review_required'
    if status == 'candidate' and similarity_assessment(document) == 'related_source':
        return 'candidate_related_source_review_required'
    if status == 'candidate' and similarity_assessment(document) == 'not_assessed':
        return 'candidate_similarity_review_required'
    if status == 'candidate':
        return 'candidate_decision_required'
    if status == 'draft':
        return 'draft_source_of_truth_decision_required'
    if status == 'review':
        return 'active_review_in_progress'
    if status == 'intake':
        return 'accepted_intake'
    if status == 'approved':
        return 'approved_normative_source'
    if status in CLOSED_STATUSES:
        return 'closed_source'
    return 'unknown_status'

def attention_level(document: dict) -> str:
    status = document.get('status')
    if status in {'candidate', 'draft', 'review'}:
        return 'attention'
    if status in CLOSED_STATUSES:
        return 'closed'
    if status in ACTIVE_STATUSES:
        return 'ok'
    return 'unknown'

def next_action(document: dict) -> str:
    state = review_state(document)
    actions = {'candidate_replacement_review_required': 'Review replacement decision before promoting the source or moving lineage.', 'candidate_similarity_review_required': 'Complete similarity review and decide whether the source is new, duplicate, replacement, or not relevant.', 'candidate_related_source_review_required': 'Confirm coexistence, scope boundaries, and approved derivation before promoting the related source.', 'candidate_decision_required': 'Complete candidate intake decision before deriving governance behavior.', 'draft_source_of_truth_decision_required': 'Confirm source-of-truth and approval path before treating the draft as a baseline source.', 'active_review_in_progress': 'Complete review and record the intake decision.', 'accepted_intake': 'Maintain lineage and run impact review for future source updates.', 'approved_normative_source': 'Use as a normative input only through governed derivation and release changes.', 'closed_source': 'Keep for history; do not derive new governance behavior.', 'unknown_status': 'Normalize source status in the source-document register.'}
    return actions[state]

def replacement_items_by_candidate(replacement_report: dict, register: dict) -> dict[str, list[dict]]:
    candidates = defaultdict(list)
    for item in replacement_report.get('comparisons', []):
        if item.get('classification') not in {'registered_replacement_candidate', 'replacement_candidate'}:
            continue
        candidates[item['candidate_id']].append({'target_id': item['target_id'], 'classification': item['classification'], 'title_overlap': item['title_overlap'], 'content_overlap': item['content_overlap'], 'recommendation': item['recommendation']})
    for document in register.get('documents', []):
        targets = document.get('candidate_replacement_for', [])
        for target_id in targets:
            item = {'target_id': target_id, 'classification': 'registered_replacement_candidate', 'title_overlap': None, 'content_overlap': None, 'recommendation': 'Review the registered replacement relationship before promotion.'}
            existing = candidates[document['id']]
            if not any((comparison['target_id'] == target_id for comparison in existing)):
                existing.append(item)
    return dict(candidates)

def build_report(data, at) -> dict:
    register = load_yaml(data, data.root / 'model' / 'documents' / 'source-document-register.yaml')
    lineage_report = report_lineage.build_report(data, at)
    replacement_report = report_source_replacement.build_report(data, at)
    lineage_by_source = {item['source_document']: item.get('derived_artifacts', []) for item in lineage_report.get('lineage', [])}
    replacement_by_candidate = replacement_items_by_candidate(replacement_report, register)
    status_counter = Counter()
    domain_counter = Counter()
    owner_counter = Counter()
    review_state_counter = Counter()
    attention_counter = Counter()
    documents = []
    open_items = []
    replacement_review_items = []
    for document in register.get('documents', []):
        source_path = document['source_path']
        artifacts = lineage_by_source.get(source_path, [])
        operational = operational_artifacts(artifacts)
        status = document['status']
        state = review_state(document)
        attention = attention_level(document)
        replacements = replacement_by_candidate.get(document['id'], [])
        status_counter[status] += 1
        owner_counter[document['owner']] += 1
        review_state_counter[state] += 1
        attention_counter[attention] += 1
        for domain in document.get('governance_domains', []):
            domain_counter[domain] += 1
        intake_item = {'id': document['id'], 'title': document['title'], 'status': status, 'owner': document['owner'], 'version': document['version'], 'source_path': source_path, 'governance_domains': document.get('governance_domains', []), 'intake_date': document['intake_date'], 'review_state': state, 'attention': attention, 'next_action': next_action(document), 'similarity_assessment': similarity_assessment(document), 'candidate_replacement_for': document.get('candidate_replacement_for', []), 'supersedes': document.get('supersedes'), 'superseded_by': document.get('superseded_by'), 'lineage_artifact_count': len(artifacts), 'operational_artifact_count': len(operational), 'operational_artifact_types': dict(sorted(Counter((item.get('artifact_type', 'unknown') for item in operational)).items())), 'derived_artifact_areas': document.get('derived_artifact_areas', []), 'replacement_review_items': replacements}
        documents.append(intake_item)
        if attention == 'attention':
            open_items.append({'id': intake_item['id'], 'title': intake_item['title'], 'status': intake_item['status'], 'owner': intake_item['owner'], 'review_state': intake_item['review_state'], 'next_action': intake_item['next_action']})
        if replacements:
            replacement_review_items.append({'id': intake_item['id'], 'title': intake_item['title'], 'owner': intake_item['owner'], 'candidate_replacement_for': intake_item['candidate_replacement_for'], 'comparisons': replacements, 'next_action': intake_item['next_action']})
    return {'schema_version': '1.0.0', 'generated_at': report_time(at), 'inputs': {'source_document_register': rel(data, data.root / 'model' / 'documents' / 'source-document-register.yaml'), 'source_lineage_report': rel(data, data.root / 'generated' / 'reports' / 'source-lineage-report.json'), 'architecture_source_replacement_assessment': rel(data, data.root / 'generated' / 'reports' / 'architecture-source-replacement-assessment.json')}, 'decision': {'current_state': 'report_only', 'runtime_governance_changed': False, 'stricter_rules_enabled': False}, 'summary': {'registered_source_documents': len(documents), 'status_counts': dict(sorted(status_counter.items())), 'governance_domain_counts': dict(sorted(domain_counter.items())), 'owner_counts': dict(sorted(owner_counter.items())), 'review_state_counts': dict(sorted(review_state_counter.items())), 'attention_counts': dict(sorted(attention_counter.items())), 'open_review_items': len(open_items), 'replacement_review_items': len(replacement_review_items), 'documents_with_operational_artifacts': sum((1 for item in documents if item['operational_artifact_count'] > 0)), 'documents_without_operational_artifacts': sum((1 for item in documents if item['operational_artifact_count'] == 0))}, 'open_items': open_items, 'replacement_review_items': replacement_review_items, 'documents': documents, 'process_notes': ['Candidate and draft source documents remain non-blocking until a separate governance change confirms promotion.', 'This report is informational and does not promote source documents or alter runtime governance.', 'Operational artifact counts exclude intake bookkeeping and impact-report artifacts.']}

def render_counter_table(lines: list[str], title: str, key_label: str, values: dict[str, int]) -> None:
    lines.extend(['', f'## {title}', '', f'| {key_label} | Count |', '|---|---:|'])
    for key, count in values.items():
        lines.append(f'| `{key}` | `{count}` |')

def render_markdown(report: dict) -> str:
    summary = report['summary']
    decision = report['decision']
    lines = ['# Source Document Intake Status', '', f"Generated: `{report['generated_at']}`", '', '## Decision State', '', f"- Current state: `{decision['current_state']}`", f"- Runtime governance changed: `{str(decision['runtime_governance_changed']).lower()}`", f"- Stricter rules enabled: `{str(decision['stricter_rules_enabled']).lower()}`", '', '## Summary', '', f"- Registered source documents: `{summary['registered_source_documents']}`", f"- Open review items: `{summary['open_review_items']}`", f"- Replacement review items: `{summary['replacement_review_items']}`", f"- Documents with operational artifacts: `{summary['documents_with_operational_artifacts']}`", f"- Documents without operational artifacts: `{summary['documents_without_operational_artifacts']}`"]
    render_counter_table(lines, 'Status Counts', 'Status', summary['status_counts'])
    render_counter_table(lines, 'Review State Counts', 'Review state', summary['review_state_counts'])
    render_counter_table(lines, 'Domain Counts', 'Domain', summary['governance_domain_counts'])
    lines.extend(['', '## Open Intake Items', ''])
    if report['open_items']:
        lines.extend(['| Source ID | Status | Owner | Review state | Next action |', '|---|---|---|---|---|'])
        for item in report['open_items']:
            lines.append(f"| `{item['id']}` | `{item['status']}` | `{item['owner']}` | `{item['review_state']}` | {item['next_action']} |")
    else:
        lines.append('No open intake review items.')
    lines.extend(['', '## Replacement Review Items', ''])
    if report['replacement_review_items']:
        lines.extend(['| Candidate source | Replaces | Owner | Classification | Next action |', '|---|---|---|---|---|'])
        for item in report['replacement_review_items']:
            classifications = sorted({comparison['classification'] for comparison in item['comparisons']})
            lines.append(f"| `{item['id']}` | `{', '.join(item['candidate_replacement_for'])}` | `{item['owner']}` | `{', '.join(classifications)}` | {item['next_action']} |")
    else:
        lines.append('No replacement review items.')
    lines.extend(['', '## Source Documents', ''])
    lines.extend(['| Source ID | Status | Domains | Review state | Operational artifacts |', '|---|---|---|---|---:|'])
    for item in report['documents']:
        domains = ', '.join(item['governance_domains'])
        lines.append(f"| `{item['id']}` | `{item['status']}` | `{domains}` | `{item['review_state']}` | `{item['operational_artifact_count']}` |")
    lines.extend(['', '## Process Notes', ''])
    for note in report['process_notes']:
        lines.append(f'- {note}')
    lines.append('')
    return '\n'.join(lines)
