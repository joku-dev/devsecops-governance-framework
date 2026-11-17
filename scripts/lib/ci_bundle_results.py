"""Explicit CI bundle mapping and validation from frozen V1 6b557fef.

Data declarations do not verify producer execution or grant governance authority.
Only privately copied, bounded material is supplied by the application.
"""
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError
from lib.portable.runtime import read_json


def load_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024**2:
        raise ValueError('invalid_ci_bundle_json')
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError('ci_bundle_object_required')
    return value


def find_file(root, *names):
    for name in names:
        matches = sorted(Path(root).rglob(name))
        if len(matches) > 1:
            raise ValueError('ambiguous_ci_bundle_member')
        if matches:
            return matches[0]
    return None


def bool_from_path(payload: dict, path: list[str]) -> bool:
    current = payload
    for key in path:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def devsecops_evidence_flags(pipeline_evidence: dict, governance_input: dict, control_report_path: Path | None) -> dict:
    traceability_ok = all(
        bool_from_path(governance_input, ["traceability", key])
        for key in ("requirements_linked", "testcases_linked", "reports_linked")
    )
    operations_ok = all(
        bool_from_path(governance_input, ["operations", key])
        for key in ("deployed_versions_recorded", "security_events_recorded")
    )
    return {
        "sbom": bool_from_path(pipeline_evidence, ["evidence", "sbom", "exists"]),
        "vulnerability_scan": bool_from_path(pipeline_evidence, ["evidence", "vulnerability_scan", "exists"]),
        "artifact_digest": bool_from_path(pipeline_evidence, ["artifact", "digest", "exists"]),
        "governance_control_report": bool(control_report_path),
        "governance_run_input": bool(governance_input),
        "static_analysis_summary": bool_from_path(governance_input, ["static_analysis", "performed"]),
        "traceability_mapping": traceability_ok,
        "operations_evidence": operations_ok,
    }


def architecture_evidence_flags(release_input: dict) -> dict:
    architecture = release_input.get("architecture", {})
    return {
        "release_input": True,
        "architecture_report": True,
        "marker_assessments": len(architecture.get("marker_assessments", [])),
        "release_compatibility_declaration": bool(architecture.get("release_compatibility_declaration", {}).get("exists")),
        "solution_baseline": bool(architecture.get("solution_baseline", {}).get("exists")),
        "compatibility_evidence": bool(architecture.get("compatibility_evidence", {}).get("exists")),
        "security_evidence": bool(architecture.get("security_evidence", {}).get("exists")),
        "deployment_evidence": bool(architecture.get("deployment_evidence", {}).get("exists")),
        "runtime_evidence": bool(architecture.get("runtime_evidence", {}).get("exists")),
        "review_evidence": bool(architecture.get("review_evidence", {}).get("exists")),
        "exception_evidence": bool(architecture.get("exception_evidence", {}).get("exists")),
        "feedback_evidence": bool(architecture.get("feedback_evidence", {}).get("exists")),
        "exceptions": len(architecture.get("exceptions", [])),
    }


