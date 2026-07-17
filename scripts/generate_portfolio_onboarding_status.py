#!/usr/bin/env python3
"""Generate a portfolio onboarding status report from the integration registry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "status" / "application-repository-integrations.yaml"
DEVSECOPS = ROOT / "status" / "repository-results-index.json"
ARCHITECTURE = ROOT / "status" / "architecture-results-index.json"
OUTPUT_JSON = ROOT / "generated" / "reports" / "portfolio-onboarding-status.json"
OUTPUT_MD = ROOT / "generated" / "reports" / "portfolio-onboarding-status.md"
MAX_AGE_DAYS = 30


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def by_repository(index: dict) -> dict[str, dict]:
    return {item["repository_id"]: item for item in index.get("repositories", [])}


def parse_timestamp(timestamp: str) -> datetime | None:
    if not timestamp:
        return None
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def freshness(timestamp: str, now: datetime) -> dict:
    produced_at = parse_timestamp(timestamp)
    if produced_at is None:
        return {"status": "missing", "stale_after": None}
    stale_after = produced_at + timedelta(days=MAX_AGE_DAYS)
    return {
        "status": "stale" if now > stale_after else "current",
        "stale_after": stale_after.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def build_payload(registry: dict, devsecops_index: dict, architecture_index: dict, now: datetime, previous: dict | None = None) -> dict:
    devsecops = by_repository(devsecops_index)
    architecture = by_repository(architecture_index)
    rows = []
    for entry in registry.get("integrations", []):
        repository_id = entry["repository"]
        dev = devsecops.get(repository_id, {}).get("latest_result", {})
        arch = architecture.get(repository_id, {}).get("latest_result", {})
        dev_freshness = freshness(dev.get("generated_at", ""), now)
        arch_freshness = freshness(arch.get("generated_at", ""), now) if arch else None
        stale = dev_freshness["status"] != "current"
        state = "pilot" if entry.get("governance_mode") == "report-only" else "active"
        rows.append({
            "repository_id": repository_id,
            "owner": entry.get("owner", "missing"),
            "action_owner": entry.get("action_owner", "missing"),
            "business_or_product_area": entry.get("business_or_product_area", "unspecified"),
            "adoption_state": state,
            "target_devsecops_baseline": entry.get("governance_workflow_ref", "unknown"),
            "latest_devsecops": {
                "status": dev.get("status", "missing"),
                "run_id": dev.get("pipeline_run_id"),
                "generated_at": dev.get("generated_at"),
                "freshness": dev_freshness,
            },
            "architecture_in_scope": bool(arch),
            "target_architecture_baseline": arch.get("architecture_baseline_ref", "unknown") if arch else None,
            "latest_architecture": {
                "status": arch.get("status", "missing"),
                "run_id": arch.get("pipeline_run_id"),
                "generated_at": arch.get("generated_at"),
                "freshness": arch_freshness,
            } if arch else None,
            "stale_or_missing": stale,
            "governance_mode": entry.get("governance_mode", "unknown"),
            "next_action": "Review report-only findings" if entry.get("governance_mode") == "report-only" else "Maintain accepted mainline evidence",
        })
    payload = {
        "schema_version": "2.0.0",
        "generated_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {
            "repository_count": len(rows),
            "stale_or_missing_count": sum(row["stale_or_missing"] for row in rows),
            "report_only_count": sum(row["governance_mode"] == "report-only" for row in rows),
            "active_count": sum(row["adoption_state"] == "active" for row in rows),
        },
        "repositories": rows,
    }
    if previous and previous.get("summary") == payload["summary"] and previous.get("repositories") == payload["repositories"]:
        payload["generated_at"] = previous.get("generated_at", payload["generated_at"])
    return payload


def main() -> int:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    previous = load(OUTPUT_JSON) if OUTPUT_JSON.exists() else None
    payload = build_payload(registry, load(DEVSECOPS), load(ARCHITECTURE), now, previous)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = ["# Portfolio Onboarding Status", "", f"Generated: `{payload['generated_at']}`", "", "| Repository | Owner | State | DevSecOps | Architecture | Stale | Next action |", "|---|---|---|---|---|---|---|"]
    for row in payload["repositories"]:
        dev = row["latest_devsecops"]
        arch = row["latest_architecture"] or {"status": "not in scope"}
        lines.append(f"| `{row['repository_id']}` | {row['owner']} | `{row['adoption_state']}` | `{dev['status']}` | `{arch['status']}` | `{row['stale_or_missing']}` | {row['next_action']} |")
    lines += ["", "This report is informational and does not approve waivers or change enforcement modes."]
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
