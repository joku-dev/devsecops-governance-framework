#!/usr/bin/env python3
"""Create a normalized governance result snapshot from pipeline metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse

from lib.identifiers import sanitize_timestamp, slugify_repository
from lib.json_io import load_json, write_json


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "results"


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--baseline-level", required=True)
    parser.add_argument("--governance-baseline-ref", required=True)
    parser.add_argument("--pipeline-name", default="DevSecOps Baseline")
    parser.add_argument("--pipeline-run-id", required=True)
    parser.add_argument("--pipeline-url", required=True)
    parser.add_argument("--pipeline-event", required=True)
    parser.add_argument("--pipeline-status", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--branch-protected", required=True)
    parser.add_argument("--commit-id", required=True)
    parser.add_argument("--baseline-gate-status", default="unknown")
    parser.add_argument("--ci-status", default="")
    parser.add_argument("--governance-control-evaluation-status", default="")
    parser.add_argument("--sbom", default="true")
    parser.add_argument("--vulnerability-scan", default="true")
    parser.add_argument("--artifact-digest", default="true")
    parser.add_argument("--governance-control-report", default="false")
    parser.add_argument("--governance-run-input", default="false")
    parser.add_argument("--static-analysis-summary", default="false")
    parser.add_argument("--traceability-mapping", default="false")
    parser.add_argument("--operations-evidence", default="false")
    parser.add_argument("--overall-status", required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--control-evaluation-summary-file")
    parser.add_argument("--generated-at")
    args = parser.parse_args()

    generated_at = args.generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    control_summary = {}
    if args.control_evaluation_summary_file:
        report = load_json(Path(args.control_evaluation_summary_file))
        control_summary = report.get("summary", report)

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
        "governance_repository": "joku-dev/devsecops-governance-as-code",
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

    repo_dir = STATUS_RESULTS / slugify_repository(args.repository_id)
    filename = f"{sanitize_timestamp(generated_at)}-run-{args.pipeline_run_id}.json"
    output_path = repo_dir / filename
    write_json(output_path, payload)
    print(output_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
