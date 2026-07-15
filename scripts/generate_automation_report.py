#!/usr/bin/env python3
"""Generate a Markdown report for automation coverage."""

from collections import Counter, defaultdict
from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "html" / "automation_report.md"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    controls = []
    for path in sorted((ROOT / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        for requirement in data.get("requirements", []):
            controls.append({**requirement, "level": data.get("level")})

    governance = []
    for path in [
        ROOT / "governance" / "policy-requirements.yaml",
        ROOT / "governance" / "directive-requirements.yaml",
    ]:
        data = load_yaml(path)
        if "requirements" not in data:
            continue
        for requirement in data.get("requirements", []):
            governance.append({**requirement, "source_document": data.get("source_document")})

    by_type = Counter(item["automation"]["type"] for item in controls)
    by_maturity = Counter(item["automation"]["maturity"] for item in controls)
    by_check_type = Counter(item["automation"]["check_type"] for item in controls)
    by_level = defaultdict(Counter)
    for item in controls:
        by_level[item["level"]][item["automation"]["type"]] += 1

    automation_supported = sum(
        1 for item in controls if item["automation"]["type"] in {"blocking_gate", "warning_gate", "evidence_check"}
    )
    blocking = by_type["blocking_gate"]

    lines = [
        "# Automation Coverage Report",
        "",
        "## Summary",
        "",
        f"- Total requirements: {len(controls)}",
        f"- Blocking gates: {blocking}",
        f"- Automation-supported requirements: {automation_supported}",
        f"- Review-led requirements: {by_type['review_check']}",
        f"- Automation-supported coverage: {automation_supported / len(controls):.1%}",
        f"- Blocking-gate coverage: {blocking / len(controls):.1%}",
        "",
        "## By Automation Type",
        "",
        "| Type | Count |",
        "|---|---:|",
    ]
    for key in ["blocking_gate", "warning_gate", "evidence_check", "review_check"]:
        lines.append(f"| `{key}` | {by_type[key]} |")

    lines.extend([
        "",
        "## By Maturity",
        "",
        "| Maturity | Count |",
        "|---|---:|",
    ])
    for key in ["immediate", "tool_integration_required", "future"]:
        lines.append(f"| `{key}` | {by_maturity[key]} |")

    lines.extend([
        "",
        "## By Check Type",
        "",
        "| Check Type | Count |",
        "|---|---:|",
    ])
    for key in ["presence", "linkage", "threshold", "configuration", "approval", "review", "integrity", "provenance"]:
        lines.append(f"| `{key}` | {by_check_type[key]} |")

    lines.extend([
        "",
        "## By Level",
        "",
        "| Level | Blocking Gate | Warning Gate | Evidence Check | Review Check |",
        "|---|---:|---:|---:|---:|",
    ])
    for level in ["L1", "L2", "L3", "GOV"]:
        counts = by_level[level]
        lines.append(
            f"| {level} | {counts['blocking_gate']} | {counts['warning_gate']} | {counts['evidence_check']} | {counts['review_check']} |"
        )

    lines.extend([
        "",
        "## Governance Requirements",
        "",
        f"- Policy requirements: {sum(1 for item in governance if item['source_document'] == 'DevSecOps Policy')}",
        f"- Directive requirements: {sum(1 for item in governance if item['source_document'] == 'DevSecOps Directive')}",
        f"- Total Policy/Directive requirements: {len(governance)}",
        "",
        "| Source | Blocking Gate | Evidence Check | Review Check | Warning Gate |",
        "|---|---:|---:|---:|---:|",
    ])
    for source in ["DevSecOps Policy", "DevSecOps Directive"]:
        counts = Counter(item["automation"]["type"] for item in governance if item["source_document"] == source)
        lines.append(
            f"| {source} | {counts['blocking_gate']} | {counts['evidence_check']} | {counts['review_check']} | {counts['warning_gate']} |"
        )

    lines.extend([
        "",
        "## Requirement Classification",
        "",
        "| ID | Level | Title | Type | Maturity |",
        "|---|---|---|---|---|",
    ])
    for item in sorted(controls, key=lambda x: x["id"]):
        lines.append(
            f"| `{item['id']}` | {item['level']} | {item['title']} | `{item['automation']['type']}` | `{item['automation']['maturity']}` |"
        )

    lines.extend([
        "",
        "## Verification Requirements",
        "",
        "| ID | Check Type | Verification Requirement |",
        "|---|---|---|",
    ])
    for item in sorted(controls, key=lambda x: x["id"]):
        lines.append(
            f"| `{item['id']}` | `{item['automation']['check_type']}` | {item.get('verification_requirement', '')} |"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
