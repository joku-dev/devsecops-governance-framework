#!/usr/bin/env python3
"""Write a pull-request summary for modular publication requirement changes."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from build_publication import DEFAULT_MANIFEST, ROOT, load_publication, parse_frontmatter


TRACKED_FIELDS = ("title", "status", "normative_level", "owner", "effective_from", "source_ids", "control_ids", "evidence_types", "supersedes")


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(ROOT), *arguments], check=False, capture_output=True, text=True)


def metadata_at_revision(revision: str, path: str) -> dict | None:
    result = git("show", f"{revision}:{path}")
    if result.returncode:
        return None
    temporary = ROOT / "build/doc-as-code/.previous-requirement.md"
    temporary.parent.mkdir(parents=True, exist_ok=True)
    try:
        temporary.write_text(result.stdout, encoding="utf-8")
        metadata, _ = parse_frontmatter(temporary)
        return metadata
    finally:
        temporary.unlink(missing_ok=True)


def summarize(base_ref: str, manifest_path: Path) -> str:
    _, sections = load_publication(manifest_path)
    current = {
        section["path"].relative_to(ROOT).as_posix(): section["metadata"]
        for section in sections if section["kind"] == "requirement"
    }
    diff = git("diff", "--name-status", f"{base_ref}...HEAD", "--", "docs/publishing/*/requirements/*.md")
    if diff.returncode:
        return f"# Doc-as-Code-Anforderungsänderungen\n\nKeine Auswertung möglich: Basis `{base_ref}` ist nicht verfügbar.\n"
    rows = []
    details = []
    for line in diff.stdout.splitlines():
        status, *paths = line.split("\t")
        path = paths[-1]
        before = metadata_at_revision(base_ref, path)
        after = current.get(path)
        requirement_id = (after or before or {}).get("id", Path(path).stem)
        label = {"A": "hinzugefügt", "D": "entfernt", "M": "geändert"}.get(status[0], status)
        changed = []
        if before and after:
            changed = [field for field in TRACKED_FIELDS if before.get(field) != after.get(field)]
        rows.append(f"| {requirement_id} | {label} | {', '.join(changed) or 'Inhalt/Datei'} | `{path}` |")
        if changed:
            details.append(f"- **{requirement_id}:** " + ", ".join(f"`{field}`" for field in changed))
    if not rows:
        return "# Doc-as-Code-Anforderungsänderungen\n\nKeine einzelnen Anforderungen geändert.\n"
    result = [
        "# Doc-as-Code-Anforderungsänderungen",
        "",
        "| Anforderung | Änderung | Geänderte Metadaten | Datei |",
        "|---|---|---|---|",
        *rows,
    ]
    if details:
        result.extend(["", "## Metadatenänderungen", "", *details])
    return "\n".join(result) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=ROOT / "build/doc-as-code/requirements-change-summary.md")
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    output = args.output if args.output.is_absolute() else ROOT / args.output
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(summarize(args.base_ref, manifest), encoding="utf-8")
        print(f"Wrote {output.relative_to(ROOT)}")
    except (OSError, ValueError) as exc:
        print(f"Requirement summary failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
