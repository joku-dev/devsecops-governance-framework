#!/usr/bin/env python3
"""Validate the hybrid requirement authority, catalog and lifecycle cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "model/requirements/governance-requirement-catalog.yaml"
LEDGER = ROOT / "model/requirements/requirement-authority-ledger.yaml"
CASES = ROOT / "model/requirements/lifecycle-cases"


def read(path: Path):
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_schema(path: Path, schema_name: str, errors: list[str]) -> None:
    schema = read(ROOT / "schemas" / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for issue in sorted(validator.iter_errors(read(path)), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in issue.absolute_path) or "<root>"
        errors.append(f"{path.relative_to(ROOT)} at {location}: {issue.message}")


def main() -> int:
    errors: list[str] = []
    validate_schema(CATALOG, "governance-requirement-catalog.schema.json", errors)
    validate_schema(LEDGER, "requirement-authority-ledger.schema.json", errors)
    case_paths = sorted(CASES.glob("*.json")) if CASES.exists() else []
    for path in case_paths:
        validate_schema(path, "requirement-lifecycle-case.schema.json", errors)

    catalog = read(CATALOG)
    ledger = read(LEDGER)
    ids = [item["id"] for item in catalog["requirements"]]
    if len(ids) != len(set(ids)):
        errors.append("canonical requirement IDs must be unique")
    expected_next = max([int(item.split("-")[-1]) for item in ids], default=0) + 1
    if catalog["next_sequence"] != expected_next:
        errors.append("catalog next_sequence does not follow the highest allocated ID")
    known = set(ids)
    source_refs = set()
    for requirement in catalog["requirements"]:
        revision_numbers = [item["revision"] for item in requirement["revisions"]]
        if revision_numbers != list(range(1, len(revision_numbers) + 1)):
            errors.append(f"{requirement['id']} revisions must be contiguous and ordered")
        active = [item for item in requirement["revisions"] if item["status"] == "effective"]
        if len(active) != 1 or active[0]["revision"] != requirement["active_revision"]:
            errors.append(f"{requirement['id']} must have exactly one matching effective revision")
        for revision in requirement["revisions"]:
            for source_ref in revision["source_refs"]:
                source_refs.add(source_ref)
            for relation in revision["relationships"]:
                relation_id = relation["target"].split("@rev", 1)[0]
                if relation_id.startswith("GRQ-") and relation_id not in known:
                    errors.append(f"{requirement['id']} references unknown requirement {relation['target']}")
            if revision["runtime_enforcement"] == "blocking":
                errors.append(f"{requirement['id']} activates blocking without a separate enforcement contract")

    ledger_ids = [item["source_id"] for item in ledger["sources"]]
    if len(ledger_ids) != len(set(ledger_ids)):
        errors.append("authority ledger source IDs must be unique")
    for source in ledger["sources"]:
        path = ROOT / source["source_path"]
        if not path.is_file():
            errors.append(f"authority source missing: {source['source_path']}")
        else:
            import hashlib
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["document_sha256"]:
                errors.append(f"authority source hash changed: {source['source_id']}")
        coverage = source["coverage"]
        if coverage["unresolved"] != coverage["total"] - coverage["decided"]:
            errors.append(f"authority coverage arithmetic invalid: {source['source_id']}")
        if coverage["effective"] > coverage["decided"] or coverage["decided"] > coverage["total"]:
            errors.append(f"authority coverage ordering invalid: {source['source_id']}")
        if source["authority_mode"] == "git_authoritative":
            if coverage["unresolved"] != 0 or coverage["effective"] == 0 or not source["catalog_release"]:
                errors.append(f"git-authoritative source is incomplete: {source['source_id']}")

    activated_refs = set()
    for path in case_paths:
        case = read(path)
        for proposal in case["proposals"]:
            activation = proposal["activation"]
            if activation:
                activated_refs.add(proposal["source_requirement_id"])
                if activation["requirement_id"] not in known:
                    errors.append(f"{case['case_id']} activates unknown requirement")
            if proposal["decision"] is None and activation is not None:
                errors.append(f"{proposal['proposal_id']} activated without decision")
        if case["status"] == "activated" and any(item["decision"] is None for item in case["proposals"]):
            errors.append(f"{case['case_id']} activated with open decisions")
    if not activated_refs.issubset(source_refs):
        errors.append("activated proposal source references are missing from the canonical catalog")

    if errors:
        print("Requirement lifecycle validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Requirement lifecycle validation passed")
    print(f"- authority sources: {len(ledger['sources'])}")
    print(f"- lifecycle cases: {len(case_paths)}")
    print(f"- canonical requirements: {len(catalog['requirements'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
