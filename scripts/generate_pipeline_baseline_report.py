#!/usr/bin/env python3
"""Generate a Markdown report for the CI/CD Pipeline Control Baseline."""

from collections import Counter
from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "html" / "pipeline_baseline_report.md"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    placements = load_yaml(ROOT / "pipeline-baseline" / "control-placement.yaml")["control_placements"]
    by_stage = Counter(item["stage"] for item in placements)
    by_gate = Counter(item["gate_type"] for item in placements)
    by_check = Counter(item["check_type"] for item in placements)

    lines = [
        "# CI/CD Pipeline Control Baseline Report",
        "",
        "## Summary",
        "",
        f"- Control placements: {len(placements)}",
        f"- Stages used: {len(by_stage)}",
        "",
        "## Controls by Stage",
        "",
        "| Stage | Controls |",
        "|---|---:|",
    ]
    for stage in ["plan", "code", "build", "test", "package", "release", "deploy", "operate"]:
        lines.append(f"| `{stage}` | {by_stage[stage]} |")

    lines.extend([
        "",
        "## Controls by Gate Type",
        "",
        "| Gate Type | Controls |",
        "|---|---:|",
    ])
    for gate in ["blocking_gate", "warning_gate", "evidence_check", "review_check"]:
        lines.append(f"| `{gate}` | {by_gate[gate]} |")

    lines.extend([
        "",
        "## Controls by Check Type",
        "",
        "| Check Type | Controls |",
        "|---|---:|",
    ])
    for check_type in ["presence", "linkage", "threshold", "configuration", "approval", "review", "integrity", "provenance"]:
        lines.append(f"| `{check_type}` | {by_check[check_type]} |")

    lines.extend([
        "",
        "## Control Placement Detail",
        "",
        "| Control | Stage | Gate Type | Check Type | Failure Result | Maturity |",
        "|---|---|---|---|---|---|",
    ])
    for item in sorted(placements, key=lambda x: x["control"]):
        lines.append(
            f"| `{item['control']}` | `{item['stage']}` | `{item['gate_type']}` | `{item['check_type']}` | `{item['default_gate_result_on_failure']}` | `{item['maturity']}` |"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
