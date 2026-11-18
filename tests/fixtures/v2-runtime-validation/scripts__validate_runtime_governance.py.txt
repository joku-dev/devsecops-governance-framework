#!/usr/bin/env python3
"""Validate the SDD runtime governance addendum.

The addendum is intentionally model-first: YAML and JSON files are the
machine-readable layer, Markdown is the explanatory view, and OPA is the first
executable policy gate. This validator keeps those pieces aligned.
"""

from pathlib import Path
import json
import shutil
import subprocess
import sys

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_CHECKS = [
    ("architecture/quality-markers.yaml", "schemas/quality-marker.schema.json", "yaml"),
    ("architecture/guardrails.yaml", "schemas/architecture-guardrail.schema.json", "yaml"),
    ("architecture/review-gates.yaml", "schemas/review-gate.schema.json", "yaml"),
    ("architecture/arch-l1.yaml", "schemas/architecture-level.schema.json", "yaml"),
    ("architecture/arch-l2.yaml", "schemas/architecture-level.schema.json", "yaml"),
    ("architecture/arch-l3.yaml", "schemas/architecture-level.schema.json", "yaml"),
    ("architecture/arch-gov.yaml", "schemas/architecture-level.schema.json", "yaml"),
    (
        "policies/example-input.architecture-release-candidate.json",
        "schemas/architecture-release-candidate.schema.json",
        "json",
    ),
    (
        "generated/demo/ha-cpswms-architecture-release-input.json",
        "schemas/architecture-release-candidate.schema.json",
        "json",
    ),
]

EXPECTED_MARKERS = (
    {f"B{i}" for i in range(1, 6)}
    | {f"E{i}" for i in range(0, 11)}
    | {f"S{i}" for i in range(0, 11)}
    | {f"P{i}" for i in range(0, 14)}
)
EXPECTED_ARCH_LEVEL_COUNTS = {"ARCH-L1": 4, "ARCH-L2": 4, "ARCH-L3": 3, "ARCH-GOV": 3}


def load_data(path: Path, kind: str):
    text = path.read_text(encoding="utf-8")
    if kind == "json":
        return json.loads(text)
    return yaml.safe_load(text)


def validate_schema(data_path: str, schema_path: str, kind: str, errors: list[str]) -> None:
    try:
        data = load_data(ROOT / data_path, kind)
        schema = json.loads((ROOT / schema_path).read_text(encoding="utf-8"))
        jsonschema.validate(data, schema)
    except Exception as exc:  # noqa: BLE001 - validator should report all failures cleanly
        errors.append(f"{data_path} failed schema validation against {schema_path}: {exc}")


