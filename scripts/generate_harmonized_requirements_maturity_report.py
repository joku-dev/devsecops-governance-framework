#!/usr/bin/env python3
"""Generate non-normative maturity decision support for harmonized requirements."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "model" / "requirements" / "harmonized-devsecops-requirements.yaml"
MAPPING_PATH = ROOT / "model" / "traceability" / "harmonized-requirements-to-maturity-levels.yaml"
JSON_OUTPUT = ROOT / "generated" / "reports" / "harmonized-requirements-maturity.json"
MD_OUTPUT = ROOT / "generated" / "reports" / "harmonized-requirements-maturity.md"
LEVELS = ("L1", "L2", "L3", "GOV")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_report(model: dict, mapping: dict) -> dict:
    requirements = {item["id"]: item for item in model["requirements"]}
    minimum_counts = Counter(item["minimum_level"] for item in mapping["mappings"])
    routing_counts = Counter(item["routing_lane"] for item in mapping["mappings"])
    cumulative_counts = {
        level: sum(level in item["maturity_path"] for item in mapping["mappings"])
        for level in ("L1", "L2", "L3")
    }
    cumulative_counts["GOV"] = minimum_counts["GOV"]

    items = []
    for assignment in mapping["mappings"]:
        requirement = requirements[assignment["requirement_id"]]
        items.append(
            {
                "requirement_id": requirement["id"],
                "title": requirement["title"],
                "domain": requirement["domain"],
                "applicability": requirement["applicability"],
                "minimum_level": assignment["minimum_level"],
                "maturity_path": assignment["maturity_path"],
                "governance_overlay": assignment["governance_overlay"],
                "routing_lane": assignment["routing_lane"],
                "assignment_basis": assignment["assignment_basis"],
                "current_coverage": requirement["coverage"]["status"],
                "existing_refs": requirement["coverage"]["refs"],
                "rationale": assignment["rationale"],
                "review_status": assignment["review_status"],
            }
        )

    return {
        "schema_version": "0.1.0",
        "report_id": "harmonized-requirements-candidate-maturity",
        "status": "candidate",
        "normative": False,
        "enforcement": "none",
        "source_document_id": mapping["source_document_id"],
        "summary": {
            "harmonized_requirements": len(items),
            "minimum_level_counts": {level: minimum_counts[level] for level in LEVELS},
            "cumulative_level_counts": {level: cumulative_counts[level] for level in LEVELS},
            "routing_lane_counts": dict(sorted(routing_counts.items())),
            "human_review_required": sum(item["review_status"] == "human_review_required" for item in items),
        },
        "level_definitions": mapping["level_definitions"],
        "maturity_by_requirement": items,
        "decision_boundary": mapping["decision_boundary"],
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Harmonized Requirements Candidate Maturity Assignment",
        "",
        "This report is non-normative decision support. It assigns proposed minimum maturity levels but does not change controls, baselines, evidence contracts, policy, enforcement, releases, or consumer compliance state.",
        "",
        "## Level Model",
        "",
        "| Level | Name | Intent | Introduced | Cumulative active |",
        "|---|---|---|---:|---:|",
    ]
    for level in LEVELS:
        definition = report["level_definitions"][level]
        lines.append(
            f"| `{level}` | {definition['name']} | {definition['intent']} | "
            f"{summary['minimum_level_counts'][level]} | {summary['cumulative_level_counts'][level]} |"
        )

    lines.extend(
        [
            "",
            "Levels are cumulative: an L1 requirement remains active at L2 and L3; an L2 requirement remains active at L3. GOV is a cross-level overlay and is counted separately. Applicability remains an independent decision, so a capability-based requirement applies only when the relevant capability exists.",
            "",
            "## Routing Lanes",
            "",
            "| Routing lane | Requirements |",
            "|---|---:|",
        ]
    )
    for lane, count in summary["routing_lane_counts"].items():
        lines.append(f"| `{lane}` | {count} |")

    lines.extend(
        [
            "",
            "## Proposed Assignments",
            "",
            "| ID | Requirement | Minimum | Path | Applicability | Route | Current coverage | Existing refs |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["maturity_by_requirement"]:
        path = " → ".join(item["maturity_path"])
        refs = ", ".join(f"`{ref}`" for ref in item["existing_refs"]) or "-"
        lines.append(
            f"| `{item['requirement_id']}` | {item['title']} | `{item['minimum_level']}` | "
            f"{path} | `{item['applicability']}` | `{item['routing_lane']}` | "
            f"`{item['current_coverage']}` | {refs} |"
        )

    lines.extend(["", "## Assignment Rationales", ""])
    for item in report["maturity_by_requirement"]:
        lines.append(
            f"- `{item['requirement_id']}` **{item['title']}** — {item['rationale']} "
            f"Review: `{item['review_status']}`."
        )

    lines.extend(
        [
            "",
            "## Human Review Checklist",
            "",
            "- [ ] Confirm the minimum level for every requirement.",
            "- [ ] Confirm that risk- and capability-based applicability remains independent of maturity.",
            "- [ ] Confirm GOV as the cross-level overlay for lifecycle, applicability, roles, and controlled documentation.",
            "- [ ] Confirm routing to Governance, DevSecOps Baseline, Architecture, Product Security, Platform, Evidence, or Operations.",
            "- [ ] Confirm whether partial and gap items require new controls or only stronger evidence and verification.",
            "- [ ] Record any authorized derivation in a separate governance change and release decision.",
            "",
            "## Decision Boundary",
            "",
            "Every assignment requires human review. This candidate report does not authorize changes to runtime governance or released baselines.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report(load_yaml(MODEL_PATH), load_yaml(MAPPING_PATH))
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    MD_OUTPUT.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {JSON_OUTPUT.relative_to(ROOT)}")
    print(f"Wrote {MD_OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
