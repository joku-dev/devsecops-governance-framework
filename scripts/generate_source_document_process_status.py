#!/usr/bin/env python3
"""Project the full source-intake process and authorized-source baseline gate.

This report joins existing source registration, requirement migration,
Document Consistency Review and requirement-to-artifact records. It is a
read-only projection: it does not approve sources, resolve findings or publish
a normative baseline.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "model/documents/source-document-register.yaml"
INTAKE_STATUS = ROOT / "generated/reports/source-document-intake-status.json"
REQUIREMENT_DELTA = ROOT / "generated/reports/source-document-requirement-delta.json"
AUTHORITY_LEDGER = ROOT / "model/requirements/requirement-authority-ledger.yaml"
LIFECYCLE_CASES = ROOT / "model/requirements/lifecycle-cases"
DCR_PROJECTION = ROOT / "status/document-consistency-public-projection.json"
DCR_ROLLOUT = ROOT / "model/governance/document-consistency/rollout-decision-v2.json"
ARTIFACT_REGISTER = ROOT / "model/requirements/requirement-to-artifact-register.yaml"
OUT_JSON = ROOT / "generated/reports/source-document-process-status.json"
OUT_MD = ROOT / "generated/reports/source-document-process-status.md"


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.is_file():
        return default or {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else default or {}


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def requirement_lifecycle_summary(approved_source_ids: set[str]) -> dict:
    ledger = load_yaml(AUTHORITY_LEDGER)
    ledger_sources = {
        item.get("source_id"): item
        for item in ledger.get("sources", [])
        if item.get("source_id") in approved_source_ids
    }
    cases_by_source = {}
    case_errors = []
    for path in sorted(LIFECYCLE_CASES.glob("*.json")):
        case = load_json(path)
        source = case.get("source", {})
        source_id = source.get("source_id")
        if source_id not in approved_source_ids:
            continue
        case_by = cases_by_source.setdefault(source_id, [])
        case_by.append(path)
        source_path = ROOT / source.get("source_path", "")
        if not source_path.is_file() or sha256(source_path) != source.get("source_sha256"):
            case_errors.append(f"{source_id}: lifecycle case source hash is stale")

    totals = Counter()
    for source_id, paths in cases_by_source.items():
        for path in paths:
            case = load_json(path)
            for proposal in case.get("proposals", []):
                totals["proposals"] += 1
                if proposal.get("decision") is None:
                    totals["undecided"] += 1
                else:
                    totals["decided"] += 1
                if proposal.get("activation") is not None:
                    totals["activated"] += 1
                elif proposal.get("decision") is None:
                    totals["unresolved"] += 1
        ledger_entry = ledger_sources.get(source_id)
        if ledger_entry:
            totals[f"authority_mode:{ledger_entry.get('authority_mode', 'unknown')}"] += 1

    missing_cases = sorted(approved_source_ids - set(cases_by_source))
    totals["sources_with_cases"] = len(cases_by_source)
    totals["approved_sources_without_cases"] = len(missing_cases)
    totals["approved_sources_without_ledger_entry"] = len(approved_source_ids - set(ledger_sources))
    return {
        "summary": dict(sorted(totals.items())),
        "missing_case_source_ids": missing_cases,
        "case_errors": case_errors,
    }


def build_report() -> dict:
    register = load_yaml(REGISTER)
    documents = register.get("documents", [])
    intake = load_json(INTAKE_STATUS)
    delta = load_json(REQUIREMENT_DELTA)
    dcr = load_json(DCR_PROJECTION)
    rollout = load_json(DCR_ROLLOUT)
    artifact_register = load_yaml(ARTIFACT_REGISTER)
    approved = [item for item in documents if item.get("status") == "approved"]
    approved_ids = {item["id"] for item in approved}

    missing_sources = [
        item["id"] for item in documents
        if not isinstance(item.get("source_path"), str)
        or not (ROOT / item["source_path"]).is_file()
    ]
    registered_paths = {item.get("source_path") for item in documents}
    source_root = ROOT / "docs/governance/source-documents"
    unregistered_files = sorted(
        str(path.relative_to(ROOT))
        for path in source_root.iterdir()
        if path.is_file() and str(path.relative_to(ROOT)) not in registered_paths
    ) if source_root.is_dir() else []

    inventory = delta.get("requirement_intake_inventory", {})
    inventory_summary = inventory.get("summary", {})
    identification_counts = inventory_summary.get("identification_counts", {})
    approved_inventory_sources = [
        item for item in inventory.get("sources", [])
        if item.get("source_id") in approved_ids
    ]
    approved_identification_counts = Counter()
    for item in approved_inventory_sources:
        approved_identification_counts.update(item.get("identification_counts", {}))
    approved_extraction_errors = [
        item for item in inventory.get("extraction_errors", [])
        if item.get("source_id") in approved_ids
    ]
    approved_skipped_sources = [
        item for item in inventory.get("skipped_sources", [])
        if item.get("source_id") in approved_ids
    ]
    lifecycle = requirement_lifecycle_summary(approved_ids)
    lifecycle_counts = lifecycle["summary"]
    dcr_findings = dcr.get("findings", [])
    unresolved_dcr_findings = [
        item for item in dcr_findings
        if item.get("disposition") not in {"helpful", "false_positive", "resolved"}
    ]
    dcr_source_ids = dcr.get("scope", {}).get("source_ids", [])
    dcr_scope_matches_approved = bool(dcr_source_ids) and set(dcr_source_ids) == approved_ids

    artifact_entries = artifact_register.get("entries", [])
    effective_artifact_entries = [
        item for item in artifact_entries
        if item.get("decision", {}).get("status") == "effective"
    ]
    authorized_source_hashes = []
    for item in sorted(approved, key=lambda source: source["id"]):
        source_path = ROOT / item["source_path"]
        authorized_source_hashes.append(
            {
                "source_id": item["id"],
                "version": item.get("version"),
                "path": item["source_path"],
                "status": item["status"],
                "sha256": sha256(source_path) if source_path.is_file() else None,
            }
        )

    baseline_blockers = []
    if missing_sources:
        baseline_blockers.append("registered source files are missing")
    if unregistered_files:
        baseline_blockers.append("source-document folder contains unregistered files")
    if approved_extraction_errors:
        baseline_blockers.append("one or more source documents could not be extracted")
    if approved_skipped_sources:
        baseline_blockers.append("one or more approved source inputs have withheld source text")
    if approved_identification_counts.get("extraction_row_id", 0):
        baseline_blockers.append("requirement identifier origin remains unverified for extracted row IDs")
    if lifecycle_counts.get("unresolved", 0) or lifecycle_counts.get("undecided", 0):
        baseline_blockers.append("approved-source requirement lifecycle decisions remain open")
    if lifecycle["missing_case_source_ids"]:
        baseline_blockers.append("approved sources are missing requirement lifecycle cases")
    if lifecycle["case_errors"]:
        baseline_blockers.append("one or more requirement lifecycle cases are stale")
    if dcr.get("freshness", {}).get("status") != "current":
        baseline_blockers.append("Document Consistency Review projection is not current")
    if not dcr_scope_matches_approved:
        baseline_blockers.append("Document Consistency Review scope does not expose an exact approved-source set")
    if dcr.get("coverage", {}).get("semantic_item_coverage_status") != "complete":
        baseline_blockers.append("semantic consistency review is not exhaustive for the approved source set")
    if unresolved_dcr_findings:
        baseline_blockers.append("proposed or unresolved consistency findings remain")
    # DCR production rollout is an operational adoption decision, not approval
    # of this exact authorized-source set. Keep it visible as context only.

    baseline = {
        "status": "blocked" if baseline_blockers else "ready_for_human_approval",
        "authorized_source_count": len(approved),
        "authorized_source_set_sha256": canonical_sha256(authorized_source_hashes),
        "sources": authorized_source_hashes,
        "blocking_reasons": baseline_blockers,
        "consistency_review_id": dcr.get("review_id"),
        "consistency_review_status": dcr.get("overall_status", "not_run"),
        "unresolved_finding_count": len(unresolved_dcr_findings),
            "final_source_baseline_approval": "not_recorded",
    }

    phases = [
        {
            "id": "source_intake",
            "title": "Source Documents aufnehmen und registrieren",
            "status": "blocked" if missing_sources or unregistered_files else "complete",
            "counts": {"registered": len(documents), "approved": len(approved), "missing_files": len(missing_sources), "unregistered_files": len(unregistered_files)},
            "next_action": "Fehlende Dateien oder Registereinträge vervollständigen." if missing_sources or unregistered_files else "Eingaben sind registriert; Quellenstatus separat prüfen.",
        },
        {
            "id": "extract_and_classify",
            "title": "Dokumente extrahieren und Anforderungen klassifizieren",
            "status": "blocked" if inventory_summary.get("blocked_source_documents", 0) else "partial" if inventory_summary.get("skipped_source_documents", 0) else "complete",
            "counts": {"scanned": inventory_summary.get("scanned_source_documents", 0), "withheld": inventory_summary.get("skipped_source_documents", 0), "extraction_blocked": inventory_summary.get("blocked_source_documents", 0)},
            "next_action": "Extraktionslücken oder zurückgehaltene Quellen bearbeiten.",
        },
        {
            "id": "p1_requirement_lifecycle",
            "title": "P1: gekennzeichnete Anforderungen und Status prüfen",
            "status": "blocked" if approved_identification_counts.get("extraction_row_id", 0) else "in_progress" if lifecycle_counts.get("undecided", 0) else "complete",
            "counts": {"confirmed_author_ids": approved_identification_counts.get("author_identified", 0), "unverified_extraction_ids": approved_identification_counts.get("extraction_row_id", 0), "decided": lifecycle_counts.get("decided", 0), "undecided": lifecycle_counts.get("undecided", 0), "activated": lifecycle_counts.get("activated", 0)},
            "next_action": "Kennungsherkunft belegen und offene Requirement-Entscheidungen bearbeiten.",
        },
        {
            "id": "p2_inferred_review",
            "title": "P2: Inferred Candidates prüfen",
            "status": "review_required" if inventory_summary.get("inferred_candidate_count", 0) else "complete",
            "counts": {"inferred_candidates": inventory_summary.get("inferred_candidate_count", 0)},
            "next_action": "Kandidaten gegen die Quelldokumente und P1-Anforderungen prüfen.",
        },
        {
            "id": "consistency_review",
            "title": "Quellen auf Widersprüche und Konsistenz prüfen",
            "status": "blocked" if dcr.get("freshness", {}).get("status") != "current" else "partial" if unresolved_dcr_findings or dcr.get("coverage", {}).get("semantic_item_coverage_status") != "complete" else "complete",
            "counts": {"review_scope_sources": dcr.get("scope", {}).get("source_count", 0), "proposed_or_unresolved_findings": len(unresolved_dcr_findings), "semantically_assessed_requirements": dcr.get("coverage", {}).get("semantically_assessed_requirement_count")},
            "next_action": "Vollständigen, frischen Review über exakt die autorisierte Quellenmenge durchführen.",
        },
        {
            "id": "decision_proposals",
            "title": "Entscheidungsvorlagen bearbeiten",
            "status": "decision_required" if unresolved_dcr_findings or lifecycle_counts.get("undecided", 0) else "complete",
            "counts": {"consistency_findings_open": len(unresolved_dcr_findings), "requirements_undecided": lifecycle_counts.get("undecided", 0)},
            "next_action": "Befunde und Requirement-Vorschläge durch die zuständigen Rollen entscheiden lassen.",
        },
        {
            "id": "source_baseline",
            "title": "Widerspruchsfreie Quellenbaseline freigeben",
            "status": baseline["status"],
            "counts": {"authorized_sources": len(approved), "blocking_reasons": len(baseline_blockers)},
            "next_action": baseline_blockers[0] if baseline_blockers else "Baseline-Entscheidung formell freigeben.",
        },
        {
            "id": "governance_implementation",
            "title": "Freigegebene Anforderungen auf Governance-Artefakte abbilden",
            "status": "in_progress" if effective_artifact_entries else "not_started",
            "counts": {"effective_requirement_artifact_links": len(effective_artifact_entries), "all_links": len(artifact_entries)},
            "next_action": "Nur durch menschliche Entscheidung autorisierte Anforderungen in Controls, Plattformmodelle und OPA ableiten.",
        },
    ]

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "report_type": "source_document_process_status",
        "source_of_truth": {
            "register": "model/documents/source-document-register.yaml",
            "requirement_authority_ledger": "model/requirements/requirement-authority-ledger.yaml",
            "consistency_projection": "status/document-consistency-public-projection.json",
            "artifact_register": "model/requirements/requirement-to-artifact-register.yaml",
        },
        "summary": {
            "registered_sources": len(documents),
            "authorized_sources": len(approved),
            "source_status_counts": dict(sorted(Counter(item.get("status", "unknown") for item in documents).items())),
            "requirement_identification_counts": dict(sorted(identification_counts.items())),
            "authorized_source_requirement_identification_counts": dict(sorted(approved_identification_counts.items())),
            "lifecycle": lifecycle_counts,
            "inferred_candidate_count": inventory_summary.get("inferred_candidate_count", 0),
            "consistency_findings_open": len(unresolved_dcr_findings),
            "effective_requirement_artifact_links": len(effective_artifact_entries),
            "baseline_status": baseline["status"],
        },
        "phases": phases,
        "source_extraction": {
            "scanned_sources": inventory_summary.get("scanned_source_documents", 0),
            "skipped_sources": inventory.get("skipped_sources", []),
            "extraction_errors": inventory.get("extraction_errors", []),
            "missing_source_ids": missing_sources,
            "unregistered_source_paths": unregistered_files,
        },
        "consistency_review": {
            "review_id": dcr.get("review_id"),
            "status": dcr.get("overall_status", "not_run"),
            "freshness": dcr.get("freshness", {}).get("status", "unknown"),
            "scope_source_count": dcr.get("scope", {}).get("source_count", 0),
            "scope_source_ids_available": bool(dcr_source_ids),
            "semantic_review_status": dcr.get("coverage", {}).get("semantic_review_status", "not_run"),
            "semantic_item_coverage_status": dcr.get("coverage", {}).get("semantic_item_coverage_status", "not_run"),
            "findings": [
                {"id": item.get("id"), "category": item.get("category"), "disposition": item.get("disposition")}
                for item in dcr_findings
            ],
            "rollout_readiness": rollout.get("readiness_level", "unknown"),
            "production_rollout": rollout.get("production_rollout", "unknown"),
        },
        "requirement_lifecycle": lifecycle,
        "authorized_source_baseline": baseline,
        "limitations": [
            "This report joins existing governed records and does not make human source, requirement, conflict or release decisions.",
            "A report-only consistency result is not proof that no semantic contradiction exists.",
            "The authorized-source baseline remains blocked until source provenance, requirement lifecycle, exhaustive consistency review and human decision conditions are met.",
        ],
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Source Document Process Status",
        "",
        f"- Authorized-source baseline readiness: `{report['authorized_source_baseline']['status']}`",
        f"- Registered sources: `{report['summary']['registered_sources']}`",
        f"- Authorized sources: `{report['summary']['authorized_sources']}`",
        f"- Confirmed source-author IDs (P1): `{report['summary']['requirement_identification_counts'].get('author_identified', 0)}`",
        f"- Unverified extraction row IDs in approved sources: `{report['summary']['authorized_source_requirement_identification_counts'].get('extraction_row_id', 0)}`",
        f"- Unverified extraction row IDs across all registered sources: `{report['summary']['requirement_identification_counts'].get('extraction_row_id', 0)}`",
        f"- Inferred candidates (P2): `{report['summary']['inferred_candidate_count']}`",
        "",
        "## Process Phases",
        "",
        "| Phase | Status | Counts | Next action |",
        "|---|---|---|---|",
    ]
    for phase in report["phases"]:
        counts = ", ".join(f"{key}: {value}" for key, value in phase["counts"].items())
        lines.append(
            f"| {phase['title']} | `{phase['status']}` | {counts} | {phase['next_action']} |"
        )
    lines.extend(["", "## Baseline Blocking Reasons", ""])
    blockers = report["authorized_source_baseline"]["blocking_reasons"]
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- None")
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    print(f"Authorized-source baseline readiness: {report['authorized_source_baseline']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
