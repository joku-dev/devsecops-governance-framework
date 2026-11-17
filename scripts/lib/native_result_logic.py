"""Explicit-context native result domain mappings from frozen V1 6b557fe.

Acquisition, source-provider selection and publication are adapter/application
responsibilities. These functions operate only on captured metadata and files.
"""
from pathlib import Path
from lib.ci_bundle_results import find_file, architecture_evidence_flags
from lib.evidence_verification import compute_sha256
from lib.result_bytes import strict_json
from lib.result_bytes import safe_bytes


def load_json(path):
    return strict_json(safe_bytes(Path(path), limit=16 * 1024**2))


def conclusion_to_status(value: str | None) -> str:
    if value == "success":
        return "success"
    if value in {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}:
        return "failure"
    if value:
        return value
    return "unknown"


def find_job_status(jobs: list[dict], *name_fragments: str) -> str:
    normalized_fragments = [fragment.lower() for fragment in name_fragments]
    for job in jobs:
        name = job.get("name", "").lower()
        if all(fragment in name for fragment in normalized_fragments):
            return conclusion_to_status(job.get("conclusion"))
    return ""


def bool_from_path(payload: dict, path: list[str]) -> bool:
    value = payload
    for key in path:
        if not isinstance(value, dict):
            return False
        value = value.get(key)
    return bool(value)


def resolve_declared_evidence_file(root: Path, declared_path: object) -> Path | None:
    """Resolve a producer-declared file only to a unique file in the downloaded artifact."""
    if not isinstance(declared_path, str) or not declared_path.strip():
        return None
    normalized = declared_path.replace("\\", "/").lstrip("/")
    candidates = [root / normalized, root / "application" / normalized]
    resolved_root = root.resolve()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_relative_to(resolved_root) and resolved.is_file():
            return resolved
    basename = Path(normalized).name
    matches = sorted(
        resolved
        for path in root.rglob(basename)
        if (resolved := path.resolve()).is_relative_to(resolved_root) and resolved.is_file()
    )
    return matches[0] if len(matches) == 1 else None


def evidence_flags_from_artifacts(
    pipeline_evidence: dict,
    evidence_root: Path,
    governance_input: dict,
    artifact_names: set[str],
    governance_control_report: bool,
) -> dict:
    evidence = pipeline_evidence.get("evidence", {})
    artifact = pipeline_evidence.get("artifact", {})
    sbom = evidence.get("sbom", {}) if isinstance(evidence, dict) else {}
    scan = evidence.get("vulnerability_scan", {}) if isinstance(evidence, dict) else {}
    digest = artifact.get("digest", {}) if isinstance(artifact, dict) else {}
    traceability_ok = all(
        bool_from_path(governance_input, ["traceability", key])
        for key in ("requirements_linked", "testcases_linked", "reports_linked")
    )
    operations_ok = all(
        bool_from_path(governance_input, ["operations", key])
        for key in ("deployed_versions_recorded", "security_events_recorded")
    )
    sbom_file = resolve_declared_evidence_file(evidence_root, sbom.get("path"))
    scan_file = resolve_declared_evidence_file(evidence_root, scan.get("path"))
    artifact_file = resolve_declared_evidence_file(evidence_root, digest.get("path") or artifact.get("artifact_id"))
    return {
        "sbom": bool(sbom.get("exists")) and sbom_file is not None,
        "vulnerability_scan": bool(scan.get("exists")) and scan_file is not None,
        "artifact_digest": (
            bool(digest.get("exists"))
            and digest.get("algorithm") == "sha256"
            and isinstance(digest.get("value"), str)
            and artifact_file is not None
            and compute_sha256(artifact_file) == digest.get("value")
        ),
        "governance_control_report": governance_control_report,
        "governance_run_input": bool(governance_input) or "devsecops-governance-run-input" in artifact_names,
        "static_analysis_summary": bool_from_path(governance_input, ["static_analysis", "performed"]),
        "traceability_mapping": traceability_ok,
        "operations_evidence": operations_ok,
    }


