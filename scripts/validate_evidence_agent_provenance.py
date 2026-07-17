#!/usr/bin/env python3
"""Validate explicit evidence-agent provenance records and subject digests."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "evidence-agent-provenance.schema.json"
RECORD_ROOT = ROOT / "status" / "evidence-agent-provenance"


def load_subject_digest(payload: dict, subject_id: str) -> str | None:
    candidates = [
        payload.get("trust", {}).get("capture", {}).get("subjects", []),
        payload.get("capture", {}).get("subjects", []),
        payload.get("subjects", []),
    ]
    for subjects in candidates:
        for subject in subjects:
            if subject.get("id") == subject_id:
                return subject.get("digest")
    return None


def validate_record(path: Path, schema: dict) -> list[str]:
    errors = []
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{path}: cannot read JSON: {error}"]
    errors.extend(f"{path}: {error.message}" for error in Draft202012Validator(schema).iter_errors(record))
    source_file = record.get("evidence", {}).get("source_file")
    if not source_file:
        return errors
    source_path = ROOT / source_file
    if not source_path.is_file():
        errors.append(f"{path}: evidence source file does not exist: {source_file}")
        return errors
    try:
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{path}: evidence source file is not valid JSON: {error}")
        return errors
    subject = record.get("evidence", {})
    actual_digest = load_subject_digest(source_payload, subject.get("subject_id", ""))
    if actual_digest is None:
        errors.append(f"{path}: subject is not present in source file: {subject.get('subject_id', 'unknown')}")
    elif actual_digest != subject.get("subject_digest"):
        errors.append(f"{path}: subject digest does not match source file")
    return errors


def validate_records(root: Path = RECORD_ROOT) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = []
    if not root.exists():
        return errors
    for path in sorted(root.rglob("*.json")):
        errors.extend(validate_record(path, schema))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=RECORD_ROOT)
    args = parser.parse_args()
    errors = validate_records(args.root)
    if errors:
        print("Evidence agent provenance validation failed", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Evidence agent provenance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
