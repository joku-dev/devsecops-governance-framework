"""Control coverage and traceability computation from frozen V1 6b557fe.

Only captured governed data is read. No source CLI, file writer or native client
is invoked. Original CSV ordering, types and line endings remain unchanged.
"""
from pathlib import Path
import csv
import io
import json
import yaml
from lib.result_bytes import safe_bytes


def load_yaml(path):
    return yaml.safe_load(safe_bytes(Path(path), limit=16 * 1024**2))



def load_controls(root: Path) -> list[dict]:
    controls = []
    for path in sorted((root / "model" / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        for requirement in data.get("requirements", []):
            controls.append(
                {
                    "control_id": requirement["id"],
                    "level": data["level"],
                    "title": requirement["title"],
                    "domain": requirement["domain"],
                    "verification_method": requirement.get("verification", {}).get("method", "unknown"),
                    "policy_candidate": bool(requirement.get("policy_as_code", {}).get("candidate", False)),
                }
            )
    return controls


def control_coverage(root: Path):
    controls = load_controls(root)
    coverage_data = load_yaml(root / "model" / "controls" / "control-coverage.yaml").get("coverage", [])
    coverage_by_id = {item["control_id"]: item for item in coverage_data}

    rows = []
    status_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    for control in controls:
        coverage = coverage_by_id[control["control_id"]]
        status = coverage["automation_status"]
        priority = coverage["priority"]
        status_counts[status] = status_counts.get(status, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
        rows.append({**control, **coverage})

    planned_rows = sorted(
        [row for row in rows if row["automation_status"] == "planned"],
        key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item["priority"]], item["control_id"]),
    )

    report = {
        "schema_version": "1.0.0",
        "summary": {
            "total_controls": len(rows),
            "automation_status_counts": status_counts,
            "priority_counts": priority_counts,
            "planned_controls": len(planned_rows),
        },
        "controls": rows,
    }

    lines = [
        "# Control Coverage Report",
        "",
        "## Summary",
        "",
        f"- Total controls: `{report['summary']['total_controls']}`",
        f"- Automated: `{status_counts.get('automated', 0)}`",
        f"- Manual: `{status_counts.get('manual', 0)}`",
        f"- Planned: `{status_counts.get('planned', 0)}`",
        f"- Not applicable: `{status_counts.get('not_applicable', 0)}`",
        "",
        "## Prioritized Planned Controls",
        "",
    ]
    if not planned_rows:
        lines.append("- No planned controls are currently recorded.")
    else:
        for item in planned_rows:
            lines.extend(
                [
                    f"### `{item['control_id']}`",
                    "",
                    f"- Level: `{item['level']}`",
                    f"- Priority: `{item['priority']}`",
                    f"- Verification method: `{item['verification_method']}`",
                    f"- Policy candidate: `{str(item['policy_candidate']).lower()}`",
                    f"- Rationale: {item['rationale']}",
                    f"- Next action: {item['next_action']}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Full Control Status Table",
            "",
            "| Control | Level | Status | Priority | Verification | Policy Candidate |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in rows:
        lines.append(
            f"| `{item['control_id']}` | `{item['level']}` | `{item['automation_status']}` | `{item['priority']}` | `{item['verification_method']}` | `{str(item['policy_candidate']).lower()}` |"
        )
    lines.append("")
    return report, "\n".join(lines)


def traceability(root: Path):
    controls = {}
    for path in sorted((root / "model" / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        level = data.get("level")
        for requirement in data.get("requirements", []):
            controls[requirement["id"]] = {
                **requirement,
                "level": level,
            }

    traceability = load_yaml(root / "model" / "traceability" / "control-to-platform.yaml")
    document_catalog = load_yaml(root / "model" / "documents" / "governance-documents.yaml")
    document_traceability = load_yaml(root / "model" / "traceability" / "document-to-control.yaml")
    document_titles = {item["id"]: item["title"] for item in document_catalog.get("documents", [])}
    control_documents = {control_id: [] for control_id in controls}

    for mapping in document_traceability.get("mappings", []):
        document_id = mapping["document_id"]
        target_ids = set(mapping.get("control_ids", []))
        target_levels = set(mapping.get("control_levels", []))
        for control_id, control in controls.items():
            if control_id in target_ids or control["level"] in target_levels:
                control_documents.setdefault(control_id, []).append(document_id)

    rows = []
    for mapping in traceability.get("mappings", []):
        control = controls[mapping["control"]]
        authority_documents = control_documents.get(control["id"], [])
        rows.append(
            {
                "control_id": control["id"],
                "level": control["level"],
                "domain": control["domain"],
                "title": control["title"],
                "requirement": control["requirement"],
                "required_platform_level": mapping["platform_level"],
                "platform_capabilities": "; ".join(mapping.get("platform_capabilities", [])),
                "evidence": "; ".join(mapping.get("evidence", [])),
                "verification_method": control.get("verification", {}).get("method", ""),
                "verification_frequency": control.get("verification", {}).get("frequency", ""),
                "authority_documents": "; ".join(authority_documents),
                "authority_document_titles": "; ".join(document_titles[doc_id] for doc_id in authority_documents),
                "policy_candidate": str(mapping.get("policy_candidate", False)).lower(),
                "policy_rule": control.get("policy_as_code", {}).get("rule", ""),
                "waiver_allowed": str(control.get("waiver", {}).get("allowed", "")).lower(),
                "waiver_authority": control.get("waiver", {}).get("authority", ""),
            }
        )

    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()



def architecture_traceability(root: Path):
    rows = []

    for path in sorted((root / "architecture").glob("arch-*.yaml")):
        data = load_yaml(path)
        level = data["level"]
        for requirement in data.get("requirements", []):
            rows.append(
                {
                    "level": level,
                    "requirement_id": requirement["id"],
                    "domain": requirement["domain"],
                    "title": requirement["title"],
                    "source_markers": ";".join(requirement.get("source_markers", [])),
                    "source_guardrails": ";".join(requirement.get("source_guardrails", [])),
                    "source_review_gates": ";".join(requirement.get("source_review_gates", [])),
                    "evidence": ";".join(requirement.get("evidence", [])),
                    "automation_type": requirement.get("automation", {}).get("type", ""),
                    "automation_maturity": requirement.get("automation", {}).get("maturity", ""),
                    "check_type": requirement.get("automation", {}).get("check_type", ""),
                    "policy_candidate": requirement.get("policy_as_code", {}).get("candidate", ""),
                    "policy_rule": requirement.get("policy_as_code", {}).get("rule", ""),
                    "exception_allowed": requirement.get("exception", {}).get("allowed", ""),
                    "exception_authority": requirement.get("exception", {}).get("authority", ""),
                }
            )

    handle = io.StringIO(newline="")
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "level",
            "requirement_id",
            "domain",
            "title",
            "source_markers",
            "source_guardrails",
            "source_review_gates",
            "evidence",
            "automation_type",
            "automation_maturity",
            "check_type",
            "policy_candidate",
            "policy_rule",
            "exception_allowed",
            "exception_authority",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()



def governance_traceability(root: Path):
    rows = []
    for path in [
        root / "governance" / "policy-requirements.yaml",
        root / "governance" / "directive-requirements.yaml",
    ]:
        data = load_yaml(path)
        source = data["source_document"]
        for req in data["requirements"]:
            linked_controls = req.get("derived_controls", req.get("implemented_by", []))
            rows.append(
                {
                    "source_document": source,
                    "requirement_id": req["id"],
                    "domain": req["domain"],
                    "title": req["title"],
                    "requirement": req["requirement"],
                    "verification_requirement": req["verification_requirement"],
                    "linked_controls": "; ".join(linked_controls),
                    "automation_type": req["automation"]["type"],
                    "automation_maturity": req["automation"]["maturity"],
                    "automation_check_type": req["automation"]["check_type"],
                    "machine_readable_evidence_required": str(req["automation"]["machine_readable_evidence_required"]).lower(),
                    "automation_rationale": req["automation"]["rationale"],
                }
            )

    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()

