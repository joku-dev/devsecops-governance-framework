#!/usr/bin/env python3
"""Generate document-to-control authority reports from governance YAML."""

from pathlib import Path
import csv
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
CSV_OUT = ROOT / "generated" / "xlsx" / "document_control_matrix.csv"
MD_OUT = ROOT / "generated" / "reports" / "document-control-matrix.md"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    controls = {}
    for path in sorted((MODEL / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        level = data.get("level")
        for requirement in data.get("requirements", []):
            controls[requirement["id"]] = {
                **requirement,
                "level": level,
            }

    documents = load_yaml(MODEL / "documents" / "governance-documents.yaml").get("documents", [])
    mappings = load_yaml(MODEL / "traceability" / "document-to-control.yaml").get("mappings", [])
    document_by_id = {item["id"]: item for item in documents}

    rows = []
    for mapping in mappings:
        document = document_by_id[mapping["document_id"]]
        control_ids = set(mapping.get("control_ids", []))
        control_levels = set(mapping.get("control_levels", []))

        matched_controls = []
        for control_id, control in controls.items():
            if control_id in control_ids or control["level"] in control_levels:
                matched_controls.append((control_id, control))

        matched_controls.sort(key=lambda item: item[0])
        for control_id, control in matched_controls:
            rows.append(
                {
                    "document_id": document["id"],
                    "document_type": document["type"],
                    "document_title": document["title"],
                    "document_status": document["status"],
                    "control_id": control_id,
                    "control_level": control["level"],
                    "control_domain": control["domain"],
                    "control_title": control["title"],
                    "rationale": mapping["rationale"],
                }
            )

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Document To Control Authority Matrix",
        "",
        f"Document Count: `{len(documents)}`",
        f"Mapped Rows: `{len(rows)}`",
        "",
        "| Document | Type | Control | Level | Domain | Rationale |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['document_id']}` {row['document_title']} | `{row['document_type']}` | "
            f"`{row['control_id']}` {row['control_title']} | `{row['control_level']}` | "
            f"`{row['control_domain']}` | {row['rationale']} |"
        )

    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {CSV_OUT.relative_to(ROOT)} with {len(rows)} rows")
    print(f"Wrote {MD_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
