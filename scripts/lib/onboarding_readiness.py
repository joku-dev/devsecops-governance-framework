"""Original source-only onboarding findings from an explicit frozen snapshot."""
from pathlib import Path

def make_check(check_id: str, title: str, status: str, evidence: list[str], recommendation: str) -> dict:
    return {
        "check_id": check_id,
        "title": title,
        "status": status,
        "evidence": evidence,
        "recommendation": recommendation,
    }

def assess_repository(target_repo: Path, repository_id: str, *, ci_files: list[str], ci_text: str, integration: dict, at: str, target_label: str) -> dict:
    from lib.provider_ports import onboarding_source_surface
    return assess_surface(repository_id, surface=onboarding_source_surface(target_repo), ci_files=ci_files,
        ci_text=ci_text, integration=integration, at=at, target_label=target_label)


def assess_surface(repository_id: str, *, surface: dict, ci_files: list[str], ci_text: str, integration: dict, at: str, target_label: str) -> dict:
    workflow_files = ci_files; workflow_text = ci_text
    governance_docs = surface['governance_docs']; security_docs = surface['security_docs']
    agent_records = surface['agent_records']; slice_records = surface['slice_records']
    governance_examples = surface['governance_examples']; tests = surface['tests']; source_files = surface['source_files']

    checks = []
    checks.append(
        make_check(
            "repository_shape",
            "Repository has discoverable project structure",
            "pass" if surface['readme_present'] and (surface['project_manifest_present'] or source_files) else "warn",
            [
                *([ "README.md" ] if surface['readme_present'] else []),
                *([ "pyproject.toml" ] if surface['project_manifest_present'] else []),
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
            workflow_files[:8] + [f"{name}={value}" for name, value in ci_markers.items()],
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
        "ci_supply_chain_script": surface['ci_supply_chain_script_present'],
        "secrets_scan_support": surface['secrets_scan_support'],
        "sbom_or_vulnerability_artifact": surface['supply_chain_artifact_present'],
    }
    supply_chain_status = "pass" if all(supply_chain_markers.values()) else "warn"
    checks.append(
        make_check(
            "supply_chain_and_security_evidence",
            "Security and supply-chain evidence is present or planned",
            supply_chain_status,
            security_docs[:5]
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
