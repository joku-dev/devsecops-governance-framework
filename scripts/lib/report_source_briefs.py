"""Original V1 source-report semantics with explicit inert data and UTC."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
from lib.report_data import report_time
from lib import report_source_intake, report_impact
from lib.explicit_requirements import extract_explicit_requirements
from lib.source_document_text import SourceDocumentExtractionError, line_for_markdown_parser

def rel(data, path): return data.relative(path)
def read_text(data, path): return data.raw(path).decode('utf-8', errors='ignore')
def sha256(data, path): return hashlib.sha256(data.raw(path)).hexdigest()

def load_json(data, path): return data.json(path)
def load_yaml(data, path): return data.yaml(path)


def required_inputs(document: dict) -> list[str]:
    inputs = ['source document owner decision', 'change request with documented rationale', 'impact classification: documentation-only, model change, policy change, schema change, or release change']
    domains = set(document.get('governance_domains', []))
    if 'architecture' in domains:
        inputs.append('architecture owner or enterprise architect review')
    if document.get('candidate_replacement_for'):
        inputs.append('replacement confirmation against the referenced existing source')
    if document.get('status') == 'draft':
        inputs.append('source-of-truth and approval-path decision')
    return inputs

def decision_options(document: dict) -> list[dict]:
    review_state = document['review_state']
    if review_state == 'candidate_replacement_review_required':
        return [{'option': 'replacement_confirmed', 'meaning': 'Accept this source as replacing the referenced source after human review.', 'register_updates': ['set candidate status to intake or review', 'set candidate supersedes to the replaced source ID', 'set replaced source superseded_by to this source ID'], 'derived_artifacts_allowed_after_decision': True, 'release_consideration': 'architecture or baseline release candidate likely required if runtime behavior changes'}, {'option': 'related_source_keep_candidate', 'meaning': 'Keep the source registered as related material, but do not replace the active source.', 'register_updates': ['keep status as candidate or move to review', 'record why replacement was not confirmed'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}, {'option': 'duplicate_or_not_relevant_retire', 'meaning': 'Close the source for future derivation while preserving history.', 'register_updates': ['set status to retired', 'record retirement reason in notes or change request'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}]
    if review_state == 'candidate_similarity_review_required':
        return [{'option': 'new_independent_source', 'meaning': 'Accept the source as a separate intake source after review.', 'register_updates': ['set status to intake or review', 'set similarity_assessment.assessment to new_source'], 'derived_artifacts_allowed_after_decision': True, 'release_consideration': 'depends on derived governance behavior'}, {'option': 'possible_duplicate', 'meaning': 'Keep the source as a candidate until duplicate analysis is complete.', 'register_updates': ['keep status as candidate', 'set similarity_assessment.assessment to possible_duplicate'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}, {'option': 'replacement_candidate', 'meaning': 'Treat the source as a possible replacement, but require a separate replacement decision.', 'register_updates': ['keep status as candidate', 'populate candidate_replacement_for', 'set similarity_assessment.assessment to replacement_candidate'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release until replacement is confirmed'}, {'option': 'not_relevant_retire', 'meaning': 'Close the source for governed derivation.', 'register_updates': ['set status to retired', 'set similarity_assessment.assessment to not_relevant'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}]
    if review_state == 'candidate_related_source_review_required':
        return [{'option': 'related_source_confirmed', 'meaning': 'Accept the source as related material with explicit scope and coexistence boundaries.', 'register_updates': ['move status to review or intake after approval', 'retain similarity assessment as related_source', 'record approved derivation scope in the change request'], 'derived_artifacts_allowed_after_decision': True, 'release_consideration': 'depends on separately approved derived governance behavior'}, {'option': 'keep_related_candidate', 'meaning': 'Keep the related source visible for analysis without authorizing derivation.', 'register_updates': ['keep status as candidate', 'record unresolved authority, applicability, or licensing questions'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}, {'option': 'not_relevant_retire', 'meaning': 'Close the source for future derivation while preserving the review history.', 'register_updates': ['set status to retired', 'record the retirement rationale'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}]
    if review_state == 'draft_source_of_truth_decision_required':
        return [{'option': 'confirm_as_working_source', 'meaning': 'Keep the draft as governed working source material with explicit ownership.', 'register_updates': ['keep or move status according to approval decision', 'record source-of-truth decision'], 'derived_artifacts_allowed_after_decision': True, 'release_consideration': 'depends on whether downstream behavior changes'}, {'option': 'keep_draft', 'meaning': 'Keep the document visible but do not treat it as approved source material.', 'register_updates': ['keep status as draft', 'record missing approval or source-of-truth dependency'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}, {'option': 'retire_or_supersede', 'meaning': 'Close the draft if another source is authoritative.', 'register_updates': ['set status to retired or superseded', 'set superseded_by when there is a known replacement'], 'derived_artifacts_allowed_after_decision': False, 'release_consideration': 'no release by default'}]
    return [{'option': 'maintain_current_state', 'meaning': 'No decision required beyond normal lineage maintenance.', 'register_updates': [], 'derived_artifacts_allowed_after_decision': document.get('status') in {'intake', 'review', 'approved'}, 'release_consideration': 'depends on future source updates'}]

def decision_template(document: dict, impact: dict) -> dict:
    return {'source_document_id': document['id'], 'source_document_title': document['title'], 'review_decision': '<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>', 'decision_owner': document['owner'], 'decision_date': '<YYYY-MM-DD>', 'rationale': '<why this decision is correct>', 'register_updates_required': '<yes/no and fields>', 'derived_artifacts_allowed': '<yes/no>', 'runtime_governance_change': '<yes/no>', 'release_decision': impact.get('release_consideration', 'not_assessed'), 'validation_required': impact.get('suggested_validation', [])}

def review_focus(document: dict) -> str:
    state = document['review_state']
    focus = {'candidate_replacement_review_required': 'replacement decision', 'candidate_similarity_review_required': 'similarity and source classification', 'candidate_related_source_review_required': 'coexistence and derivation scope', 'draft_source_of_truth_decision_required': 'source-of-truth and approval path'}
    return focus.get(state, 'lineage maintenance')

def build_brief(document: dict, impact: dict) -> dict:
    return {'brief_id': f"SDI-REVIEW-{document['id']}", 'prepared_by_agent': 'source-document-intake', 'agent_scope': 'decision_support_only', 'autonomous_decision': False, 'decision_authority': document['owner'], 'review_focus': review_focus(document), 'source_document': {'id': document['id'], 'title': document['title'], 'status': document['status'], 'owner': document['owner'], 'version': document['version'], 'source_path': document['source_path'], 'governance_domains': document.get('governance_domains', []), 'review_state': document['review_state'], 'similarity_assessment': document.get('similarity_assessment'), 'candidate_replacement_for': document.get('candidate_replacement_for', [])}, 'agent_observations': [f"Current status is {document['status']}.", f"Review state is {document['review_state']}.", f"Operational artifact count is {document['operational_artifact_count']}.", f"Impact release consideration is {impact.get('release_consideration', 'not_assessed')}."], 'required_inputs': required_inputs(document), 'decision_options': decision_options(document), 'decision_template': decision_template(document, impact), 'guardrails': ['The agent must not promote the source document.', 'The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.', 'A human-owned change request must record the final decision.']}

def build_report(data, at) -> dict:
    intake_status = report_source_intake.build_report(data, at)
    impact_report = report_impact.build_report(data, at)
    impact_by_id = {item['id']: item for item in impact_report.get('source_impacts', [])}
    review_documents = [item for item in intake_status.get('documents', []) if item.get('attention') == 'attention']
    briefs = [build_brief(document, impact_by_id.get(document['id'], {})) for document in review_documents]
    focus_counts = Counter((brief['review_focus'] for brief in briefs))
    return {'schema_version': '1.0.0', 'generated_at': report_time(at), 'inputs': {'source_document_intake_status': rel(data, data.root / 'generated' / 'reports' / 'source-document-intake-status.json'), 'governance_change_impact': rel(data, data.root / 'generated' / 'reports' / 'governance-change-impact.json')}, 'decision': {'current_state': 'decision_support_only', 'autonomous_decisions_enabled': False, 'runtime_governance_changed': False, 'stricter_rules_enabled': False}, 'summary': {'review_briefs': len(briefs), 'focus_counts': dict(sorted(focus_counts.items())), 'human_decision_required': len(briefs)}, 'review_briefs': briefs}

def render_markdown(report: dict) -> str:
    summary = report['summary']
    decision = report['decision']
    lines = ['# Source Document Intake Review Briefs', '', f"Generated: `{report['generated_at']}`", '', '## Decision State', '', f"- Current state: `{decision['current_state']}`", f"- Autonomous decisions enabled: `{str(decision['autonomous_decisions_enabled']).lower()}`", f"- Runtime governance changed: `{str(decision['runtime_governance_changed']).lower()}`", f"- Stricter rules enabled: `{str(decision['stricter_rules_enabled']).lower()}`", '', '## Summary', '', f"- Review briefs: `{summary['review_briefs']}`", f"- Human decisions required: `{summary['human_decision_required']}`", '', '## Focus Counts', '', '| Focus | Count |', '|---|---:|']
    for focus, count in summary['focus_counts'].items():
        lines.append(f'| `{focus}` | `{count}` |')
    lines.extend(['', '## Briefs', ''])
    for brief in report['review_briefs']:
        source = brief['source_document']
        lines.extend([f"### `{brief['brief_id']}`", '', f"- Prepared by agent: `{brief['prepared_by_agent']}`", f"- Agent scope: `{brief['agent_scope']}`", f"- Autonomous decision: `{str(brief['autonomous_decision']).lower()}`", f"- Decision authority: `{brief['decision_authority']}`", f"- Review focus: `{brief['review_focus']}`", f"- Source ID: `{source['id']}`", f"- Title: {source['title']}", f"- Status: `{source['status']}`", f"- Source path: `{source['source_path']}`", '', 'Agent observations:', ''])
        for observation in brief['agent_observations']:
            lines.append(f'- {observation}')
        lines.extend(['', 'Required inputs:', ''])
        for item in brief['required_inputs']:
            lines.append(f'- {item}')
        lines.extend(['', 'Decision options:', ''])
        for option in brief['decision_options']:
            lines.append(f"- `{option['option']}`: {option['meaning']}")
        template = brief['decision_template']
        lines.extend(['', 'Decision template:', '', f"- Review decision: `{template['review_decision']}`", f"- Decision owner: `{template['decision_owner']}`", f"- Decision date: `{template['decision_date']}`", f"- Derived artifacts allowed: `{template['derived_artifacts_allowed']}`", f"- Runtime governance change: `{template['runtime_governance_change']}`", f"- Release decision: `{template['release_decision']}`", '', 'Guardrails:', ''])
        for guardrail in brief['guardrails']:
            lines.append(f'- {guardrail}')
        lines.append('')
    return '\n'.join(lines)
