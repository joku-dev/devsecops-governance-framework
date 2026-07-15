#!/usr/bin/env python3
"""Generate an open gap report for governance model follow-up."""

from pathlib import Path
import csv
import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "model"
CSV_OUT = ROOT / "generated" / "xlsx" / "open_gap_report.csv"
MD_OUT = ROOT / "generated" / "reports" / "open-gap-report.md"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def collect_controls():
    controls = {}
    for path in sorted((MODEL / "controls").glob("dscb-*.yaml")):
        data = load_yaml(path)
        level = data.get("level")
        for requirement in data.get("requirements", []):
            controls[requirement["id"]] = {
                **requirement,
                "level": level,
                "source_file": str(path.relative_to(ROOT)),
            }
    return controls


def main() -> int:
    controls = collect_controls()
    documents = load_yaml(MODEL / "documents" / "governance-documents.yaml").get("documents", [])
    capabilities = load_yaml(MODEL / "platform" / "platform-capabilities.yaml").get("capabilities", [])
    waiver_authorities = load_yaml(MODEL / "waivers" / "waiver-authorities.yaml").get("authorities", {})
    waiver_schema = load_yaml(ROOT / "schemas" / "waiver.schema.json")

    rows = []

    for document in documents:
        if document["status"] == "draft":
            rows.append(
                {
                    "gap_id": f"GAP-DOC-{document['id']}",
                    "category": "governance_document_status",
                    "severity": "medium",
                    "subject": document["id"],
                    "location": document["repository_path"],
                    "summary": f"{document['title']} is still in draft status.",
                    "recommended_action": "Review, approve, and update the catalog status once the document is formally adopted.",
                }
            )

    for capability in capabilities:
        if capability.get("area") == "TBD":
            rows.append(
                {
                    "gap_id": f"GAP-CAP-{capability['id']}",
                    "category": "platform_capability_model",
                    "severity": "medium",
                    "subject": capability["id"],
                    "location": "model/platform/platform-capabilities.yaml",
                    "summary": f"Platform capability {capability['id']} still uses placeholder area 'TBD'.",
                    "recommended_action": "Assign the capability to a concrete architectural area for governance and ownership reporting.",
                }
            )

    for control_id, control in controls.items():
        verification_method = control.get("verification", {}).get("method")
        policy = control.get("policy_as_code", {})
        if verification_method == "automated" and not policy.get("candidate"):
            rows.append(
                {
                    "gap_id": f"GAP-POL-{control_id}",
                    "category": "policy_automation_candidate",
                    "severity": "low",
                    "subject": control_id,
                    "location": control["source_file"],
                    "summary": f"{control_id} uses automated verification but is not yet modeled as a policy-as-code candidate.",
                    "recommended_action": "Review whether this control should remain evidence-only or be promoted into an executable policy candidate.",
                }
            )

    schema_risk_levels = set(waiver_schema["properties"]["risk_classification"]["enum"])
    authority_risk_levels = set(waiver_authorities.keys())

    for risk_level in sorted(schema_risk_levels - authority_risk_levels):
        rows.append(
            {
                "gap_id": f"GAP-WAIVER-AUTH-{risk_level}",
                "category": "waiver_governance",
                "severity": "high",
                "subject": risk_level,
                "location": "model/waivers/waiver-authorities.yaml",
                "summary": f"Waiver schema allows risk classification {risk_level} but no approval authority is defined.",
                "recommended_action": "Add an explicit approval authority for the missing risk classification.",
            }
        )

    for risk_level in sorted(authority_risk_levels - schema_risk_levels):
        rows.append(
            {
                "gap_id": f"GAP-WAIVER-SCHEMA-{risk_level}",
                "category": "waiver_governance",
                "severity": "high",
                "subject": risk_level,
                "location": "schemas/waiver.schema.json",
                "summary": f"Waiver authorities define risk classification {risk_level} but the waiver schema does not allow it.",
                "recommended_action": "Align the waiver schema with the defined approval authority model.",
            }
        )

    rows.sort(key=lambda item: (item["severity"], item["category"], item["subject"]))

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    severity_counts = {
        "high": sum(1 for row in rows if row["severity"] == "high"),
        "medium": sum(1 for row in rows if row["severity"] == "medium"),
        "low": sum(1 for row in rows if row["severity"] == "low"),
    }
    lines = [
        "# Open Gap Report",
        "",
        f"Gap Count: `{len(rows)}`",
        f"High: `{severity_counts['high']}`",
        f"Medium: `{severity_counts['medium']}`",
        f"Low: `{severity_counts['low']}`",
        "",
        "| Gap | Category | Severity | Subject | Location | Summary | Recommended Action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['gap_id']}` | `{row['category']}` | `{row['severity']}` | "
            f"`{row['subject']}` | `{row['location']}` | {row['summary']} | {row['recommended_action']} |"
        )

    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {CSV_OUT.relative_to(ROOT)} with {len(rows)} rows")
    print(f"Wrote {MD_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
