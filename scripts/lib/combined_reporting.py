"""Original V1 combined report mapping and renderer, with explicit pair guards.

This renderer retains legacy prose. The private application envelope remains
unverified, report-only and without production or governance approval.
"""
def architecture_summary(report: dict) -> tuple[str, int, list[str]]:
    findings = []
    for gate in report.get("gates", []):
        for finding in gate.get("findings", []):
            findings.append(f"{gate.get('title', gate.get('id'))}: {finding}")
    status = "PASS" if not findings else "FINDINGS"
    return status, len(findings), findings

def devsecops_summary(report: dict) -> tuple[str, int, list[str]]:
    findings = report.get("gate", {}).get("findings", [])
    status = "PASS" if not findings else "FINDINGS"
    return status, len(findings), findings

def render_markdown(architecture_report: dict, devsecops_report: dict, architecture_md: str, devsecops_md: str) -> str:
    architecture_status, architecture_findings_count, architecture_findings = architecture_summary(architecture_report)
    devsecops_status, devsecops_findings_count, devsecops_findings = devsecops_summary(devsecops_report)
    overall_status = "PASS" if architecture_status == "PASS" and devsecops_status == "PASS" else "FINDINGS"

    target = architecture_report.get("target") or devsecops_report.get("target") or {}

    lines = [
        "# End-to-End Governance Report",
        "",
        "## Target",
        "",
        f"- Repository: `{target.get('path', 'unknown')}`",
        f"- Commit: `{target.get('commit', 'unknown')}`",
        f"- Release ID: `{target.get('release_id', 'unknown')}`",
        "",
        "## Overall Result",
        "",
        "| Domain | Status | Findings | Detail report |",
        "|---|---:|---:|---|",
        f"| Architecture Runtime Governance | {architecture_status} | {architecture_findings_count} | `{architecture_md}` |",
        f"| DevSecOps Governance | {devsecops_status} | {devsecops_findings_count} | `{devsecops_md}` |",
        f"| **Overall** | **{overall_status}** | **{architecture_findings_count + devsecops_findings_count}** | |",
        "",
        "## Interpretation",
        "",
    ]

    if overall_status == "PASS":
        lines.extend(
            [
                "The target repository currently satisfies the governance gates for both architecture runtime governance and DevSecOps release governance.",
                "",
                "This does not mean the system is production-certified. It means that the required evidence is present, machine-readable, and accepted by the current governance policies.",
            ]
        )
    else:
        lines.extend(
            [
                "The target repository still has governance findings. The findings are actionable gaps, not generic quality comments.",
                "",
                "A finding should be closed by adding or improving evidence, approving a controlled exception, or changing the implementation so that the policy condition is satisfied.",
            ]
        )

    lines.extend(["", "## Architecture Findings", ""])
    if architecture_findings:
        for finding in architecture_findings:
            lines.append(f"- {finding}")
    else:
        lines.append("No architecture findings.")

    lines.extend(["", "## DevSecOps Findings", ""])
    if devsecops_findings:
        for finding in devsecops_findings:
            lines.append(f"- {finding}")
    else:
        lines.append("No DevSecOps findings.")

    lines.extend(
        [
            "",
            "## Evidence Model",
            "",
            "The report uses two evidence layers:",
            "",
            "- `.governance/architecture/*.json` for architecture baseline, compatibility, security, resilience, operation and feedback evidence.",
            "- `.governance/devsecops/release-evidence.json` for DevSecOps release evidence such as SBOM, vulnerability scan, artifact integrity, dependency source approval and pipeline security gate evidence.",
            "",
            "The governance repository turns those files into policy inputs, evaluates OPA policies and produces human-readable reports.",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"

def pair_target(architecture, devsecops):
    left, right = architecture.get('target'), devsecops.get('target')
    for target in (left, right):
        if not isinstance(target, dict) or any(not isinstance(target.get(key), str) or not target[key]
                                               for key in ('path', 'commit', 'release_id')):
            raise ValueError('explicit_combined_target_required')
    if any(left[key] != right[key] for key in ('path', 'commit', 'release_id')):
        raise ValueError('combined_target_mismatch')
    return left


def build(architecture, devsecops):
    target = pair_target(architecture, devsecops)
    gates = architecture.get('gates')
    expected = {'architecture_readiness', 'integration_readiness', 'operation_readiness', 'release_readiness'}
    if (not isinstance(gates, list) or len(gates) != 4 or any(not isinstance(row, dict) for row in gates)
            or {row.get('id') for row in gates} != expected):
        raise ValueError('complete_combined_architecture_gates_required')
    gate = devsecops.get('gate')
    if not isinstance(gate, dict) or gate.get('id') != 'devsecops_release_readiness':
        raise ValueError('complete_combined_devsecops_gate_required')
    for row in [*gates, gate]:
        findings = row.get('findings')
        if (not isinstance(findings, list) or any(not isinstance(item, str) for item in findings)
                or row.get('status') != ('findings' if findings else 'pass')):
            raise ValueError('invalid_combined_gate_findings_or_status')
    architecture_status, architecture_count, architecture_findings = architecture_summary(architecture)
    devsecops_status, devsecops_count, devsecops_findings = devsecops_summary(devsecops)
    return {'target': target,
        'overall_status': 'pass' if architecture_status == 'PASS' and devsecops_status == 'PASS' else 'findings',
        'domains': {'architecture': {'status': architecture_status.lower(), 'finding_count': architecture_count,
                                    'findings': architecture_findings},
                    'devsecops': {'status': devsecops_status.lower(), 'finding_count': devsecops_count,
                                 'findings': devsecops_findings}},
        'summary': {'finding_count': architecture_count + devsecops_count}}
