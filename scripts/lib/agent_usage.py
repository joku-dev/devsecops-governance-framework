"""Original declared agent-selection metadata counts; no actual execution inference."""
from collections import Counter
import json

def summarize_usage(events: list[dict]) -> dict:
    agent_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    run_type_counts: Counter[str] = Counter()

    for event in events:
        agent_counts.update(event.get("selected_agents", []))
        skill_counts.update(event.get("skills", []))
        provider_counts.update([event.get("provider", "unknown")])
        platform_counts.update([event.get("platform", "unknown")])
        run_type_counts.update([event.get("run_type", "unknown")])

    return {
        "event_count": len(events),
        "agent_counts": dict(sorted(agent_counts.items())),
        "skill_counts": dict(sorted(skill_counts.items())),
        "provider_counts": dict(sorted(provider_counts.items())),
        "platform_counts": dict(sorted(platform_counts.items())),
        "run_type_counts": dict(sorted(run_type_counts.items())),
    }

def sorted_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))

def change_area(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "unknown"
    if parts[0] in {"scripts", "schemas", "tests", "status", "releases"}:
        return parts[0]
    if parts[0] in {"docs", "generated", "policies"} and len(parts) >= 2:
        return "/".join(parts[:2])
    if parts[0] == "pipeline-baseline" and len(parts) >= 3:
        return "/".join(parts[:3])
    if parts[0] == ".agents" and len(parts) >= 2:
        return "/".join(parts[:2])
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]

def latest_event_summary(event: dict) -> dict:
    changed_paths = event.get("changed_paths", [])
    return {
        "timestamp": event.get("timestamp", ""),
        "run_type": event.get("run_type", "unknown"),
        "provider": event.get("provider", "unknown"),
        "platform": event.get("platform", "unknown"),
        "source": event.get("source", "unknown"),
        "release_impact": event.get("release_impact", "unknown"),
        "selected_agents": event.get("selected_agents", []),
        "changed_path_count": len(changed_paths),
        "changed_areas": sorted({change_area(path) for path in changed_paths}),
        "warnings": event.get("warnings", []),
    }

def build_snapshot(events: list[dict], *, source_log_label: str, generated_at: str, latest_count: int) -> dict:
    base_summary = summarize_usage(events)
    change_area_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()

    for event in events:
        change_area_counts.update(change_area(path) for path in event.get("changed_paths", []))
        warning_counts.update(event.get("warnings", []))

    timestamps = [event.get("timestamp", "") for event in events if event.get("timestamp")]
    latest_events = [latest_event_summary(event) for event in events[-latest_count:]]

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "source_log": source_log_label,
        "metadata_only": True,
        "event_count": base_summary["event_count"],
        "first_event_at": min(timestamps) if timestamps else "",
        "last_event_at": max(timestamps) if timestamps else "",
        "agent_counts": base_summary["agent_counts"],
        "skill_counts": base_summary["skill_counts"],
        "provider_counts": base_summary["provider_counts"],
        "platform_counts": base_summary["platform_counts"],
        "run_type_counts": base_summary["run_type_counts"],
        "change_area_counts": sorted_counts(change_area_counts),
        "warning_counts": sorted_counts(warning_counts),
        "latest_events": latest_events,
    }

def table_lines(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    if rows:
        lines.extend("| " + " | ".join(row) + " |" for row in rows)
    else:
        lines.append("| none |" + " none |" * (len(headers) - 1))
    return lines

def count_rows(counts: dict[str, int]) -> list[list[str]]:
    return [[name, str(count)] for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]

def render_markdown(snapshot: dict) -> str:
    lines = [
        "# Agent Usage Snapshot Latest",
        "",
        f"Generated at: `{snapshot['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Source log: `{snapshot['source_log']}`",
        f"- Events: `{snapshot['event_count']}`",
        f"- First event: `{snapshot['first_event_at'] or 'n/a'}`",
        f"- Last event: `{snapshot['last_event_at'] or 'n/a'}`",
        "- Data handling: metadata-only; no prompts, secrets, file contents, or model responses are stored.",
        "",
        "## Agent Usage",
        "",
    ]
    lines.extend(table_lines(["Agent", "Count"], count_rows(snapshot["agent_counts"])))
    lines.extend(["", "## Skill Usage", ""])
    lines.extend(table_lines(["Skill", "Count"], count_rows(snapshot["skill_counts"])))
    lines.extend(["", "## Provider Usage", ""])
    lines.extend(table_lines(["Provider", "Count"], count_rows(snapshot["provider_counts"])))
    lines.extend(["", "## Platform Usage", ""])
    lines.extend(table_lines(["Platform", "Count"], count_rows(snapshot["platform_counts"])))
    lines.extend(["", "## Run Type Usage", ""])
    lines.extend(table_lines(["Run type", "Count"], count_rows(snapshot["run_type_counts"])))
    lines.extend(["", "## Frequent Change Areas", ""])
    lines.extend(table_lines(["Change area", "Count"], count_rows(snapshot["change_area_counts"])))
    lines.extend(["", "## Warnings", ""])
    lines.extend(table_lines(["Warning", "Count"], count_rows(snapshot["warning_counts"])))

    latest_rows = []
    for event in snapshot["latest_events"]:
        latest_rows.append(
            [
                event["timestamp"],
                event["run_type"],
                event["provider"],
                event["platform"],
                ", ".join(event["selected_agents"]) or "none",
                event["release_impact"],
                str(event["changed_path_count"]),
                ", ".join(event["changed_areas"]) or "none",
            ]
        )

    lines.extend(["", "## Latest Runs", ""])
    lines.extend(
        table_lines(
            ["Timestamp", "Type", "Provider", "Platform", "Agents", "Impact", "Paths", "Areas"],
            latest_rows,
        )
    )
    lines.append("")
    return "\n".join(lines)

def files(events, source_log_label, at, latest_count):
    value = build_snapshot(events, source_log_label=source_log_label, generated_at=at, latest_count=max(latest_count, 0))
    return {'result.json': json.dumps(value, indent=2, sort_keys=True) + '\n', 'result.md': render_markdown(value)}
