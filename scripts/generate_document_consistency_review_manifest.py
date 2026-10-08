#!/usr/bin/env python3
"""Snapshot registered source identities for a bounded document review.

The source register remains authoritative. This tool records selected register
metadata, exact source-file hashes, and the current repository commit. It does
not emit source text, promote sources, assess semantic consistency, or create
governance decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTER_RELATIVE_PATH = Path("model/documents/source-document-register.yaml")
SOURCE_ROOT_RELATIVE_PATH = Path("docs/governance/source-documents")
SOURCE_ID_PATTERN = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$")
REPOSITORY = "joku-dev/devsecops-governance-framework"
LIMITATIONS = [
    "This manifest binds registered metadata to exact file bytes only.",
    "It contains no source text, excerpts, semantic findings, or human decisions.",
    "Source register owner metadata is review routing and does not confirm source authority.",
    "A source status is recorded as registered; it is not changed or promoted.",
    "reviewed_commit is null when Git is unavailable or the working tree is not clean.",
]


class ManifestError(ValueError):
    """Raised when the requested source scope cannot be bound safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_revision(root: Path) -> str | None:
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    revision = result.stdout.strip()
    return revision if re.fullmatch(r"[0-9a-f]{40,64}", revision) else None


def load_register(root: Path) -> tuple[dict, Path]:
    register_path = root / REGISTER_RELATIVE_PATH
    if not register_path.is_file():
        raise ManifestError(f"source register is missing: {REGISTER_RELATIVE_PATH}")
    try:
        payload = yaml.safe_load(register_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestError(f"source register cannot be read: {exc.__class__.__name__}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
        raise ManifestError("source register must contain a documents list")
    return payload, register_path


def build_manifest(root: Path, requested_ids: list[str]) -> dict:
    """Build a deterministic source manifest without storing source contents."""
    if not requested_ids:
        raise ManifestError("select at least one registered source ID")
    if len(requested_ids) != len(set(requested_ids)):
        raise ManifestError("source IDs must be unique in the requested scope")
    if any(not SOURCE_ID_PATTERN.fullmatch(source_id) for source_id in requested_ids):
        raise ManifestError("a requested source ID has an invalid format")

    register, register_path = load_register(root)
    by_id: dict[str, dict] = {}
    for entry in register["documents"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise ManifestError("source register contains an entry without a valid ID")
        source_id = entry["id"]
        if source_id in by_id:
            raise ManifestError(f"source register contains duplicate ID: {source_id}")
        by_id[source_id] = entry

    source_root = (root / SOURCE_ROOT_RELATIVE_PATH).resolve()
    sources = []
    for source_id in sorted(requested_ids):
        entry = by_id.get(source_id)
        if entry is None:
            raise ManifestError(f"source ID is not registered: {source_id}")

        relative_path = entry.get("source_path")
        if not isinstance(relative_path, str) or not relative_path:
            raise ManifestError(f"registered source has no path: {source_id}")
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ManifestError(f"registered source path must be repository-relative: {source_id}")
        try:
            resolved_path = (root / relative).resolve(strict=True)
            resolved_path.relative_to(source_root)
        except (OSError, ValueError) as exc:
            raise ManifestError(f"registered source path is missing or outside the source directory: {source_id}") from exc
        if not resolved_path.is_file():
            raise ManifestError(f"registered source is not a regular file: {source_id}")

        required_text = ("title", "status", "version", "owner")
        if any(not isinstance(entry.get(field), str) or not entry[field] for field in required_text):
            raise ManifestError(f"registered source has incomplete metadata: {source_id}")
        domains = entry.get("governance_domains")
        if not isinstance(domains, list) or not domains or any(not isinstance(value, str) for value in domains):
            raise ManifestError(f"registered source has invalid governance domains: {source_id}")

        sources.append(
            {
                "id": source_id,
                "title": entry["title"],
                "status": entry["status"],
                "version": entry["version"],
                "owner": entry["owner"],
                "governance_domains": sorted(domains),
                "source_path": relative.as_posix(),
                "content_sha256": sha256_file(resolved_path),
            }
        )

    return {
        "schema_version": "1.0.0",
        "manifest_type": "document_consistency_review_source_manifest",
        "repository": REPOSITORY,
        "reviewed_commit": repository_revision(root),
        "source_register_path": REGISTER_RELATIVE_PATH.as_posix(),
        "source_register_sha256": sha256_file(register_path),
        "source_count": len(sources),
        "source_documents": sources,
        "limitations": LIMITATIONS.copy(),
    }


def write_manifest(path: Path, payload: dict) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == serialized:
            return
        raise ManifestError(f"refusing to replace an existing manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-id",
        action="append",
        required=True,
        help="registered source ID to bind; repeat for each selected source",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON to a new path (refuses to overwrite different content); default: stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        manifest = build_manifest(ROOT, args.source_id)
        if args.output:
            output_path = args.output if args.output.is_absolute() else ROOT / args.output
            write_manifest(output_path, manifest)
            print(f"Wrote source manifest for {manifest['source_count']} source(s): {output_path}")
        else:
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