def validate_marker_catalogue(errors: list[str]) -> None:
    try:
        data = yaml.safe_load((ROOT / "architecture" / "quality-markers.yaml").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Could not load architecture/quality-markers.yaml: {exc}")
        return

    markers = data.get("markers", [])
    ids = [marker.get("id") for marker in markers]
    duplicates = sorted({marker_id for marker_id in ids if ids.count(marker_id) > 1})
    missing = sorted(EXPECTED_MARKERS - set(ids))
    unknown = sorted(set(ids) - EXPECTED_MARKERS)

    if duplicates:
        errors.append(f"Duplicate architecture marker IDs: {duplicates}")
    if missing:
        errors.append(f"Missing architecture marker IDs: {missing}")
    if unknown:
        errors.append(f"Unknown architecture marker IDs: {unknown}")


def validate_opa_policy(errors: list[str]) -> None:
    if not shutil.which("opa"):
        errors.append("OPA executable not found; cannot validate architecture release-readiness policy")
        return

    command = [
        "opa",
        "eval",
        "--data",
        str(ROOT / "policies" / "opa" / "architecture_release_readiness.rego"),
        "--input",
        str(ROOT / "policies" / "example-input.architecture-release-candidate.json"),
        "data.architecture.release_readiness.deny",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"OPA evaluation failed: {result.stderr.strip() or result.stdout.strip()}")
        return

    try:
        payload = json.loads(result.stdout)
        value = payload["result"][0]["expressions"][0]["value"]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Could not parse OPA evaluation result: {exc}")
        return

    if value:
        errors.append(f"Example architecture release candidate failed policy: {value}")

    readiness_command = [
        "opa",
        "eval",
        "--data",
        str(ROOT / "policies" / "opa" / "architecture_readiness.rego"),
        "--input",
        str(ROOT / "policies" / "example-input.architecture-release-candidate.json"),
        "data.architecture.readiness.deny",
    ]
    readiness_result = subprocess.run(readiness_command, capture_output=True, text=True, check=False)
    if readiness_result.returncode != 0:
        errors.append(f"OPA architecture-readiness evaluation failed: {readiness_result.stderr.strip() or readiness_result.stdout.strip()}")

    integration_command = [
        "opa",
        "eval",
        "--data",
        str(ROOT / "policies" / "opa" / "architecture_integration_readiness.rego"),
        "--input",
        str(ROOT / "policies" / "example-input.architecture-release-candidate.json"),
        "data.architecture.integration_readiness.deny",
    ]
    integration_result = subprocess.run(integration_command, capture_output=True, text=True, check=False)
    if integration_result.returncode != 0:
        errors.append(f"OPA integration-readiness evaluation failed: {integration_result.stderr.strip() or integration_result.stdout.strip()}")

    operation_command = [
        "opa",
        "eval",
        "--data",
        str(ROOT / "policies" / "opa" / "architecture_operation_readiness.rego"),
        "--input",
        str(ROOT / "policies" / "example-input.architecture-release-candidate.json"),
        "data.architecture.operation_readiness.deny",
    ]
    operation_result = subprocess.run(operation_command, capture_output=True, text=True, check=False)
    if operation_result.returncode != 0:
        errors.append(f"OPA operation-readiness evaluation failed: {operation_result.stderr.strip() or operation_result.stdout.strip()}")


def validate_generated_traceability(errors: list[str]) -> None:
    command = [sys.executable, str(ROOT / "scripts" / "generate_architecture_traceability_csv.py")]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Architecture traceability generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return

    output = ROOT / "generated" / "csv" / "architecture_runtime_traceability.csv"
    if not output.exists():
        errors.append("Architecture traceability CSV was not generated")


def validate_generated_demo_report(errors: list[str]) -> None:
    input_path = ROOT / "generated" / "demo" / "ha-cpswms-architecture-release-input.json"
    if not input_path.exists():
        return

    command = [
        sys.executable,
        str(ROOT / "scripts" / "generate_architecture_governance_report.py"),
        "--input",
        str(input_path),
        "--output-json",
        str(ROOT / "generated" / "demo" / "ha-cpswms-architecture-governance-report.json"),
        "--output-md",
        str(ROOT / "generated" / "demo" / "ha-cpswms-architecture-governance-report.md"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Architecture governance report generation failed: {result.stderr.strip() or result.stdout.strip()}")


def validate_generated_end_to_end_demo_report(errors: list[str]) -> None:
    architecture_report = ROOT / "generated" / "demo" / "ha-cpswms-architecture-governance-report.json"
    devsecops_report = ROOT / "generated" / "demo" / "ha-cpswms-devsecops-governance-report.json"
    if not architecture_report.exists() or not devsecops_report.exists():
        return

    command = [
        sys.executable,
        str(ROOT / "scripts" / "generate_end_to_end_governance_report.py"),
        "--architecture-json",
        str(architecture_report),
        "--devsecops-json",
        str(devsecops_report),
        "--output-json",
        str(ROOT / "generated" / "demo" / "ha-cpswms-end-to-end-governance-report.json"),
        "--output-md",
        str(ROOT / "generated" / "demo" / "ha-cpswms-end-to-end-governance-report.md"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"End-to-end governance report generation failed: {result.stderr.strip() or result.stdout.strip()}")


def validate_architecture_levels(errors: list[str]) -> None:
    marker_ids = {
        marker["id"]
        for marker in yaml.safe_load((ROOT / "architecture" / "quality-markers.yaml").read_text(encoding="utf-8")).get("markers", [])
    }
    guardrail_ids = {
        guardrail["id"]
        for guardrail in yaml.safe_load((ROOT / "architecture" / "guardrails.yaml").read_text(encoding="utf-8")).get("guardrails", [])
    }
    review_gate_ids = {
        gate["id"]
        for gate in yaml.safe_load((ROOT / "architecture" / "review-gates.yaml").read_text(encoding="utf-8")).get("review_gates", [])
    }

    requirement_ids: list[str] = []
    level_counts: dict[str, int] = {}
    for path in sorted((ROOT / "architecture").glob("arch-*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        level = data.get("level")
        requirements = data.get("requirements", [])
        level_counts[level] = level_counts.get(level, 0) + len(requirements)
        for requirement in requirements:
            requirement_ids.append(requirement.get("id"))
            unknown_markers = sorted(set(requirement.get("source_markers", [])) - marker_ids)
            unknown_guardrails = sorted(set(requirement.get("source_guardrails", [])) - guardrail_ids)
            unknown_review_gates = sorted(set(requirement.get("source_review_gates", [])) - review_gate_ids)
            if unknown_markers:
                errors.append(f"{requirement.get('id')} references unknown markers: {unknown_markers}")
            if unknown_guardrails:
                errors.append(f"{requirement.get('id')} references unknown guardrails: {unknown_guardrails}")
            if unknown_review_gates:
                errors.append(f"{requirement.get('id')} references unknown review gates: {unknown_review_gates}")

            rule = requirement.get("policy_as_code", {}).get("rule")
            if requirement.get("policy_as_code", {}).get("candidate") and rule and not (ROOT / rule).exists():
                # Planned policies are allowed for future gates, but implemented gates must exist.
                if rule.endswith("architecture_release_readiness.rego") or rule.endswith("validate_runtime_governance.py"):
                    errors.append(f"{requirement.get('id')} references missing policy rule: {rule}")

    duplicates = sorted({requirement_id for requirement_id in requirement_ids if requirement_ids.count(requirement_id) > 1})
    if duplicates:
        errors.append(f"Duplicate architecture requirement IDs: {duplicates}")

    for level, expected in EXPECTED_ARCH_LEVEL_COUNTS.items():
        actual = level_counts.get(level, 0)
        if actual != expected:
            errors.append(f"Unexpected {level} architecture requirement count: expected {expected}, got {actual}")


def main() -> int:
    errors: list[str] = []

    for data_path, schema_path, kind in SCHEMA_CHECKS:
        validate_schema(data_path, schema_path, kind, errors)

    for schema_path in ["schemas/architecture-exception.schema.json"]:
        try:
            json.loads((ROOT / schema_path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{schema_path} is not valid JSON: {exc}")

    try:
        remediation_payload = yaml.safe_load((ROOT / "architecture" / "remediation-actions.yaml").read_text(encoding="utf-8"))
        if not remediation_payload.get("remediations"):
            errors.append("architecture/remediation-actions.yaml contains no remediations")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Could not load architecture/remediation-actions.yaml: {exc}")

    validate_marker_catalogue(errors)
    validate_architecture_levels(errors)
    validate_generated_traceability(errors)
    validate_generated_demo_report(errors)
    validate_generated_end_to_end_demo_report(errors)
    validate_opa_policy(errors)

    if errors:
        print("Runtime governance validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Runtime governance validation passed")
    print(f"- expected markers: {len(EXPECTED_MARKERS)}")
    print(f"- schema checks: {len(SCHEMA_CHECKS)}")
    print(f"- architecture requirements: {sum(EXPECTED_ARCH_LEVEL_COUNTS.values())}")
    print("- OPA release-readiness example: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
