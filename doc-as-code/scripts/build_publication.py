#!/usr/bin/env python3
"""Build governed HTML, DOCX and PDF outputs from one Git-authored Markdown file."""

from __future__ import annotations

import argparse
from html import escape
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "doc-as-code"
TOOLCHAIN = COMPONENT / "toolchain.env"
DEFAULT_SOURCE = ROOT / "docs/publishing/doc-as-code-pilot.md"
DEFAULT_CSS = COMPONENT / "styles/publication.css"
DEFAULT_OUTPUT = ROOT / "build/doc-as-code"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_metadata(source: Path) -> dict:
    content = source.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not match:
        raise ValueError(f"{source.relative_to(ROOT)} must start with a YAML metadata block")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError("publication metadata must be a YAML mapping")
    required = {"id", "title", "lang", "status", "publication_class", "source_of_truth", "export_formats"}
    missing = sorted(required - metadata.keys())
    if missing:
        raise ValueError(f"publication metadata is missing: {', '.join(missing)}")
    if metadata["publication_class"] != "explanatory" or metadata["source_of_truth"] != "markdown":
        raise ValueError("this pilot renderer only accepts explanatory Markdown publications")
    if set(metadata["export_formats"]) != {"html", "docx", "pdf"}:
        raise ValueError("pilot export_formats must declare html, docx and pdf")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{2,63}", str(metadata["id"])):
        raise ValueError("publication id must contain uppercase letters, digits and hyphens")
    return metadata


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


def build(source: Path, css: Path, output: Path, pandoc_archive: Path | None) -> list[Path]:
    toolchain = load_toolchain()
    source = source.resolve()
    css = css.resolve()
    output = output.resolve()
    if not source.is_relative_to(ROOT / "docs/publishing"):
        raise ValueError("publication source must stay under docs/publishing/")
    if source.suffix.lower() != ".md" or not source.is_file():
        raise ValueError("publication source must be an existing Markdown file")
    if not css.is_file():
        raise ValueError(f"publication CSS not found: {css}")
    if not output.is_relative_to(ROOT / "build"):
        raise ValueError("generated publication outputs must stay under build/")
    metadata = parse_metadata(source)
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
    stem = re.sub(r"[^a-z0-9]+", "-", metadata["id"].lower()).strip("-")
    html_path = output / f"{stem}.html"
    docx_path = output / f"{stem}.docx"
    pdf_path = output / f"{stem}.pdf"
    css_copy = output / "doc-as-code.css"
    shutil.copyfile(css, css_copy)
    common = [
        pandoc,
        str(source),
        "--from=gfm+yaml_metadata_block",
        "--standalone",
        "--toc",
        f"--resource-path={source.parent}:{ROOT}",
    ]
    run(common + [f"--css={css_copy.name}", "--to=html5", "-o", str(html_path)])
    run(common + ["--to=docx", "-o", str(docx_path)])
    run(common + [
        f"--pdf-engine={toolchain['PDF_ENGINE']}",
        f"--variable=mainfont:{toolchain['PDF_MAIN_FONT']}",
        f"--variable=geometry:margin={toolchain['PDF_MARGIN']}",
        "--to=pdf",
        "-o",
        str(pdf_path),
    ])

    html_content = html_path.read_text(encoding="utf-8")
    download_links = (
        '<nav class="publication-downloads" aria-label="Publication downloads">'
        '<strong>Download this publication:</strong> '
        f'<a href="{escape(docx_path.name)}">Word (.docx)</a> · '
        f'<a href="{escape(pdf_path.name)}">PDF</a> · '
        '<a href="publication-provenance.json">Build provenance</a></nav>'
    )
    if "</body>" not in html_content:
        raise RuntimeError("Pandoc standalone HTML has no closing body element")
    html_path.write_text(html_content.replace("</body>", download_links + "</body>"), encoding="utf-8")

    try:
        revision = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    except RuntimeError:
        revision = "unavailable"
    products = [html_path, docx_path, pdf_path]
    provenance = {
        "schema_version": 1,
        "document_id": metadata["id"],
        "title": metadata["title"],
        "classification": metadata["publication_class"],
        "source_of_truth": metadata["source_of_truth"],
        "language": metadata["lang"],
        "document_status": metadata["status"],
        "source_path": source.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(source),
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
    manifest = output / "publication-provenance.json"
    manifest.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [*products, manifest]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="generated output under build/")
    parser.add_argument("--pandoc-archive", type=Path, help="verify and record the release archive used in CI")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        for path in build(args.source, args.css, output.resolve(), args.pandoc_archive):
            print(f"Wrote {path.relative_to(ROOT)}")
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
        print(f"Publication build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
