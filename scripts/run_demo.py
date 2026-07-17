#!/usr/bin/env python3
"""Run an end-to-end governance demo using local sample inputs."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess

from control_evaluation import generate_control_evaluation_report, render_control_evaluation_markdown

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated" / "demo"

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


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)


def ensure_success(cmd: list[str]) -> None:
    result = run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.stdout + result.stderr)


def evaluate_policy(input_path: Path, query: str) -> list[str]:
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
        raise SystemExit(result.stdout + result.stderr)
    payload = json.loads(result.stdout)
    return payload["result"][0]["expressions"][0]["value"]


def render_scenario(name: str, input_path: Path) -> dict:
    policy_results = {}
    for policy_name, query in POLICY_QUERIES.items():
        denies = evaluate_policy(input_path, query)
        policy_results[policy_name] = {
            "pass": len(denies) == 0,
            "deny_messages": denies,
        }

    failing = [name for name, data in policy_results.items() if not data["pass"]]
    control_report = generate_control_evaluation_report(input_path)
    return {
        "scenario": name,
        "input_file": str(input_path.relative_to(ROOT)),
        "pass": len(failing) == 0,
        "failing_policies": failing,
        "policy_results": policy_results,
        "control_evaluations": control_report,
    }


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        f"# Demo Scenario: {summary['scenario']}",
        "",
        f"Overall Result: `{'pass' if summary['pass'] else 'fail'}`",
        f"Input File: `{summary['input_file']}`",
        "",
        "| Policy | Result | Deny Messages |",
        "| --- | --- | --- |",
    ]
    for policy_name, result in summary["policy_results"].items():
        deny_messages = "<br>".join(result["deny_messages"]) if result["deny_messages"] else "-"
        lines.append(
            f"| `{policy_name}` | `{'pass' if result['pass'] else 'fail'}` | {deny_messages} |"
        )
    lines.extend(
        [
            "",
            "## Control Evaluation Summary",
            "",
            f"- Tested controls: `{summary['control_evaluations']['summary']['tested_controls']}`",
            f"- Passed controls: `{summary['control_evaluations']['summary']['pass']}`",
            f"- Failed controls: `{summary['control_evaluations']['summary']['fail']}`",
            f"- Not tested: `{summary['control_evaluations']['summary']['not_tested']}`",
            f"- Not applicable: `{summary['control_evaluations']['summary']['not_applicable']}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    ensure_success(["python3", "scripts/validate_governance_repo.py"])
    ensure_success(["python3", "scripts/generate_traceability_csv.py"])
    ensure_success(["python3", "scripts/generate_document_control_matrix.py"])
    ensure_success(["python3", "scripts/generate_open_gap_report.py"])
    ensure_success(["python3", "scripts/render_governance_documents.py"])
    ensure_success(["python3", "scripts/generate_governance_graph.py"])
    ensure_success(["python3", "scripts/generate_status_viewer.py"])

    scenarios = {
        "green": ROOT / "demo" / "inputs" / "release-candidate-green.json",
        "red": ROOT / "demo" / "inputs" / "release-candidate-red.json",
    }
    run_results = []
    for scenario_name, input_path in scenarios.items():
        summary = render_scenario(scenario_name, input_path)
        json_path = OUTPUT / f"{scenario_name}-summary.json"
        md_path = OUTPUT / f"{scenario_name}-summary.md"
        control_json_path = OUTPUT / f"{scenario_name}-control-evaluation.json"
        control_md_path = OUTPUT / f"{scenario_name}-control-evaluation.md"
        json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        write_markdown(summary, md_path)
        control_json_path.write_text(json.dumps(summary["control_evaluations"], indent=2) + "\n", encoding="utf-8")
        control_md_path.write_text(render_control_evaluation_markdown(summary["control_evaluations"]), encoding="utf-8")
        run_results.append(summary)

    overview_lines = [
        "# Governance Demo Run",
        "",
        "This run validates the repository, regenerates all governance artifacts, and evaluates two demo release candidates.",
        "",
        "| Scenario | Result | Failing Policies | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for summary in run_results:
        failures = ", ".join(summary["failing_policies"]) if summary["failing_policies"] else "-"
        overview_lines.append(
            f"| `{summary['scenario']}` | `{'pass' if summary['pass'] else 'fail'}` | {failures} | "
            f"`generated/demo/{summary['scenario']}-summary.md` |"
        )
    overview_lines.extend(
        [
            "",
            "## Generated Governance Artifacts",
            "",
            "- `generated/viewer/status-viewer.html`",
            "- `generated/control-evaluation-report.json`",
            "- `generated/control-evaluation-report.md`",
            "- `generated/reports/open-gap-report.md`",
            "- `generated/reports/document-control-matrix.md`",
            "- `generated/documents/devsecops-pol-001.html`",
            "- `generated/documents/devsecops-dir-001.html`",
        ]
    )
    (OUTPUT / "demo-run.md").write_text("\n".join(overview_lines) + "\n", encoding="utf-8")
    print(f"Wrote {(OUTPUT / 'demo-run.md').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
