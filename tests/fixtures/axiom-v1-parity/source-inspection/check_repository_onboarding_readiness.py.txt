#!/usr/bin/env python3
"""Assess a repository before central governance baseline onboarding."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def collect_files(root: Path, patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                files.append(path)
                seen.add(path)
    return sorted(files)


def relative_paths(root: Path, paths: list[Path], *, limit: int = 8) -> list[str]:
    return [str(path.relative_to(root)) for path in paths[:limit]]


def make_check(check_id: str, title: str, status: str, evidence: list[str], recommendation: str) -> dict:
    return {
        "check_id": check_id,
        "title": title,
        "status": status,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def run_integration_scanner(target_repo: Path) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_repo_governance_integration.py"),
            "--target-repo",
            str(target_repo),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if not result.stdout.strip():
        return {
            "status": "fail",
            "checks": [],
            "details": result.stderr.strip() or "No scanner output.",
        }
    payload = json.loads(result.stdout)
    return {
        "status": payload.get("status", "fail"),
        "checks": payload.get("checks", []),
        "details": "Central integration scanner completed.",
    }


def assess_repository(target_repo: Path, repository_id: str) -> dict:
    workflow_files = collect_files(
        target_repo,
        [".github/workflows/*.yml", ".github/workflows/*.yaml", "*.gitlab-ci.yml", "Jenkinsfile"],
    )
    workflow_text = "\n".join(read_text(path) for path in workflow_files)
    governance_docs = collect_files(target_repo, ["docs/governance/*.md", "docs/governance/*.json"])
    security_docs = collect_files(target_repo, ["docs/security/*.md", "docs/security/*.json", ".factory/security/*"])
    agent_records = collect_files(target_repo, [".agent-executions/*.yaml", ".agent-executions/*.yml", ".agent-executions/*.json"])
    slice_records = collect_files(
        target_repo,
        [".slice-candidate-creations/*.yaml", ".slice-candidate-creations/*.yml", ".slice-candidate-creations/*.json"],
    )
    governance_examples = collect_files(
        target_repo,
        ["examples/governance_*/*", "examples/governance_*/*.*", "examples/governance_reports/*", "examples/governance_runtime/*"],
    )
    tests = collect_files(target_repo, ["tests/**/*.py", "tests/*.py"])
    source_files = collect_files(target_repo, ["src/**/*.py", "scripts/*.py"])

    checks = []
    checks.append(
        make_check(
            "repository_shape",
            "Repository has discoverable project structure",
            "pass" if (target_repo / "README.md").exists() and ((target_repo / "pyproject.toml").exists() or source_files) else "warn",
            [
                *([ "README.md" ] if (target_repo / "README.md").exists() else []),
                *([ "pyproject.toml" ] if (target_repo / "pyproject.toml").exists() else []),
                f"{len(source_files)} source/script files",
                f"{len(tests)} test files",
            ],
            "Keep README, setup instructions, source layout, and test entrypoints stable before wiring central governance.",
        )
    )

    ci_markers = {
        "pytest": "pytest" in workflow_text,
        "ruff": "ruff" in workflow_text,
        "mypy": "mypy" in workflow_text,
        "governance_evidence_check": "regenerate_governance_evidence.py --check" in workflow_text,
        "agent_execution_gate": "check_pr_execution_evidence.py" in workflow_text,
    }
    ci_status = "pass" if all(ci_markers.values()) else "warn" if workflow_files else "fail"
    checks.append(
        make_check(
            "local_quality_gates",
            "Local CI already covers tests, lint, typing, and governance freshness",
            ci_status,
            relative_paths(target_repo, workflow_files) + [f"{name}={value}" for name, value in ci_markers.items()],
            "Preserve existing local quality gates and add the central L1 baseline as a separate report-only job first.",
        )
    )

    governance_status = "pass" if governance_docs and agent_records and governance_examples else "warn"
    checks.append(
        make_check(
            "governance_evidence_surface",
            "Repository already contains governance and execution evidence",
            governance_status,
            [
                f"{len(governance_docs)} governance docs",
                f"{len(agent_records)} agent execution records",
                f"{len(slice_records)} slice candidate records",
                f"{len(governance_examples)} generated governance examples",
            ],
            "Map this repository-native evidence into the central L1 evidence contract instead of duplicating it manually.",
        )
    )

    supply_chain_markers = {
        "security_docs": bool(security_docs),
        "ci_supply_chain_script": (target_repo / "scripts" / "check_factory_ci_supply_chain.py").exists(),
        "secrets_scan_support": "secrets" in "\n".join(read_text(path).lower() for path in security_docs[:8]),
        "sbom_or_vulnerability_artifact": bool(
            collect_files(target_repo, ["**/*sbom*", "**/*vulnerability*", "**/*trivy*", "**/*dependency*"])
        ),
    }
    supply_chain_status = "pass" if all(supply_chain_markers.values()) else "warn"
    checks.append(
        make_check(
            "supply_chain_and_security_evidence",
            "Security and supply-chain evidence is present or planned",
            supply_chain_status,
            relative_paths(target_repo, security_docs, limit=5)
            + [f"{name}={value}" for name, value in supply_chain_markers.items()],
            "Before mainline enforcement, provide concrete SBOM and vulnerability scan artifacts for central intake.",
        )
    )

    integration = run_integration_scanner(target_repo)
    integration_status = "pass" if integration["status"] == "pass" else "warn"
    integration_recommendation = (
        "Continue report-only L1 branch runs, publish a released baseline pin before production use, "
        "and move to block-on-error only after branch protection is ready."
        if integration_status == "pass"
        else "Add the reusable L1 workflow in report-only mode, then record the first branch run."
    )
    checks.append(
        make_check(
            "central_baseline_integration",
            "Central governance baseline workflow is wired",
            integration_status,
            [
                f"scanner_status={integration['status']}",
                *[
                    f"{item.get('check_id')}: {item.get('status')}"
                    for item in integration.get("checks", [])
                ],
            ],
            integration_recommendation,
        )
    )

    failing = sum(1 for check in checks if check["status"] == "fail")
    warnings = sum(1 for check in checks if check["status"] == "warn")
    if failing:
        status = "not_ready"
    elif warnings:
        status = "ready_with_gaps"
    else:
        status = "ready"

    recommended_next_step = (
        "Continue report-only central L1 runs and prepare branch protection before block-on-error enforcement."
        if integration_status == "pass"
        else "Create a report-only central L1 baseline branch run."
    )

    return {
        "schema_version": "1.0.0",
        "repository_id": repository_id,
        "target_repo": target_repo.name,
        "target_path": str(target_repo),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "summary": {
            "checks": len(checks),
            "pass": sum(1 for check in checks if check["status"] == "pass"),
            "warn": warnings,
            "fail": failing,
            "recommended_next_step": recommended_next_step,
        },
        "checks": checks,
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['repository_id']} Governance Onboarding Readiness",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Target path: `{report['target_path']}`",
        f"- Recommended next step: {report['summary']['recommended_next_step']}",
        "",
        "## Summary",
        "",
        "| Checks | Pass | Warn | Fail |",
        "| --- | ---: | ---: | ---: |",
        f"| {report['summary']['checks']} | {report['summary']['pass']} | {report['summary']['warn']} | {report['summary']['fail']} |",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence | Recommendation |",
        "| --- | --- | --- | --- |",
    ]
    for check in report["checks"]:
        evidence = "<br>".join(check["evidence"]) if check["evidence"] else "No evidence detected"
        lines.append(
            f"| `{check['check_id']}` {check['title']} | `{check['status']}` | {evidence} | {check['recommendation']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()

    target_repo = Path(args.target_repo).resolve()
    if not target_repo.exists():
        raise SystemExit(f"Target repository not found: {target_repo}")

    report = assess_repository(target_repo, args.repository_id)
    payload = json.dumps(report, indent=2) + "\n"
    if args.output_json:
        output_json = Path(args.output_json)
        if not output_json.is_absolute():
            output_json = Path.cwd() / output_json
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(payload, encoding="utf-8")
        print(f"Wrote {output_json}")
    else:
        print(payload, end="")

    if args.output_md:
        output_md = Path(args.output_md)
        if not output_md.is_absolute():
            output_md = Path.cwd() / output_md
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(report), encoding="utf-8")
        print(f"Wrote {output_md}")

    return 0 if report["status"] in {"ready", "ready_with_gaps"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