def devsecops_snapshot(bundle_root: Path, args, *, governance_repository: str, at: str) -> dict:
    pipeline_path = find_file(bundle_root, "pipeline-evidence.json")
    if not pipeline_path:
        raise FileNotFoundError("pipeline-evidence.json not found in bundle")
    gate_path = find_file(bundle_root, "baseline-gate-result.json")
    control_report_path = find_file(bundle_root, "control-evaluation-report.json")
    governance_input_path = find_file(bundle_root, "governance-run-input.json")

    pipeline_evidence = load_json(pipeline_path)
    gate = load_json(gate_path) if gate_path else {}
    control_summary = {}
    if control_report_path:
        report = load_json(control_report_path)
        control_summary = report.get("summary", report)
    governance_input = load_json(governance_input_path) if governance_input_path else {}

    repository = pipeline_evidence.get("repository", {})
    pipeline = pipeline_evidence.get("pipeline", {})
    repo_id = args.repository_id or repository.get("repository_id", "unknown")
    run_id = args.pipeline_run_id or str(pipeline.get("pipeline_run_id", "unknown"))
    created_at = args.generated_at or pipeline_evidence.get("evidence", {}).get("pipeline_execution", {}).get("generated_at") or at
    gate_status = gate.get("status", "unknown")
    overall_status = "pass" if gate_status == "pass" and control_summary.get("fail", 0) == 0 else "fail"

    checks = {"baseline_gate": "success" if gate_status == "pass" else "failure" if gate_status == "fail" else gate_status}
    if control_report_path:
        checks["governance_control_evaluation"] = "success" if control_summary.get("fail", 0) == 0 else "failure"

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repo_id,
        "baseline_level": args.baseline_level,
        "governance_baseline_ref": args.governance_baseline_ref,
        "governance_repository": governance_repository,
        "result_type": "governance-baseline-run",
        "generated_at": created_at,
        "pipeline": {
            "pipeline_name": pipeline.get("pipeline_id", "DevSecOps Baseline"),
            "pipeline_run_id": run_id,
            "pipeline_url": pipeline.get("pipeline_url", ""),
            "event": pipeline.get("event", "unknown"),
            "status": pipeline.get("status", "unknown"),
        },
        "repository": {
            "branch": repository.get("branch", "unknown"),
            "branch_protected": bool(repository.get("protected_branch", False)),
            "commit_id": pipeline.get("commit_id", "unknown"),
        },
        "checks": checks,
        "evidence": devsecops_evidence_flags(pipeline_evidence, governance_input, control_report_path),
        "control_evaluation_summary": control_summary,
        "overall_status": overall_status,
        "notes": args.notes,
    }

    return payload


def architecture_snapshot(bundle_root: Path, args, *, governance_repository: str, at: str) -> dict:
    release_input_path = find_file(bundle_root, "architecture-release-input.json")
    report_path = find_file(bundle_root, "architecture-governance-report.json")
    if not release_input_path:
        raise FileNotFoundError("architecture-release-input.json not found in bundle")
    if not report_path:
        raise FileNotFoundError("architecture-governance-report.json not found in bundle")

    release_input = load_json(release_input_path)
    report = load_json(report_path)
    target = report.get("target", release_input.get("target_repository", {}))
    repo_id = args.repository_id or target.get("repository_id") or target.get("path", "unknown")
    run_id = args.pipeline_run_id or target.get("release_id", "unknown")
    created_at = args.generated_at or at
    summary = report.get("summary", {})
    finding_count = summary.get("finding_count", 0)

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repo_id,
        "architecture_baseline_ref": args.architecture_baseline_ref,
        "governance_repository": governance_repository,
        "result_type": "architecture-runtime-governance-run",
        "generated_at": created_at,
        "pipeline": {
            "pipeline_name": args.pipeline_name or "Architecture Runtime Governance",
            "pipeline_run_id": str(run_id),
            "pipeline_url": args.pipeline_url,
            "event": args.pipeline_event,
            "status": args.pipeline_status,
        },
        "repository": {
            "branch": args.branch,
            "branch_protected": args.branch_protected,
            "commit_id": target.get("commit", "unknown"),
        },
        "target": target,
        "checks": {
            "architecture_runtime_governance": args.pipeline_status,
        },
        "evidence": architecture_evidence_flags(release_input),
        "architecture_summary": summary,
        "gates": report.get("gates", []),
        "overall_status": "pass" if args.pipeline_status == "success" and finding_count == 0 else "findings",
        "notes": args.notes,
    }

    return payload


def validate_schema(payload: dict, schema_path: Path, errors: list[str]) -> None:
    schema = load_json(schema_path)
    try:
        Draft202012Validator(schema).validate(payload)
    except ValidationError as error:
        errors.append(f"{schema_path.name} validation failed: {error.message}")


