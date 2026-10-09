"""Validate and redact Document Consistency Review data for the public viewer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import yaml

from jsonschema import Draft202012Validator
from generate_document_consistency_review_model import generate_model


REPORT = Path("docs/examples/document-consistency-review-phase2-live-pilot-report.json")
MANIFEST = Path("docs/examples/document-consistency-review-phase1-source-manifest.json")
REPORT_SCHEMA = Path("schemas/document-consistency-semantic-report.schema.json")
MANIFEST_SCHEMA = Path("schemas/document-consistency-review-manifest.schema.json")
PROJECTION_SCHEMA = Path("schemas/document-consistency-public-projection.schema.json")
PUBLIC_SNAPSHOT = Path("status/document-consistency-public-projection.json")
SOURCE_REGISTER = Path("model/documents/source-document-register.yaml")


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


def _registered_requirement_sources(root: Path) -> list[dict]:
    """Return tracked, registered requirements extracts that define the review population."""
    register = yaml.safe_load((root / "model/documents/source-document-register.yaml").read_text(encoding="utf-8"))
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "docs/governance/source-documents/*.requirements.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    tracked_paths = set(tracked)
    return [
        item
        for item in register.get("documents", [])
        if item.get("source_path") in tracked_paths and item["source_path"].endswith(".requirements.md")
    ]


def _population_commitments(root: Path) -> tuple[str, str]:
    """Hash the register and tracked requirement-source population without exposing paths."""
    register_hash = _sha256(root / SOURCE_REGISTER)
    population = _registered_requirement_sources(root)
    rows = []
    source_root = (root / "docs/governance/source-documents").resolve()
    for item in population:
        source_path = (root / item["source_path"]).resolve()
        source_path.relative_to(source_root)
        if not source_path.is_file():
            raise ValueError("registered requirement source is missing")
        rows.append({"path": item["source_path"], "sha256": _sha256(source_path)})
    canonical = json.dumps(sorted(rows, key=lambda item: item["path"]), sort_keys=True, separators=(",", ":"))
    return register_hash, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _freshness(root: Path, report: dict, manifest: dict, manifest_path: Path, manifest_bytes: bytes | None = None) -> dict:
    try:
        actual_manifest_hash = hashlib.sha256(manifest_bytes).hexdigest() if manifest_bytes is not None else _sha256(manifest_path)
        manifest_matches = actual_manifest_hash == report["scope"]["source_manifest_sha256"]
        source_results = []
        for source in manifest["source_documents"]:
            source_path = (root / source["source_path"]).resolve()
            source_path.relative_to((root / "docs/governance/source-documents").resolve())
            source_results.append(source_path.is_file() and _sha256(source_path) == source["content_sha256"])
        sources_match = all(source_results)
        register_hash, population_hash = _population_commitments(root)
        status = "current" if manifest_matches and sources_match else "stale"
    except (OSError, KeyError, TypeError, ValueError):
        manifest_matches = None
        sources_match = None
        register_hash = None
        population_hash = None
        status = "unknown"
    return {
        "status": status,
        "reviewed_commit": manifest.get("reviewed_commit"),
        "manifest_matches": manifest_matches,
        "sources_match": sources_match,
        "source_register_matches": None,
        "source_register_sha256": register_hash,
        "source_population_sha256": population_hash,
    }


def _refresh_public_snapshot(root: Path, snapshot: dict) -> dict:
    """Refresh freshness from aggregate commitments; the source manifest stays private."""
    _validate(snapshot, root / PROJECTION_SCHEMA)
    result = json.loads(json.dumps(snapshot))
    try:
        register_hash, population_hash = _population_commitments(root)
        register_matches = register_hash == result["freshness"]["source_register_sha256"]
        population_matches = population_hash == result["freshness"]["source_population_sha256"]
        result["freshness"]["status"] = "current" if register_matches and population_matches else "stale"
        result["freshness"]["sources_match"] = population_matches
        result["freshness"]["source_register_matches"] = register_matches
        if not (register_matches and population_matches):
            result["coverage"]["source_integrity_verified_count"] = 0
    except (OSError, KeyError, TypeError, ValueError):
        result["freshness"]["status"] = "unknown"
        result["freshness"]["sources_match"] = None
        result["freshness"]["source_register_matches"] = None
    _validate(result, root / PROJECTION_SCHEMA)
    return result


def project_public(root: Path, report: dict | None = None, manifest: dict | None = None,
                   manifest_bytes: bytes | None = None) -> dict:
    """Return an explicit allowlist projection without excerpts or semantic prose."""
    snapshot_path = root / PUBLIC_SNAPSHOT
    if report is None and manifest is None and snapshot_path.is_file():
        return _refresh_public_snapshot(root, _json(snapshot_path))
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
    population = _registered_requirement_sources(root)
    population_ids = {item["id"] for item in population}
    scoped_population_ids = set(source_ids) & population_ids
    if set(source_ids) - population_ids:
        raise ValueError("report scope contains a source outside the tracked requirements population")
    scoped_manifest = dict(manifest)
    scoped_manifest["source_documents"] = [source_by_id[source_id] for source_id in source_ids]
    scoped_manifest["source_count"] = len(source_ids)
    structural_model = generate_model(root, scoped_manifest)
    section_refs = {
        (item["source_id"], item["section_ref"])
        for item in structural_model["requirements"]
    }
    semantic_not_run = report["semantic_review"]["status"] == "not_run"
    source_root = (root / "docs/governance/source-documents").resolve()
    source_integrity_verified = 0
    for source_id in source_ids:
        try:
            source_path = (root / source_by_id[source_id]["source_path"]).resolve()
            source_path.relative_to(source_root)
            if source_path.is_file() and _sha256(source_path) == source_by_id[source_id]["content_sha256"]:
                source_integrity_verified += 1
        except (OSError, ValueError):
            continue
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
        "freshness": _freshness(root, report, manifest, manifest_path, manifest_bytes),
        "scope": {"source_count": len(source_ids), "source_ids": list(source_ids)},
        "semantic_comparison_coverage": {
            "assessed_count": None,
            "population_count": None,
            "status": "not_measured",
        },
        "coverage": {
            "source_population_count": len(population),
            "in_scope_source_count": len(scoped_population_ids),
            "omitted_source_count": len(population_ids - scoped_population_ids),
            "source_integrity_verified_count": source_integrity_verified,
            "source_scope_status": "complete" if scoped_population_ids == population_ids else "partial",
            "section_count": len(section_refs),
            "structurally_inventoried_section_count": len(section_refs),
            "semantically_assessed_section_count": 0 if semantic_not_run else None,
            "semantic_section_coverage_status": "not_run" if semantic_not_run else "not_measured",
            "requirement_count": len(structural_model["requirements"]),
            "structurally_inventoried_requirement_count": len(structural_model["requirements"]),
            "semantically_assessed_requirement_count": 0 if semantic_not_run else None,
            "semantic_item_coverage_status": "not_run" if semantic_not_run else "not_measured",
            "semantic_review_status": report["semantic_review"]["status"],
        },
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


def build_redacted_snapshot(root: Path, report: dict, manifest: dict, manifest_bytes: bytes,
                            comparison_count: int) -> dict:
    """Build the one-time allowlisted snapshot from validated private review inputs."""
    projection = project_public(root, report=report, manifest=manifest, manifest_bytes=manifest_bytes)
    if projection["freshness"]["status"] != "current":
        raise ValueError("review manifest or source files are stale; refusing publication snapshot")
    projection["scope"]["source_ids"] = []
    projection["documents"] = []
    projection["sections"]["human_decisions"] = "recorded_locally_details_withheld"
    projection["semantic_comparison_coverage"] = {
        "assessed_count": comparison_count,
        "population_count": None,
        "status": "targeted_non_exhaustive",
    }
    projection["limitations"]["message"] = (
        "One-time redacted, report-only pilot projection. Structural inventory is not semantic coverage. "
        "Three targeted comparisons do not represent exhaustive review or prove consistency, compliance, "
        "implementation or normative approval. Human decision details are withheld."
    )
    projection["freshness"]["source_register_matches"] = True
    _validate(projection, root / PROJECTION_SCHEMA)
    return projection