def normalize_governance_report(report: dict, report_path: Path) -> dict:
    """Normalize the released report or the consumer's report-only gate output."""
    if report_path.name != "baseline-gate-result.json":
        return report
    failed = report.get("status") == "fail"
    return {
        "summary": {
            "applicable_controls": 1,
            "pass": 0 if failed else 1,
            "fail": 1 if failed else 0,
            "not_tested": 0,
        },
        "baseline_gate_result": report,
    }


def artifact_size_bytes(artifact: dict) -> int:
    return int(artifact.get("size_in_bytes", artifact.get("size", 0)))


def gate_result_status(report: dict) -> str:
    gate = report.get("baseline_gate_result", report)
    status = gate.get("status") if isinstance(gate, dict) else None
    if status == "pass":
        return "success"
    if status == "fail":
        return "failure"
    return ""


def evidence_context(pipeline_evidence: dict, governance_input: dict, report: dict) -> dict:
    pipeline = pipeline_evidence.get("pipeline", {})
    security_gates = pipeline.get("security_gates", {})
    run_input_pipeline = governance_input.get("pipeline", {})
    run_input_gates = run_input_pipeline.get("security_gates", {})
    gate_result = report.get("baseline_gate_result", {})
    return {
        "pipeline_evidence": {
            "governance_mode": pipeline.get("governance_mode"),
            "security_gates": {
                "enforced": security_gates.get("enforced"),
                "blocks_merge": security_gates.get("blocks_merge"),
            },
            "external_direct_downloads_detected": pipeline.get("external_direct_downloads_detected"),
            "artifact_digest": pipeline_evidence.get("artifact", {}).get("digest", {}).get("value"),
        },
        "governance_run_input_declared": {
            "security_gates": {
                "enforced": run_input_gates.get("enforced"),
                "blocks_merge": run_input_gates.get("blocks_merge"),
            },
            "external_direct_downloads_detected": run_input_pipeline.get("external_direct_downloads_detected"),
        },
        "baseline_gate_result": {
            "status": gate_result.get("status"),
            "governance_mode": gate_result.get("governance_mode"),
            "blocks_merge": gate_result.get("blocks_merge"),
        },
        "interpretation": {
            "security_gates_enforced": "Gate execution/evaluation; merge blocking is represented separately.",
            "external_direct_downloads_detected": "Producer-declared observation; not independently inferred by this intake.",
        },
    }


