#!/usr/bin/env python3
"""Validate provider-neutral Document Consistency Review operations artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
MODEL = Path("model/governance/document-consistency")
FILES = {
    "operating": (MODEL / "operating-model-v1.json", Path("schemas/document-consistency-operating-model.schema.json")),
    "configuration": (MODEL / "reviewer-config-v1.json", Path("schemas/document-consistency-reviewer-config.schema.json")),
    "provider_adapter": (MODEL / "provider-adapter-config-v1.json", Path("schemas/document-consistency-provider-adapter-config.schema.json")),
    "semantic_evaluation_catalog": (MODEL / "semantic-evaluation-catalog-v1.json", Path("schemas/document-consistency-semantic-evaluation-catalog.schema.json")),
    "triggers": (MODEL / "trigger-scope-matrix-v1.json", Path("schemas/document-consistency-trigger-scope.schema.json")),
    "rollout": (MODEL / "rollout-decision-v2.json", Path("schemas/document-consistency-rollout-decision-v2.schema.json")),
    "ledger": (Path("tests/fixtures/document-consistency-review-operations/synthetic-ledger.json"), Path("schemas/document-consistency-finding-ledger.schema.json")),
    "package": (Path("docs/examples/document-consistency-review-phase4-candidate-package.json"), Path("schemas/document-consistency-review-package.schema.json")),
}
SEVERITY = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class OperationsValidationError(ValueError):
    pass


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OperationsValidationError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise OperationsValidationError(f"expected JSON object: {path}")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schema(value: dict, schema: dict, label: str) -> None:
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise OperationsValidationError(f"{label} schema error at {location}: {errors[0].message}")


def classify_transition(previous: dict | None, current: dict | None, *, reassessed: bool) -> str:
    """Classify continuity without treating an omitted finding as resolved."""
    if previous is None and current is not None:
        return "new"
    if not reassessed:
        return "not_reassessed"
    if previous is not None and current is None:
        return "resolved"
    if previous is None or current is None:
        raise OperationsValidationError("transition needs at least one occurrence")
    if previous.get("state") == "resolved":
        return "reopened"
    previous_sources = set(previous.get("source_ids", []))
    current_sources = set(current.get("source_ids", []))
    if SEVERITY[current["severity"]] > SEVERITY[previous["severity"]] or current_sources > previous_sources:
        return "worsened"
    return "unchanged"


def plan_scope(matrix: dict, change_types: list[str], *, impact_known: bool = True) -> dict:
    rules = {row["change_type"]: row for row in matrix["rules"]}
    selected = []
    for change_type in change_types:
        if change_type not in rules:
            return {"mode": matrix["default_mode"], "invalidate_evidence": True, "actions": ["classify_unknown_change"]}
        selected.append(rules[change_type])
    if not selected:
        raise OperationsValidationError("at least one change type is required")
    if any(row["scope"] == "full_review" for row in selected) or (not impact_known and any(row["scope"] == "full_if_impact_unknown" for row in selected)):
        mode = "full_review"
    elif any(row["scope"] == "methodology_comparison" for row in selected):
        mode = "methodology_comparison"
    else:
        mode = "incremental"
    return {
        "mode": mode,
        "invalidate_evidence": any(row["invalidate_evidence"] for row in selected),
        "actions": sorted({action for row in selected for action in row["required_actions"]}),
    }


def validate(root: Path = ROOT) -> dict:
    loaded = {}
    for label, (path, schema_path) in FILES.items():
        value = read_json(root / path)
        validate_schema(value, read_json(root / schema_path), label)
        loaded[label] = value

    config = loaded["configuration"]
    provider = config["provider"]
    if provider["status"] == "not_configured" and (provider["name"] is not None or provider["model"] is not None or provider["parameters"]):
        raise OperationsValidationError("unconfigured provider must not claim identity or parameters")
    manifest_path = root / config["source_manifest"]["path"]
    if digest(manifest_path) != config["source_manifest"]["sha256"]:
        raise OperationsValidationError("reviewer configuration source manifest digest mismatch")

    adapter = loaded["provider_adapter"]
    for key in ("projection_schema", "canonical_schema"):
        candidate = (root / adapter[key]).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise OperationsValidationError(f"provider adapter path escapes repository: {adapter[key]}") from exc
        if not candidate.is_file():
            raise OperationsValidationError(f"provider adapter contract is missing: {adapter[key]}")

    package = loaded["package"]
    for artifact in package["artifacts"]:
        candidate = (root / artifact["path"]).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise OperationsValidationError(f"package artifact escapes repository: {artifact['path']}") from exc
        if not candidate.is_file() or digest(candidate) != artifact["sha256"]:
            raise OperationsValidationError(f"package artifact digest mismatch: {artifact['path']}")
    if package["completeness"] == "incomplete" and package["rollout_decision"] != "pending":
        raise OperationsValidationError("incomplete package cannot carry a rollout decision")

    rollout = loaded["rollout"]
    evidence_ids = [item["evidence_id"] for item in rollout["evidence"]]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise OperationsValidationError("rollout evidence IDs must be unique")
    evidence_by_id = {item["evidence_id"]: item for item in rollout["evidence"]}
    for item in rollout["evidence"]:
        candidate = (root / item["path"]).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError as exc:
            raise OperationsValidationError(f"rollout evidence path escapes repository: {item['path']}") from exc
        if not candidate.is_file() or digest(candidate) != item["sha256"]:
            raise OperationsValidationError(f"rollout evidence digest mismatch: {item['path']}")
    for criterion in rollout["criteria"]:
        unknown = sorted(set(criterion["evidence_ids"]) - set(evidence_by_id))
        if unknown:
            raise OperationsValidationError(
                f"rollout criterion references unknown evidence: {criterion['id']}: {', '.join(unknown)}"
            )
    if rollout["readiness_level"] == "limited_pilot_ready":
        authorization = rollout["authorization"]
        if not authorization["per_run_authorization_required"] or authorization["automatic_execution"]:
            raise OperationsValidationError("limited pilot readiness requires per-run authorization and disabled automation")

    for finding in loaded["ledger"]["findings"]:
        occurrences = finding["occurrences"]
        if occurrences[0]["state"] != "new":
            raise OperationsValidationError(f"first occurrence must be new: {finding['persistent_id']}")
        for occurrence in occurrences:
            if not occurrence["reassessed"] and occurrence["state"] != "not_reassessed":
                raise OperationsValidationError(f"non-reassessed occurrence cannot change lifecycle: {finding['persistent_id']}")
        if finding["triage"]["decision"] in {"false_positive", "accepted_exception"} and not finding["triage"]["decision_scope"]:
            raise OperationsValidationError(f"scope-limited decision is missing scope: {finding['persistent_id']}")

    return {
        "status": "pass",
        "artifacts": len(loaded),
        "rollout": loaded["rollout"]["production_rollout"],
        "readiness": loaded["rollout"]["readiness_level"],
        "provider": provider["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
