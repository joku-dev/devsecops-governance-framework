#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.agent_routing import ROLE_CONTRACTS, evaluate_scenario, normalize_path, routing_reasons  # noqa: E402
from scripts.lib.agent_review import changed_files, prepare_plan, results_template, check_results  # noqa: E402
import jsonschema  # noqa: E402


SOURCE_DOCUMENT_PREFIXES = (
    "docs/governance/source-documents/",
    "model/documents/",
)
DERIVED_GOVERNANCE_PREFIXES = (
    "architecture/",
    "model/controls/",
    "policies/opa/",
    "releases/",
    "schemas/",
)
DEFAULT_USAGE_LOG = ROOT / "generated" / "agent-usage" / "agent-usage.jsonl"
DEFAULT_USAGE_STATE = ROOT / "generated" / "agent-usage" / "recording-state.json"
SKILL_BY_AGENT = {name: role["skill"] for name, role in ROLE_CONTRACTS.items()}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def changed_files_from_git(base_ref: str | None = None) -> list[str]:
    return changed_files(ROOT, base_ref)


def build_dispatch(changed_files: list[str]) -> dict:
    changed_files = sorted({normalize_path(path) for path in changed_files})
    result = evaluate_scenario({"changed_files": changed_files})
    warnings: list[str] = []
    has_source_document_change = any(path.startswith(SOURCE_DOCUMENT_PREFIXES) for path in changed_files)
    has_derived_governance_change = any(path.startswith(DERIVED_GOVERNANCE_PREFIXES) for path in changed_files)
    if has_source_document_change and has_derived_governance_change:
        warnings.append("Derived governance artifact path changed; verify no candidate source was used before review.")
    if result["release_impact"] == "released_baseline":
        warnings.append("Released baseline path changed; release-manager review is mandatory.")

    return {
        "changed_files": changed_files,
        "selected_agents": result["selected_agents"],
        "release_impact": result["release_impact"],
        "required_validations": result["required_validations"],
        "warnings": warnings,
        "selection_reasons": routing_reasons(changed_files),
    }


def build_usage_event(
    dispatch: dict,
    *,
    run_type: str,
    provider: str,
    platform: str,
    source: str,
) -> dict:
    selected_agents = dispatch["selected_agents"]
    return {
        "timestamp": now_utc(),
        "run_type": run_type,
        "provider": provider,
        "platform": platform,
        "source": source,
        "changed_paths": dispatch["changed_files"],
        "selected_agents": selected_agents,
        "skills": [SKILL_BY_AGENT[agent] for agent in selected_agents if agent in SKILL_BY_AGENT],
        "release_impact": dispatch["release_impact"],
        "required_validations": dispatch["required_validations"],
        "warnings": dispatch["warnings"],
    }


def append_usage_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_recording_state(path: Path) -> dict:
    if not path.exists():
        return {"active": False, "mode": "window", "remaining": 0}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path}: invalid recording state: {exc}") from exc
    if not isinstance(state, dict):
        raise RuntimeError(f"{path}: recording state must be a JSON object")
    state.setdefault("active", False)
    state.setdefault("mode", "window")
    state.setdefault("remaining", 0)
    return state


def save_recording_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def activate_recording(state_path: Path, *, count: int, usage_log: Path) -> dict:
    if count <= 0:
        raise RuntimeError("--record-next must be greater than zero")
    state = {
        "active": True,
        "initial_count": count,
        "mode": "window",
        "remaining": count,
        "started_at": now_utc(),
        "usage_log": repo_relative(usage_log),
    }
    save_recording_state(state_path, state)
    return state


def activate_continuous_recording(state_path: Path, *, usage_log: Path) -> dict:
    state = load_recording_state(state_path)
    state.update(
        {
            "active": True,
            "mode": "continuous",
            "remaining": None,
            "started_at": state.get("started_at") or now_utc(),
            "usage_log": repo_relative(usage_log),
        }
    )
    state.pop("completed_at", None)
    save_recording_state(state_path, state)
    return state


def recording_usage_log(state: dict) -> Path:
    usage_log = Path(state.get("usage_log", str(DEFAULT_USAGE_LOG)))
    if not usage_log.is_absolute():
        usage_log = ROOT / usage_log
    return usage_log


def consume_recording_event(state_path: Path, state: dict, event: dict) -> tuple[bool, int | None]:
    if not state.get("active"):
        return False, state.get("remaining")

    if state.get("mode") == "continuous":
        append_usage_event(recording_usage_log(state), event)
        state["last_recorded_at"] = event["timestamp"]
        save_recording_state(state_path, state)
        return True, None

    remaining = int(state.get("remaining", 0) or 0)
    if remaining <= 0:
        return False, remaining

    append_usage_event(recording_usage_log(state), event)
    remaining -= 1
    state["remaining"] = remaining
    state["last_recorded_at"] = event["timestamp"]
    if remaining == 0:
        state["active"] = False
        state["completed_at"] = event["timestamp"]
    save_recording_state(state_path, state)
    return True, remaining


