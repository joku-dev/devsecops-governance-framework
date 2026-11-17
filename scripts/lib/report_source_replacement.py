"""Original V1 source-report semantics with explicit inert data and UTC."""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
from lib.report_data import report_time
from lib.explicit_requirements import extract_explicit_requirements
from lib.source_document_text import SourceDocumentExtractionError, line_for_markdown_parser

def rel(data, path): return data.relative(path)
def read_text(data, path): return data.raw(path).decode('utf-8', errors='ignore')
def sha256(data, path): return hashlib.sha256(data.raw(path)).hexdigest()

def load_json(data, path): return data.json(path)
def load_yaml(data, path): return data.yaml(path)


def normalize(text: str) -> str:
    return re.sub('[^a-z0-9]+', ' ', text.lower()).strip()

def words(text: str) -> set[str]:
    stop = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'table', 'architecture', 'sdd'}
    return {word for word in normalize(text).split() if len(word) > 2 and word not in stop}

def extract_doc_id(text: str) -> str:
    match = re.search('Doc\\.\\s*ID:\\s*\\|?\\s*([^|\\n]+)', text, re.IGNORECASE)
    if not match:
        return ''
    return ' '.join(match.group(1).split())

def extract_title(text: str, fallback: str) -> str:
    match = re.search('Title:\\s*\\|?\\s*([^|\\n]+)', text, re.IGNORECASE)
    if not match:
        return fallback
    return ' '.join(match.group(1).split())

def extract_headings_and_tables(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#'):
            items.append(stripped.lstrip('#').strip())
            continue
        table_match = re.search('Table\\s+[0-9]+:\\s*([^<\\n]+)', stripped, re.IGNORECASE)
        if table_match:
            items.append(table_match.group(1).strip())
    return items

def document_profile(data, document: dict) -> dict:
    path = data.root / document['source_path']
    text = read_text(data, path)
    headings = extract_headings_and_tables(text)
    return {'id': document['id'], 'title': document['title'], 'status': document['status'], 'source_path': document['source_path'], 'version': document['version'], 'doc_id': extract_doc_id(text), 'detected_title': extract_title(text, document['title']), 'line_count': len(text.splitlines()), 'word_count': len(normalize(text).split()), 'heading_count': len(headings), 'headings': headings, 'tokens': words(text), 'registered_candidate_replacement_for': document.get('candidate_replacement_for', []), 'registered_similarity_assessment': document.get('similarity_assessment', {})}

def participates_in_replacement_assessment(document: dict) -> bool:
    return True

def overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)

def classify(candidate: dict, target: dict, title_overlap: float, content_overlap: float, shared_headings: list[str]) -> str:
    registered_assessment = candidate.get('registered_similarity_assessment', {}).get('assessment')
    registered_targets = {item.get('source_id') for item in candidate.get('registered_similarity_assessment', {}).get('compared_to', [])}
    if target['id'] in candidate.get('registered_candidate_replacement_for', []):
        return 'registered_replacement_candidate'
    if registered_assessment == 'replacement_candidate' and target['id'] in registered_targets:
        return 'registered_replacement_candidate'
    if title_overlap >= 0.75 and content_overlap >= 0.25:
        return 'replacement_candidate'
    if title_overlap >= 0.5 or len(shared_headings) >= 5:
        return 'possible_related_source'
    return 'independent_candidate'

def compare(candidate: dict, target: dict) -> dict:
    candidate_title_words = words(candidate['detected_title'])
    target_title_words = words(target['detected_title'])
    title_overlap = overlap_ratio(candidate_title_words, target_title_words)
    content_overlap = overlap_ratio(candidate['tokens'], target['tokens'])
    candidate_heading_counter = Counter((normalize(item) for item in candidate['headings']))
    target_heading_counter = Counter((normalize(item) for item in target['headings']))
    shared_heading_keys = sorted(set(candidate_heading_counter) & set(target_heading_counter))
    shared_headings = [item for item in candidate['headings'] if normalize(item) in shared_heading_keys][:20]
    classification = classify(candidate, target, title_overlap, content_overlap, shared_headings)
    recommendation = {'registered_replacement_candidate': 'Review as likely replacement before moving lineage or creating a new architecture baseline.', 'replacement_candidate': 'Review as replacement candidate; confirm scope and changed governance semantics.', 'possible_related_source': 'Review as related architecture source; do not replace existing source without further analysis.', 'independent_candidate': 'Keep as candidate or classify as separate source; no replacement action recommended yet.'}[classification]
    return {'candidate_id': candidate['id'], 'candidate_title': candidate['title'], 'candidate_source_path': candidate['source_path'], 'target_id': target['id'], 'target_title': target['title'], 'target_source_path': target['source_path'], 'candidate_doc_id': candidate['doc_id'], 'target_doc_id': target['doc_id'], 'title_overlap': round(title_overlap, 3), 'content_overlap': round(content_overlap, 3), 'shared_heading_count': len(shared_heading_keys), 'shared_headings': shared_headings, 'classification': classification, 'recommendation': recommendation, 'registered_candidate_replacement_for': candidate.get('registered_candidate_replacement_for', []), 'registered_similarity_assessment': candidate.get('registered_similarity_assessment', {})}

