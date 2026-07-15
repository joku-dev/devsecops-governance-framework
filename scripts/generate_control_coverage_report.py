#!/usr/bin/env python3
"""Generate a control automation coverage report."""

from __future__ import annotations

from pathlib import Path
import json

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_controls() -> list[dict]:
    controls = []
    for path in sorted((MODEL / "controls").glob("dscb-*.yaml")):
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


def main() -> int:
    controls = load_controls()
    coverage_data = load_yaml(MODEL / "controls" / "control-coverage.yaml").get("coverage", [])
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

    json_path = ROOT / "generated" / "reports" / "control-coverage-report.json"
    md_path = ROOT / "generated" / "reports" / "control-coverage-report.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

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
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