def require_json(root: Path, filename: str, errors: list[str]) -> dict:
    path = find_file(root, filename)
    if not path:
        errors.append(f"missing required file: {filename}")
        return {}
    try:
        return load_json(path)
    except (ValueError, OSError) as error:
        errors.append(f"invalid JSON in {path}: {error}")
        return {}


def validate_devsecops(root: Path, errors: list[str], *, schema_root: Path) -> None:
    pipeline_evidence = require_json(root, "pipeline-evidence.json", errors)
    gate_result = require_json(root, "baseline-gate-result.json", errors)

    if pipeline_evidence:
        validate_schema(pipeline_evidence, schema_root / "schemas" / "pipeline-evidence-input.schema.json", errors)
        if not pipeline_evidence.get("artifact", {}).get("digest", {}).get("exists"):
            errors.append("pipeline-evidence.json does not confirm artifact digest existence")
        if not pipeline_evidence.get("evidence", {}).get("sbom", {}).get("exists"):
            errors.append("pipeline-evidence.json does not confirm SBOM existence")
        if not pipeline_evidence.get("evidence", {}).get("vulnerability_scan", {}).get("exists"):
            errors.append("pipeline-evidence.json does not confirm vulnerability scan existence")

    if gate_result and gate_result.get("status") not in {"pass", "fail"}:
        errors.append("baseline-gate-result.json status must be pass or fail")


def validate_architecture(root: Path, errors: list[str], *, schema_root: Path) -> None:
    release_input = require_json(root, "architecture-release-input.json", errors)
    report = require_json(root, "architecture-governance-report.json", errors)

    if release_input:
        validate_schema(release_input, schema_root / "schemas" / "architecture-release-candidate.schema.json", errors)

    if report:
        summary = report.get("summary")
        gates = report.get("gates")
        if not isinstance(summary, dict):
            errors.append("architecture-governance-report.json must contain a summary object")
        if not isinstance(gates, list):
            errors.append("architecture-governance-report.json must contain a gates array")



def parse_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def manual_snapshot(args, *, governance_repository: str, at: str, control_summary=None) -> dict:
    generated_at = args.generated_at or at
    control_summary = (control_summary.get("summary", control_summary) if control_summary is not None else {})

    checks = {
        "baseline_gate": args.baseline_gate_status,
    }
    if args.ci_status:
        checks["ci"] = args.ci_status
    if args.governance_control_evaluation_status:
        checks["governance_control_evaluation"] = args.governance_control_evaluation_status

    evidence = {
        "sbom": parse_bool(args.sbom),
        "vulnerability_scan": parse_bool(args.vulnerability_scan),
        "artifact_digest": parse_bool(args.artifact_digest),
    }
    optional_evidence = {
        "governance_control_report": args.governance_control_report,
        "governance_run_input": args.governance_run_input,
        "static_analysis_summary": args.static_analysis_summary,
        "traceability_mapping": args.traceability_mapping,
        "operations_evidence": args.operations_evidence,
    }
    for key, value in optional_evidence.items():
        if parse_bool(value):
            evidence[key] = True

    payload = {
        "schema_version": "1.0.0",
        "repository_id": args.repository_id,
        "baseline_level": args.baseline_level,
        "governance_baseline_ref": args.governance_baseline_ref,
        "governance_repository": governance_repository,
        "result_type": "governance-baseline-run",
        "generated_at": generated_at,
        "pipeline": {
            "pipeline_name": args.pipeline_name,
            "pipeline_run_id": args.pipeline_run_id,
            "pipeline_url": args.pipeline_url,
            "event": args.pipeline_event,
            "status": args.pipeline_status,
        },
        "repository": {
            "branch": args.branch,
            "branch_protected": parse_bool(args.branch_protected),
            "commit_id": args.commit_id,
        },
        "checks": checks,
        "evidence": evidence,
        "control_evaluation_summary": control_summary,
        "overall_status": args.overall_status,
        "notes": args.notes,
    }

    return payload
