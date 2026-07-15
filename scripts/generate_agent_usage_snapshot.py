#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dispatch_governance_agents import DEFAULT_USAGE_LOG, load_usage_events, summarize_usage  # noqa: E402


DEFAULT_OUTPUT_JSON = ROOT / "generated" / "agent-usage" / "agent-usage-summary.json"
DEFAULT_OUTPUT_MD = ROOT / "docs" / "operations" / "agent-usage-snapshot-latest.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


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


def build_snapshot(events: list[dict], *, usage_log: Path, generated_at: str, latest_count: int) -> dict:
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
        "source_log": repo_relative(usage_log),
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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate agent usage JSON and Markdown snapshots.")
    parser.add_argument("--usage-log", default=str(DEFAULT_USAGE_LOG), help="Agent usage JSONL log path.")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="Output JSON summary path.")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="Output Markdown snapshot path.")
    parser.add_argument("--latest-count", type=int, default=10, help="Number of latest events to include.")
    parser.add_argument("--generated-at", default="", help="Override generated_at timestamp for repeatable tests.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    usage_log = Path(args.usage_log)
    if not usage_log.is_absolute():
        usage_log = ROOT / usage_log
    output_json = Path(args.output_json)
    if not output_json.is_absolute():
        output_json = ROOT / output_json
    output_md = Path(args.output_md)
    if not output_md.is_absolute():
        output_md = ROOT / output_md

    try:
        events = load_usage_events(usage_log)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    latest_count = max(args.latest_count, 0)
    snapshot = build_snapshot(
        events,
        usage_log=usage_log,
        generated_at=args.generated_at or now_utc(),
        latest_count=latest_count,
    )
    write_json(output_json, snapshot)
    write_text(output_md, render_markdown(snapshot))

    print(f"Wrote {repo_relative(output_json)}")
    print(f"Wrote {repo_relative(output_md)}")
    print(f"- events: {snapshot['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
