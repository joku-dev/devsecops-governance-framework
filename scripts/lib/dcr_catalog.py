"""Prepare an isolated, provider-unbound semantic catalog run package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator


from lib.portable.contracts import ROOT
FIXTURES = ROOT / "tests/fixtures/document-consistency-review-semantic"
CATALOG = ROOT / "model/governance/document-consistency/semantic-evaluation-catalog-v1.json"
PROMPT = ROOT / "model/governance/document-consistency/semantic-catalog-prompt-v1.txt"
PACKAGE_SCHEMA = ROOT / "schemas/document-consistency-semantic-catalog-run-package.schema.json"


class CatalogRunPreparationError(ValueError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CatalogRunPreparationError(f"expected JSON object: {path}")
    return value


def prepare(output_dir: Path, *, root: Path = ROOT) -> dict:
    fixtures = root / FIXTURES.relative_to(ROOT)
    catalog_path = root / CATALOG.relative_to(ROOT)
    prompt = root / PROMPT.relative_to(ROOT)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise CatalogRunPreparationError("output directory must not exist or must be empty")
    provider = output_dir / "provider-input"
    sources = provider / "docs/governance/source-documents"
    register = provider / "model/documents"
    sources.mkdir(parents=True, exist_ok=True)
    register.mkdir(parents=True, exist_ok=True)

    copies = {
        fixtures / "manifest.json": provider / "source-manifest.json",
        fixtures / "source-a.md": sources / "SYN-SRC-A-001.md",
        fixtures / "source-b.md": sources / "SYN-SRC-B-001.md",
        fixtures / "source-document-register.yaml": register / "source-document-register.yaml",
        root / "schemas/document-consistency-provider-projection.schema.json": provider / "provider-projection.schema.json",
        prompt: provider / "prompt.txt",
    }
    for source, target in copies.items():
        shutil.copyfile(source, target)

    manifest = read_json(provider / "source-manifest.json")
    catalog = read_json(catalog_path)
    if digest(provider / "source-manifest.json") != catalog["source_manifest_sha256"]:
        raise CatalogRunPreparationError("catalog and source manifest digest differ")
    if set(catalog["source_ids"]) != {item["id"] for item in manifest["source_documents"]}:
        raise CatalogRunPreparationError("catalog and source manifest source IDs differ")
    for item in manifest["source_documents"]:
        path = provider / item["source_path"]
        if digest(path) != item["content_sha256"]:
            raise CatalogRunPreparationError(f"source digest differs from manifest: {item['id']}")
    if digest(provider / manifest["source_register_path"]) != manifest["source_register_sha256"]:
        raise CatalogRunPreparationError("source register digest differs from manifest")

    input_rows = []
    for path in sorted(provider.rglob("*")):
        if path.is_file():
            input_rows.append({"path": path.relative_to(output_dir).as_posix(), "sha256": digest(path)})
    package = {
        "schema_version": "1.0.0",
        "package_type": "document_consistency_semantic_catalog_run_package",
        "package_id": "dcr-catalog-run-0001",
        "status": "prepared_not_run",
        "provider_binding": "runtime_authorization_required",
        "model_binding": "runtime_authorization_required",
        "prompt_version": "semantic-catalog-v1",
        "adapter_configuration": "dcr-adapter-0001",
        "catalog": {"id": catalog["catalog_id"], "path": CATALOG.relative_to(ROOT).as_posix(), "sha256": digest(catalog_path)},
        "provider_input": input_rows,
        "decision_boundary": "Package preparation invokes no provider; each execution requires separate explicit authorization and runtime provider/model binding.",
    }
    errors = list(Draft202012Validator(read_json(root / PACKAGE_SCHEMA.relative_to(ROOT))).iter_errors(package))
    if errors:
        raise CatalogRunPreparationError(errors[0].message)
    (output_dir / "run-package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")
    return package

