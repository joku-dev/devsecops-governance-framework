#!/usr/bin/env python3
"""Assess architecture source document replacement candidates.

This v0.1 assessment is intentionally conservative. It uses register metadata
and lightweight text overlap signals to support review; it does not promote or
replace any source document.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "model" / "documents" / "source-document-register.yaml"
OUT_JSON = ROOT / "generated" / "reports" / "architecture-source-replacement-assessment.json"
OUT_MD = ROOT / "generated" / "reports" / "architecture-source-replacement-assessment.md"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def words(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "table",
        "architecture",
        "sdd",
    }
    return {word for word in normalize(text).split() if len(word) > 2 and word not in stop}


def extract_doc_id(text: str) -> str:
    match = re.search(r"Doc\.\s*ID:\s*\|?\s*([^|\n]+)", text, re.IGNORECASE)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def extract_title(text: str, fallback: str) -> str:
    match = re.search(r"Title:\s*\|?\s*([^|\n]+)", text, re.IGNORECASE)
    if not match:
        return fallback
    return " ".join(match.group(1).split())


def extract_headings_and_tables(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            items.append(stripped.lstrip("#").strip())
            continue
        table_match = re.search(r"Table\s+[0-9]+:\s*([^<\n]+)", stripped, re.IGNORECASE)
        if table_match:
            items.append(table_match.group(1).strip())
    return items


def document_profile(document: dict) -> dict:
    path = ROOT / document["source_path"]
    text = read_text(path)
    headings = extract_headings_and_tables(text)
    return {
        "id": document["id"],
        "title": document["title"],
        "status": document["status"],
        "source_path": document["source_path"],
        "version": document["version"],
        "doc_id": extract_doc_id(text),
        "detected_title": extract_title(text, document["title"]),
        "line_count": len(text.splitlines()),
        "word_count": len(normalize(text).split()),
        "heading_count": len(headings),
        "headings": headings,
        "tokens": words(text),
        "registered_candidate_replacement_for": document.get("candidate_replacement_for", []),
        "registered_similarity_assessment": document.get("similarity_assessment", {}),
    }


def participates_in_replacement_assessment(document: dict) -> bool:
    return document.get("version") != "requirements-only-sanitized"


def overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def classify(candidate: dict, target: dict, title_overlap: float, content_overlap: float, shared_headings: list[str]) -> str:
    registered_assessment = candidate.get("registered_similarity_assessment", {}).get("assessment")
    if target["id"] in candidate.get("registered_candidate_replacement_for", []):
        return "registered_replacement_candidate"
    if registered_assessment == "replacement_candidate":
        return "registered_replacement_candidate"
    if title_overlap >= 0.75 and content_overlap >= 0.25:
        return "replacement_candidate"
    if title_overlap >= 0.5 or len(shared_headings) >= 5:
        return "possible_related_source"
    return "independent_candidate"


def compare(candidate: dict, target: dict) -> dict:
    candidate_title_words = words(candidate["detected_title"])
    target_title_words = words(target["detected_title"])
    title_overlap = overlap_ratio(candidate_title_words, target_title_words)
    content_overlap = overlap_ratio(candidate["tokens"], target["tokens"])

    candidate_heading_counter = Counter(normalize(item) for item in candidate["headings"])
    target_heading_counter = Counter(normalize(item) for item in target["headings"])
    shared_heading_keys = sorted(set(candidate_heading_counter) & set(target_heading_counter))
    shared_headings = [
        item
        for item in candidate["headings"]
        if normalize(item) in shared_heading_keys
    ][:20]
    classification = classify(candidate, target, title_overlap, content_overlap, shared_headings)
    recommendation = {
        "registered_replacement_candidate": "Review as likely replacement before moving lineage or creating a new architecture baseline.",
        "replacement_candidate": "Review as replacement candidate; confirm scope and changed governance semantics.",
        "possible_related_source": "Review as related architecture source; do not replace existing source without further analysis.",
        "independent_candidate": "Keep as candidate or classify as separate source; no replacement action recommended yet.",
    }[classification]

    return {
        "candidate_id": candidate["id"],
        "candidate_title": candidate["title"],
        "candidate_source_path": candidate["source_path"],
        "target_id": target["id"],
        "target_title": target["title"],
        "target_source_path": target["source_path"],
        "candidate_doc_id": candidate["doc_id"],
        "target_doc_id": target["doc_id"],
        "title_overlap": round(title_overlap, 3),
        "content_overlap": round(content_overlap, 3),
        "shared_heading_count": len(shared_heading_keys),
        "shared_headings": shared_headings,
        "classification": classification,
        "recommendation": recommendation,
        "registered_candidate_replacement_for": candidate.get("registered_candidate_replacement_for", []),
        "registered_similarity_assessment": candidate.get("registered_similarity_assessment", {}),
    }


def build_report() -> dict:
    register = load_yaml(REGISTER_PATH)
    architecture_documents = [
        document
        for document in register.get("documents", [])
        if "architecture" in document.get("governance_domains", [])
    ]
    replacement_assessment_documents = [
        document
        for document in architecture_documents
        if participates_in_replacement_assessment(document)
    ]
    active_sources = [
        document_profile(document)
        for document in replacement_assessment_documents
        if document.get("status") in {"intake", "review", "approved"}
    ]
    candidates = [
        document_profile(document)
        for document in replacement_assessment_documents
        if document.get("status") == "candidate"
    ]

    comparisons = []
    for candidate in candidates:
        for target in active_sources:
            comparisons.append(compare(candidate, target))

    likely_replacements = [
        item
        for item in comparisons
        if item["classification"] in {"registered_replacement_candidate", "replacement_candidate"}
    ]

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "source_document_register": rel(REGISTER_PATH),
        },
        "summary": {
            "architecture_source_documents": len(architecture_documents),
            "active_architecture_sources": len(active_sources),
            "candidate_architecture_sources": len(candidates),
            "comparisons": len(comparisons),
            "likely_replacements": len(likely_replacements),
        },
        "active_sources": [
            {key: value for key, value in item.items() if key not in {"tokens", "headings"}}
            for item in active_sources
        ],
        "candidates": [
            {key: value for key, value in item.items() if key not in {"tokens", "headings"}}
            for item in candidates
        ],
        "comparisons": comparisons,
        "decision": {
            "current_state": "assessment_only",
            "runtime_governance_changed": False,
            "recommended_next_step": "Manually review likely replacements before changing source status, lineage, architecture YAML source_document fields, or baseline release planning.",
        },
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Architecture Source Replacement Assessment",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Architecture source documents: `{report['summary']['architecture_source_documents']}`",
        f"- Active architecture sources: `{report['summary']['active_architecture_sources']}`",
        f"- Candidate architecture sources: `{report['summary']['candidate_architecture_sources']}`",
        f"- Comparisons: `{report['summary']['comparisons']}`",
        f"- Likely replacements: `{report['summary']['likely_replacements']}`",
        "",
        "## Decision State",
        "",
        f"- Current state: `{report['decision']['current_state']}`",
        f"- Runtime governance changed: `{str(report['decision']['runtime_governance_changed']).lower()}`",
        f"- Recommended next step: {report['decision']['recommended_next_step']}",
        "",
        "## Active Architecture Sources",
        "",
        "| Source ID | Title | Version | Source path |",
        "|---|---|---|---|",
    ]
    for source in report["active_sources"]:
        lines.append(f"| `{source['id']}` | {source['title']} | `{source['version']}` | `{source['source_path']}` |")

    lines.extend(["", "## Candidate Architecture Sources", "", "| Source ID | Title | Version | Source path |", "|---|---|---|---|"])
    for candidate in report["candidates"]:
        lines.append(
            f"| `{candidate['id']}` | {candidate['title']} | `{candidate['version']}` | `{candidate['source_path']}` |"
        )

    lines.extend(["", "## Comparisons", ""])
    for item in report["comparisons"]:
        lines.extend(
            [
                f"### `{item['candidate_id']}` versus `{item['target_id']}`",
                "",
                f"- Candidate: `{item['candidate_source_path']}`",
                f"- Target: `{item['target_source_path']}`",
                f"- Candidate Doc ID: `{item['candidate_doc_id'] or 'unknown'}`",
                f"- Target Doc ID: `{item['target_doc_id'] or 'unknown'}`",
                f"- Title overlap: `{item['title_overlap']}`",
                f"- Content overlap: `{item['content_overlap']}`",
                f"- Shared headings: `{item['shared_heading_count']}`",
                f"- Classification: `{item['classification']}`",
                f"- Recommendation: {item['recommendation']}",
                "",
            ]
        )
        registered_assessment = item.get("registered_similarity_assessment", {}).get("assessment")
        if registered_assessment:
            lines.append(f"- Registered similarity assessment: `{registered_assessment}`")
        if item.get("registered_candidate_replacement_for"):
            lines.append(f"- Registered candidate replacement for: `{', '.join(item['registered_candidate_replacement_for'])}`")
        if item["shared_headings"]:
            lines.extend(["", "Shared heading examples:", ""])
            for heading in item["shared_headings"][:8]:
                lines.append(f"- {heading}")
        lines.append("")

    lines.extend(
        [
            "## Review Guidance",
            "",
            "- Do not change architecture runtime governance behavior from this report alone.",
            "- Confirm replacement manually in a change request before changing register status.",
            "- If replacement is confirmed, update `supersedes`, `superseded_by`, architecture YAML `source_document` fields, lineage, and release planning together.",
            "- A confirmed replacement will likely need a new architecture baseline release candidate.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"- likely replacements: {report['summary']['likely_replacements']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
