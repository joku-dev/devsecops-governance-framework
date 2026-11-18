#!/usr/bin/env python3
"""Generate architecture runtime governance traceability CSV."""

from pathlib import Path
import csv

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "generated" / "csv" / "architecture_runtime_traceability.csv"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    rows = []

    for path in sorted((ROOT / "architecture").glob("arch-*.yaml")):
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

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
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

    print(f"Generated {OUTPUT.relative_to(ROOT)}")
    print(f"- architecture requirements: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
