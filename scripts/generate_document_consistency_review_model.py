#!/usr/bin/env python3
"""Build a deterministic, text-free structural inventory from a source manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from jsonschema import Draft202012Validator
from lib.source_document_text import (
    ExtractedSourceDocument,
    SourceDocumentExtractionError,
    extract_source_document,
    line_for_markdown_parser,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = ROOT / "schemas" / "document-consistency-review-manifest.schema.json"
MODEL_SCHEMA = ROOT / "schemas" / "document-consistency-review-model.schema.json"
ID_CELL = re.compile(r"^\|\s*`([A-Z0-9]+(?:-[A-Z0-9]+)+)`\s*\|")
STABLE_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]{3}\b")


class InventoryError(ValueError):
    """Raised when source identity or structure cannot be verified."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError(f"cannot read JSON input: {path}") from exc
    if not isinstance(payload, dict):
        raise InventoryError(f"JSON input must be an object: {path}")
    return payload


def validate_schema(payload: dict, schema_path: Path, label: str) -> None:
    schema = load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "<root>"
        raise InventoryError(f"{label} schema error at {location}: {error.message}")


def extract_identifiers(
    source_id: str,
    source_path: Path,
    document: ExtractedSourceDocument | None = None,
) -> list[dict]:
    identifiers = []
    document = document or extract_source_document(source_path)
    for source_line in document.lines:
        line_number = source_line.number
        line = line_for_markdown_parser(source_line)
        match = ID_CELL.match(line)
        if not match:
            continue
        cells = [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        row_id = match.group(1)
        for identifier in sorted(set(STABLE_ID.findall(" | ".join(cells[1:]))) - {row_id}):
            kind = "declared" if identifier.split("-", 1)[0] == source_id.split("-", 1)[0] else "reference"
            identifiers.append({"id": identifier, "line": line_number, "kind": kind})
    return identifiers


def extract_requirement_rows(
    source_id: str,
    source_path: Path,
    document: ExtractedSourceDocument | None = None,
) -> tuple[list[dict], list[dict]]:
    """Extract stable row IDs, strength, and opaque section references without source prose."""
    requirements = []
    references = []
    document = document or extract_source_document(source_path)
    for source_line in document.lines:
        line_number = source_line.number
        line = line_for_markdown_parser(source_line)
        match = ID_CELL.match(line)
        if not match:
            continue
        cells = [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 4 or cells[1] not in {"MUST", "SHALL", "SHOULD", "REQUIREMENT"}:
            continue
        requirement_id = match.group(1)
        mandatory = cells[1] in {"MUST", "SHALL"}
        section_ref = "SEC-" + hashlib.sha256(f"{source_id}\0{cells[2]}".encode("utf-8")).hexdigest()[:12].upper()
        requirements.append(
            {
                "id": requirement_id,
                "source_id": source_id,
                "strength": cells[1],
                "mandatory": mandatory,
                "section_ref": section_ref,
                "owner_role_id": None,
                "verification_artifact_id": None,
                "open_gap": (
                    "Owner and verification mappings are outside this requirements-only input."
                    if mandatory
                    else None
                ),
            }
        )
        for target_id in sorted(set(STABLE_ID.findall(" | ".join(cells[3:]))) - {requirement_id}):
            references.append(
                {
                    "type": "references",
                    "source_entity_id": requirement_id,
                    "target_entity_id": target_id,
                    "source_document_id": source_id,
                    "status": "candidate",
                }
            )
    return requirements, references


def generate_model(root: Path, manifest: dict) -> dict:
    validate_schema(manifest, root / "schemas/document-consistency-review-manifest.schema.json", "manifest")
    sources = []
    requirements = []
    relationships = []
    for item in manifest["source_documents"]:
        path = (root / item["source_path"]).resolve()
        try:
            path.relative_to((root / "docs/governance/source-documents").resolve())
        except ValueError as exc:
            raise InventoryError(f"source path escapes governed source directory: {item['id']}") from exc
        if not path.is_file() or sha256_file(path) != item["content_sha256"]:
            raise InventoryError(f"source bytes do not match manifest: {item['id']}")
        extraction_error = None
        try:
            extracted_document = extract_source_document(path)
        except SourceDocumentExtractionError as exc:
            extracted_document = None
            extraction_error = str(exc)
        extraction_warnings = (
            list(extracted_document.warnings)
            if extracted_document
            else [f"source_document_extraction_blocked:{extraction_error}"]
        )
        sources.append(
            {
                "id": item["id"],
                "status": item["status"],
                "version": item["version"],
                "source_path": item["source_path"],
                "sha256": item["content_sha256"],
                "identifiers": extract_identifiers(item["id"], path, extracted_document)
                if extracted_document
                else [],
                "extraction_format": extracted_document.format
                if extracted_document
                else path.suffix.lower().lstrip("."),
                "extraction_warnings": extraction_warnings,
            }
        )
        if extracted_document is None:
            continue
        extracted_requirements, extracted_references = extract_requirement_rows(
            item["id"], path, extracted_document
        )
        requirements.extend(extracted_requirements)
        relationships.extend(extracted_references)

    model = {
        "schema_version": "1.0.0",
        "reviewed_commit": manifest["reviewed_commit"],
        "sources": sources,
        "roles": [],
        "local_role_profiles": [],
        "requirements": requirements,
        "gates": [],
        "artifacts": [],
        "evidence_links": [],
        "relationships": relationships,
        "derivation_relationships": [],
        "topic_authorities": [],
    }
    validate_schema(model, root / "schemas/document-consistency-review-model.schema.json", "model")
    return model


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="source manifest JSON")
    parser.add_argument("--output", type=Path, help="new output path; defaults to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output_path = args.output if args.output and args.output.is_absolute() else ROOT / args.output if args.output else None
    try:
        model = generate_model(ROOT, load_json(manifest_path))
        serialized = json.dumps(model, indent=2, ensure_ascii=False) + "\n"
        if output_path:
            if output_path.exists() and output_path.read_text(encoding="utf-8") != serialized:
                raise InventoryError(f"refusing to replace different existing output: {output_path}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(serialized, encoding="utf-8")
            print(f"Wrote structural inventory for {len(model['sources'])} source(s): {output_path}")
        else:
            print(serialized, end="")
    except (InventoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