def render_recording_status(state: dict) -> str:
    continuous = state.get("mode") == "continuous"
    status = "active" if state.get("active") and (continuous or int(state.get("remaining", 0) or 0) > 0) else "inactive"
    usage_log = state.get("usage_log", repo_relative(DEFAULT_USAGE_LOG))
    lines = [
        "Governance Agent Usage Recording",
        "",
        f"Status: {status}",
        f"Mode: {state.get('mode', 'window')}",
        f"Usage log: {usage_log}",
    ]
    if continuous:
        lines.append("Remaining runs: continuous")
    else:
        lines.append(f"Remaining runs: {int(state.get('remaining', 0) or 0)}")
    if state.get("started_at"):
        lines.append(f"Started at: {state['started_at']}")
    if state.get("last_recorded_at"):
        lines.append(f"Last recorded at: {state['last_recorded_at']}")
    if state.get("completed_at"):
        lines.append(f"Completed at: {state['completed_at']}")
    return "\n".join(lines) + "\n"


def load_usage_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{path}:{line_number}: invalid JSONL event: {exc}") from exc
    return events


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


def render_usage_summary(summary: dict) -> str:
    def render_counts(title: str, counts: dict[str, int]) -> list[str]:
        lines = [f"{title}:"]
        if counts:
            lines.extend(f"- {name}: {count}" for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])))
        else:
            lines.append("- none")
        return lines

    lines = [
        "Governance Agent Usage Summary",
        "",
        f"Events: {summary['event_count']}",
        "",
    ]
    lines.extend(render_counts("Agent usage", summary["agent_counts"]))
    lines.append("")
    lines.extend(render_counts("Skill usage", summary["skill_counts"]))
    lines.append("")
    lines.extend(render_counts("Provider usage", summary["provider_counts"]))
    lines.append("")
    lines.extend(render_counts("Platform usage", summary["platform_counts"]))
    lines.append("")
    lines.extend(render_counts("Run type usage", summary["run_type_counts"]))
    return "\n".join(lines) + "\n"


