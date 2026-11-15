#!/usr/bin/env python3
"""Neutral full architecture assessment, extracted from the V1 report implementation.

Source lineage: 6b557fefe295b58272d2271326576ca3a3687197 /
scripts/generate_architecture_governance_report.py. Gate/report semantics are
retained; execution requires the explicit pinned product OPA. The frozen V1
entrypoint is not imported or dispatched by this module.
"""

from pathlib import Path
import json

import yaml


from lib.portable.contracts import ROOT
from lib.tool_integrity import require_opa, evaluate_query

GATES = [
    {
        "id": "architecture_readiness",
        "title": "Architecture Readiness",
        "policy": "policies/opa/architecture_readiness.rego",
        "query": "data.architecture.readiness.deny",
    },
    {
        "id": "integration_readiness",
        "title": "Integration Readiness",
        "policy": "policies/opa/architecture_integration_readiness.rego",
        "query": "data.architecture.integration_readiness.deny",
    },
    {
        "id": "operation_readiness",
        "title": "Operation Readiness",
        "policy": "policies/opa/architecture_operation_readiness.rego",
        "query": "data.architecture.operation_readiness.deny",
    },
    {
        "id": "release_readiness",
        "title": "Release Readiness",
        "policy": "policies/opa/architecture_release_readiness.rego",
        "query": "data.architecture.release_readiness.deny",
    },
]

RECOMMENDED_DETAILED_EVIDENCE = [
    {
        "type": "threat_model",
        "coarse_type": "security_evidence",
        "markers": ["E6", "S5", "P8"],
        "reason": "Security assumptions and mitigations are easier to review when a threat model is explicit.",
    },
    {
        "type": "interface_contract",
        "coarse_type": "release_compatibility_declaration",
        "markers": ["E3", "S3", "P6"],
        "reason": "Integration readiness depends on explicit interface ownership, versioning, and compatibility.",
    },
    {
        "type": "deployment_manifest",
        "coarse_type": "deployment_evidence",
        "markers": ["E8", "P5"],
        "reason": "Deployment readiness is stronger when runtime configuration is linked as evidence.",
    },
    {
        "type": "model_based_architecture",
        "coarse_type": "solution_baseline",
        "markers": ["B2", "S1", "S2", "P3"],
        "reason": "Model-based evidence is useful for complex or release-critical systems without mandating a vendor tool.",
    },
]


def run_opa(policy: Path, input_path: Path, query: str, *, opa) -> list[str]:
    return evaluate_query(opa, policy, input_path, query)


