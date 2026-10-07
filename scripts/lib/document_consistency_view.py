"""Validate and redact Document Consistency Review data for the public viewer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


REPORT = Path("docs/examples/document-consistency-review-phase2-report.json")
MANIFEST = Path("docs/examples/document-consistency-review-phase1-source-manifest.json")
REPORT_SCHEMA = Path("schemas/document-consistency-semantic-report.schema.json")
MANIFEST_SCHEMA = Path("schemas/document-consistency-review-manifest.schema.json")
PROJECTION_SCHEMA = Path("schemas/document-consistency-public-projection.schema.json")


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _validate(value: dict, schema_path: Path) -> None:
    errors = sorted(Draft202012Validator(_json(schema_path)).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise ValueError(f"schema error at {location}: {errors[0].message}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _freshness(root: Path, report: dict, manifest: dict, manifest_path: Path) -> dict:
    try:
        manifest_matches = _sha256(manifest_path) == report["scope"]["source_manifest_sha256"]
        source_results = []
        for source in manifest["source_documents"]:
            source_path = (root / source["source_path"]).resolve()
            source_path.relative_to((root / "docs/governance/source-documents").resolve())
            source_results.append(source_path.is_file() and _sha256(source_path) == source["content_sha256"])
        sources_match = all(source_results)
        status = "current" if manifest_matches and sources_match else "stale"
    except (OSError, KeyError, TypeError, ValueError):
        manifest_matches = None
        sources_match = None
        status = "unknown"
    return {
        "status": status,
        "reviewed_commit": manifest.get("reviewed_commit"),
        "manifest_matches": manifest_matches,
        "sources_match": sources_match,
    }


def project_public(root: Path, report: dict | None = None, manifest: dict | None = None) -> dict:
    """Return an explicit allowlist projection without excerpts or semantic prose."""
    report_path = root / REPORT
    manifest_path = root / MANIFEST
    report = report if report is not None else _json(report_path)
    manifest = manifest if manifest is not None else _json(manifest_path)
    _validate(report, root / REPORT_SCHEMA)
    _validate(manifest, root / MANIFEST_SCHEMA)

    source_by_id = {item["id"]: item for item in manifest.get("source_documents", [])}
    source_ids = report["scope"]["source_ids"]
    missing_sources = sorted(set(source_ids) - set(source_by_id))
    if missing_sources:
        raise ValueError(f"report sources are absent from manifest: {', '.join(missing_sources)}")
    documents = [
        {"id": source_id, "status": source_by_id[source_id]["status"], "version": source_by_id[source_id]["version"]}
        for source_id in source_ids if source_id in source_by_id
    ]
    projection = {
        "projection_version": "1.0.0",
        "projection_type": "document_consistency_public_projection",
        "audience": "public_redacted",
        "review_id": report["review_id"],
        "overall_status": report["overall_status"],
        "freshness": _freshness(root, report, manifest, manifest_path),
        "scope": {"source_count": len(source_ids), "source_ids": list(source_ids)},
        "execution": {
            "mode": report["execution"]["mode"],
            "status": report["execution"]["status"],
            "truncated": report["execution"]["truncated"],
        },
        "sections": {
            "formal_validation": report["formal_validation"]["status"],
            "semantic_review": report["semantic_review"]["status"],
            "human_decisions": report["human_decisions"]["status"],
            "implementation_coverage": report["implementation_coverage"]["status"],
        },
        "documents": documents,
        "findings": [
            {
                "id": item["finding_id"],
                "category": item["category"],
                "semantic_state": item["semantic_state"],
                "evidence_status": item["evidence_status"],
                "disposition": item["disposition"],
            }
            for item in report["findings"]
        ],
        "limitations": {
            "redacted": True,
            "no_consistency_claim": True,
            "no_public_internal_view": True,
            "message": "Public metadata projection only. No source excerpts, semantic prose, recommendations or human decisions are published.",
        },
    }
    _validate(projection, root / PROJECTION_SCHEMA)
    return projection
