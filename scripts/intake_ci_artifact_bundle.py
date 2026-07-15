#!/usr/bin/env python3
"""Intake platform-neutral CI artifact bundles into central status snapshots."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil
import sys
import zipfile

from intake_governance_result import sanitize_timestamp, slugify_repository


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "results"
ARCHITECTURE_RESULTS = ROOT / "status" / "architecture-results"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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


def find_file(root: Path, *names: str) -> Path | None:
    for name in names:
        direct = root / name
        if direct.is_file():
            return direct
        matches = sorted(root.rglob(name))
        if matches:
            return matches[0]
    return None


def generated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def intake_devsecops(bundle_root: Path, args: object) -> Path:
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
    created_at = args.generated_at or pipeline_evidence.get("evidence", {}).get("pipeline_execution", {}).get("generated_at") or generated_at()
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
        "governance_repository": "joku-dev/devsecops-governance-framework",
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

    output = STATUS_RESULTS / slugify_repository(repo_id) / f"{sanitize_timestamp(created_at)}-run-{run_id}.json"
    write_json(output, payload)
    return output


def intake_architecture(bundle_root: Path, args: object) -> Path:
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
    created_at = args.generated_at or generated_at()
    summary = report.get("summary", {})
    finding_count = summary.get("finding_count", 0)

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repo_id,
        "architecture_baseline_ref": args.architecture_baseline_ref,
        "governance_repository": "joku-dev/devsecops-governance-framework",
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

    output = ARCHITECTURE_RESULTS / slugify_repository(repo_id) / f"{sanitize_timestamp(created_at)}-run-{run_id}.json"
    write_json(output, payload)
    return output


def main() -> int:
    parser = ArgumentParser(description="Intake local CI artifact bundles into governance status snapshots.")
    parser.add_argument("--bundle", required=True, help="Artifact directory or ZIP file")
    parser.add_argument("--type", choices=["devsecops", "architecture"], required=True)
    parser.add_argument("--repository-id", default="")
    parser.add_argument("--pipeline-run-id", default="")
    parser.add_argument("--pipeline-name", default="")
    parser.add_argument("--pipeline-url", default="")
    parser.add_argument("--pipeline-event", default="unknown")
    parser.add_argument("--pipeline-status", default="success")
    parser.add_argument("--branch", default="unknown")
    parser.add_argument("--branch-protected", action="store_true")
    parser.add_argument("--baseline-level", default="L1")
    parser.add_argument("--governance-baseline-ref", default="unknown")
    parser.add_argument("--architecture-baseline-ref", default="architecture-baseline-l1-v0.1.0")
    parser.add_argument("--generated-at", default="")
    parser.add_argument("--notes", default="Intaken from platform-neutral CI artifact bundle.")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    with TemporaryDirectory(prefix="ci-artifact-intake-") as tempdir:
        bundle_root = extract_bundle(bundle, Path(tempdir))
        if args.type == "devsecops":
            output = intake_devsecops(bundle_root, args)
        else:
            output = intake_architecture(bundle_root, args)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
