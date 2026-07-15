#!/usr/bin/env python3
"""Validate the DevSecOps governance-as-code repository MVP.

The validator intentionally performs repository-level checks that are more
useful for the pilot than pure schema validation:

- all control IDs are unique
- expected L1/L2/L3/GOV counts are present
- every control has traceability
- policy candidate rules exist on disk
- every traceability target points to a known control
"""

from pathlib import Path
import json
import shutil
import subprocess
import sys

import yaml

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:
    Draft202012Validator = None


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
SOURCE_DOCUMENT_ROOT = ROOT / "docs" / "governance" / "source-documents"
APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR = (
    ROOT / "pipeline-baseline" / "templates" / "app-architecture-evidence" / ".governance" / "architecture"
)
EXPECTED_COUNTS = {"L1": 16, "L2": 14, "L3": 11, "GOV": 5}
SOURCE_STATUSES_ALLOWING_NO_LINEAGE = {"candidate", "draft", "retired"}


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema(errors, schema_path: Path, instance_path: Path):
    if Draft202012Validator is None:
        print(
            "Warning: jsonschema is not installed; skipping schema validation for "
            f"{instance_path.relative_to(ROOT)}",
            file=sys.stderr,
        )
        return
    validator = Draft202012Validator(load_json(schema_path))
    instance = load_yaml(instance_path)
    for issue in validator.iter_errors(instance):
        location = " -> ".join(str(part) for part in issue.absolute_path) or "<root>"
        errors.append(f"Schema validation failed for {instance_path.relative_to(ROOT)} at {location}: {issue.message}")


def validate_typed_evidence_results(errors):
    results_root = ROOT / "status" / "typed-evidence-results"
    if not results_root.exists():
        return
    trust_schema = load_json(ROOT / "schemas" / "evidence-trust-record.schema.json")
    trust_validator = Draft202012Validator(trust_schema) if Draft202012Validator is not None else None
    for result_path in sorted(results_root.rglob("*.json")):
        validate_schema(errors, ROOT / "schemas" / "typed-evidence-result.schema.json", result_path)
        if trust_validator is None:
            continue
        payload = load_json(result_path)
        for issue in trust_validator.iter_errors(payload.get("trust")):
            location = " -> ".join(str(part) for part in issue.absolute_path) or "<root>"
            errors.append(
                f"Trust schema validation failed for {result_path.relative_to(ROOT)} at {location}: {issue.message}"
            )


