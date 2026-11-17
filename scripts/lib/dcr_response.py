"""Neutral DCR domain implementation extracted from frozen V1.

Source lineage: 6b557fefe295b58272d2271326576ca3a3687197 / scripts/adapt_document_consistency_provider_response.py.
Schemas are product resources; source data uses the explicit caller workspace.
No source CLI is imported or dispatched.
"""
from __future__ import annotations

from copy import deepcopy

import json

from pathlib import Path

from jsonschema import Draft202012Validator

from lib.portable.contracts import ROOT

DEFAULT_CONFIG = ROOT / "model/governance/document-consistency/provider-adapter-config-v1.json"

class ProviderAdapterError(ValueError):
    """Raised when provider output cannot be normalized without ambiguity."""

def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProviderAdapterError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ProviderAdapterError(f"expected JSON object: {path}")
    return value

def validate(value: dict, schema: dict, label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ProviderAdapterError(f"{label} schema error at {location}: {errors[0].message}")

def adapt_provider_response(
    projection: dict,
    config: dict,
    *,
    review_id: str,
    source_manifest_sha256: str,
    provider: str,
    model: str,
    prompt_version: str,
    truncated: bool = False,
) -> dict:
    """Normalize the bounded projection; never validate evidence or semantics."""
    projection_schema = read_json(ROOT / "schemas/document-consistency-provider-projection.schema.json")
    canonical_schema = read_json(ROOT / "schemas/document-consistency-semantic-response.schema.json")
    validate(projection, projection_schema, "provider projection")
    normalized_findings = []
    normalization_notes = []
    aliases = config["normalization"]["misplaced_semantic_states"]

    for original in projection["findings"]:
        finding = deepcopy(original)
        status = finding["applicability"]["status"]
        if status in aliases:
            target = aliases[status]
            if finding["semantic_state"] not in {"proposed", target}:
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: conflicting semantic_state and applicability.status"
                )
            finding["semantic_state"] = target
            finding["applicability"]["status"] = "unknown"
            normalization_notes.append(
                f"{finding['finding_id']}: moved misplaced applicability status {status} to semantic_state"
            )
        finding["recommendation"] = finding["recommendation"] or None
        scope = finding.pop("search_scope")
        if scope["status"] == "not_applicable":
            if scope["source_ids"] or scope["method"] or scope["limitations"]:
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: not_applicable search scope must be empty"
                )
            finding["search_scope"] = None
        else:
            if not scope["source_ids"] or not scope["method"] or not scope["limitations"]:
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: provided search scope is incomplete"
                )
            if len(scope["source_ids"]) != len(set(scope["source_ids"])):
                raise ProviderAdapterError(
                    f"{finding['finding_id']}: search scope contains duplicate source IDs"
                )
            finding["search_scope"] = {
                "source_ids": scope["source_ids"],
                "method": scope["method"],
                "limitations": scope["limitations"],
            }
        normalized_findings.append(finding)

    limitations = list(projection["limitations"])
    limitations.extend(f"Adapter normalization: {note}." for note in normalization_notes)
    result = {
        "schema_version": "1.0.0",
        "response_type": "document_consistency_semantic_response",
        "review_id": review_id,
        "source_manifest_sha256": source_manifest_sha256,
        "execution": {
            "mode": "provider",
            "status": "completed",
            "provider": provider,
            "model": model,
            "prompt_version": prompt_version,
            "configuration_version": config["configuration_id"],
            "truncated": truncated,
        },
        "findings": normalized_findings,
        "limitations": limitations,
    }
    validate(result, canonical_schema, "canonical semantic response")
    return result
