#!/usr/bin/env python3
"""Generate a flat governance traceability CSV for Policy and Directive requirements."""

from pathlib import Path
import csv
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "xlsx" / "governance_traceability_matrix.csv"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    rows = []
    for path in [
        ROOT / "governance" / "policy-requirements.yaml",
        ROOT / "governance" / "directive-requirements.yaml",
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