def run_opa_check(errors):
    opa = shutil.which("opa")
    if not opa:
        errors.append("OPA CLI not found on PATH.")
        return

    result = subprocess.run(
        [opa, "check", str(ROOT / "policies" / "opa")],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown OPA error"
        errors.append(f"OPA policy validation failed: {details}")


def validate_source_lineage_report(errors):
    command = [sys.executable, str(ROOT / "scripts" / "generate_source_lineage_report.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Source lineage report generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return
    report_path = ROOT / "generated" / "reports" / "source-lineage-report.json"
    if not report_path.exists():
        errors.append("Source lineage report JSON was not generated")
        return
    report = load_json(report_path)
    if report.get("summary", {}).get("missing_derived_artifacts", 0):
        errors.append("Source lineage report contains missing derived artifacts")
    return report


def validate_governance_change_impact_report(errors):
    command = [sys.executable, str(ROOT / "scripts" / "generate_governance_change_impact_report.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Governance change impact report generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return
    report_path = ROOT / "generated" / "reports" / "governance-change-impact.json"
    if not report_path.exists():
        errors.append("Governance change impact report JSON was not generated")
        return
    report = load_json(report_path)
    registered = report.get("summary", {}).get("registered_source_documents")
    if registered != len(load_yaml(MODEL / "documents" / "source-document-register.yaml").get("documents", [])):
        errors.append("Governance change impact report source document count does not match register")


def validate_architecture_source_replacement_assessment(errors):
    command = [sys.executable, str(ROOT / "scripts" / "generate_architecture_source_replacement_assessment.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Architecture source replacement assessment generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return
    report_path = ROOT / "generated" / "reports" / "architecture-source-replacement-assessment.json"
    if not report_path.exists():
        errors.append("Architecture source replacement assessment JSON was not generated")
        return
    report = load_json(report_path)
    if report.get("decision", {}).get("runtime_governance_changed") is not False:
        errors.append("Architecture source replacement assessment must not change runtime governance behavior")


def validate_source_document_intake_status(errors, source_document_register):
    command = [sys.executable, str(ROOT / "scripts" / "generate_source_document_intake_status.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Source document intake status generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return
    report_path = ROOT / "generated" / "reports" / "source-document-intake-status.json"
    if not report_path.exists():
        errors.append("Source document intake status JSON was not generated")
        return
    report = load_json(report_path)
    registered = report.get("summary", {}).get("registered_source_documents")
    if registered != len(source_document_register.get("documents", [])):
        errors.append("Source document intake status source document count does not match register")
    if report.get("decision", {}).get("runtime_governance_changed") is not False:
        errors.append("Source document intake status must not change runtime governance behavior")
    if report.get("decision", {}).get("stricter_rules_enabled") is not False:
        errors.append("Source document intake status must not enable stricter rules")
    open_items = len(report.get("open_items", []))
    if open_items != report.get("summary", {}).get("open_review_items"):
        errors.append("Source document intake status open item count does not match item list")


def validate_source_document_intake_review_briefs(errors, source_document_register):
    command = [sys.executable, str(ROOT / "scripts" / "generate_source_document_intake_review_briefs.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Source document intake review brief generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return
    report_path = ROOT / "generated" / "reports" / "source-document-intake-review-briefs.json"
    if not report_path.exists():
        errors.append("Source document intake review briefs JSON was not generated")
        return
    report = load_json(report_path)
    if report.get("decision", {}).get("autonomous_decisions_enabled") is not False:
        errors.append("Source document intake review briefs must not enable autonomous decisions")
    if report.get("decision", {}).get("runtime_governance_changed") is not False:
        errors.append("Source document intake review briefs must not change runtime governance behavior")
    if report.get("decision", {}).get("stricter_rules_enabled") is not False:
        errors.append("Source document intake review briefs must not enable stricter rules")
    review_briefs = report.get("review_briefs", [])
    if report.get("summary", {}).get("review_briefs") != len(review_briefs):
        errors.append("Source document intake review brief count does not match item list")
    registered_source_ids = {
        document.get("id")
        for document in source_document_register.get("documents", [])
    }
    for brief in review_briefs:
        source_id = brief.get("source_document", {}).get("id")
        if source_id not in registered_source_ids:
            errors.append(f"Source document intake review brief references unknown source document: {source_id}")
        if brief.get("autonomous_decision") is not False:
            errors.append(f"Source document intake review brief must not make autonomous decisions: {source_id}")


def validate_source_document_requirement_delta(errors):
    command = [sys.executable, str(ROOT / "scripts" / "generate_source_document_requirement_delta.py")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        errors.append(f"Source document requirement delta generation failed: {result.stderr.strip() or result.stdout.strip()}")
        return
    report_path = ROOT / "generated" / "reports" / "source-document-requirement-delta.json"
    if not report_path.exists():
        errors.append("Source document requirement delta JSON was not generated")
        return
    report = load_json(report_path)
    if report.get("decision", {}).get("runtime_governance_changed") is not False:
        errors.append("Source document requirement delta must not change runtime governance behavior")
    if report.get("decision", {}).get("candidate_promoted") is not False:
        errors.append("Source document requirement delta must not promote candidate sources")
    if report.get("decision", {}).get("stricter_rules_enabled") is not False:
        errors.append("Source document requirement delta must not enable stricter rules")
    pairs = report.get("requirement_delta_pairs", [])
    if report.get("summary", {}).get("replacement_pairs") != len(pairs):
        errors.append("Source document requirement delta replacement pair count does not match item list")
    for pair in pairs:
        status_counts = pair.get("summary", {}).get("status_counts", {})
        if not any(status_counts.get(status, 0) for status in ["added", "changed", "removed", "equivalent"]):
            errors.append(
                "Source document requirement delta pair has no classified statements: "
                f"{pair.get('candidate_id')} versus {pair.get('target_id')}"
            )


def validate_app_architecture_evidence_templates(errors):
    if not APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR.exists():
        errors.append(
            "App architecture evidence template directory missing: "
            f"{APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR.relative_to(ROOT)}"
        )
        return

    template_paths = sorted(APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR.glob("*.json"))
    if not template_paths:
        errors.append(
            "App architecture evidence template directory contains no JSON templates: "
            f"{APP_ARCHITECTURE_EVIDENCE_TEMPLATE_DIR.relative_to(ROOT)}"
        )
        return

    schema_path = ROOT / "schemas" / "app-architecture-evidence.schema.json"
    for template_path in template_paths:
        validate_schema(errors, schema_path, template_path)


def validate_source_document_path(errors, source_path: str, source_label: str):
    if not source_path:
        errors.append(f"Missing source document path in {source_label}")
        return
    path = ROOT / source_path
    if not path.exists():
        errors.append(f"Source document path missing in {source_label}: {source_path}")
        return
    try:
        path.relative_to(SOURCE_DOCUMENT_ROOT)
    except ValueError:
        errors.append(
            f"Source document path in {source_label} must be under "
            f"{SOURCE_DOCUMENT_ROOT.relative_to(ROOT)}: {source_path}"
        )


def validate_source_document_register(errors, source_document_register, source_lineage_report):
    registered_sources = []
    seen_ids = set()
    seen_paths = set()

    for document in source_document_register.get("documents", []):
        document_id = document.get("id")
        source_path = document.get("source_path")
        if document_id in seen_ids:
            errors.append(f"Duplicate source document register id: {document_id}")
        seen_ids.add(document_id)
        if source_path in seen_paths:
            errors.append(f"Duplicate source document register path: {source_path}")
        seen_paths.add(source_path)
        registered_sources.append(source_path)
        validate_source_document_path(
            errors,
            source_path,
            f"model/documents/source-document-register.yaml {document_id}",
        )

    source_files = sorted(
        str(path.relative_to(ROOT))
        for path in SOURCE_DOCUMENT_ROOT.iterdir()
        if path.is_file()
    )
    missing_from_register = sorted(set(source_files) - set(registered_sources))
    if missing_from_register:
        errors.append(f"Source documents missing from register: {missing_from_register}")

    registered_but_missing_file = sorted(set(registered_sources) - set(source_files))
    if registered_but_missing_file:
        errors.append(f"Registered source documents not found in source directory: {registered_but_missing_file}")

    known_source_ids = {
        document.get("id")
        for document in source_document_register.get("documents", [])
    }

    for document in source_document_register.get("documents", []):
        document_id = document.get("id")
        supersedes = document.get("supersedes")
        superseded_by = document.get("superseded_by")
        if supersedes and supersedes not in known_source_ids:
            errors.append(f"Source document {document_id} supersedes unknown source id: {supersedes}")
        if superseded_by and superseded_by not in known_source_ids:
            errors.append(f"Source document {document_id} is superseded_by unknown source id: {superseded_by}")
        for candidate_id in document.get("candidate_replacement_for", []):
            if candidate_id not in known_source_ids:
                errors.append(f"Source document {document_id} candidate_replacement_for unknown source id: {candidate_id}")

    lineage_sources = {
        item.get("source_document")
        for item in source_lineage_report.get("lineage", [])
    }
    lineage_required_sources = {
        document.get("source_path")
        for document in source_document_register.get("documents", [])
        if document.get("status") not in SOURCE_STATUSES_ALLOWING_NO_LINEAGE
    }
    missing_lineage = sorted(lineage_required_sources - lineage_sources)
    if missing_lineage:
        errors.append(f"Registered non-draft source documents missing lineage entries: {missing_lineage}")


def validate_waiver_authority(errors, waiver, waiver_authorities, source_label: str):
    risk = waiver.get("risk_classification")
    expected_authority = waiver_authorities.get(risk, {}).get("approval_authority")
    actual_authority = waiver.get("approval_authority")
    if expected_authority and actual_authority and expected_authority != actual_authority:
        errors.append(
            f"Waiver authority mismatch in {source_label} for risk {risk}: "
            f"expected '{expected_authority}', got '{actual_authority}'"
        )


def main() -> int:
    errors = []
    controls = []
    capabilities = load_yaml(MODEL / "platform" / "platform-capabilities.yaml")
    evidence_catalog = load_yaml(MODEL / "evidence" / "evidence-types.yaml")
    governance_documents = load_yaml(MODEL / "documents" / "governance-documents.yaml")
    source_document_register = load_yaml(MODEL / "documents" / "source-document-register.yaml")
    document_traceability = load_yaml(MODEL / "traceability" / "document-to-control.yaml")
    waiver_authorities = load_yaml(MODEL / "waivers" / "waiver-authorities.yaml").get("authorities", {})
    governance_run_input_example = load_json(ROOT / "docs" / "examples" / "governance-run-input.example.json")
    waiver_example = load_yaml(MODEL / "waivers" / "waiver-example.yaml")

    validate_schema(errors, ROOT / "schemas" / "control.schema.json", MODEL / "controls" / "dscb-l1.yaml")
    validate_schema(errors, ROOT / "schemas" / "control.schema.json", MODEL / "controls" / "dscb-l2.yaml")
    validate_schema(errors, ROOT / "schemas" / "control.schema.json", MODEL / "controls" / "dscb-l3.yaml")
    validate_schema(errors, ROOT / "schemas" / "control.schema.json", MODEL / "controls" / "dscb-gov.yaml")
    validate_schema(errors, ROOT / "schemas" / "control-coverage.schema.json", MODEL / "controls" / "control-coverage.yaml")
    validate_schema(errors, ROOT / "schemas" / "evidence-trust-model.schema.json", MODEL / "evidence" / "evidence-trust-model.yaml")
    validate_schema(
        errors,
        ROOT / "schemas" / "evidence-collector-contract.schema.json",
        MODEL / "evidence" / "evidence-collector-contract.yaml",
    )
    validate_schema(
        errors,
        ROOT / "schemas" / "evidence-collector-record.schema.json",
        ROOT / "docs" / "examples" / "evidence-collector-record.example.json",
    )
    validate_schema(
        errors,
        ROOT / "schemas" / "vulnerability-scan-input.schema.json",
        ROOT / "docs" / "examples" / "vulnerability-scan-input.example.json",
    )
    validate_schema(
        errors,
        ROOT / "schemas" / "evidence-freshness-policies.schema.json",
        MODEL / "evidence" / "evidence-freshness-policies.yaml",
    )
    validate_schema(
        errors,
        ROOT / "schemas" / "evidence-trust-record.schema.json",
        ROOT / "docs" / "examples" / "evidence-trust-record.example.json",
    )
    validate_schema(errors, ROOT / "schemas" / "governance-document-catalog.schema.json", MODEL / "documents" / "governance-documents.yaml")
    validate_schema(errors, ROOT / "schemas" / "source-document-register.schema.json", MODEL / "documents" / "source-document-register.yaml")
    validate_schema(errors, ROOT / "schemas" / "document-control-traceability.schema.json", MODEL / "traceability" / "document-to-control.yaml")
    validate_schema(errors, ROOT / "schemas" / "governance-document-rendering.schema.json", MODEL / "documents" / "governance-document-rendering.yaml")
    validate_schema(errors, ROOT / "schemas" / "governance-compliance-result.schema.json", ROOT / "docs" / "examples" / "governance-compliance-result.example.json")
    validate_schema(errors, ROOT / "schemas" / "governance-run-input.schema.json", ROOT / "docs" / "examples" / "governance-run-input.example.json")
    validate_schema(errors, ROOT / "schemas" / "waiver.schema.json", MODEL / "waivers" / "waiver-example.yaml")
    architecture_index_path = ROOT / "status" / "architecture-results-index.json"
    if architecture_index_path.exists():
        validate_schema(errors, ROOT / "schemas" / "architecture-results-index.schema.json", architecture_index_path)
    repository_index_path = ROOT / "status" / "repository-results-index.json"
    if repository_index_path.exists():
        validate_schema(errors, ROOT / "schemas" / "governance-results-index.schema.json", repository_index_path)
    typed_evidence_index_path = ROOT / "status" / "typed-evidence-results-index.json"
    if typed_evidence_index_path.exists():
        validate_schema(
            errors,
            ROOT / "schemas" / "typed-evidence-results-index.schema.json",
            typed_evidence_index_path,
        )
    validate_typed_evidence_results(errors)

    for path in sorted((MODEL / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        level = data.get("level")
        for requirement in data.get("requirements", []):
            requirement["_source_file"] = str(path.relative_to(ROOT))
            requirement["_level_file"] = level
            controls.append(requirement)

    ids = [item["id"] for item in controls]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        errors.append(f"Duplicate control IDs: {duplicates}")

    for level, expected in EXPECTED_COUNTS.items():
        actual = sum(1 for item in controls if item.get("_level_file") == level)
        if actual != expected:
            errors.append(f"Unexpected {level} count: expected {expected}, got {actual}")

    traceability = load_yaml(MODEL / "traceability" / "control-to-platform.yaml")
    control_coverage = load_yaml(MODEL / "controls" / "control-coverage.yaml")
    traced = {item["control"] for item in traceability.get("mappings", [])}
    known = set(ids)
    coverage_controls = {item["control_id"] for item in control_coverage.get("coverage", [])}
    known_capabilities = {item["id"] for item in capabilities.get("capabilities", [])}
    known_evidence = {item["id"] for item in evidence_catalog.get("evidence_types", [])}
    known_documents = {item["id"] for item in governance_documents.get("documents", [])}

    missing_traceability = sorted(known - traced)
    if missing_traceability:
        errors.append(f"Controls missing traceability: {missing_traceability}")

    unknown_traceability = sorted(traced - known)
    if unknown_traceability:
        errors.append(f"Traceability references unknown controls: {unknown_traceability}")

    missing_coverage = sorted(known - coverage_controls)
    if missing_coverage:
        errors.append(f"Controls missing coverage status: {missing_coverage}")

    unknown_coverage = sorted(coverage_controls - known)
    if unknown_coverage:
        errors.append(f"Coverage status references unknown controls: {unknown_coverage}")

    coverage_ids = [item["control_id"] for item in control_coverage.get("coverage", [])]
    duplicate_coverage = sorted({item for item in coverage_ids if coverage_ids.count(item) > 1})
    if duplicate_coverage:
        errors.append(f"Duplicate coverage status entries: {duplicate_coverage}")

    for item in controls:
        policy = item.get("policy_as_code", {})
        rule = policy.get("rule")
        if policy.get("candidate") and rule and not (ROOT / rule).exists():
            errors.append(f"Policy rule missing for {item['id']}: {rule}")
        for capability in item.get("platform_capabilities", []):
            if capability not in known_capabilities:
                errors.append(f"Unknown platform capability on {item['id']}: {capability}")
        for evidence in item.get("evidence", []):
            if evidence not in known_evidence:
                errors.append(f"Unknown evidence type on {item['id']}: {evidence}")

    for document in governance_documents.get("documents", []):
        document_path = ROOT / document["repository_path"]
        if not document_path.exists():
            errors.append(f"Governance document path missing for {document['id']}: {document['repository_path']}")
        source_documents = document.get("source_documents", [])
        if not source_documents:
            errors.append(f"Governance document missing source_documents for {document['id']}")
        for source_document in source_documents:
            validate_source_document_path(errors, source_document, f"model/documents/governance-documents.yaml {document['id']}")

    for architecture_path in sorted((ROOT / "architecture").glob("*.yaml")):
        payload = load_yaml(architecture_path)
        if isinstance(payload, dict) and "source_document" in payload:
            validate_source_document_path(
                errors,
                payload.get("source_document", ""),
                str(architecture_path.relative_to(ROOT)),
            )

    validate_source_document_requirement_delta(errors)
    validate_source_document_intake_review_briefs(errors, source_document_register)
    validate_source_document_intake_status(errors, source_document_register)
    source_lineage_report = validate_source_lineage_report(errors) or {}
    validate_source_document_register(errors, source_document_register, source_lineage_report)
    validate_governance_change_impact_report(errors)
    validate_architecture_source_replacement_assessment(errors)
    validate_app_architecture_evidence_templates(errors)

    for mapping in traceability.get("mappings", []):
        control_id = mapping["control"]
        for capability in mapping.get("platform_capabilities", []):
            if capability not in known_capabilities:
                errors.append(f"Unknown traceability platform capability on {control_id}: {capability}")
        for evidence in mapping.get("evidence", []):
            if evidence not in known_evidence:
                errors.append(f"Unknown traceability evidence on {control_id}: {evidence}")

    for mapping in document_traceability.get("mappings", []):
        document_id = mapping["document_id"]
        if document_id not in known_documents:
            errors.append(f"Document traceability references unknown document: {document_id}")
        for control_id in mapping.get("control_ids", []):
            if control_id not in known:
                errors.append(f"Document traceability references unknown control: {control_id}")

    validate_waiver_authority(errors, waiver_example, waiver_authorities, "model/waivers/waiver-example.yaml")
    for index, waiver in enumerate(governance_run_input_example.get("waivers", [])):
        validate_waiver_authority(errors, waiver, waiver_authorities, f"docs/examples/governance-run-input.example.json waiver[{index}]")

    run_opa_check(errors)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Validation passed")
    print(f"- controls: {len(controls)}")
    for level in ["L1", "L2", "L3", "GOV"]:
        print(f"- {level}: {sum(1 for item in controls if item.get('_level_file') == level)}")
    print(f"- traceability mappings: {len(traced)}")
    print(f"- registered source documents: {len(source_document_register.get('documents', []))}")
    print(f"- policy candidates: {sum(1 for item in controls if item.get('policy_as_code', {}).get('candidate'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
