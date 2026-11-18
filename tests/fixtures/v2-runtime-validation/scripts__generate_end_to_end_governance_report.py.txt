#!/usr/bin/env python3
"""Generate a combined architecture and DevSecOps governance report."""

from argparse import ArgumentParser
from pathlib import Path
import json


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def main() -> int:
    parser = ArgumentParser(description="Generate combined end-to-end governance report.")
    parser.add_argument("--architecture-json", required=True, help="Architecture governance report JSON")
    parser.add_argument("--devsecops-json", required=True, help="DevSecOps governance report JSON")
    parser.add_argument("--output-json", required=True, help="Combined JSON output")
    parser.add_argument("--output-md", required=True, help="Combined Markdown output")
    parser.add_argument("--architecture-md-ref", default="ha-cpswms-architecture-governance-report.md")
    parser.add_argument("--devsecops-md-ref", default="ha-cpswms-devsecops-governance-report.md")
    args = parser.parse_args()

    architecture_report = load_json(Path(args.architecture_json))
    devsecops_report = load_json(Path(args.devsecops_json))

    architecture_status, architecture_findings_count, architecture_findings = architecture_summary(architecture_report)
    devsecops_status, devsecops_findings_count, devsecops_findings = devsecops_summary(devsecops_report)
    overall_status = "pass" if architecture_status == "PASS" and devsecops_status == "PASS" else "findings"

    combined = {
        "target": architecture_report.get("target") or devsecops_report.get("target") or {},
        "overall_status": overall_status,
        "domains": {
            "architecture": {
                "status": architecture_status.lower(),
                "finding_count": architecture_findings_count,
                "findings": architecture_findings,
            },
            "devsecops": {
                "status": devsecops_status.lower(),
                "finding_count": devsecops_findings_count,
                "findings": devsecops_findings,
            },
        },
        "summary": {
            "finding_count": architecture_findings_count + devsecops_findings_count,
        },
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(
        render_markdown(architecture_report, devsecops_report, args.architecture_md_ref, args.devsecops_md_ref),
        encoding="utf-8",
    )

    print(f"Generated {output_json}")
    print(f"Generated {output_md}")
    print(f"- overall_status: {overall_status}")
    print(f"- findings: {combined['summary']['finding_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
