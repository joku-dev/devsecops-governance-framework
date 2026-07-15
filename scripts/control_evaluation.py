#!/usr/bin/env python3
"""Shared helpers for control-level governance evaluation reports."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"

POLICY_QUERIES = {
    "branch_protection": "data.devsecops.branch_protection.deny",
    "sbom": "data.devsecops.sbom.deny",
    "vulnerability_gate": "data.devsecops.vulnerability_gate.deny",
    "artifact_integrity": "data.devsecops.artifact_integrity.deny",
    "access_control": "data.devsecops.access_control.deny",
    "dependency_source_control": "data.devsecops.dependency_source_control.deny",
    "iac": "data.devsecops.iac.deny",
    "artifact_signing": "data.devsecops.artifact_signing.deny",
    "pipeline_security_gates": "data.devsecops.pipeline_security_gates.deny",
    "waiver_validity": "data.devsecops.waiver_validity.deny",
}

CONTROL_POLICY_MAP = {
    "DSCB-L1-REQ-003": "branch_protection",
    "DSCB-L1-REQ-006": "sbom",
    "DSCB-L1-REQ-009": "vulnerability_gate",
    "DSCB-L1-REQ-010": "vulnerability_gate",
    "DSCB-L1-REQ-011": "artifact_integrity",
    "DSCB-L2-REQ-004": "access_control",
    "DSCB-L2-REQ-006": "dependency_source_control",
    "DSCB-L2-REQ-007": "artifact_signing",
    "DSCB-L2-REQ-009": "iac",
    "DSCB-L2-REQ-011": "pipeline_security_gates",
    "DSCB-L2-REQ-012": "pipeline_security_gates",
}


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_controls() -> list[dict]:
    controls = []
    for path in sorted((MODEL / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        level = data.get("level")
        for requirement in data.get("requirements", []):
            controls.append(
                {
                    **requirement,
                    "_level_file": level,
                    "_source_file": str(path.relative_to(ROOT)),
                }
            )
    return controls


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def evaluate_policies(input_path: Path) -> dict[str, dict]:
    results = {}
    for policy_id, query in POLICY_QUERIES.items():
        result = run(
            [
                "opa",
                "eval",
                "-f",
                "json",
                "-d",
                str(ROOT / "policies" / "opa"),
                "-i",
                str(input_path),
                query,
            ]
        )
        if result.returncode != 0:
            results[policy_id] = {
                "status": "error",
                "deny_count": -1,
                "deny_messages": [result.stderr.strip() or result.stdout.strip() or "OPA evaluation failed"],
            }
            continue
        payload = json.loads(result.stdout)
        denies = payload["result"][0]["expressions"][0]["value"]
        results[policy_id] = {
            "status": "pass" if len(denies) == 0 else "fail",
            "deny_count": len(denies),
            "deny_messages": denies,
        }
    return results


def platform_level_rank(value: str | None) -> int:
    if not value:
        return 1
    if "3" in value:
        return 3
    if "2" in value:
        return 2
    return 1


def nested_get(payload: dict, dotted_path: str):
    current = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def is_release_context(payload: dict) -> bool:
    explicit = nested_get(payload, "run_context.release_context")
    if isinstance(explicit, bool):
        return explicit

    purpose = nested_get(payload, "run_context.purpose")
    if purpose in {"diagnostic", "branch_validation", "pull_request_validation"}:
        return False
    if purpose == "release":
        return True

    event = nested_get(payload, "run_context.event") or nested_get(payload, "pipeline.event")
    if event in {"workflow_dispatch", "pull_request", "schedule", "local"}:
        return False

    return bool(payload.get("release_candidate", False))


def build_decision(
    control: dict,
    status: str,
    message: str,
    decision_basis: list[str] | None = None,
    evidence_sources: list[str] | None = None,
) -> dict:
    policy_id = CONTROL_POLICY_MAP.get(control["id"])
    return {
        "control_id": control["id"],
        "level": control["_level_file"],
        "domain": control["domain"],
        "title": control["title"],
        "required_platform_level": control["required_platform_level"],
        "verification_method": control.get("verification", {}).get("method", "unknown"),
        "status": status,
        "policy_rule": control.get("policy_as_code", {}).get("rule"),
        "policy_id": policy_id,
        "source_file": control["_source_file"],
        "expected_evidence": control.get("evidence", []),
        "evidence_sources": evidence_sources or [],
        "decision_basis": decision_basis or [],
        "message": message,
    }


def manual_or_hybrid_decision(control: dict, message: str) -> dict:
    return build_decision(
        control,
        "not_tested",
        message,
        decision_basis=[],
        evidence_sources=control.get("evidence", []),
    )


def evaluate_single_control(control: dict, payload: dict, policy_results: dict[str, dict]) -> dict:
    if control["_level_file"] == "GOV":
        return build_decision(
            control,
            "not_applicable",
            "Governance-board-level controls are not directly evaluated by this repository pipeline run.",
        )

    input_platform_rank = platform_level_rank(payload.get("required_platform_level"))
    control_platform_rank = platform_level_rank(control.get("required_platform_level"))
    if control_platform_rank > input_platform_rank:
        return build_decision(
            control,
            "not_applicable",
            f"Control requires {control['required_platform_level']}, but the evaluated run declares {payload.get('required_platform_level', 'PRA-Level 1')}.",
        )

    policy_id = CONTROL_POLICY_MAP.get(control["id"])
    if policy_id:
        policy_result = policy_results.get(policy_id, {})
        if policy_result.get("status") == "error":
            return build_decision(
                control,
                "not_tested",
                f"Policy evaluation could not be completed for {policy_id}.",
                evidence_sources=control.get("evidence", []),
            )
        if policy_result:
            return build_decision(
                control,
                "pass" if policy_result["status"] == "pass" else "fail",
                f"Mapped policy `{policy_id}` returned {policy_result['deny_count']} deny messages.",
                decision_basis=[policy_id],
                evidence_sources=control.get("evidence", []),
            )

    control_id = control["id"]

    if control_id == "DSCB-L1-REQ-001":
        requirements_linked = bool(nested_get(payload, "traceability.requirements_linked"))
        testcases_linked = bool(nested_get(payload, "traceability.testcases_linked"))
        reports_linked = bool(nested_get(payload, "traceability.reports_linked"))
        return build_decision(
            control,
            "pass" if requirements_linked and testcases_linked and reports_linked else "fail",
            "Traceability is evaluated from explicit structured linkage fields for requirements, testcases, and reports.",
            decision_basis=[
                "traceability.requirements_linked",
                "traceability.testcases_linked",
                "traceability.reports_linked",
            ],
            evidence_sources=["requirements_traceability_records", "configuration_management_records"],
        )

    if control_id == "DSCB-L1-REQ-002":
        approved_vcs = bool(nested_get(payload, "source_control.approved_vcs"))
        identifiable_authors = bool(nested_get(payload, "source_control.identifiable_authors"))
        review_records_present = bool(nested_get(payload, "source_control.review_records_present"))
        return build_decision(
            control,
            "pass" if approved_vcs and identifiable_authors and review_records_present else "fail",
            "Source control governance is evaluated from explicit version-control, author-traceability, and review-record fields.",
            decision_basis=[
                "source_control.approved_vcs",
                "source_control.identifiable_authors",
                "source_control.review_records_present",
            ],
            evidence_sources=["commit_history", "code_review_records", "branch_protection_configuration"],
        )

    if control_id == "DSCB-L1-REQ-004":
        performed = bool(nested_get(payload, "static_analysis.performed"))
        findings_reviewed = bool(nested_get(payload, "static_analysis.findings_reviewed"))
        return build_decision(
            control,
            "pass" if performed and findings_reviewed else "fail",
            "Secure coding evidence is evaluated from structured static-analysis execution and review fields.",
            decision_basis=["static_analysis.performed", "static_analysis.findings_reviewed"],
            evidence_sources=["static_code_analysis_reports", "code_review_documentation"],
        )

    if control_id == "DSCB-L1-REQ-005":
        sbom_exists = bool(nested_get(payload, "evidence.sbom.exists"))
        dependencies = payload.get("dependencies", [])
        return build_decision(
            control,
            "pass" if sbom_exists and isinstance(dependencies, list) else "fail",
            "Dependencies are treated as documented when the input includes a dependency list and an SBOM.",
            decision_basis=["evidence.sbom.exists", "dependencies"],
            evidence_sources=["sbom", "dependencies"],
        )

    if control_id == "DSCB-L1-REQ-007":
        pipeline_present = isinstance(payload.get("pipeline"), dict) and bool(payload.get("pipeline"))
        return build_decision(
            control,
            "pass" if pipeline_present else "fail",
            "The run is treated as pipeline-executed when structured pipeline metadata is present.",
            decision_basis=["pipeline"],
            evidence_sources=["pipeline_execution_logs"],
        )

    if control_id == "DSCB-L1-REQ-008":
        identifiable = bool(nested_get(payload, "artifact.digest.exists")) or bool(nested_get(payload, "artifact.artifact_version"))
        return build_decision(
            control,
            "pass" if identifiable else "fail",
            "Artifact uniqueness is inferred from digest presence or explicit artifact version metadata.",
            decision_basis=["artifact.digest.exists", "artifact.artifact_version"],
            evidence_sources=["artifact_checksum_or_digest_records", "artifact_metadata"],
        )

    if control_id == "DSCB-L1-REQ-012":
        identifiable = bool(nested_get(payload, "artifact.digest.linked_to_artifact")) or bool(nested_get(payload, "artifact.digest.exists"))
        return build_decision(
            control,
            "pass" if identifiable else "fail",
            "Artifact identity is inferred from digest linkage to the evaluated artifact.",
            decision_basis=["artifact.digest.linked_to_artifact", "artifact.digest.exists"],
            evidence_sources=["artifact_checksum_or_digest_records"],
        )

    if control_id == "DSCB-L1-REQ-013":
        if not is_release_context(payload):
            return build_decision(
                control,
                "not_applicable",
                "Release authorization is not applicable for this non-release diagnostic or validation run.",
                decision_basis=["run_context.release_context", "run_context.purpose", "pipeline.event"],
                evidence_sources=["release_approval_records"],
            )
        approved = bool(nested_get(payload, "release_approval.approved"))
        approver = nested_get(payload, "release_approval.approver")
        return build_decision(
            control,
            "pass" if approved and bool(approver) else "fail",
            "Release authorization is evaluated from explicit structured approval metadata.",
            decision_basis=["release_approval.approved", "release_approval.approver"],
            evidence_sources=["release_approval_records"],
        )

    if control_id == "DSCB-L1-REQ-014":
        if not is_release_context(payload):
            return build_decision(
                control,
                "not_applicable",
                "Approved-artifact deployment is not applicable for this non-release diagnostic or validation run.",
                decision_basis=["run_context.release_context", "run_context.purpose", "pipeline.event"],
                evidence_sources=["release_approval_records", "deployment_logs", "artifact_checksum_or_digest_records"],
            )
        approved_artifact_only = bool(nested_get(payload, "release_approval.approved_artifact_only"))
        digest_exists = bool(nested_get(payload, "artifact.digest.exists"))
        return build_decision(
            control,
            "pass" if approved_artifact_only and digest_exists else "fail",
            "Approved-artifact deployment is evaluated from explicit release approval metadata plus artifact identity evidence.",
            decision_basis=["release_approval.approved_artifact_only", "artifact.digest.exists"],
            evidence_sources=["release_approval_records", "deployment_logs", "artifact_checksum_or_digest_records"],
        )

    if control_id == "DSCB-L1-REQ-015":
        evidence_present = bool(nested_get(payload, "evidence.pipeline_execution")) or bool(payload.get("pipeline"))
        return build_decision(
            control,
            "pass" if evidence_present else "fail",
            "Machine-readable evidence generation is inferred from structured pipeline execution data.",
            decision_basis=["evidence.pipeline_execution", "pipeline"],
            evidence_sources=["pipeline_execution_logs", "security_scan_reports", "artifact_metadata"],
        )

    if control_id == "DSCB-L1-REQ-016":
        deployed_versions_recorded = bool(nested_get(payload, "operations.deployed_versions_recorded"))
        security_events_recorded = bool(nested_get(payload, "operations.security_events_recorded"))
        return build_decision(
            control,
            "pass" if deployed_versions_recorded and security_events_recorded else "fail",
            "Operational traceability is evaluated from explicit deployed-version and security-event recording fields.",
            decision_basis=["operations.deployed_versions_recorded", "operations.security_events_recorded"],
            evidence_sources=["deployment_records", "system_logs", "incident_records"],
        )

    if control_id == "DSCB-L2-REQ-001":
        centrally_managed = bool(nested_get(payload, "environment.centrally_managed"))
        secure_workspace = bool(nested_get(payload, "environment.secure_workspace"))
        return build_decision(
            control,
            "pass" if centrally_managed and secure_workspace else "fail",
            "Development environment central management is evaluated from explicit environment management fields.",
            decision_basis=["environment.centrally_managed", "environment.secure_workspace"],
            evidence_sources=["environment_configuration_records"],
        )

    if control_id == "DSCB-L2-REQ-002":
        config_compliant = bool(nested_get(payload, "environment.config_compliant"))
        baselines_defined = bool(nested_get(payload, "environment.configuration_baselines_defined"))
        return build_decision(
            control,
            "pass" if config_compliant and baselines_defined else "fail",
            "Environment configuration compliance is evaluated from explicit baseline and compliance fields.",
            decision_basis=["environment.config_compliant", "environment.configuration_baselines_defined"],
            evidence_sources=["environment_configuration_records", "system_configuration_baselines"],
        )

    if control_id == "DSCB-L2-REQ-003":
        central_identity = bool(nested_get(payload, "platform.central_identity_management"))
        return build_decision(
            control,
            "pass" if central_identity else "fail",
            "Central identity management is taken directly from the evaluated platform metadata.",
            decision_basis=["platform.central_identity_management"],
            evidence_sources=["access_control_configuration"],
        )

    if control_id == "DSCB-L2-REQ-005":
        dependencies = payload.get("dependencies", [])
        approved = bool(dependencies) and all(item.get("source_approved") for item in dependencies if isinstance(item, dict))
        return build_decision(
            control,
            "pass" if approved else "fail",
            "Dependency repository approval is inferred from the source_approved flag on all declared dependencies.",
            decision_basis=["dependencies[*].source_approved"],
            evidence_sources=["dependency_management_logs"],
        )

    if control_id == "DSCB-L2-REQ-008":
        keys_protected = bool(nested_get(payload, "signing.keys_protected"))
        return build_decision(
            control,
            "pass" if keys_protected else "fail",
            "Signing key protection is taken from the signing metadata in the run input.",
            decision_basis=["signing.keys_protected"],
            evidence_sources=["signing_records"],
        )

    if control_id == "DSCB-L2-REQ-010":
        version_controlled = bool(nested_get(payload, "infrastructure.iac_repository.version_controlled"))
        return build_decision(
            control,
            "pass" if version_controlled else "fail",
            "Infrastructure version control is inferred from the IaC repository metadata.",
            decision_basis=["infrastructure.iac_repository.version_controlled"],
            evidence_sources=["infrastructure_change_history"],
        )

    if control_id == "DSCB-L2-REQ-013":
        security_events_generated = bool(nested_get(payload, "monitoring.security_events_generated"))
        monitoring_integrated = bool(nested_get(payload, "monitoring.integration_enabled"))
        return build_decision(
            control,
            "pass" if security_events_generated and monitoring_integrated else "fail",
            "Security monitoring generation is evaluated from explicit monitoring event generation and integration fields.",
            decision_basis=["monitoring.security_events_generated", "monitoring.integration_enabled"],
            evidence_sources=["security_monitoring_logs", "security_event_records"],
        )

    if control_id == "DSCB-L2-REQ-014":
        forwarded = bool(nested_get(payload, "monitoring.forwarded_to_monitoring"))
        security_events_generated = bool(nested_get(payload, "monitoring.security_events_generated"))
        return build_decision(
            control,
            "pass" if forwarded and security_events_generated else "fail",
            "Security event forwarding is evaluated from explicit forwarding metadata.",
            decision_basis=["monitoring.forwarded_to_monitoring", "monitoring.security_events_generated"],
            evidence_sources=["security_monitoring_logs", "security_event_records"],
        )

    return manual_or_hybrid_decision(
        control,
        "No machine-readable evaluator is implemented yet for this control in the current run profile.",
    )


def generate_control_evaluation_report(input_path: Path) -> dict:
    payload = load_json(input_path)
    controls = load_controls()
    policy_results = evaluate_policies(input_path)
    decisions = [evaluate_single_control(control, payload, policy_results) for control in controls]
    summary = {
        "total_controls": len(decisions),
        "pass": sum(1 for item in decisions if item["status"] == "pass"),
        "fail": sum(1 for item in decisions if item["status"] == "fail"),
        "not_tested": sum(1 for item in decisions if item["status"] == "not_tested"),
        "not_applicable": sum(1 for item in decisions if item["status"] == "not_applicable"),
        "applicable_controls": sum(1 for item in decisions if item["status"] != "not_applicable"),
        "tested_controls": sum(1 for item in decisions if item["status"] in {"pass", "fail"}),
    }
    return {
        "schema_version": "1.0.0",
        "input_file": str(input_path.relative_to(ROOT)) if input_path.is_relative_to(ROOT) else str(input_path),
        "required_platform_level": payload.get("required_platform_level", "PRA-Level 1"),
        "release_candidate": bool(payload.get("release_candidate", False)),
        "run_context": payload.get("run_context", {}),
        "policy_results": policy_results,
        "summary": summary,
        "controls": decisions,
    }


def render_control_evaluation_markdown(report: dict) -> str:
    lines = [
        "# Control Evaluation Report",
        "",
        f"Input File: `{report['input_file']}`",
        f"Required Platform Level: `{report['required_platform_level']}`",
        f"Release Candidate: `{str(report['release_candidate']).lower()}`",
        f"Run Context: `{report.get('run_context', {}).get('purpose', 'unspecified')}`",
        "",
        "## Summary",
        "",
        f"- Total controls: `{report['summary']['total_controls']}`",
        f"- Applicable controls: `{report['summary']['applicable_controls']}`",
        f"- Tested controls: `{report['summary']['tested_controls']}`",
        f"- Passed: `{report['summary']['pass']}`",
        f"- Failed: `{report['summary']['fail']}`",
        f"- Not tested: `{report['summary']['not_tested']}`",
        f"- Not applicable: `{report['summary']['not_applicable']}`",
        "",
        "## Control Decisions",
        "",
        "| Control | Level | Method | Status | Message |",
        "| --- | --- | --- | --- | --- |",
    ]
    for control in report["controls"]:
        lines.append(
            f"| `{control['control_id']}` | `{control['level']}` | `{control['verification_method']}` | "
            f"`{control['status']}` | {control['message']} |"
        )
    return "\n".join(lines) + "\n"