def build_report(data, at) -> dict:
    register = load_yaml(data, data.root / 'model' / 'documents' / 'source-document-register.yaml')
    architecture_documents = [document for document in register.get('documents', []) if 'architecture' in document.get('governance_domains', [])]
    replacement_assessment_documents = [document for document in architecture_documents if participates_in_replacement_assessment(document)]
    active_sources = [document_profile(data, document) for document in replacement_assessment_documents if document.get('status') in {'intake', 'review', 'approved'}]
    candidates = [document_profile(data, document) for document in replacement_assessment_documents if document.get('status') == 'candidate']
    comparisons = []
    for candidate in candidates:
        for target in active_sources:
            comparisons.append(compare(candidate, target))
    likely_replacements = [item for item in comparisons if item['classification'] in {'registered_replacement_candidate', 'replacement_candidate'}]
    return {'schema_version': '1.0.0', 'generated_at': report_time(at), 'inputs': {'source_document_register': rel(data, data.root / 'model' / 'documents' / 'source-document-register.yaml')}, 'summary': {'architecture_source_documents': len(architecture_documents), 'active_architecture_sources': len(active_sources), 'candidate_architecture_sources': len(candidates), 'comparisons': len(comparisons), 'likely_replacements': len(likely_replacements)}, 'active_sources': [{key: value for key, value in item.items() if key not in {'tokens', 'headings'}} for item in active_sources], 'candidates': [{key: value for key, value in item.items() if key not in {'tokens', 'headings'}} for item in candidates], 'comparisons': comparisons, 'decision': {'current_state': 'assessment_only', 'runtime_governance_changed': False, 'recommended_next_step': 'Manually review likely replacements before changing source status, lineage, architecture YAML source_document fields, or baseline release planning.'}}

def render_markdown(report: dict) -> str:
    lines = ['# Architecture Source Replacement Assessment', '', f"Generated: `{report['generated_at']}`", '', '## Summary', '', f"- Architecture source documents: `{report['summary']['architecture_source_documents']}`", f"- Active architecture sources: `{report['summary']['active_architecture_sources']}`", f"- Candidate architecture sources: `{report['summary']['candidate_architecture_sources']}`", f"- Comparisons: `{report['summary']['comparisons']}`", f"- Likely replacements: `{report['summary']['likely_replacements']}`", '', '## Decision State', '', f"- Current state: `{report['decision']['current_state']}`", f"- Runtime governance changed: `{str(report['decision']['runtime_governance_changed']).lower()}`", f"- Recommended next step: {report['decision']['recommended_next_step']}", '', '## Active Architecture Sources', '', '| Source ID | Title | Version | Source path |', '|---|---|---|---|']
    for source in report['active_sources']:
        lines.append(f"| `{source['id']}` | {source['title']} | `{source['version']}` | `{source['source_path']}` |")
    lines.extend(['', '## Candidate Architecture Sources', '', '| Source ID | Title | Version | Source path |', '|---|---|---|---|'])
    for candidate in report['candidates']:
        lines.append(f"| `{candidate['id']}` | {candidate['title']} | `{candidate['version']}` | `{candidate['source_path']}` |")
    lines.extend(['', '## Comparisons', ''])
    for item in report['comparisons']:
        lines.extend([f"### `{item['candidate_id']}` versus `{item['target_id']}`", '', f"- Candidate: `{item['candidate_source_path']}`", f"- Target: `{item['target_source_path']}`", f"- Candidate Doc ID: `{item['candidate_doc_id'] or 'unknown'}`", f"- Target Doc ID: `{item['target_doc_id'] or 'unknown'}`", f"- Title overlap: `{item['title_overlap']}`", f"- Content overlap: `{item['content_overlap']}`", f"- Shared headings: `{item['shared_heading_count']}`", f"- Classification: `{item['classification']}`", f"- Recommendation: {item['recommendation']}", ''])
        registered_assessment = item.get('registered_similarity_assessment', {}).get('assessment')
        if registered_assessment:
            lines.append(f'- Registered similarity assessment: `{registered_assessment}`')
        if item.get('registered_candidate_replacement_for'):
            lines.append(f"- Registered candidate replacement for: `{', '.join(item['registered_candidate_replacement_for'])}`")
        if item['shared_headings']:
            lines.extend(['', 'Shared heading examples:', ''])
            for heading in item['shared_headings'][:8]:
                lines.append(f'- {heading}')
        lines.append('')
    lines.extend(['## Review Guidance', '', '- Do not change architecture runtime governance behavior from this report alone.', '- Confirm replacement manually in a change request before changing register status.', '- If replacement is confirmed, update `supersedes`, `superseded_by`, architecture YAML `source_document` fields, lineage, and release planning together.', '- A confirmed replacement will likely need a new architecture baseline release candidate.', ''])
    return '\n'.join(lines)
