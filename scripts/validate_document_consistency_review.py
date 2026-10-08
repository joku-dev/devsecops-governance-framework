#!/usr/bin/env python3
"""Run deterministic structural checks without interpreting source meaning."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = ROOT / "schemas/document-consistency-review-manifest.schema.json"
MODEL_SCHEMA = ROOT / "schemas/document-consistency-review-model.schema.json"
ENTITY_ARRAYS = ("roles", "local_role_profiles", "requirements", "gates", "artifacts")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def require_schema(payload: dict, schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        where = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"{label} schema error at {where}: {first.message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _rule(rule_id: str, status: str, details: list[str] | None = None) -> dict:
    return {"rule_id": rule_id, "status": status, "details": details or []}


def validate_model(root: Path, manifest: dict, model: dict) -> dict:
    """Return rule results; semantic consistency is always outside this report."""
    require_schema(manifest, root / MANIFEST_SCHEMA.relative_to(ROOT), "manifest")
    require_schema(model, root / MODEL_SCHEMA.relative_to(ROOT), "model")
    manifest_sources = {source["id"]: source for source in manifest["source_documents"]}
    model_sources = {source["id"]: source for source in model["sources"]}
    rules: list[dict] = []

    # DCR-001: stable IDs are unique, and all explicit cross-references resolve.
    all_ids: list[str] = list(model_sources)
    for source in model["sources"]:
        all_ids.extend(item["id"] for item in source["identifiers"] if item["kind"] == "declared")
    for key in ENTITY_ARRAYS:
        all_ids.extend(item["id"] if isinstance(item, dict) else item for item in model[key])
    duplicates = sorted({item for item in all_ids if all_ids.count(item) > 1})
    source_ids = set(manifest_sources)
    role_ids = set(model["roles"]) | set(model["local_role_profiles"])
    artifact_ids = {item["id"] for item in model["artifacts"]}
    requirement_ids = {item["id"] for item in model["requirements"]}
    reference_errors = []
    for relation in model["derivation_relationships"]:
        if relation["source_id"] not in source_ids:
            reference_errors.append(f"derivation source is not in manifest: {relation['source_id']}")
    # Only declared IDs resolve a reference; a mere mention of an unknown ID
    # must not make its own target appear valid.
    entity_ids = set(all_ids)
    for relation in model["relationships"]:
        if relation["source_entity_id"] not in entity_ids:
            reference_errors.append(f"relationship source is unresolved: {relation['source_entity_id']}")
        if relation["target_entity_id"] not in entity_ids:
            reference_errors.append(f"relationship target is unresolved: {relation['target_entity_id']}")
        if relation["source_document_id"] not in source_ids:
            reference_errors.append(f"relationship source document is not in manifest: {relation['source_document_id']}")
    for collection in ("requirements", "gates", "artifacts"):
        for item in model[collection]:
            if item["source_id"] not in source_ids:
                reference_errors.append(f"{collection[:-1]} source is not in manifest: {item['source_id']}")
    for topic in model["topic_authorities"]:
        for source_id in topic["source_ids"]:
            if source_id not in source_ids:
                reference_errors.append(f"authority source is not in manifest: {source_id}")
    dcr001 = [f"duplicate ID: {item}" for item in duplicates] + reference_errors
    rules.append(_rule("DCR-001", "fail" if dcr001 else "pass", dcr001))

    # DCR-002: source snapshot metadata and exact bytes match the manifest/register view.
    dcr002 = []
    register_path = (root / manifest["source_register_path"]).resolve()
    register_entries = {}
    try:
        if sha256_file(register_path) != manifest["source_register_sha256"]:
            dcr002.append("source register bytes differ from manifest")
        register_payload = yaml.safe_load(register_path.read_text(encoding="utf-8"))
        register_entries = {item["id"]: item for item in register_payload["documents"]}
    except (OSError, KeyError, TypeError, yaml.YAMLError):
        dcr002.append("source register cannot be read as registered metadata")
    if set(model_sources) != set(manifest_sources):
        dcr002.append("model source IDs differ from manifest source IDs")
    for source_id in sorted(set(model_sources) & set(manifest_sources)):
        current = model_sources[source_id]
        registered = manifest_sources[source_id]
        for field in ("status", "version", "source_path"):
            if current[field] != registered[field]:
                dcr002.append(f"{source_id}: {field} differs from manifest")
        register_item = register_entries.get(source_id)
        if register_item is None:
            dcr002.append(f"{source_id}: not found in current source register")
        else:
            for model_field, register_field in (("status", "status"), ("version", "version"), ("source_path", "source_path")):
                if registered[model_field] != register_item.get(register_field):
                    dcr002.append(f"{source_id}: manifest {model_field} differs from current register")
            if registered["title"] != register_item.get("title") or registered["owner"] != register_item.get("owner"):
                dcr002.append(f"{source_id}: manifest title/owner differs from current register")
            if sorted(registered["governance_domains"]) != sorted(register_item.get("governance_domains", [])):
                dcr002.append(f"{source_id}: manifest governance domains differ from current register")
        if current["sha256"] != registered["content_sha256"]:
            dcr002.append(f"{source_id}: model hash differs from manifest")
        path = (root / current["source_path"]).resolve()
        if not path.is_file() or sha256_file(path) != registered["content_sha256"]:
            dcr002.append(f"{source_id}: source bytes differ from manifest")
    rules.append(_rule("DCR-002", "fail" if dcr002 else "pass", dcr002))

    # DCR-003: role references resolve to a declared role or explicit local profile.
    role_refs = []
    for item in model["requirements"]:
        if item["owner_role_id"]:
            role_refs.append(item["owner_role_id"])
    for item in model["gates"]:
        if item["decision_owner_role_id"]:
            role_refs.append(item["decision_owner_role_id"])
    if not role_refs:
        rules.append(_rule("DCR-003", "not_in_scope", ["model contains no role references"]))
    else:
        missing = sorted(set(role_refs) - role_ids)
        rules.append(_rule("DCR-003", "fail" if missing else "pass", [f"unresolved role: {item}" for item in missing]))

    # DCR-004: mandatory requirements have owner and verification, or an explicit gap.
    if not model["requirements"]:
        rules.append(_rule("DCR-004", "not_in_scope", ["no structured requirement records supplied"]))
    else:
        gaps = []
        acknowledged_gaps = []
        for item in model["requirements"]:
            if item["mandatory"] and not item["open_gap"]:
                if not item["owner_role_id"] or not item["verification_artifact_id"]:
                    gaps.append(f"{item['id']}: mandatory requirement lacks owner/verification or documented gap")
            elif item["mandatory"] and item["open_gap"]:
                acknowledged_gaps.append(item["id"])
            if item["verification_artifact_id"] and item["verification_artifact_id"] not in artifact_ids:
                gaps.append(f"{item['id']}: unresolved verification artifact {item['verification_artifact_id']}")
            if item["source_id"] not in source_ids:
                gaps.append(f"{item['id']}: source is not in manifest")
        details = gaps
        if acknowledged_gaps:
            details = [
                f"{len(acknowledged_gaps)} mandatory requirement(s) have an explicit scope gap for owner/verification mapping."
            ] + gaps
        rules.append(_rule("DCR-004", "fail" if gaps else "pass", details))

    # DCR-005: gates expose inputs, outputs and a decision owner, or an explicit gap.
    if not model["gates"]:
        rules.append(_rule("DCR-005", "not_in_scope", ["no structured gate records supplied"]))
    else:
        gaps = []
        for gate in model["gates"]:
            complete = gate["input_artifact_ids"] and gate["output_artifact_ids"] and gate["decision_owner_role_id"]
            if not complete and not gate["open_gap"]:
                gaps.append(f"{gate['id']}: missing gate input/output/decision owner without documented gap")
            for artifact_id in gate["input_artifact_ids"] + gate["output_artifact_ids"]:
                if artifact_id not in artifact_ids:
                    gaps.append(f"{gate['id']}: unresolved artifact {artifact_id}")
        rules.append(_rule("DCR-005", "fail" if gaps else "pass", gaps))

    # DCR-006: evidence links resolve to known requirements and artifact types.
    if not model["evidence_links"]:
        rules.append(_rule("DCR-006", "not_in_scope", ["no structured evidence links supplied"]))
    else:
        gaps = []
        for link in model["evidence_links"]:
            if link["requirement_id"] not in requirement_ids:
                gaps.append(f"evidence link has unknown requirement: {link['requirement_id']}")
            if link["artifact_id"] not in artifact_ids:
                gaps.append(f"evidence link has unknown artifact: {link['artifact_id']}")
        rules.append(_rule("DCR-006", "fail" if gaps else "pass", gaps))

    # DCR-007: no accepted derivation may originate from an unapproved candidate.
    dcr007 = []
    for relation in model["relationships"]:
        source = manifest_sources.get(relation["source_document_id"])
        if source and source["status"] == "candidate" and relation["status"] == "confirmed":
            dcr007.append(f"candidate source has confirmed relationship: {relation['source_document_id']}")
    for relation in model["derivation_relationships"]:
        source = manifest_sources.get(relation["source_id"])
        if source is None:
            continue
        if source["status"] == "candidate" and relation["status"] == "accepted":
            dcr007.append(f"candidate source has accepted derivation: {relation['source_id']}")
    rules.append(_rule("DCR-007", "fail" if dcr007 else "pass", dcr007))

    # DCR-008: authority is unique, or ambiguity is explicitly left open.
    if not model["topic_authorities"]:
        rules.append(_rule("DCR-008", "not_in_scope", ["no topic-authority map supplied"]))
    else:
        ambiguity = []
        for topic in model["topic_authorities"]:
            if len(topic["source_ids"]) != 1 and not topic["decision_open"]:
                ambiguity.append(f"{topic['topic']}: authority is not unique and no open decision is recorded")
        rules.append(_rule("DCR-008", "fail" if ambiguity else "pass", ambiguity))

    # DCR-009: report and model refer to the same recorded snapshot; freshness
    # follows the selected register/source bytes rather than unrelated commits.
    freshness = []
    snapshot_notes = []
    head = git_head(root)
    if not manifest["reviewed_commit"] or model["reviewed_commit"] != manifest["reviewed_commit"]:
        freshness.append("manifest/model commit is missing or differs")
    elif head and head != manifest["reviewed_commit"]:
        snapshot_notes.append(
            "repository HEAD is newer than the recorded source snapshot; freshness is checked against register and source bytes"
        )
    if set(model_sources) != set(manifest_sources):
        freshness.append("model source set differs from manifest")
    register_path = root / manifest["source_register_path"]
    if not register_path.is_file() or sha256_file(register_path) != manifest["source_register_sha256"]:
        freshness.append("source register snapshot is stale")
    for source_id, source in model_sources.items():
        registered = manifest_sources.get(source_id)
        if not registered or source["sha256"] != registered["content_sha256"]:
            freshness.append(f"{source_id}: source review is stale")
            continue
        source_path = (root / source["source_path"]).resolve()
        if not source_path.is_file() or sha256_file(source_path) != registered["content_sha256"]:
            freshness.append(f"{source_id}: current source bytes differ from the reviewed snapshot")
    rules.append(_rule("DCR-009", "fail" if freshness else "pass", freshness + snapshot_notes))

    statuses = [item["status"] for item in rules]
    overall = "fail" if "fail" in statuses else "partial" if "not_in_scope" in statuses else "pass"
    return {
        "report_version": "1.0.0",
        "reviewed_commit": manifest["reviewed_commit"],
        "scope": {"source_ids": sorted(manifest_sources), "source_count": len(manifest_sources)},
        "overall_status": overall,
        "semantic_review": "not_run",
        "rules": rules,
        "limitations": [
            "Structural checks do not prove semantic consistency, completeness, implementation, or compliance.",
            "not_in_scope rules remain open for a later structured governance model.",
            "Owner metadata is review routing and does not confirm source authority.",
        ],
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Document Consistency Review — Structural Report",
        "",
        f"- Overall structural status: `{report['overall_status']}`",
        f"- Semantic review: `{report['semantic_review']}`",
        f"- Reviewed commit: `{report['reviewed_commit'] or 'not bound'}`",
        f"- Sources: {', '.join(report['scope']['source_ids'])}",
        "",
        "| Rule | Status | Details |",
        "|---|---|---|",
    ]
    for rule in report["rules"]:
        details = "; ".join(rule["details"]) or "—"
        lines.append(f"| {rule['rule_id']} | `{rule['status']}` | {details} |")
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    paths = [args.manifest, args.model, args.output_json, args.output_markdown]
    resolved = [path if path.is_absolute() else ROOT / path for path in paths]
    try:
        report = validate_model(ROOT, read_json(resolved[0]), read_json(resolved[1]))
        json_path, markdown_path = resolved[2], resolved[3]
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        markdown_path.write_text(markdown_report(report), encoding="utf-8")
        print(f"Structural review status: {report['overall_status']}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1 if report["overall_status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
