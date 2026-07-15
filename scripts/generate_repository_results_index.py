#!/usr/bin/env python3
"""Aggregate repository governance results into a central index."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "results"
INDEX_PATH = ROOT / "status" / "repository-results-index.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    repositories = []
    result_count = 0
    passing_results = 0
    failing_results = 0
    mainline_results = 0
    branch_results = 0
    manual_results = 0

    for repo_dir in sorted(path for path in STATUS_RESULTS.iterdir() if path.is_dir()):
        results = sorted(repo_dir.glob("*.json"))
        if not results:
            continue
        parsed = [load_json(path) for path in results]
        parsed.sort(key=lambda item: item.get("generated_at", ""))
        latest = parsed[-1]
        latest_main = None
        for item in reversed(parsed):
            if item.get("repository", {}).get("branch") == "main" and item.get("pipeline", {}).get("event") == "push":
                latest_main = item
                break
        representative = latest_main or latest
        result_count += len(parsed)
        for item in parsed:
            if item.get("overall_status") == "pass":
                passing_results += 1
            else:
                failing_results += 1
            if item.get("pipeline", {}).get("event") == "workflow_dispatch":
                manual_results += 1
            elif item.get("repository", {}).get("branch") == "main":
                mainline_results += 1
            else:
                branch_results += 1
        history = []
        for item, path in zip(parsed, results):
            control_summary = item.get("control_evaluation_summary", {})
            history.append(
                {
                    "generated_at": item.get("generated_at", ""),
                    "status": item.get("overall_status", "unknown"),
                    "pipeline_run_id": item.get("pipeline", {}).get("pipeline_run_id", "unknown"),
                    "pipeline_event": item.get("pipeline", {}).get("event", "unknown"),
                    "pipeline_url": item.get("pipeline", {}).get("pipeline_url", ""),
                    "branch": item.get("repository", {}).get("branch", "unknown"),
                    "commit_id": item.get("repository", {}).get("commit_id", "unknown"),
                    "governance_baseline_ref": item.get("governance_baseline_ref", "unknown"),
                    "control_evaluation_summary": control_summary,
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
        repositories.append(
            {
                "repository_id": latest["repository_id"],
                "baseline_level": representative.get("baseline_level", "unknown"),
                "results_path": f"status/results/{repo_dir.name}/",
                "latest_result": {
                    "status": representative.get("overall_status", "unknown"),
                    "pipeline_run_id": representative.get("pipeline", {}).get("pipeline_run_id", "unknown"),
                    "commit_id": representative.get("repository", {}).get("commit_id", "unknown"),
                    "generated_at": representative.get("generated_at", ""),
                    "governance_baseline_ref": representative.get("governance_baseline_ref", "unknown"),
                    "source_file": next(
                        str(path.relative_to(ROOT))
                        for path, item in zip(results, parsed)
                        if item == representative
                    ),
                    "control_evaluation_summary": representative.get("control_evaluation_summary", {}),
                },
                "history": history,
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {
            "repository_count": len(repositories),
            "result_count": result_count,
            "passing_results": passing_results,
            "failing_results": failing_results,
            "mainline_results": mainline_results,
            "branch_results": branch_results,
            "manual_results": manual_results,
        },
        "repositories": repositories,
    }
    INDEX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
