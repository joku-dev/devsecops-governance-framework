#!/usr/bin/env python3
"""Prepare a human-reviewed documentation update for a merged functional PR."""

from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CATALOG = ROOT / "docs/operations/guides/repository-function-catalog.md"
INVENTORY = ROOT / "docs/operations/guides/repository-technical-function-inventory.md"
AUDIT = ROOT / "generated/reports/documentation-refresh-audit.md"
FUNCTIONAL_ROOTS = (
    "scripts/", ".github/workflows/", "policies/opa/", "architecture/", "model/",
    "apps/", "schemas/", "pipeline-baseline/", "examples/", "adoption-package/",
    ".agents/", ".codex/",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)|<((?:\.\.?/|/)[^>]+)>")


def changed_paths(base: str, merge: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMR", f"{base}..{merge}"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return sorted(set(result.stdout.splitlines()))


def functional(paths: list[str]) -> list[str]:
    return [path for path in paths if path.startswith(FUNCTIONAL_ROOTS)]


def clean_summary(body: str, title: str) -> list[str]:
    """Extract plain text bullets from the merged PR's Summary section."""
    match = re.search(r"(?ims)^##\s+Summary\s*\n(.*?)(?=^##\s+|\Z)", body or "")
    lines = match.group(1).splitlines() if match else []
    bullets = []
    for line in lines:
        line = line.strip()
        if not re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)", line):
            continue
        value = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", line)
        value = re.sub(r"`([^`]+)`", r"\1", value)
        value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
        value = html.unescape(re.sub(r"<[^>]*>", "", value)).strip()
        if value and value != "-" and not value.startswith("<!--"):
            bullets.append(value[:240])
        if len(bullets) == 5:
            break
    safe_title = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", title)).strip()
    return bullets or [safe_title[:240]]


def replace_block(text: str, name: str, content: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    block = f"{start}\n{content.rstrip()}\n{end}"
    if start in text and end in text:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), block, text, count=1, flags=re.S)
    return text.rstrip() + "\n\n" + block + "\n"


def link_audit() -> list[tuple[str, str]]:
    broken: list[tuple[str, str]] = []
    tracked = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    for source in tracked:
        source_path = ROOT / source
        try:
            content = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for match in MARKDOWN_LINK.finditer(content):
            target = (match.group(1) or match.group(2)).strip()
            target = target.split(" ", 1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            decoded = unquote(parsed.path)
            candidate = (source_path.parent / decoded).resolve() if not decoded.startswith("/") else (ROOT / decoded.lstrip("/")).resolve()
            if not candidate.exists():
                broken.append((source, target))
    return sorted(set(broken))


def render(args: argparse.Namespace) -> bool:
    paths = changed_paths(args.base, args.merge)
    affected = functional(paths)
    if not affected:
        return False
    summary = clean_summary(args.body, args.title)
    safe_title = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", args.title)).strip()
    safe_title = safe_title.replace("`", "'")[:240]
    heading = f"PR #{args.pr}: {safe_title} (`{args.merge[:12]}`)"
    details = "\n".join(f"- {item}" for item in summary)
    path_list = "\n".join(f"- `{path}`" for path in affected)

    readme_entry = f"## {heading}\n\n{details}\n"
    catalog_entry = (
        f"### {heading}\n\n{details}\n\n"
        "Die fachliche Zuordnung und Auswirkungen auf bestehende Funktionsbereiche "
        "sind vor dem Merge dieses Dokumentations-PRs redaktionell zu prüfen.\n"
    )
    inventory_entry = f"### {heading}\n\n{path_list}\n"

    README.write_text(replace_block(README.read_text(encoding="utf-8"), "DOCS_REFRESH_LATEST", readme_entry), encoding="utf-8")
    CATALOG.write_text(replace_block(CATALOG.read_text(encoding="utf-8"), "DOCS_REFRESH_CATALOG", catalog_entry), encoding="utf-8")
    INVENTORY.write_text(replace_block(INVENTORY.read_text(encoding="utf-8"), "DOCS_REFRESH_INVENTORY", inventory_entry), encoding="utf-8")

    broken = link_audit()
    audit_status = "keine lokalen Markdown-Zielpfade fehlen" if not broken else f"{len(broken)} fehlende lokale Markdown-Zielpfade"
    build_status = args.docs_build_status or "nicht ausgeführt"
    lines = [
        "# Dokumentationsabgleich nach Merge", "",
        f"Auslöser: {heading}", "",
        "## Ergebnis", "",
        f"- Lokale Markdown-Linkprüfung: {audit_status}.",
        f"- `mkdocs build --strict`: {build_status}.",
        "- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; "
        "fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.", "",
        "## Betroffene Implementierungspfade", "", path_list, "",
        "## Fehlende lokale Markdown-Ziele", "",
    ]
    if broken:
        lines.extend(f"- `{source}` → `{target}`" for source, target in broken)
    else:
        lines.append("Keine gefunden.")
    lines += ["", "## Redaktionelle Prüfpunkte", "", "- README-Einstieg und Funktionsumfang aktualisieren.",
              "- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.",
              "- Technische Inventareinträge und Navigations-/Querverweise ergänzen.",
              "- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.", ""]
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base SHA of the merged PR")
    parser.add_argument("--merge", required=True, help="merge commit SHA")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--docs-build-status", default="")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    if args.body_file:
        args.body = args.body_file.read_text(encoding="utf-8")
    required = render(args)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"required={'true' if required else 'false'}\n")
    print("documentation refresh required" if required else "no functional implementation paths changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