def devsecops_snapshot(
    *,
    repository_id: str,
    baseline_level: str,
    governance_baseline_ref: str,
    run: dict,
    jobs: list[dict],
    report: dict,
    governance_input: dict,
    report_sha256: str,
    governance_input_sha256: str | None,
    branch_protected: bool | None,
    branch_protection_lookup: dict,
    artifacts: list[dict],
    selected_artifact: dict | None,
    governance_input_artifact: dict | None,
    governance_input_artifact_archive_sha256: str | None,
    artifact_names: set[str],
    evidence: dict,
    evidence_context_payload: dict,
    pipeline_evidence_sha256: str | None,
    trust: dict,
    notes: str,
    governance_repository: str,
) -> dict:
    control_summary = report.get("summary", report)
    baseline_gate_job_status = find_job_status(jobs, "baseline", "gate") or conclusion_to_status(run.get("conclusion"))
    baseline_gate_status = gate_result_status(report) or baseline_gate_job_status
    governance_control_status = find_job_status(jobs, "governance", "control", "evaluation")
    overall_status = "pass" if run.get("conclusion") == "success" and control_summary.get("fail", 0) == 0 else "fail"
    generated_at = run.get("updated_at") or run.get("created_at")
    branch = run.get("head_branch", "unknown")

    checks = {
        "baseline_gate": baseline_gate_status,
        "baseline_gate_workflow_job": baseline_gate_job_status,
    }
    if governance_control_status:
        checks["governance_control_evaluation"] = governance_control_status

    artifact_sizes = {artifact.get("name", "unknown"): artifact_size_bytes(artifact) for artifact in artifacts}
    downloaded_artifact_info = None
    if selected_artifact is not None:
        downloaded_artifact_info = {
            "downloaded": True,
            "artifact_size_bytes": artifact_size_bytes(selected_artifact),
            "control_evaluation_report_sha256": report_sha256,
            "governance_run_input_sha256": governance_input_sha256,
            "pipeline_evidence_sha256": pipeline_evidence_sha256,
            "governance_run_input_refs": governance_input.get("evidence_refs", []),
            "governance_run_input_artifact": (
                {
                    "name": governance_input_artifact.get("name"),
                    "artifact_id": str(governance_input_artifact.get("id", "unknown")),
                    "archive_sha256": governance_input_artifact_archive_sha256,
                }
                if governance_input_artifact is not None
                else None
            ),
        }

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repository_id,
        "baseline_level": baseline_level,
        "governance_baseline_ref": governance_baseline_ref,
        "governance_repository": governance_repository,
        "result_type": "governance-baseline-run",
        "generated_at": generated_at,
        "pipeline": {
            "pipeline_name": run.get("name", "DevSecOps Baseline"),
            "pipeline_run_id": str(run.get("id")),
            "pipeline_url": run.get("html_url", ""),
            "event": run.get("event", "unknown"),
            "status": conclusion_to_status(run.get("conclusion")),
        },
        "repository": {
            "branch": branch,
            "branch_protected": branch_protected,
            "branch_protection_lookup": branch_protection_lookup,
            "commit_id": run.get("head_sha", "unknown"),
        },
        "checks": checks,
        "evidence": evidence,
        "evidence_context": evidence_context_payload,
        "artifact_metadata": {
            "artifact_names": sorted(artifact_names),
            "artifact_sizes": artifact_sizes,
        },
        "downloaded_artifact": downloaded_artifact_info,
        "trust": trust,
        "control_evaluation_summary": control_summary,
        "overall_status": overall_status,
        "notes": notes,
    }

    return payload


def architecture_snapshot(
    *,
    repository_id: str,
    architecture_baseline_ref: str,
    run: dict,
    report: dict,
    release_input: dict,
    branch_protected: bool | None,
    branch_protection_lookup: dict,
    artifact_metadata: dict,
    trust: dict,
    notes: str,
    governance_repository: str,
) -> dict:
    summary = report.get("summary", {})
    finding_count = summary.get("finding_count", 0)
    overall_status = "pass" if run.get("conclusion") == "success" and finding_count == 0 else "findings"
    generated_at = run.get("updated_at") or run.get("created_at")
    branch = run.get("head_branch", "unknown")

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repository_id,
        "architecture_baseline_ref": architecture_baseline_ref,
        "governance_repository": governance_repository,
        "result_type": "architecture-runtime-governance-run",
        "generated_at": generated_at,
        "pipeline": {
            "pipeline_name": run.get("name", "Architecture Runtime Governance"),
            "pipeline_run_id": str(run.get("id")),
            "pipeline_url": run.get("html_url", ""),
            "event": run.get("event", "unknown"),
            "status": conclusion_to_status(run.get("conclusion")),
        },
        "repository": {
            "branch": branch,
            "branch_protected": branch_protected,
            "branch_protection_lookup": branch_protection_lookup,
            "commit_id": run.get("head_sha", "unknown"),
        },
        "target": report.get("target", {}),
        "checks": {
            "architecture_runtime_governance": conclusion_to_status(run.get("conclusion")),
        },
        "evidence": architecture_evidence_flags(release_input),
        "artifact_metadata": artifact_metadata,
        "trust": trust,
        "architecture_summary": summary,
        "gates": report.get("gates", []),
        "overall_status": overall_status,
        "notes": notes,
    }

    return payload


def find_report(root):
    result = find_file(root, 'control-evaluation-report.json')
    if result is None: result = find_file(root, 'baseline-gate-result.json')
    if result is None: raise ValueError('native_governance_report_missing')
    return result


def optional_json(root, name):
    path = find_file(root, name)
    return (load_json(path), path) if path is not None else ({}, None)
