#!/usr/bin/env python3
"""Validate and build governed HTML, DOCX and PDF from a publication manifest."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from html import escape
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "doc-as-code"
TOOLCHAIN = COMPONENT / "toolchain.env"
DEFAULT_MANIFEST = ROOT / "docs/publishing/doc-as-code-pilot/publication.yaml"
PUBLICATION_SCHEMA = COMPONENT / "schemas/publication.schema.json"
REQUIREMENT_SCHEMA = COMPONENT / "schemas/requirement.schema.json"
DEFAULT_CSS = COMPONENT / "styles/publication.css"
DEFAULT_OUTPUT = ROOT / "build/doc-as-code"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a YAML mapping")
    return value


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        raise ValueError(f"{path.relative_to(ROOT)} must start with YAML frontmatter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"{path.relative_to(ROOT)} frontmatter must be a YAML mapping")
    return metadata, content[match.end():].lstrip()


def validate_schema(instance: dict, schema_path: Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            details.append(f"{location}: {error.message}")
        raise ValueError(f"{label} failed schema validation: {'; '.join(details)}")


def json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def load_publication(manifest_path: Path) -> tuple[dict, list[dict]]:
    manifest_path = manifest_path.resolve()
    publishing_root = (ROOT / "docs/publishing").resolve()
    if not manifest_path.is_relative_to(publishing_root) or manifest_path.name != "publication.yaml":
        raise ValueError("publication manifest must be named publication.yaml under docs/publishing/")
    if not manifest_path.is_file():
        raise ValueError(f"publication manifest not found: {manifest_path}")
    manifest = json_safe(read_yaml(manifest_path))
    validate_schema(manifest, PUBLICATION_SCHEMA, manifest_path.relative_to(ROOT).as_posix())

    publication_root = manifest_path.parent
    seen_paths: set[Path] = set()
    requirement_ids: set[str] = set()
    sections: list[dict] = []
    for position, declaration in enumerate(manifest["sections"], start=1):
        path = (publication_root / declaration["path"]).resolve()
        if not path.is_relative_to(publication_root):
            raise ValueError(f"section {position} escapes the publication directory")
        if path in seen_paths:
            raise ValueError(f"section path is declared more than once: {declaration['path']}")
        seen_paths.add(path)
        if path.suffix.lower() != ".md" or not path.is_file():
            raise ValueError(f"section is not an existing Markdown file: {declaration['path']}")
        entry = {"position": position, "kind": declaration["kind"], "path": path}
        if declaration["kind"] == "requirement":
            requirements_root = (publication_root / "requirements").resolve()
            if not path.is_relative_to(requirements_root):
                raise ValueError(f"requirement section must stay under requirements/: {declaration['path']}")
            metadata, body = parse_frontmatter(path)
            metadata = json_safe(metadata)
            validate_schema(metadata, REQUIREMENT_SCHEMA, path.relative_to(ROOT).as_posix())
            if metadata["id"] in requirement_ids:
                raise ValueError(f"duplicate requirement id: {metadata['id']}")
            requirement_ids.add(metadata["id"])
            entry.update({"metadata": metadata, "body": body})
        else:
            content = path.read_text(encoding="utf-8")
            if content.startswith("---"):
                raise ValueError(f"chapter must not define separate frontmatter: {declaration['path']}")
            entry["body"] = content.strip() + "\n"
        sections.append(entry)
    return manifest, sections


def assembled_markdown(manifest: dict, sections: list[dict]) -> str:
    metadata = {
        "title": manifest["title"],
        "lang": manifest["language"],
        "date": manifest["version"],
        "document-id": manifest["id"],
    }
    parts = ["---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip() + "\n---\n"]
    for section in sections:
        if section["kind"] == "requirement":
            requirement = section["metadata"]
            parts.append(
                f"# {requirement['id']}: {requirement['title']}\n\n"
                f"| Merkmal | Wert |\n|---|---|\n"
                f"| Status | {requirement['status']} |\n"
                f"| Normativer Grad | {requirement['normative_level']} |\n"
                f"| Verantwortlich | {requirement['owner']} |\n"
                f"| Gültig ab | {requirement['effective_from']} |\n\n"
                f"{section['body'].strip()}\n"
            )
        else:
            parts.append(section["body"].strip() + "\n")
    return "\n\n".join(parts).rstrip() + "\n"


def requirement_index(manifest: dict, sections: list[dict]) -> dict:
    requirements = []
    for section in sections:
        if section["kind"] != "requirement":
            continue
        metadata = section["metadata"]
        requirements.append({
            **metadata,
            "position": section["position"],
            "path": section["path"].relative_to(ROOT).as_posix(),
            "sha256": sha256(section["path"]),
        })
    return {
        "schema_version": 1,
        "publication_id": manifest["id"],
        "publication_version": manifest["version"],
        "requirements": requirements,
    }


def load_toolchain() -> dict[str, str]:
    values = {}
    for line in TOOLCHAIN.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, raw_value = stripped.partition("=")
        if not separator or not key.isidentifier() or not raw_value:
            raise ValueError(f"invalid toolchain setting: {line}")
        parsed_value = shlex.split(raw_value)
        value = " ".join(parsed_value)
        if not value:
            raise ValueError(f"invalid toolchain setting: {line}")
        values[key] = value
    required = {"PANDOC_VERSION", "PANDOC_ARCHIVE_URL", "PANDOC_ARCHIVE_NAME", "PANDOC_ARCHIVE_SHA256", "PDF_ENGINE", "PDF_MAIN_FONT", "PDF_MARGIN", "PDF_PACKAGES"}
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError(f"toolchain configuration is missing: {', '.join(missing)}")
    return values


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}")
    return completed.stdout.strip()


def build(manifest_path: Path, css: Path, output: Path, pandoc_archive: Path | None) -> list[Path]:
    manifest_path = manifest_path.resolve()
    css = css.resolve()
    output = output.resolve()
    if not css.is_file():
        raise ValueError(f"publication CSS not found: {css}")
    if not output.is_relative_to(ROOT / "build"):
        raise ValueError("generated publication outputs must stay under build/")
    manifest, sections = load_publication(manifest_path)
    toolchain = load_toolchain()
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("Pandoc is required; install the pinned version 3.12")
    version_output = run([pandoc, "--version"]).splitlines()[0]
    version_match = re.search(r"\bpandoc\s+(\d+\.\d+)", version_output)
    if not version_match or version_match.group(1) != toolchain["PANDOC_VERSION"]:
        raise RuntimeError(f"expected Pandoc {toolchain['PANDOC_VERSION']}, found: {version_output}")
    archive_hash = None
    if pandoc_archive is not None:
        pandoc_archive = pandoc_archive.resolve()
        if not pandoc_archive.is_file():
            raise ValueError(f"Pandoc archive not found: {pandoc_archive}")
        archive_hash = sha256(pandoc_archive)
        if archive_hash != toolchain["PANDOC_ARCHIVE_SHA256"]:
            raise RuntimeError("Pandoc archive hash does not match the configured release")
    pdf_engine = shutil.which(toolchain["PDF_ENGINE"])
    if not pdf_engine:
        raise RuntimeError(f"{toolchain['PDF_ENGINE']} is required to create the PDF export")

    output.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^a-z0-9]+", "-", manifest["id"].lower()).strip("-")
    html_path = output / f"{stem}.html"
    docx_path = output / f"{stem}.docx"
    pdf_path = output / f"{stem}.pdf"
    css_copy = output / "doc-as-code.css"
    index_path = output / "requirements-index.json"
    shutil.copyfile(css, css_copy)
    index_path.write_text(json.dumps(requirement_index(manifest, sections), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="doc-as-code-") as temporary:
        assembled = Path(temporary) / "publication.md"
        assembled.write_text(assembled_markdown(manifest, sections), encoding="utf-8")
        resource_paths = [manifest_path.parent, ROOT]
        common = [
            pandoc,
            str(assembled),
            "--from=gfm+yaml_metadata_block",
            "--standalone",
            "--toc",
            f"--resource-path={':'.join(str(path) for path in resource_paths)}",
        ]
        run(common + [f"--css={css_copy.name}", "--to=html5", "-o", str(html_path)])
        run(common + ["--to=docx", "-o", str(docx_path)])
        run(common + [
            f"--pdf-engine={toolchain['PDF_ENGINE']}",
            f"--variable=mainfont:{toolchain['PDF_MAIN_FONT']}",
            f"--variable=geometry:margin={toolchain['PDF_MARGIN']}",
            "--to=pdf",
            "-o", str(pdf_path),
        ])

    html_content = html_path.read_text(encoding="utf-8")
    download_links = (
        '<nav class="publication-downloads" aria-label="Publication downloads">'
        '<strong>Download this publication:</strong> '
        f'<a href="{escape(docx_path.name)}">Word (.docx)</a> · '
        f'<a href="{escape(pdf_path.name)}">PDF</a> · '
        '<a href="requirements-index.json">Requirements index</a> · '
        '<a href="publication-provenance.json">Build provenance</a></nav>'
    )
    if "</body>" not in html_content:
        raise RuntimeError("Pandoc standalone HTML has no closing body element")
    html_path.write_text(html_content.replace("</body>", download_links + "</body>"), encoding="utf-8")

    try:
        revision = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    except RuntimeError:
        revision = "unavailable"
    products = [html_path, docx_path, pdf_path, index_path]
    source_records = []
    for section in sections:
        record = {
            "kind": section["kind"],
            "path": section["path"].relative_to(ROOT).as_posix(),
            "sha256": sha256(section["path"]),
        }
        if section["kind"] == "requirement":
            record["requirement_id"] = section["metadata"]["id"]
        source_records.append(record)
    provenance = {
        "schema_version": 2,
        "document_id": manifest["id"],
        "document_version": manifest["version"],
        "title": manifest["title"],
        "classification": manifest["publication_class"],
        "source_of_truth": manifest["source_of_truth"],
        "language": manifest["language"],
        "document_status": manifest["status"],
        "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": sha256(manifest_path),
        "sources": source_records,
        "stylesheet_path": css.relative_to(ROOT).as_posix(),
        "stylesheet_sha256": sha256(css),
        "git_revision": revision,
        "renderer": {
            "name": "Pandoc",
            "version": toolchain["PANDOC_VERSION"],
            "archive_sha256": archive_hash,
            "archive_hash_verified": archive_hash is not None,
        },
        "pdf_engine": {"name": toolchain["PDF_ENGINE"], "version": run([pdf_engine, "--version"]).splitlines()[0]},
        "outputs": {path.name: {"sha256": sha256(path)} for path in products},
    }
    provenance_path = output / "publication-provenance.json"
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [*products, provenance_path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="generated output under build/")
    parser.add_argument("--pandoc-archive", type=Path, help="verify and record the release archive used in CI")
    parser.add_argument("--validate-only", action="store_true", help="validate manifest and sources without rendering")
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        if args.validate_only:
            publication, sections = load_publication(manifest)
            count = sum(section["kind"] == "requirement" for section in sections)
            print(f"Validated {publication['id']} with {len(sections)} sections and {count} requirements")
        else:
            for path in build(manifest, args.css, output.resolve(), args.pandoc_archive):
                print(f"Wrote {path.relative_to(ROOT)}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"Publication build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