def load_target_summary(input_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    return payload.get("target_repository", {})


def load_architecture(input_path: Path) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    return payload.get("architecture", {})


def load_detailed_evidence(input_path: Path) -> dict:
    return load_architecture(input_path).get(
        "detailed_evidence",
        {"report_only": True, "declared_types": [], "by_type": {}, "by_coarse_type": {}},
    )


def load_remediations() -> list[dict]:
    path = ROOT / "architecture" / "remediation-actions.yaml"
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload.get("remediations", [])


def match_remediations(findings: list[str], remediations: list[dict]) -> list[dict]:
    matched = []
    seen = set()
    for finding in findings:
        normalized = finding.lower()
        for remediation in remediations:
            match = remediation.get("match", "").lower()
            if match and match in normalized and remediation["id"] not in seen:
                matched.append(remediation)
                seen.add(remediation["id"])
    return matched


def render_detailed_evidence_markdown(detailed_evidence: dict) -> list[str]:
    lines = ["## Detailed Evidence", ""]
    declared_types = detailed_evidence.get("declared_types", [])
    if not declared_types:
        lines.append("No detailed evidence declared.")
        lines.append("")
        return lines

    mode = "report-only" if detailed_evidence.get("report_only", True) else "enforced"
    lines.append(f"Mode: `{mode}`")
    lines.extend(["", "| Evidence type | Coarse area | Status | Owner | Path |", "|---|---|---|---|---|"])
    by_type = detailed_evidence.get("by_type", {})
    for evidence_type in declared_types:
        item = by_type.get(evidence_type, {})
        lines.append(
            "| "
            f"`{evidence_type}` | "
            f"`{item.get('coarse_type', 'unknown')}` | "
            f"`{item.get('status', '')}` | "
            f"{item.get('owner', '')} | "
            f"`{item.get('path', '')}` |"
        )
    lines.append("")
    return lines


def marker_score(architecture: dict, marker_ids: list[str]) -> int:
    scores = [
        int(item.get("score", 0) or 0)
        for item in architecture.get("marker_assessments", [])
        if item.get("id") in marker_ids
    ]
    return max(scores or [0])


def coarse_evidence_exists(architecture: dict, coarse_type: str) -> bool:
    return bool(architecture.get(coarse_type, {}).get("exists"))


def recommendation_applies(architecture: dict, recommendation: dict) -> bool:
    coarse_type = recommendation["coarse_type"]
    if coarse_evidence_exists(architecture, coarse_type):
        return True
    return marker_score(architecture, recommendation.get("markers", [])) >= 3


def detailed_evidence_advisories(architecture: dict, detailed_evidence: dict) -> list[dict]:
    declared = set(detailed_evidence.get("declared_types", []))
    advisories = []
    for item in RECOMMENDED_DETAILED_EVIDENCE:
        if item["type"] not in declared and recommendation_applies(architecture, item):
            advisories.append(
                {
                    "severity": "info",
                    "mode": "report_only",
                    "evidence_type": item["type"],
                    "coarse_type": item["coarse_type"],
                    "trigger": "coarse_evidence_or_marker_signal",
                    "message": f"Recommended detailed evidence `{item['type']}` is not declared.",
                    "reason": item["reason"],
                }
            )
    return advisories


def render_advisories_markdown(advisories: list[dict]) -> list[str]:
    lines = ["## Report-Only Advisories", ""]
    if not advisories:
        lines.append("No report-only advisories.")
        lines.append("")
        return lines

    lines.extend(["| Severity | Evidence type | Coarse area | Message |", "|---|---|---|---|"])
    for advisory in advisories:
        lines.append(
            "| "
            f"`{advisory['severity']}` | "
            f"`{advisory['evidence_type']}` | "
            f"`{advisory['coarse_type']}` | "
            f"{advisory['message']} |"
        )
    lines.append("")
    return lines


def render_markdown(target: dict, gate_results: list[dict], detailed_evidence: dict, advisories: list[dict]) -> str:
    lines = [
        "# Architecture Runtime Governance Report",
        "",
        "## Target",
        "",
        f"- Repository: `{target.get('path', 'unknown')}`",
        f"- Commit: `{target.get('commit', 'unknown')}`",
        f"- Release ID: `{target.get('release_id', 'unknown')}`",
        f"- Detected services: `{target.get('detected_services', 'unknown')}`",
        "",
        "## Gate Summary",
        "",
        "| Gate | Status | Findings |",
        "|---|---:|---:|",
    ]

    for gate in gate_results:
        status = "PASS" if not gate["findings"] else "FINDINGS"
        lines.append(f"| {gate['title']} | {status} | {len(gate['findings'])} |")

    lines.extend(["", *render_detailed_evidence_markdown(detailed_evidence)])
    lines.extend(render_advisories_markdown(advisories))
    lines.extend(["", "## Findings", ""])
    for gate in gate_results:
        lines.append(f"### {gate['title']}")
        lines.append("")
        if not gate["findings"]:
            lines.append("No findings.")
        else:
            for finding in gate["findings"]:
                lines.append(f"- {finding}")
            if gate.get("remediations"):
                lines.extend(["", "Recommended actions:"])
                for remediation in gate["remediations"]:
                    evidence = ", ".join(f"`{item}`" for item in remediation.get("evidence", []))
                    lines.append(f"- **{remediation['title']}**: {remediation['action']}")
                    if evidence:
                        lines.append(f"  Evidence: {evidence}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def evaluate(input_path: Path, *, opa) -> dict:
    opa = require_opa(opa)
    gate_results = []
    remediations = load_remediations()
    for gate in GATES:
        findings = run_opa(ROOT / gate["policy"], input_path, gate["query"], opa=opa)
        gate_results.append({
            "id": gate["id"], "title": gate["title"],
            "status": "pass" if not findings else "findings", "findings": findings,
            "remediations": match_remediations(findings, remediations),
        })
    target = load_target_summary(input_path)
    architecture = load_architecture(input_path)
    detailed_evidence = architecture.get("detailed_evidence", {
        "report_only": True, "declared_types": [], "by_type": {}, "by_coarse_type": {},
    })
    advisories = detailed_evidence_advisories(architecture, detailed_evidence)
    return {
        "target": target, "gates": gate_results, "detailed_evidence": detailed_evidence,
        "advisories": advisories,
        "summary": {"gate_count": len(gate_results),
                    "passed": sum(1 for gate in gate_results if not gate["findings"]),
                    "with_findings": sum(1 for gate in gate_results if gate["findings"]),
                    "finding_count": sum(len(gate["findings"]) for gate in gate_results)},
    }
