#!/usr/bin/env python3
"""Validate platform-neutral CI artifact bundles before central intake."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import zipfile

try:
    import jsonschema
except ImportError:  # pragma: no cover - exercised by users without jsonschema
    jsonschema = None


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_bundle(bundle: Path, destination: Path) -> Path:
    if bundle.is_dir():
        return bundle
    if not bundle.is_file():
        raise FileNotFoundError(f"bundle not found: {bundle}")
    if bundle.suffix.lower() != ".zip":
        raise ValueError(f"unsupported bundle type; expected directory or .zip: {bundle}")
    with zipfile.ZipFile(bundle) as handle:
        handle.extractall(destination)
    return destination


def find_file(root: Path, name: str) -> Path | None:
    direct = root / name
    if direct.is_file():
        return direct
    matches = sorted(root.rglob(name))
    if matches:
        return matches[0]
    return None


def validate_schema(payload: dict, schema_path: Path, errors: list[str]) -> None:
    if jsonschema is None:
        errors.append("jsonschema is not installed; install it to enable schema validation")
        return
    schema = load_json(schema_path)
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as error:
        errors.append(f"{schema_path.name} validation failed: {error.message}")


def require_json(root: Path, filename: str, errors: list[str]) -> dict:
    path = find_file(root, filename)
    if not path:
        errors.append(f"missing required file: {filename}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError as error:
        errors.append(f"invalid JSON in {path}: {error}")
        return {}


def validate_devsecops(root: Path, errors: list[str]) -> None:
    pipeline_evidence = require_json(root, "pipeline-evidence.json", errors)
    gate_result = require_json(root, "baseline-gate-result.json", errors)

    if pipeline_evidence:
        validate_schema(pipeline_evidence, ROOT / "schemas" / "pipeline-evidence-input.schema.json", errors)
        if not pipeline_evidence.get("artifact", {}).get("digest", {}).get("exists"):
            errors.append("pipeline-evidence.json does not confirm artifact digest existence")
        if not pipeline_evidence.get("evidence", {}).get("sbom", {}).get("exists"):
            errors.append("pipeline-evidence.json does not confirm SBOM existence")
        if not pipeline_evidence.get("evidence", {}).get("vulnerability_scan", {}).get("exists"):
            errors.append("pipeline-evidence.json does not confirm vulnerability scan existence")

    if gate_result and gate_result.get("status") not in {"pass", "fail"}:
        errors.append("baseline-gate-result.json status must be pass or fail")


def validate_architecture(root: Path, errors: list[str]) -> None:
    release_input = require_json(root, "architecture-release-input.json", errors)
    report = require_json(root, "architecture-governance-report.json", errors)

    if release_input:
        validate_schema(release_input, ROOT / "schemas" / "architecture-release-candidate.schema.json", errors)

    if report:
        summary = report.get("summary")
        gates = report.get("gates")
        if not isinstance(summary, dict):
            errors.append("architecture-governance-report.json must contain a summary object")
        if not isinstance(gates, list):
            errors.append("architecture-governance-report.json must contain a gates array")


def main() -> int:
    parser = ArgumentParser(description="Validate CI artifact bundles before governance intake.")
    parser.add_argument("--bundle", required=True, help="Artifact directory or ZIP file")
    parser.add_argument("--type", choices=["devsecops", "architecture"], required=True)
    args = parser.parse_args()

    errors: list[str] = []
    bundle = Path(args.bundle).resolve()
    with TemporaryDirectory(prefix="ci-artifact-validate-") as tempdir:
        try:
            root = extract_bundle(bundle, Path(tempdir))
            if args.type == "devsecops":
                validate_devsecops(root, errors)
            else:
                validate_architecture(root, errors)
        except Exception as error:
            errors.append(str(error))

    if errors:
        print("CI artifact bundle validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"CI artifact bundle validation passed ({args.type}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