def render_text(dispatch: dict) -> str:
    lines = [
        "Governance Agent Dispatch",
        "",
        "Changed files:",
    ]
    if dispatch["changed_files"]:
        lines.extend(f"- {path}" for path in dispatch["changed_files"])
    else:
        lines.append("- none")

    lines.extend(["", "Selected agents:"])
    if dispatch["selected_agents"]:
        lines.extend(f"- {agent}: {', '.join(dispatch['selection_reasons'][agent])}" for agent in dispatch["selected_agents"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            f"Release impact: {dispatch['release_impact']}",
            "",
            "Required validation:",
        ]
    )
    if dispatch["required_validations"]:
        lines.extend(f"- {command}" for command in dispatch["required_validations"])
    else:
        lines.append("- none")

    if dispatch["warnings"]:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in dispatch["warnings"])

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dispatch changed paths to governance agents using the model-neutral routing contract.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Changed repository paths. If omitted, staged/unstaged/untracked Git paths are used.",
    )
    parser.add_argument(
        "--base-ref",
        help="Also include branch changes since this ref's merge base, for example origin/main.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    parser.add_argument(
        "--log-usage",
        action="store_true",
        help="Append this dispatch result to the agent usage JSONL log.",
    )
    parser.add_argument(
        "--usage-log",
        default=str(DEFAULT_USAGE_LOG),
        help="Usage JSONL path for --log-usage or --usage-summary.",
    )
    parser.add_argument(
        "--usage-state",
        default=str(DEFAULT_USAGE_STATE),
        help="Usage recording state path for --record-next or --recording-status.",
    )
    parser.add_argument(
        "--usage-summary",
        action="store_true",
        help="Summarize an agent usage JSONL log instead of running dispatch.",
    )
    parser.add_argument(
        "--record-next",
        type=int,
        help="Automatically record the next N dispatch/provider-review runs.",
    )
    parser.add_argument(
        "--record-continuous",
        action="store_true",
        help="Continuously record future dispatch/provider-review runs until the state is changed.",
    )
    parser.add_argument(
        "--recording-status",
        action="store_true",
        help="Show the current automatic usage recording state.",
    )
    parser.add_argument(
        "--run-type",
        default="dispatch",
        choices=("dispatch", "provider_review"),
        help="Usage event run type when --log-usage is used.",
    )
    parser.add_argument(
        "--provider-review",
        metavar="PROVIDER",
        help="Shortcut for recording this run as a provider_review by PROVIDER, for example codex or mistral.",
    )
    parser.add_argument(
        "--provider",
        default="none",
        help="Usage event provider, for example none, codex, or mistral.",
    )
    parser.add_argument(
        "--platform",
        default="local",
        help="Usage event platform, for example local, github-actions, bitbucket-pipelines, or bamboo.",
    )
    parser.add_argument(
        "--source",
        default="manual",
        help="Usage event source, for example manual, pull-request, ci, or reference-run.",
    )
    parser.add_argument("--plan-output", type=Path, help="Write a revision-bound review plan to a new private JSON file; no agents are executed.")
    parser.add_argument("--results-template", type=Path, help="Write pending role/validation results alongside --plan-output.")
    parser.add_argument("--goal", help="User goal for --plan-output.")
    parser.add_argument("--check-review", type=Path, help="Check a saved plan against declared --review-results and current source bytes.")
    parser.add_argument("--review-results", type=Path, help="Private role results for --check-review.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check_review or args.review_results:
        if not args.check_review or not args.review_results or args.plan_output or args.paths or args.base_ref:
            print("error: --check-review and --review-results must be used together without dispatch inputs", file=sys.stderr)
            return 2
        try:
            report = check_results(ROOT, json.loads(args.check_review.read_text()), json.loads(args.review_results.read_text()))
        except (ValueError, OSError, KeyError, TypeError, jsonschema.ValidationError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["eligible_for_human_review"] else 1
    if (args.results_template or args.goal) and not args.plan_output:
        print("error: --results-template and --goal require --plan-output", file=sys.stderr)
        return 2
    if args.plan_output and (not args.goal or args.log_usage or args.provider_review or args.run_type != "dispatch" or args.record_next is not None or args.record_continuous or args.recording_status or args.usage_summary):
        print("error: --plan-output requires --goal and a dispatch, not an execution/recording operation", file=sys.stderr)
        return 2
    if args.provider_review:
        if args.provider_review == "none":
            print("error: --provider-review must name a real provider such as codex or mistral", file=sys.stderr)
            return 2
        args.run_type = "provider_review"
        args.provider = args.provider_review
        args.log_usage = True

    usage_log = Path(args.usage_log)
    if not usage_log.is_absolute():
        usage_log = ROOT / usage_log
    usage_state = Path(args.usage_state)
    if not usage_state.is_absolute():
        usage_state = ROOT / usage_state

    if args.record_next is not None:
        try:
            state = activate_recording(usage_state, count=args.record_next, usage_log=usage_log)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(state, indent=2, sort_keys=True))
        else:
            print(render_recording_status(state), end="")
        return 0

    if args.record_continuous:
        try:
            state = activate_continuous_recording(usage_state, usage_log=usage_log)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(state, indent=2, sort_keys=True))
        else:
            print(render_recording_status(state), end="")
        return 0

    if args.recording_status:
        try:
            state = load_recording_state(usage_state)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(state, indent=2, sort_keys=True))
        else:
            print(render_recording_status(state), end="")
        return 0

    if args.usage_summary:
        try:
            summary = summarize_usage(load_usage_events(usage_log))
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(render_usage_summary(summary), end="")
        return 0

    try:
        changed_files = args.paths or changed_files_from_git(args.base_ref)
        dispatch = build_dispatch(changed_files)
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.plan_output:
        try:
            outputs = [args.plan_output] + ([args.results_template] if args.results_template else [])
            if len({p.resolve() for p in outputs}) != len(outputs) or any(p.exists() for p in outputs):
                raise ValueError("Plan/result outputs must be distinct new files; existing files are never overwritten")
            if any(p.resolve().is_relative_to(ROOT.resolve()) for p in outputs):
                raise ValueError("Keep private review plans and results outside the repository checkout")
            plan = prepare_plan(ROOT, dispatch, args.goal, base_ref=args.base_ref, explicit_paths=bool(args.paths))
            payloads = [plan] + ([results_template(plan)] if args.results_template else [])
            for path, payload in zip(outputs, payloads):
                path.parent.mkdir(parents=True, exist_ok=True)
                with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        # Preparing a packet must not append to in-repository usage logs after
        # capturing the source snapshot, including when continuous recording is on.
        print(json.dumps(dispatch, indent=2, sort_keys=True) if args.json else render_text(dispatch), end="\n" if args.json else "")
        return 0

    try:
        recording_state = load_recording_state(usage_state)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    recording_active = recording_state.get("active") and (
        recording_state.get("mode") == "continuous" or int(recording_state.get("remaining", 0) or 0) > 0
    )

    if args.log_usage or recording_active:
        event = build_usage_event(
            dispatch,
            run_type=args.run_type,
            provider=args.provider,
            platform=args.platform,
            source=args.source,
        )
        if recording_active:
            consume_recording_event(usage_state, recording_state, event)
        else:
            append_usage_event(usage_log, event)

    if args.json:
        print(json.dumps(dispatch, indent=2, sort_keys=True))
    else:
        print(render_text(dispatch), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
