#!/usr/bin/env python3
"""Validate untrusted semantic-review output against an exact source manifest."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = ROOT / "schemas/document-consistency-review-manifest.schema.json"
RESPONSE_SCHEMA = ROOT / "schemas/document-consistency-semantic-response.schema.json"
REPORT_SCHEMA = ROOT / "schemas/document-consistency-semantic-report.schema.json"
SOURCE_ROOT = Path("docs/governance/source-documents")
ROW_PATTERN = re.compile(
    r"^\|\s*`(?P<id>[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3})`\s*"
    r"\|\s*(?P<strength>[^|]*?)\s*\|\s*(?P<context>[^|]*?)\s*\|\s*(?P<requirement>.*)\|\s*$"
)


class SemanticReviewError(ValueError):
    """Raised when the validation inputs cannot be safely processed."""


def read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SemanticReviewError(f"cannot read JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise SemanticReviewError(f"expected JSON object: {path}")
    return payload


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise SemanticReviewError(f"cannot read file for hashing: {path}") from exc


def require_schema(payload: dict, schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.path) or "<root>"
        raise SemanticReviewError(f"{label} schema error at {location}: {first.message}")


def safe_source_path(root: Path, relative_path: str) -> Path:
    source_root = (root / SOURCE_ROOT).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(source_root)
    except ValueError as exc:
        raise SemanticReviewError(f"source path is outside the source directory: {relative_path}") from exc
    if not candidate.is_file():
        raise SemanticReviewError(f"source path is missing or outside the source directory: {relative_path}")
    return candidate


def requirement_rows(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SemanticReviewError(f"cannot read source: {path}") from exc
    for line_number, line in enumerate(lines, 1):
        match = ROW_PATTERN.match(line)
        if not match:
            continue
        row_id = match.group("id")
        if row_id in rows:
            raise SemanticReviewError(f"duplicate requirement locator in source: {row_id}")
        rows[row_id] = {
            "line": line_number,
            "strength": match.group("strength").strip(),
            "context": match.group("context").strip(),
            "requirement": match.group("requirement").strip(),
        }
    return rows


def execution_errors(response: dict) -> list[str]:
    execution = response["execution"]
    errors: list[str] = []
    if execution["mode"] == "synthetic_fixture":
        if execution["provider"] is not None or execution["model"] is not None:
            errors.append("synthetic fixture must not claim a provider or model")
    elif execution["status"] == "completed":
        if not execution["provider"] or not execution["model"]:
            errors.append("completed provider execution requires exact provider and model identifiers")
    if execution["status"] != "completed" and response["findings"]:
        errors.append("failed or not-run execution must not contain findings")
    return errors


def _finding_completeness_errors(finding: dict, manifest_source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    evidence = finding["evidence"]
    if finding["semantic_state"] == "proposed" and not evidence:
        errors.append("proposed finding has no evidence")
    if finding["category"] == "conflict" and len(evidence) < 2:
        errors.append("conflict finding requires evidence for both statements")
    if finding["category"] == "coverage_gap":
        scope = finding["search_scope"]
        if scope is None:
            errors.append("coverage-gap finding requires an explicit search scope")
        else:
            unknown = sorted(set(scope["source_ids"]) - manifest_source_ids)
            if unknown:
                errors.append(f"search scope contains sources outside manifest: {', '.join(unknown)}")
    elif finding["search_scope"] is not None:
        unknown = sorted(set(finding["search_scope"]["source_ids"]) - manifest_source_ids)
        if unknown:
            errors.append(f"search scope contains sources outside manifest: {', '.join(unknown)}")
    if finding["semantic_state"] == "proposed" and finding["applicability"]["status"] == "unknown":
        errors.append("proposed finding cannot claim confirmed applicability when context is unknown")
    return errors


def validate_semantic_response(
    root: Path,
    manifest: dict,
    response: dict,
    manifest_sha256: str,
) -> dict:
    """Return a report-only validation result without accepting semantic claims."""
    require_schema(manifest, root / MANIFEST_SCHEMA.relative_to(ROOT), "manifest")
    require_schema(response, root / RESPONSE_SCHEMA.relative_to(ROOT), "semantic response")

    manifest_sources = {item["id"]: item for item in manifest["source_documents"]}
    source_rows: dict[str, dict[str, dict]] = {}
    source_errors: dict[str, str] = {}
    execution_validation_errors = execution_errors(response)
    formal_errors = list(execution_validation_errors)
    manifest_digest_mismatch = response["source_manifest_sha256"] != manifest_sha256
    if manifest_digest_mismatch:
        formal_errors.append("response source manifest digest differs from supplied manifest bytes")
    register_stale = False
    register_path = root / manifest["source_register_path"]
    try:
        if sha256_file(register_path) != manifest["source_register_sha256"]:
            formal_errors.append("current source register bytes differ from manifest")
            register_stale = True
    except SemanticReviewError as exc:
        formal_errors.append(str(exc))
        register_stale = True

    for source_id, source in manifest_sources.items():
        try:
            path = safe_source_path(root, source["source_path"])
            current_hash = sha256_file(path)
            if current_hash != source["content_sha256"]:
                source_errors[source_id] = "current source bytes differ from manifest"
            source_rows[source_id] = requirement_rows(path)
        except SemanticReviewError as exc:
            source_errors[source_id] = str(exc)

    finding_ids = [item["finding_id"] for item in response["findings"]]
    duplicate_finding_ids = {item for item in finding_ids if finding_ids.count(item) > 1}
    validated_findings: list[dict] = []
    manifest_source_ids = set(manifest_sources)

    for finding in response["findings"]:
        output = deepcopy(finding)
        errors = _finding_completeness_errors(finding, manifest_source_ids)
        statuses: list[str] = []
        if execution_validation_errors:
            errors.extend(f"execution: {item}" for item in execution_validation_errors)
            statuses.append("invalid")
        if manifest_digest_mismatch:
            errors.append("finding is bound to a different source manifest digest")
            statuses.append("stale")
        if register_stale:
            errors.append("finding source register snapshot is stale")
            statuses.append("stale")
        if finding["finding_id"] in duplicate_finding_ids:
            errors.append(f"duplicate finding ID: {finding['finding_id']}")
            statuses.append("invalid")

        evidence_ids = [item["evidence_id"] for item in finding["evidence"]]
        for duplicate in sorted({item for item in evidence_ids if evidence_ids.count(item) > 1}):
            errors.append(f"duplicate evidence ID in finding: {duplicate}")
            statuses.append("invalid")

        for evidence in finding["evidence"]:
            source_id = evidence["source_id"]
            source = manifest_sources.get(source_id)
            if source is None:
                errors.append(f"{evidence['evidence_id']}: source is outside manifest: {source_id}")
                statuses.append("invalid")
                continue
            if source_id in source_errors:
                errors.append(f"{evidence['evidence_id']}: {source_errors[source_id]}")
                statuses.append("stale")
            if evidence["content_sha256"] != source["content_sha256"]:
                errors.append(f"{evidence['evidence_id']}: evidence hash differs from manifest")
                statuses.append("stale")
            locator = evidence["locator"]["value"]
            row = source_rows.get(source_id, {}).get(locator)
            if row is None:
                errors.append(f"{evidence['evidence_id']}: requirement locator is unresolved: {locator}")
                statuses.append("invalid")
                continue
            if evidence["excerpt"] not in row["requirement"]:
                errors.append(f"{evidence['evidence_id']}: excerpt does not exactly match the located requirement")
                statuses.append("invalid")

        if errors and not statuses:
            statuses.append("incomplete")
        if "stale" in statuses:
            evidence_status = "stale"
        elif "invalid" in statuses:
            evidence_status = "invalid"
        elif "incomplete" in statuses:
            evidence_status = "incomplete"
        else:
            evidence_status = "valid"

        if evidence_status != "valid":
            disposition = "quarantined"
        elif finding["semantic_state"] == "context_missing":
            disposition = "context_missing"
        elif finding["semantic_state"] == "not_assessable":
            disposition = "not_assessable"
        else:
            disposition = "unconfirmed"
        output.update(
            evidence_status=evidence_status,
            disposition=disposition,
            validation_errors=errors,
        )
        validated_findings.append(output)

    quarantined = sum(item["disposition"] == "quarantined" for item in validated_findings)
    context_missing = sum(item["disposition"] == "context_missing" for item in validated_findings)
    not_assessable = sum(item["disposition"] == "not_assessable" for item in validated_findings)
    unconfirmed = sum(item["disposition"] == "unconfirmed" for item in validated_findings)

    execution = response["execution"]
    if execution["status"] == "not_run":
        review_status = "not_run"
    elif execution["status"] == "failed":
        review_status = "provider_failed"
    elif execution["mode"] == "synthetic_fixture":
        review_status = "synthetic_only"
    else:
        review_status = "partial"

    report = {
        "report_version": "1.0.0",
        "report_type": "document_consistency_semantic_validation_report",
        "review_id": response["review_id"],
        "overall_status": review_status,
        "scope": {
            "source_manifest_sha256": manifest_sha256,
            "source_ids": sorted(manifest_sources),
        },
        "execution": deepcopy(execution),
        "formal_validation": {
            "status": "fail" if formal_errors or source_errors or quarantined else "pass",
            "errors": formal_errors + [f"{key}: {value}" for key, value in sorted(source_errors.items())],
        },
        "semantic_review": {
            "status": review_status,
            "finding_count": len(validated_findings),
            "validated_count": unconfirmed,
            "quarantined_count": quarantined,
            "context_missing_count": context_missing,
            "not_assessable_count": not_assessable,
        },
        "human_decisions": {"status": "not_run", "decisions": []},
        "implementation_coverage": {
            "status": "not_assessed",
            "details": ["The bounded Phase 2 validator does not assess repository or consumer implementation coverage."],
        },
        "findings": validated_findings,
        "limitations": [
            "A valid excerpt proves source origin only; it does not prove the interpretation.",
            "All validated semantic findings remain unconfirmed until a documented human decision.",
            "Synthetic fixtures are validator evidence and are not findings about the registered sources.",
            "No overall consistency, compliance, or implementation claim is produced.",
        ] + response["limitations"],
    }
    require_schema(report, root / REPORT_SCHEMA.relative_to(ROOT), "semantic report")
    return report


def markdown_report(report: dict) -> str:
    lines = [
        "# Document Consistency Review — Semantic Validation Report",
        "",
        f"- Overall status: `{report['overall_status']}`",
        f"- Execution mode: `{report['execution']['mode']}`",
        f"- Execution status: `{report['execution']['status']}`",
        f"- Formal validation: `{report['formal_validation']['status']}`",
        f"- Human decisions: `{report['human_decisions']['status']}`",
        f"- Implementation coverage: `{report['implementation_coverage']['status']}`",
        "",
        "| Finding | Category | Evidence | Disposition |",
        "|---|---|---|---|",
    ]
    for finding in report["findings"]:
        lines.append(
            f"| {finding['finding_id']} | `{finding['category']}` | "
            f"`{finding['evidence_status']}` | `{finding['disposition']}` |"
        )
    if not report["findings"]:
        lines.append("| — | — | — | — |")
    lines.extend(["", "## Validation errors", ""])
    errors = report["formal_validation"]["errors"]
    lines.extend(f"- {item}" for item in errors)
    if not errors:
        lines.append("- None")
    for finding in report["findings"]:
        if finding["validation_errors"]:
            lines.append(f"- {finding['finding_id']}: {'; '.join(finding['validation_errors'])}")
    lines.extend(["", "## Limits", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    paths = [args.manifest, args.response, args.output_json, args.output_markdown]
    resolved = [path if path.is_absolute() else ROOT / path for path in paths]
    try:
        manifest_path, response_path, json_path, markdown_path = resolved
        manifest = read_json(manifest_path)
        response = read_json(response_path)
        report = validate_semantic_response(ROOT, manifest, response, sha256_file(manifest_path))
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        markdown_path.write_text(markdown_report(report), encoding="utf-8")
        print(
            "Semantic validation status: "
            f"{report['overall_status']} "
            f"({report['semantic_review']['quarantined_count']} quarantined)"
        )
    except (OSError, SemanticReviewError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
