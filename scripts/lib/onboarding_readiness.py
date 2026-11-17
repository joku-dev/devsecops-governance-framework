"""Original source-only onboarding findings from an explicit frozen snapshot."""
from pathlib import Path

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

def assess_repository(target_repo: Path, repository_id: str, *, ci_files: list[str], ci_text: str, integration: dict, at: str, target_label: str) -> dict:
    workflow_files = [target_repo / name for name in ci_files]
    workflow_text = ci_text
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
        "target_repo": Path(target_label).name,
        "target_path": target_label,
        "generated_at": at,
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
