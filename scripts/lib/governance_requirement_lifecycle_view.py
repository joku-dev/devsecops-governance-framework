"""Read-only lifecycle projection from registered governance artifacts."""

from collections import Counter, defaultdict
import json
from pathlib import Path

import yaml


def _read_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a YAML mapping in {path}")
    return value


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def project(root: Path) -> dict:
    """Summarize intake through effective artifacts without inferring compliance."""
    register = _read_yaml(root / "model/documents/source-document-register.yaml")
    artifact_register = _read_yaml(root / "model/requirements/requirement-to-artifact-register.yaml")
    migration = _read_json(root / "generated/reports/implemented-requirement-migration.json")
    sources = register.get("documents", [])
    intake_counts = Counter(item.get("status", "unknown") for item in sources)

    effective_entries = [
        item for item in artifact_register.get("entries", [])
        if item.get("decision", {}).get("status") == "effective"
    ]
    source_mappings: dict[str, list[dict]] = defaultdict(list)
    for item in effective_entries:
        for source_ref in item.get("source_requirement_refs", []):
            source_mappings[source_ref].append(item)

    cases = {}
    case_dir = root / "model/requirements/lifecycle-cases"
    for path in sorted(case_dir.glob("*.json")):
        case = _read_json(path)
        cases[case["source"]["source_id"]] = case

    rows = []
    totals = Counter()
    implementations = Counter()
    opa_paths = set()
    opa_enforcement = Counter()
    for source in sources:
        source_id = source["id"]
        case = cases.get(source_id)
        row = {
            "source_id": source_id,
            "title": source.get("title", source_id),
            "owner": source.get("owner", "unknown"),
            "intake_status": source.get("status", "unknown"),
            "case_available": bool(case),
            "case_status": case.get("status") if case else None,
            "total": 0,
            "with_candidates": 0,
            "decided": 0,
            "approved": 0,
            "rejected": 0,
            "open": 0,
            "activated": 0,
            "effective_mappings": 0,
            "mappings_by_type": {},
            "opa_mappings": 0,
            "next_step": "Anforderungsfall nicht angelegt",
        }
        if case:
            proposals = case.get("proposals", [])
            row["total"] = len(proposals)
            row["decided"] = sum(item.get("decision") is not None for item in proposals)
            row["approved"] = sum(
                (item.get("decision") or {}).get("disposition") == "approve" for item in proposals
            )
            row["rejected"] = sum(
                (item.get("decision") or {}).get("disposition") == "reject" for item in proposals
            )
            migration_state = migration.get("sources", {}).get(source_id, {})
            row["with_candidates"] = migration_state.get("with_candidates", 0)
            row["open"] = row["total"] - row["decided"]
            if migration_state.get("total") != row["total"] or migration_state.get("open") != row["open"]:
                raise ValueError(f"lifecycle decisions and migration report disagree for {source_id}")
            row["activated"] = sum(item.get("activation") is not None for item in proposals)

            source_prefix = source_id.replace("-REQ-001", "-SRC-001") + "-REQ-"
            mappings = [
                entry for ref, entries in source_mappings.items()
                if ref.startswith(source_prefix)
                for entry in entries
            ]
            by_type = Counter(item.get("artifact", {}).get("type", "unknown") for item in mappings)
            row["effective_mappings"] = len(mappings)
            row["mappings_by_type"] = dict(sorted(by_type.items()))
            row["opa_mappings"] = by_type.get("policies", 0)
            for item in mappings:
                if item.get("artifact", {}).get("type") == "policies":
                    opa_paths.add(item.get("artifact", {}).get("path"))
                    opa_enforcement[item.get("enforcement", "unknown")] += 1

            totals.update({
                "requirements": row["total"],
                "with_candidates": row["with_candidates"],
                "decided": row["decided"],
                "approved": row["approved"],
                "rejected": row["rejected"],
                "open": row["open"],
                "activated": row["activated"],
            })
            implementations.update(by_type)
            row["next_step"] = (
                "Offene fachliche Entscheidungen bearbeiten" if row["open"]
                else "Umsetzung und Nachweise prüfen" if row["activated"]
                else "Keine offene Anforderung im Lifecycle-Fall"
            )
        rows.append(row)

    policy_files = sorted((root / "policies/opa").glob("*.rego"))
    active_cases = [case for case in cases.values()]
    return {
        "available": True,
        "source_summary": {
            "total": len(sources),
            "status_counts": dict(sorted(intake_counts.items())),
            "with_lifecycle_case": len(active_cases),
            "without_lifecycle_case": len(sources) - len(active_cases),
        },
        "requirement_summary": {
            "sources_with_cases": len(active_cases),
            "total": totals["requirements"],
            "with_candidates": totals["with_candidates"],
            "decided": totals["decided"],
            "approved_decisions": totals["approved"],
            "rejected_decisions": totals["rejected"],
            "open": totals["open"],
            "activated": totals["activated"],
        },
        "implementation_summary": {
            "effective_register_entries": len(effective_entries),
            "by_artifact_type": dict(sorted(Counter(
                item.get("artifact", {}).get("type", "unknown") for item in effective_entries
            ).items())),
        },
        "opa_summary": {
            "policy_files_present": len(policy_files),
            "effective_mapping_entries": implementations.get("policies", 0),
            "distinct_mapped_policy_files": len(opa_paths),
            "enforcement_counts": dict(sorted(opa_enforcement.items())),
            "latest_validation": "not_recorded_in_viewer_data",
        },
        "sources": rows,
        "links": {
            "source_register": "model/documents/source-document-register.yaml",
            "lifecycle_cases": "model/requirements/lifecycle-cases/",
            "requirement_register": "model/requirements/requirement-to-artifact-register.yaml",
            "migration_report": "generated/reports/implemented-requirement-migration.md",
            "pra_review": "docs/governance/review-packets/PRA-2026-001/recommendation.md",
            "golden_path_workpackage": "docs/operations/planning/golden-path-pra-capability-workpackage.md",
            "opa_directory": "policies/opa/",
        },
    }
