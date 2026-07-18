#!/usr/bin/env python3
"""Reject configured private terms in public text and Office metadata."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def file_texts(path: Path):
    if path.suffix.lower() in {".xlsx", ".docx", ".pptx"}:
        try:
            with ZipFile(path) as archive:
                for name in archive.namelist():
                    try:
                        yield f"{path}:{name}", archive.read(name).decode("utf-8")
                    except UnicodeDecodeError:
                        continue
        except BadZipFile:
            yield str(path), path.read_text(encoding="utf-8", errors="ignore")
    else:
        yield str(path), path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--forbidden-term", action="append", default=[])
    args = parser.parse_args()

    env_terms = [term.strip() for term in os.environ.get("PUBLIC_ARTIFACT_FORBIDDEN_TERMS", "").split(",") if term.strip()]
    terms = [term.casefold() for term in args.forbidden_term + env_terms if term]
    if not terms:
        raise SystemExit("No forbidden terms configured")

    findings = []
    for path in args.paths:
        if not path.exists() or path.is_dir():
            continue
        for location, text in file_texts(path):
            folded = text.casefold()
            if any(term in folded for term in terms):
                findings.append(location)
    if findings:
        print("Public artifact hygiene failed; forbidden content detected in:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"Public artifact hygiene passed for {len(args.paths)} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
