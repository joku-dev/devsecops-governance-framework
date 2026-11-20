#!/usr/bin/env python3
"""Build the advisory PRA requirement-to-platform review packet."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "model/requirements/lifecycle-cases/RLC-PRA-STD-REQ-001-MIGRATION.json"
CANDIDATES = ROOT / "generated/reports/implemented-requirement-migration.json"
CAPABILITIES = ROOT / "model/platform/platform-capabilities.yaml"
ALLOCATIONS = ROOT / "model/traceability/control-to-platform.yaml"
ARTIFACT_REGISTER = ROOT / "model/requirements/requirement-to-artifact-register.yaml"
SOURCE = ROOT / "docs/governance/source-documents/PRA-STD-SRC-001.requirements.md"
OUT = ROOT / "docs/governance/review-packets/PRA-2026-001"
CONTROL_PATTERN = re.compile(r"DSCB-(?:L[123]|GOV)-REQ-[0-9]{3}")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def classify_form(statement: str) -> tuple[str, str]:
    normalized = " ".join(statement.split())
    lowered = normalized.lower()
    incomplete_introductions = (
        "implement the following logical architecture layers",
        "implement the following mandatory capabilities",
        "may be deployed for",
        "shall be responsible for",
        "shall be verified through",
        "shall be applied together with",
    )
    if normalized.endswith(":") or any(phrase in lowered for phrase in incomplete_introductions):
        return "incomplete_list_intro", "correct_or_reject"
    if lowered == "platform stack capability requirements":
        return "section_heading", "reject_non_requirement"
    if " | " in normalized and (
        lowered.startswith("control baseline level |")
        or lowered.startswith("control baseline requirement |")
    ):
        return "table_header", "reject_non_requirement"
    if lowered.startswith("they ") or lowered.startswith("it "):
        return "context_dependent_statement", "correct_or_reject"
    if " shall " in f" {lowered} " or " must " in f" {lowered} ":
        return "normative_statement", "review_for_activation"
    if " may " in f" {lowered} ":
        return "conditional_normative_statement", "review_for_activation"
    return "descriptive_or_traceability_row", "review_as_supporting_model"


def build() -> dict:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    migration = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    candidate_by_source = {
        row["source_requirement_id"]: row["mapping_candidates"]
        for row in migration["requirement_candidates"]
        if row["source_id"] == "PRA-STD-REQ-001"
    }
    capabilities = {row["id"]: row for row in load_yaml(CAPABILITIES)["capabilities"]}
    allocations = load_yaml(ALLOCATIONS)["mappings"]
    register = load_yaml(ARTIFACT_REGISTER)
    register_by_source: dict[str, list[dict]] = defaultdict(list)
    for entry in register["entries"]:
        if entry["artifact"]["type"] == "platform" and entry["decision"]["status"] == "effective":
            for source_ref in entry["source_requirement_refs"]:
                register_by_source[source_ref].append(entry)
    allocation_by_control = {row["control"]: row for row in allocations}
    controls_by_capability: dict[str, list[str]] = defaultdict(list)
    evidence_by_capability: dict[str, set[str]] = defaultdict(set)
    levels_by_capability: dict[str, set[str]] = defaultdict(set)
    for allocation in allocations:
        for capability in allocation["platform_capabilities"]:
            controls_by_capability[capability].append(allocation["control"])
            evidence_by_capability[capability].update(allocation["evidence"])
            levels_by_capability[capability].add(allocation["platform_level"])

    rows = []
    for proposal in case["proposals"]:
        statement = proposal["statement"]
        form, recommendation = classify_form(statement)
        explicit_controls = sorted(set(CONTROL_PATTERN.findall(statement)))
        allocated_capabilities = sorted({
            capability
            for control in explicit_controls
            for capability in allocation_by_control.get(control, {}).get("platform_capabilities", [])
        })
        candidates = []
        for candidate in candidate_by_source.get(proposal["source_requirement_id"], []):
            capability_id = candidate["artifact_id"]
            capability = capabilities.get(capability_id, {})
            candidates.append({
                "capability_id": capability_id,
                "similarity": candidate["similarity"],
                "required_from": capability.get("required_from"),
                "area": capability.get("area"),
                "allocated_controls": sorted(controls_by_capability.get(capability_id, [])),
                "expected_evidence": sorted(evidence_by_capability.get(capability_id, [])),
                "allocation_levels": sorted(levels_by_capability.get(capability_id, [])),
                "review_state": "human_equivalence_confirmation_required",
            })
        effective_entries = register_by_source.get(proposal["source_requirement_id"], [])
        rows.append({
            "proposal_id": proposal["proposal_id"],
            "source_requirement_id": proposal["source_requirement_id"],
            "title": proposal["title"],
            "statement": statement,
            "normative_strength": proposal["normative_strength"],
            "form_assessment": form,
            "requirement_recommendation": recommendation,
            "explicit_control_refs": explicit_controls,
            "control_allocated_capabilities": allocated_capabilities,
            "platform_candidates": candidates,
            "requirement_decision": proposal["decision"],
            "platform_equivalence_decision": ({
                "status": "effective",
                "register_entries": [entry["id"] for entry in effective_entries],
                "artifacts": [entry["artifact"]["artifact_id"] for entry in effective_entries],
            } if effective_entries else None),
        })

    forms = Counter(row["form_assessment"] for row in rows)
    recommendations = Counter(row["requirement_recommendation"] for row in rows)
    similarities = [
        row["platform_candidates"][0]["similarity"]
        for row in rows if row["platform_candidates"]
    ]
    decided = sum(row["requirement_decision"] is not None for row in rows)
    status = "decided" if decided == len(rows) else "partially_decided" if decided else "review_required"
    return {
        "schema_version": "1.0.0",
        "review_id": "PRA-2026-001",
        "status": status,
        "source": {
            "source_id": "PRA-STD-REQ-001",
            "source_path": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": sha256(SOURCE.read_bytes()).hexdigest(),
            "lifecycle_case": CASE.relative_to(ROOT).as_posix(),
        },
        "review_basis": {
            "platform_model": CAPABILITIES.relative_to(ROOT).as_posix(),
            "platform_model_sha256": sha256(CAPABILITIES.read_bytes()).hexdigest(),
            "control_allocation": ALLOCATIONS.relative_to(ROOT).as_posix(),
            "control_allocation_sha256": sha256(ALLOCATIONS.read_bytes()).hexdigest(),
            "text_similarity_role": "advisory_only",
        },
        "summary": {
            "requirements": len(rows),
            "with_platform_candidates": sum(bool(row["platform_candidates"]) for row in rows),
            "without_platform_candidates": sum(not row["platform_candidates"] for row in rows),
            "with_explicit_control_refs": sum(bool(row["explicit_control_refs"]) for row in rows),
            "decided_requirements": decided,
            "effective_platform_mappings": sum(
                len(row["platform_equivalence_decision"]["register_entries"])
                for row in rows if row["platform_equivalence_decision"]
            ),
            "form_assessments": dict(sorted(forms.items())),
            "recommendations": dict(sorted(recommendations.items())),
            "top_similarity_min": min(similarities),
            "top_similarity_max": max(similarities),
        },
        "decision_rules": {
            "requirement_classifications": ["new", "duplicate", "extend", "change", "supersede", "conflict"],
            "platform_assessments": ["equivalent", "partial", "missing", "not_equivalent"],
            "separate_human_decisions_required": True,
            "activation_or_runtime_change_authorized": False,
        },
        "requirements": rows,
    }


def render(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# PRA-2026-001: Requirement-to-Platform Review", "",
        "## Decision brief", "",
        "This packet tracks the moderated review of all 56 PRA source requirements. Recorded decisions and effective platform mappings are read from the governed lifecycle case and Requirement-to-Artifact Register. It does not change runtime enforcement.", "",
        f"The source is pinned to `{report['source']['source_sha256']}`. Existing control-to-platform allocation and capability metadata are primary review evidence; text similarity is advisory only.", "",
        "| Measure | Value |", "|---|---:|",
        f"| Source requirements | {summary['requirements']} |",
        f"| With platform candidates | {summary['with_platform_candidates']} |",
        f"| Without platform candidates | {summary['without_platform_candidates']} |",
        f"| With explicit DSCB references | {summary['with_explicit_control_refs']} |",
        f"| Requirements decided | {summary['decided_requirements']} |",
        f"| Effective platform mappings | {summary['effective_platform_mappings']} |",
        f"| Lowest top similarity | {summary['top_similarity_min']:.4f} |",
        f"| Highest top similarity | {summary['top_similarity_max']:.4f} |", "",
        "## Required decisions", "",
        "For every row, the Platform Owner must record two independent decisions:", "",
        "1. Requirement disposition and classification: approve or reject with `new`, `duplicate`, `extend`, `change`, `supersede`, or `conflict`.",
        "2. Platform equivalence: `equivalent`, `partial`, `missing`, or `not_equivalent` for each adopted capability mapping.", "",
        "Rows marked `correct_or_reject` are incomplete or context-dependent statements in the sanitized extract. Rows marked `reject_non_requirement` are headings or table headers. Neither category should be activated without correction or explicit contrary evidence.", "",
        "## Review table", "",
        "| Source requirement | Form | Recommendation | Explicit controls | Control allocation | Top platform candidates |", "|---|---|---|---|---|---|",
    ]
    for row in report["requirements"]:
        explicit = ", ".join(f"`{value}`" for value in row["explicit_control_refs"]) or "—"
        allocated = ", ".join(f"`{value}`" for value in row["control_allocated_capabilities"]) or "—"
        candidates = ", ".join(
            f"`{item['capability_id']}` ({item['similarity']:.4f})"
            for item in row["platform_candidates"][:3]
        ) or "—"
        lines.append(
            f"| `{row['source_requirement_id']}` | `{row['form_assessment']}` | `{row['requirement_recommendation']}` | {explicit} | {allocated} | {candidates} |"
        )
    lines += [
        "", "## Source protection", "",
        "- The registered PRA requirements extract is not edited by this review.",
        "- The lifecycle case remains undecided and the authority mode remains `migration_in_progress`.",
        "- A correction requires a new versioned source or lifecycle revision; it must not overwrite the approved source bytes.",
        "- No GRQ activation, platform adoption, OPA change, or enforcement change is authorized by this packet.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    report = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "review.md").write_text(render(report), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}/review.json and review.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
