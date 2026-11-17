"""Original read-only committed intake-health projection, with explicit clock."""
from datetime import datetime, timedelta, timezone
import math
from lib.collection_attempts import project_collection_attempt_lifecycle
DEFAULT_WINDOW_DAYS = 30

def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)

def utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def nearest_rank(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100) * len(ordered)))
    return ordered[rank - 1]

def event_metrics(events: list[dict]) -> dict:
    total = len(events)
    counts = {
        status: sum(event.get("status") == status for event in events)
        for status in ("success", "partial", "failed")
    }
    durations = [event["duration_ms"] for event in events]
    return {
        "total": total,
        **counts,
        "success_rate_pct": round((counts["success"] / total) * 100, 2) if total else 0.0,
        "failure_rate_pct": (
            round(((counts["partial"] + counts["failed"]) / total) * 100, 2)
            if total
            else 0.0
        ),
        "duration_ms": {
            "minimum": min(durations) if durations else None,
            "p50": nearest_rank(durations, 50),
            "p95": nearest_rank(durations, 95),
            "maximum": max(durations) if durations else None,
        },
    }

def dimension_value(event: dict, dimension: str) -> str:
    if dimension == "collector":
        collector = event.get("collector", {})
        return f"{collector.get('id', 'unknown')}@{collector.get('version', 'unknown')}"
    return str(event.get(dimension, "unknown"))

def build_dimensions(events: list[dict]) -> list[dict]:
    rows = []
    for dimension in ("repository_id", "collector", "intake_type", "evidence_type"):
        values = sorted({dimension_value(event, dimension) for event in events})
        for value in values:
            selected = [event for event in events if dimension_value(event, dimension) == value]
            rows.append({
                "dimension": dimension,
                "value": value,
                "metrics": event_metrics(selected),
            })
    return rows

def build_latest_results(indexes: dict[str, dict], as_of: datetime) -> list[dict]:
    rows = []
    for domain, index in sorted(indexes.items()):
        for repository in index.get("repositories", []):
            latest = repository.get("latest_result", {})
            generated_at = latest.get("generated_at")
            run_id = latest.get("pipeline_run_id")
            source_file = latest.get("source_file")
            if not generated_at or not run_id or not source_file:
                continue
            age_ms = max(0, int((as_of - parse_timestamp(generated_at)).total_seconds() * 1000))
            rows.append({
                "domain": domain,
                "repository_id": repository["repository_id"],
                "run_id": str(run_id),
                "generated_at": generated_at,
                "age_ms": age_ms,
                "source_file": source_file,
            })
    return sorted(rows, key=lambda row: (row["repository_id"], row["domain"]))

def build_payload(
    *,
    events: list[dict],
    attempts: list[dict],
    snapshots: list[dict],
    intake_conflict_count: int,
    indexes: dict[str, dict],
    as_of: datetime,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict:
    if window_days < 1:
        raise ValueError("window_days must be at least 1")
    as_of = as_of.astimezone(timezone.utc)
    window_start = as_of - timedelta(days=window_days)
    observed_events = [
        event
        for event in events
        if window_start <= parse_timestamp(event["completed_at"]) <= as_of
    ]
    lifecycle = project_collection_attempt_lifecycle(attempts, snapshots)
    lifecycle_counts = {
        state: sum(item.get("lifecycle", {}).get("state") == state for item in lifecycle)
        for state in ("open", "resolved", "permanent")
    }
    return {
        "schema_version": "1.0.0",
        "projection_type": "intake-health",
        "generated_at": utc_timestamp(as_of),
        "enforcement": "report_only",
        "observation_status": "observed" if observed_events else "no_data",
        "window": {
            "days": window_days,
            "started_at": utc_timestamp(window_start),
            "ended_at": utc_timestamp(as_of),
        },
        "summary": {
            "events": event_metrics(observed_events),
            "collection_attempts": {"total": len(lifecycle), **lifecycle_counts},
            "intake_conflicts": intake_conflict_count,
        },
        "dimensions": build_dimensions(observed_events),
        "latest_results": build_latest_results(indexes, as_of),
        "source_files": [
            "status/intake-events/",
            "status/collection-attempts/",
            "status/intake-conflicts/",
            "status/repository-results-index.json",
            "status/architecture-results-index.json",
            "status/typed-evidence-results-index.json",
        ],
    }


INDEX_NAMES = {'devsecops': 'repository-results-index.json',
               'architecture': 'architecture-results-index.json', 'typed_evidence': 'typed-evidence-results-index.json'}
SNAPSHOT_NAMES = ('results', 'architecture-results', 'typed-evidence-results')


def records(context, prefix):
    return [dict(context.json(context.root / name), _source_file=name)
            for name in sorted(context.files) if name.startswith(prefix + '/') and name.endswith('.json')]


def generate(context, at, window_days=30):
    from lib.result_snapshot_store import explicit_time
    if type(window_days) is not int or window_days < 1:
        raise ValueError('invalid_intake_health_window')
    indexes = {domain: context.json(context.root / 'status' / name)
               if context.is_file(context.root / 'status' / name) else {'repositories': []}
               for domain, name in INDEX_NAMES.items()}
    try:
        return build_payload(events=records(context, 'status/intake-events'),
            attempts=records(context, 'status/collection-attempts'),
            snapshots=[row for directory in SNAPSHOT_NAMES for row in records(context, 'status/' + directory)],
            intake_conflict_count=sum(name.startswith('status/intake-conflicts/') and name.endswith('.json')
                                      for name in context.files), indexes=indexes,
            as_of=explicit_time(at), window_days=window_days)
    except OverflowError:
        raise ValueError('invalid_intake_health_window') from None
