#!/usr/bin/env python3
"""Generate a flat control traceability CSV from the YAML control library."""

from pathlib import Path
import csv
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
OUT = ROOT / "generated" / "xlsx" / "traceability_matrix.csv"


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

    traceability = load_yaml(MODEL / "traceability" / "control-to-platform.yaml")
    document_catalog = load_yaml(MODEL / "documents" / "governance-documents.yaml")
    document_traceability = load_yaml(MODEL / "traceability" / "document-to-control.yaml")
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {OUT.relative_to(ROOT)} with {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
