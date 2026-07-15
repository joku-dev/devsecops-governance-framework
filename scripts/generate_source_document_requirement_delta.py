#!/usr/bin/env python3
"""Generate requirement-level deltas for source-document replacement candidates.

This report is intentionally conservative. It extracts normative-looking
statements from likely replacement pairs and classifies them as added, changed,
removed, or equivalent. It supports human review only and must not promote a
candidate source or change runtime governance behavior.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REPLACEMENT_JSON = ROOT / "generated" / "reports" / "architecture-source-replacement-assessment.json"
OUT_JSON = ROOT / "generated" / "reports" / "source-document-requirement-delta.json"
OUT_MD = ROOT / "generated" / "reports" / "source-document-requirement-delta.md"

NORMATIVE_PATTERN = re.compile(
    r"\b("
    r"must|shall|should|mandatory|required|requires|require|requirement|"
    r"needs to|need to|has to|have to|is required|are required|"
    r"must not|shall not|should not"
    r")\b",
    re.IGNORECASE,
)
MANDATORY_PATTERN = re.compile(
    r"\b(must|shall|mandatory|required|requires|require|needs to|need to|has to|have to|is required|are required)\b",
    re.IGNORECASE,
)
PROHIBITION_PATTERN = re.compile(r"\b(must not|shall not|should not)\b", re.IGNORECASE)
RECOMMENDED_PATTERN = re.compile(r"\b(should|recommended)\b", re.IGNORECASE)
TABLE_SEPARATOR_PATTERN = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$")
LINK_ONLY_PATTERN = re.compile(r"^\[[^\]]+\]\(#[^)]+\)$")
NON_NORMATIVE_HEADING_TERMS = (
    "abbreviation",
    "definition",
    "glossary",
    "terminology",
    "terms",
)

UNCHANGED_THRESHOLD = 0.9
MATCH_THRESHOLD = 0.5


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def run_generator(script_name: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"{script_name} failed: {details}")


def ensure_inputs() -> None:
    run_generator("generate_architecture_source_replacement_assessment.py")


def clean_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\\.", ".")
    text = text.replace("&nbsp;", " ")
    text = text.replace("|", " | ")
    return " ".join(text.split())


def normalize_statement(text: str) -> str:
    text = clean_markdown(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


@lru_cache(maxsize=4096)
def tokens_from_normalized(normalized: str) -> frozenset[str]:
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "shall",
        "must",
        "should",
        "required",
        "requires",
        "require",
        "mandatory",
    }
    return frozenset(
        token
        for token in normalized.split()
        if len(token) > 2 and token not in stop_words
    )


def stable_id(source_id: str, line_number: int, statement: str) -> str:
    digest = hashlib.sha1(f"{source_id}:{line_number}:{statement}".encode("utf-8")).hexdigest()[:10]
    return f"REQ-{source_id}-{digest}"


def requirement_strength(statement: str) -> str:
    if PROHIBITION_PATTERN.search(statement):
        return "prohibition"
    if MANDATORY_PATTERN.search(statement):
        return "mandatory"
    if RECOMMENDED_PATTERN.search(statement):
        return "recommended"
    return "review"


def potential_impacts(heading: str, statement: str) -> list[str]:
    text = f"{heading} {statement}".lower()
    impacts = set()
    if any(term in text for term in ["marker", "maturity", "score", "quality"]):
        impacts.add("quality_markers")
    if any(term in text for term in ["review", "gate", "readiness", "release-ready", "architecture-ready"]):
        impacts.add("review_gates")
    if any(term in text for term in ["evidence", "template", "field", "required content", "schema"]):
        impacts.add("evidence_contracts")
    if any(term in text for term in ["interface", "data contract", "security", "deployment", "compatibility"]):
        impacts.add("architecture_model")
    if any(term in text for term in ["must", "shall", "mandatory", "release", "baseline"]):
        impacts.add("runtime_governance_review")
    if not impacts:
        impacts.add("manual_review")
    return sorted(impacts)


def should_skip_line(stripped: str) -> bool:
    if not stripped:
        return True
    if stripped.startswith("[") and "](#" in stripped:
        return True
    if LINK_ONLY_PATTERN.match(stripped):
        return True
    if TABLE_SEPARATOR_PATTERN.match(stripped):
        return True
    return False


def extract_requirements(source_id: str, path: Path) -> list[dict]:
    requirements = []
    heading_stack: list[str] = []

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading = clean_markdown(stripped.lstrip("#").strip())
            heading_stack = heading_stack[: max(level - 1, 0)]
            heading_stack.append(heading)
            continue
        if should_skip_line(stripped):
            continue
        heading = " > ".join(item for item in heading_stack if item) or "<document>"
        heading_lower = heading.lower()
        if any(term in heading_lower for term in NON_NORMATIVE_HEADING_TERMS):
            continue
        if not NORMATIVE_PATTERN.search(stripped):
            continue

        statement = clean_markdown(stripped)
        if len(statement) < 35:
            continue
        normalized = normalize_statement(statement)
        requirement = {
            "id": stable_id(source_id, line_number, normalized),
            "source_id": source_id,
            "source_path": rel(path),
            "line": line_number,
            "heading": heading,
            "statement": statement,
            "normalized": normalized,
            "strength": requirement_strength(statement),
            "potential_impacts": potential_impacts(heading, statement),
        }
        requirements.append(requirement)

    deduplicated = []
    seen = set()
    for requirement in requirements:
        key = requirement["normalized"]
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(requirement)
    return deduplicated


def similarity(left: dict, right: dict) -> float:
    left_tokens = tokens_from_normalized(left["normalized"])
    right_tokens = tokens_from_normalized(right["normalized"])
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    containment = intersection / min(len(left_tokens), len(right_tokens))
    jaccard = intersection / union
    token_score = (0.55 * containment) + (0.45 * jaccard)
    if token_score < 0.25:
        return round(token_score, 3)
    sequence = SequenceMatcher(None, left["normalized"], right["normalized"]).ratio()
    return round(max(sequence, token_score), 3)


def best_match(requirement: dict, candidates: list[dict], unmatched_indexes: set[int]) -> tuple[int | None, float]:
    best_index = None
    best_score = 0.0
    for index in unmatched_indexes:
        score = similarity(requirement, candidates[index])
        if score > best_score:
            best_index = index
            best_score = score
    return best_index, best_score


def delta_status(score: float, candidate: dict, target: dict) -> str:
    if score >= UNCHANGED_THRESHOLD and candidate["strength"] == target["strength"]:
        return "equivalent"
    if score >= MATCH_THRESHOLD:
        return "changed"
    return "added"


def review_priority(status: str, candidate: dict | None, target: dict | None) -> str:
    strength = (candidate or target or {}).get("strength")
    if status in {"added", "removed"} and strength in {"mandatory", "prohibition"}:
        return "high"
    if status == "changed" and strength in {"mandatory", "prohibition"}:
        return "high"
    if status in {"added", "changed", "removed"}:
        return "medium"
    return "low"


def merge_impacts(candidate: dict | None, target: dict | None) -> list[str]:
    impacts = set()
    if candidate:
        impacts.update(candidate.get("potential_impacts", []))
    if target:
        impacts.update(target.get("potential_impacts", []))
    return sorted(impacts)


def compare_requirements(candidate_requirements: list[dict], target_requirements: list[dict]) -> list[dict]:
    deltas = []
    unmatched_target_indexes = set(range(len(target_requirements)))

    for candidate in candidate_requirements:
        match_index, score = best_match(candidate, target_requirements, unmatched_target_indexes)
        best_target = target_requirements[match_index] if match_index is not None else None
        status = delta_status(score, candidate, best_target) if best_target else "added"
        target = best_target if status != "added" else None
        if target is not None and match_index is not None:
            unmatched_target_indexes.remove(match_index)

        deltas.append(
            {
                "status": status,
                "similarity": score,
                "review_priority": review_priority(status, candidate, target),
                "potential_impacts": merge_impacts(candidate, target),
                "candidate_requirement": candidate,
                "target_requirement": target,
            }
        )

    for index in sorted(unmatched_target_indexes):
        target = target_requirements[index]
        deltas.append(
            {
                "status": "removed",
                "similarity": 0.0,
                "review_priority": review_priority("removed", None, target),
                "potential_impacts": merge_impacts(None, target),
                "candidate_requirement": None,
                "target_requirement": target,
            }
        )

    return sorted(
        deltas,
        key=lambda item: (
            {"high": 0, "medium": 1, "low": 2}.get(item["review_priority"], 3),
            {"added": 0, "changed": 1, "removed": 2, "equivalent": 3}.get(item["status"], 4),
            (item.get("candidate_requirement") or item.get("target_requirement") or {}).get("source_id", ""),
            (item.get("candidate_requirement") or item.get("target_requirement") or {}).get("line", 0),
        ),
    )


def likely_replacement_pairs(replacement_report: dict) -> list[dict]:
    return [
        item
        for item in replacement_report.get("comparisons", [])
        if item.get("classification") in {"registered_replacement_candidate", "replacement_candidate"}
    ]


def build_pair_delta(comparison: dict) -> dict:
    candidate_path = ROOT / comparison["candidate_source_path"]
    target_path = ROOT / comparison["target_source_path"]
    candidate_requirements = extract_requirements(comparison["candidate_id"], candidate_path)
    target_requirements = extract_requirements(comparison["target_id"], target_path)
    deltas = compare_requirements(candidate_requirements, target_requirements)
    status_counts = Counter(item["status"] for item in deltas)
    priority_counts = Counter(item["review_priority"] for item in deltas)
    impact_counts = Counter(impact for item in deltas for impact in item["potential_impacts"])

    return {
        "candidate_id": comparison["candidate_id"],
        "candidate_title": comparison["candidate_title"],
        "candidate_source_path": comparison["candidate_source_path"],
        "target_id": comparison["target_id"],
        "target_title": comparison["target_title"],
        "target_source_path": comparison["target_source_path"],
        "replacement_classification": comparison["classification"],
        "source_similarity": {
            "title_overlap": comparison["title_overlap"],
            "content_overlap": comparison["content_overlap"],
            "shared_heading_count": comparison["shared_heading_count"],
        },
        "summary": {
            "candidate_requirements": len(candidate_requirements),
            "target_requirements": len(target_requirements),
            "deltas": len(deltas),
            "status_counts": dict(sorted(status_counts.items())),
            "review_priority_counts": dict(sorted(priority_counts.items())),
            "potential_impact_counts": dict(sorted(impact_counts.items())),
            "differences_requiring_review": sum(
                status_counts.get(status, 0)
                for status in ["added", "changed", "removed"]
            ),
        },
        "deltas": deltas,
    }


def build_report() -> dict:
    ensure_inputs()
    replacement_report = load_json(REPLACEMENT_JSON)
    pair_deltas = [build_pair_delta(pair) for pair in likely_replacement_pairs(replacement_report)]
    aggregate_status = Counter()
    aggregate_priority = Counter()
    aggregate_impacts = Counter()
    for pair in pair_deltas:
        aggregate_status.update(pair["summary"]["status_counts"])
        aggregate_priority.update(pair["summary"]["review_priority_counts"])
        aggregate_impacts.update(pair["summary"]["potential_impact_counts"])

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "architecture_source_replacement_assessment": rel(REPLACEMENT_JSON),
        },
        "decision": {
            "current_state": "review_support_only",
            "runtime_governance_changed": False,
            "candidate_promoted": False,
            "stricter_rules_enabled": False,
        },
        "summary": {
            "replacement_pairs": len(pair_deltas),
            "status_counts": dict(sorted(aggregate_status.items())),
            "review_priority_counts": dict(sorted(aggregate_priority.items())),
            "potential_impact_counts": dict(sorted(aggregate_impacts.items())),
        },
        "requirement_delta_pairs": pair_deltas,
        "review_notes": [
            "This is a keyword-based normative statement delta, not a final legal or architecture decision.",
            "Changed, added, and removed mandatory or prohibition statements require human architecture-owner review.",
            "Removed statements may indicate content deleted from the candidate or moved into companion documents; confirm against the full architecture source set before deciding.",
            "No source document status, lineage, runtime governance, policy, schema, or release package is changed by this report.",
        ],
    }


def requirement_ref(requirement: dict | None) -> str:
    if not requirement:
        return "`n/a`"
    return f"`{requirement['source_path']}:{requirement['line']}`"


def requirement_text(requirement: dict | None) -> str:
    if not requirement:
        return ""
    statement = requirement["statement"]
    statement = statement if len(statement) <= 220 else statement[:217].rstrip() + "..."
    return statement.replace("|", "\\|")


def render_delta_table(lines: list[str], title: str, deltas: list[dict]) -> None:
    lines.extend(["", f"### {title}", ""])
    if not deltas:
        lines.append("No items.")
        return
    lines.extend(
        [
            "| Priority | Candidate ref | Target ref | Similarity | Potential impacts | Candidate statement | Target statement |",
            "|---|---|---|---:|---|---|---|",
        ]
    )
    for item in deltas:
        lines.append(
            f"| `{item['review_priority']}` | {requirement_ref(item['candidate_requirement'])} | "
            f"{requirement_ref(item['target_requirement'])} | `{item['similarity']}` | "
            f"`{', '.join(item['potential_impacts'])}` | {requirement_text(item['candidate_requirement'])} | "
            f"{requirement_text(item['target_requirement'])} |"
        )


def render_markdown(report: dict) -> str:
    decision = report["decision"]
    summary = report["summary"]
    lines = [
        "# Source Document Requirement Delta",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Decision State",
        "",
        f"- Current state: `{decision['current_state']}`",
        f"- Runtime governance changed: `{str(decision['runtime_governance_changed']).lower()}`",
        f"- Candidate promoted: `{str(decision['candidate_promoted']).lower()}`",
        f"- Stricter rules enabled: `{str(decision['stricter_rules_enabled']).lower()}`",
        "",
        "## Summary",
        "",
        f"- Replacement pairs: `{summary['replacement_pairs']}`",
        "",
        "### Status Counts",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in summary["status_counts"].items():
        lines.append(f"| `{status}` | `{count}` |")

    lines.extend(["", "### Review Priority Counts", "", "| Priority | Count |", "|---|---:|"])
    for priority, count in summary["review_priority_counts"].items():
        lines.append(f"| `{priority}` | `{count}` |")

    lines.extend(["", "## Replacement Pair Deltas", ""])
    for pair in report["requirement_delta_pairs"]:
        pair_summary = pair["summary"]
        lines.extend(
            [
                f"### `{pair['candidate_id']}` versus `{pair['target_id']}`",
                "",
                f"- Candidate: `{pair['candidate_source_path']}`",
                f"- Target: `{pair['target_source_path']}`",
                f"- Replacement classification: `{pair['replacement_classification']}`",
                f"- Candidate requirement statements: `{pair_summary['candidate_requirements']}`",
                f"- Target requirement statements: `{pair_summary['target_requirements']}`",
                f"- Differences requiring review: `{pair_summary['differences_requiring_review']}`",
                "",
                "Pair status counts:",
                "",
            ]
        )
        for status, count in pair_summary["status_counts"].items():
            lines.append(f"- `{status}`: `{count}`")

        deltas_by_status = {
            status: [item for item in pair["deltas"] if item["status"] == status]
            for status in ["added", "changed", "removed", "equivalent"]
        }
        render_delta_table(lines, "Added In Candidate", deltas_by_status["added"])
        render_delta_table(lines, "Changed In Candidate", deltas_by_status["changed"])
        render_delta_table(lines, "Removed From Candidate", deltas_by_status["removed"])

        equivalent_sample = deltas_by_status["equivalent"][:20]
        render_delta_table(lines, "Equivalent Sample", equivalent_sample)
        if len(deltas_by_status["equivalent"]) > len(equivalent_sample):
            lines.append("")
            lines.append(
                f"Equivalent items truncated in Markdown: `{len(deltas_by_status['equivalent']) - len(equivalent_sample)}`. "
                "The JSON report contains the full list."
            )
        lines.append("")

    lines.extend(["## Review Notes", ""])
    for note in report["review_notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except RuntimeError as issue:
        print(f"Error: {issue}", file=sys.stderr)
        return 1
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"- replacement pairs: {report['summary']['replacement_pairs']}")
    print(f"- status counts: {report['summary']['status_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
