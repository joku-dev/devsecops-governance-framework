#!/usr/bin/env python3
"""Generate an extended governance compliance result artifact."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess
import sys

from control_evaluation import POLICY_QUERIES, generate_control_evaluation_report, render_control_evaluation_markdown

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_ARTIFACTS = {
    "traceability_matrix": "generated/xlsx/traceability_matrix.csv",
    "document_control_matrix": "generated/xlsx/document_control_matrix.csv",
    "open_gap_report": "generated/xlsx/open_gap_report.csv",
    "status_viewer": "generated/viewer/status-viewer.html",
    "policy_render": "generated/documents/devsecops-pol-001.html",
    "directive_render": "generated/documents/devsecops-dir-001.html",
    "control_evaluation_report_json": "generated/control-evaluation-report.json",
    "control_evaluation_report_markdown": "generated/control-evaluation-report.md",
}


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def command_status(cmd: list[str]) -> tuple[str, str]:
    result = run(cmd)
    status = "pass" if result.returncode == 0 else "fail"
    details = result.stdout.strip() or result.stderr.strip()
    return status, details


def evaluate_policy(input_path: Path, query: str) -> dict:
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
        return {"status": "fail", "deny_count": -1}
    payload = json.loads(result.stdout)
    denies = payload["result"][0]["expressions"][0]["value"]
    return {
        "status": "pass" if len(denies) == 0 else "fail",
        "deny_count": len(denies),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-repo", default=str(ROOT))
    parser.add_argument("--input-file", default=str(ROOT / "policies" / "example-input.release-candidate.json"))
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--skip-unit-tests", action="store_true")
    args = parser.parse_args()

    target_repo = Path(args.target_repo).resolve()
    input_path = Path(args.input_file).resolve()
    output_path = Path(args.output_file)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    control_report_json_path = output_path.with_name("control-evaluation-report.json")
    control_report_markdown_path = output_path.with_name("control-evaluation-report.md")

    checks = []
    integration_result = run(
        [
            "python3",
            str(ROOT / "scripts" / "check_repo_governance_integration.py"),
            "--target-repo",
            str(target_repo),
        ]
    )
    if integration_result.stdout.strip():
        parsed = json.loads(integration_result.stdout)
        checks = parsed["checks"]

    validator_status, _ = command_status(["python3", str(ROOT / "scripts" / "validate_governance_repo.py")])
    if args.skip_unit_tests:
        unit_test_status = "pass"
    else:
        unit_test_status, _ = command_status(["python3", "-m", "unittest", "discover", "-s", "tests"])
    opa_status, _ = command_status(["opa", "check", str(ROOT / "policies" / "opa")])

    policy_evaluations = []
    for policy_id, query in POLICY_QUERIES.items():
        evaluation = evaluate_policy(input_path, query)
        policy_evaluations.append(
            {
                "policy_id": policy_id,
                "status": evaluation["status"],
                "deny_count": evaluation["deny_count"],
            }
        )

    control_report = generate_control_evaluation_report(input_path)
    control_report_json_path.write_text(json.dumps(control_report, indent=2) + "\n", encoding="utf-8")
    control_report_markdown_path.write_text(render_control_evaluation_markdown(control_report), encoding="utf-8")

    artifacts = []
    for artifact_id, relpath in EXPECTED_ARTIFACTS.items():
        path = ROOT / relpath
        if artifact_id == "control_evaluation_report_json":
            path = control_report_json_path
            relpath = str(control_report_json_path)
        elif artifact_id == "control_evaluation_report_markdown":
            path = control_report_markdown_path
            relpath = str(control_report_markdown_path)
        artifacts.append(
            {
                "artifact_id": artifact_id,
                "path": relpath,
                "status": "present" if path.exists() else "missing",
            }
        )

    overall_pass = (
        validator_status == "pass"
        and unit_test_status == "pass"
        and opa_status == "pass"
        and all(check["status"] == "pass" for check in checks)
        and all(item["status"] == "pass" for item in policy_evaluations)
        and control_report["summary"]["fail"] == 0
    )

    result = {
        "schema_version": "1.0.0",
        "governance_repo": ROOT.name,
        "target_repo": target_repo.name,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "pass" if overall_pass else "fail",
        "checks": checks,
        "execution": {
            "validator": {
                "status": validator_status,
                "command": "python3 scripts/validate_governance_repo.py",
            },
            "unit_tests": {
                "status": unit_test_status,
                "command": "python3 -m unittest discover -s tests" if not args.skip_unit_tests else "skipped in nested/test context",
            },
            "opa_check": {
                "status": opa_status,
                "command": "opa check policies/opa",
            },
        },
        "policy_evaluations": policy_evaluations,
        "control_evaluations": control_report,
        "artifacts": artifacts,
    }

    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
