"""Original informational portfolio view, with explicit time and previous data."""
from datetime import datetime, timedelta, timezone
MAX_AGE_DAYS = 30

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

def render_markdown(payload):
    lines = ['# Portfolio Onboarding Status', '', f"Generated: `{payload['generated_at']}`", '', '| Repository | Owner | State | DevSecOps | Architecture | Stale | Next action |', '|---|---|---|---|---|---|---|']
    for row in payload['repositories']:
        dev = row['latest_devsecops']
        arch = row['latest_architecture'] or {'status': 'not in scope'}
        lines.append(f"| `{row['repository_id']}` | {row['owner']} | `{row['adoption_state']}` | `{dev['status']}` | `{arch['status']}` | `{row['stale_or_missing']}` | {row['next_action']} |")
    lines += ['', 'This report is informational and does not approve waivers or change enforcement modes.']
    return '\n'.join(lines) + '\n'


def generate(context, at):
    from lib.result_snapshot_store import explicit_time
    previous_path = context.root / 'generated/reports/portfolio-onboarding-status.json'
    previous = context.json(previous_path) if context.is_file(previous_path) else None
    return build_payload(context.yaml(context.root / 'status/application-repository-integrations.yaml'),
        context.json(context.root / 'status/repository-results-index.json'),
        context.json(context.root / 'status/architecture-results-index.json'), explicit_time(at), previous)
