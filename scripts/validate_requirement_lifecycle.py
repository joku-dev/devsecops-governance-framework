#!/usr/bin/env python3
"""Validate the hybrid requirement authority, catalog and lifecycle cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from lib.requirement_lifecycle import parse_native_requirement


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "model/requirements/governance-requirement-catalog.yaml"
LEDGER = ROOT / "model/requirements/requirement-authority-ledger.yaml"
CASES = ROOT / "model/requirements/lifecycle-cases"
PUBLICATION = ROOT / "docs/publishing/governance-requirement-catalog/publication.yaml"
ARTIFACT_REGISTER = ROOT / "model/requirements/requirement-to-artifact-register.yaml"
DERIVED_PREFIXES = ("model/controls/", "model/platform/", "architecture/", "policies/opa/")


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


def validate_instance(instance: dict, schema_name: str, label: str, errors: list[str]) -> None:
    validator = Draft202012Validator(read(ROOT / "schemas" / schema_name), format_checker=FormatChecker())
    for issue in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in issue.absolute_path) or "<root>"
        errors.append(f"{label} at {location}: {issue.message}")


def git_value(base_ref: str, path: Path):
    relative = path.relative_to(ROOT).as_posix()
    completed = subprocess.run(["git", "show", f"{base_ref}:{relative}"], cwd=ROOT, capture_output=True, text=True)
    if completed.returncode:
        return None
    return json.loads(completed.stdout) if path.suffix == ".json" else yaml.safe_load(completed.stdout)


def git_path_exists(base_ref: str, path: str) -> bool:
    completed = subprocess.run(["git", "cat-file", "-e", f"{base_ref}:{path}"], cwd=ROOT, capture_output=True)
    return completed.returncode == 0


def validate_immutable_history(base_ref: str, catalog: dict, case_paths: list[Path], errors: list[str]) -> None:
    previous_catalog = git_value(base_ref, CATALOG)
    if previous_catalog:
        current_by_id = {item["id"]: item for item in catalog["requirements"]}
        for old in previous_catalog["requirements"]:
            current = current_by_id.get(old["id"])
            if current is None:
                errors.append(f"previous requirement deleted: {old['id']}")
            elif current["revisions"][:len(old["revisions"])] != old["revisions"]:
                errors.append(f"immutable requirement revision changed: {old['id']}")
    for path in case_paths:
        old = git_value(base_ref, path)
        if old is None:
            continue
        current = read(path)
        if old["source"] != current["source"] or len(old["proposals"]) != len(current["proposals"]):
            errors.append(f"immutable lifecycle intake changed: {current['case_id']}")
            continue
        for before, after in zip(old["proposals"], current["proposals"]):
            for field in ("proposal_id", "source_requirement_id", "title", "statement", "normative_strength", "domain"):
                if before[field] != after[field]:
                    errors.append(f"immutable proposal field changed: {before['proposal_id']}.{field}")
            if before["decision"] is not None and before["decision"] != after["decision"]:
                errors.append(f"recorded decision changed: {before['proposal_id']}")
            if before["decision"] is not None and before["analysis"] != after["analysis"]:
                errors.append(f"analysis changed after decision: {before['proposal_id']}")
            if before["activation"] is not None and before["activation"] != after["activation"]:
                errors.append(f"recorded activation changed: {before['proposal_id']}")


def changed_paths(base_ref: str) -> set[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"], cwd=ROOT, capture_output=True, text=True,
    )
    if completed.returncode:
        completed = subprocess.run(
            ["git", "diff", "--name-only", base_ref], cwd=ROOT, capture_output=True, text=True,
        )
    return set(completed.stdout.splitlines()) if completed.returncode == 0 else set()


def validate_artifact_register(register: dict, catalog: dict, ledger: dict, base_ref: str | None,
                               errors: list[str], source_map: dict[str, str] | None = None) -> None:
    active: dict[str, dict] = {}
    for requirement in catalog["requirements"]:
        revision = next(
            (item for item in requirement["revisions"] if item["revision"] == requirement["active_revision"]), None,
        )
        if revision and revision["status"] == "effective":
            active[f"{requirement['id']}@rev{revision['revision']}"] = revision
    effective_entries: dict[str, list[dict]] = {}
    ids = set()
    for entry in register["entries"]:
        if entry["id"] in ids:
            errors.append(f"duplicate artifact register ID: {entry['id']}")
        ids.add(entry["id"])
        revision = active.get(entry["requirement_ref"])
        if revision is None:
            errors.append(f"{entry['id']} references an unknown or inactive requirement revision")
            continue
        artifact = entry["artifact"]
        if artifact["type"] not in revision["authorized_derivations"]:
            errors.append(f"{entry['id']} uses unauthorized artifact type {artifact['type']}")
        if entry["enforcement"] != revision["runtime_enforcement"]:
            errors.append(f"{entry['id']} enforcement differs from its exact requirement revision")
        path = ROOT / artifact["path"]
        if not path.is_file():
            errors.append(f"{entry['id']} artifact is missing: {artifact['path']}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            errors.append(f"{entry['id']} artifact hash changed: {artifact['path']}")
        decision_ref = ROOT / entry["decision"]["decision_ref"]
        if not decision_ref.is_file():
            errors.append(f"{entry['id']} decision reference is missing")
        if entry["decision"]["status"] == "effective":
            if entry["decision"]["equivalence"] != "equivalent":
                errors.append(f"{entry['id']} is effective without confirmed equivalence")
            effective_entries.setdefault(artifact["path"], []).append(entry)
    git_sources = {item["source_id"] for item in ledger["sources"] if item["authority_mode"] == "git_authoritative"}
    source_map = source_map or {}
    for entry in register["entries"]:
        entry_sources = {source_map.get(ref, ref) for ref in entry["source_requirement_refs"]}
        if git_sources.intersection(entry_sources) and entry["decision"]["kind"] != "derivation":
            errors.append(f"{entry['id']} retains legacy adoption after source became git_authoritative")
    if not base_ref:
        return
    changes = changed_paths(base_ref)
    for path in sorted(changes):
        if path.startswith("releases/") and git_path_exists(base_ref, path):
            errors.append(f"published release artifact changed: {path}")
        if path.startswith(DERIVED_PREFIXES):
            current = ROOT / path
            if current.is_file() and path not in effective_entries:
                errors.append(f"new or changed normative artifact requires an effective GRQ mapping: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref")
    args = parser.parse_args()
    errors: list[str] = []
    validate_schema(CATALOG, "governance-requirement-catalog.schema.json", errors)
    validate_schema(LEDGER, "requirement-authority-ledger.schema.json", errors)
    validate_schema(ARTIFACT_REGISTER, "requirement-artifact-register.schema.json", errors)
    case_paths = sorted(CASES.glob("*.json")) if CASES.exists() else []
    for path in case_paths:
        validate_schema(path, "requirement-lifecycle-case.schema.json", errors)

    catalog = read(CATALOG)
    ledger = read(LEDGER)
    artifact_register = read(ARTIFACT_REGISTER)
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
        active = next((item for item in requirement["revisions"] if item["revision"] == requirement["active_revision"]), None)
        if active is None or active["status"] != "effective":
            errors.append(f"{requirement['id']} active revision must exist and be effective")
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
    source_map = {}
    proposal_ids = {
        proposal["proposal_id"]
        for path in case_paths for proposal in read(path)["proposals"]
    }
    proposal_activations = {
        proposal["proposal_id"]: proposal["activation"]
        for path in case_paths for proposal in read(path)["proposals"]
    }
    for path in case_paths:
        case = read(path)
        source_map.update({item["source_requirement_id"]: case["source"]["source_id"] for item in case["proposals"]})
        source_path = ROOT / case["source"]["source_path"]
        if not source_path.is_file():
            errors.append(f"lifecycle source missing: {case['source']['source_path']}")
        else:
            import hashlib
            if hashlib.sha256(source_path.read_bytes()).hexdigest() != case["source"]["source_sha256"]:
                errors.append(f"lifecycle source hash changed: {case['case_id']}")
        decision_ref = ROOT / case["source"]["decision_ref"]
        if not decision_ref.is_file() or not decision_ref.resolve().is_relative_to((ROOT / "docs/governance/change-requests").resolve()):
            errors.append(f"lifecycle decision reference is invalid: {case['case_id']}")
        if case["intake_type"] == "native_git" and source_path.is_file():
            try:
                validate_instance(parse_native_requirement(source_path), "native-requirement-source.schema.json", case["case_id"], errors)
            except (OSError, ValueError, yaml.YAMLError) as exc:
                errors.append(f"{case['case_id']} native source invalid: {exc}")
        for proposal in case["proposals"]:
            decision = proposal["decision"]
            if decision:
                proposal_decision_ref = ROOT / decision["decision_ref"]
                if not proposal_decision_ref.is_file() or not proposal_decision_ref.resolve().is_relative_to(
                    (ROOT / "docs/governance/change-requests").resolve()
                ):
                    errors.append(f"{proposal['proposal_id']} decision reference is invalid")
            if decision and decision["disposition"] == "approve" and decision["classification"] != "new":
                target = decision["target_requirement_id"]
                valid_targets = known | proposal_ids if decision["classification"] == "duplicate" else known
                if target not in valid_targets:
                    errors.append(f"{proposal['proposal_id']} has invalid decision target {target}")
                if decision["classification"] == "duplicate" and target in proposal_ids and proposal_activations[target] is None:
                    errors.append(f"{proposal['proposal_id']} duplicate target is not canonically activated: {target}")
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
    if args.base_ref:
        validate_immutable_history(args.base_ref, catalog, case_paths, errors)
    validate_artifact_register(artifact_register, catalog, ledger, args.base_ref, errors, source_map)
    if not PUBLICATION.is_file():
        errors.append("canonical catalog publication manifest is missing")
    else:
        publication = read(PUBLICATION)
        published = {Path(item["path"]).stem for item in publication["sections"] if item["kind"] == "requirement"}
        active_ids = {item["id"] for item in catalog["requirements"] if item["active_revision"] is not None}
        if published != active_ids:
            errors.append("canonical catalog publication does not match active catalog requirements")

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
