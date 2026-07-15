#!/usr/bin/env python3
"""Aggregate typed Evidence Trust results without changing governance outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from lib.evidence_trust import project_trust


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "typed-evidence-results"
INDEX_PATH = ROOT / "status" / "typed-evidence-results-index.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_result(trust: dict, check_id: str) -> str:
    for check in trust.get("checks", []):
        if check.get("id") == check_id:
            return check.get("result", "not_evaluated")
    return "not_evaluated"


def project_result(item: dict, source_file: Path) -> dict:
    trust = item.get("trust", {})
    capture = trust.get("capture", {})
    observations = capture.get("observations", {})
    binding = observations.get("subject_binding", {})
    return {
        "generated_at": item.get("generated_at", ""),
        "evidence_type": item.get("evidence_type", "unknown"),
        "pipeline_run_id": item.get("pipeline", {}).get("pipeline_run_id", "unknown"),
        "pipeline_event": item.get("pipeline", {}).get("event", "unknown"),
        "pipeline_url": item.get("pipeline", {}).get("pipeline_url", ""),
        "branch": item.get("repository", {}).get("branch", "unknown"),
        "commit_id": item.get("repository", {}).get("commit_id", "unknown"),
        "collector_status": capture.get("status", "unknown"),
        "enforcement": capture.get("enforcement", "report_only"),
        "scanner": observations.get("scanner", {}),
        "finding_count": observations.get("finding_count", 0),
        "max_severity": observations.get("observed_max_severity", "unknown"),
        "severity_consistent": observations.get("severity_consistent"),
        "subject_binding": {
            "mode": binding.get("mode", "unknown"),
            "scanner_attested": binding.get("scanner_attested", False),
        },
        "freshness": check_result(trust, "freshness_evaluated"),
        "content_integrity": check_result(trust, "content_digest_verified"),
        "trust": project_trust(item),
        "source_file": str(source_file.relative_to(ROOT)),
    }


def main() -> int:
    repositories = []
    result_count = 0
    mainline_results = 0
    branch_results = 0
    manual_results = 0
    freshness_failures = 0
    trust_level_counts: dict[str, int] = {}

    if STATUS_RESULTS.exists():
        repo_dirs = sorted(path for path in STATUS_RESULTS.iterdir() if path.is_dir())
    else:
        repo_dirs = []
    for repo_dir in repo_dirs:
        paths = sorted(repo_dir.glob("*.json"))
        parsed = [(load_json(path), path) for path in paths]
        parsed.sort(key=lambda pair: pair[0].get("generated_at", ""))
        if not parsed:
            continue
        result_count += len(parsed)
        projections = []
        for item, path in parsed:
            projection = project_result(item, path)
            projections.append(projection)
            level = projection["trust"]["effective_level"]
            trust_level_counts[level] = trust_level_counts.get(level, 0) + 1
            if projection["freshness"] == "fail":
                freshness_failures += 1
            if projection["pipeline_event"] == "workflow_dispatch":
                manual_results += 1
            elif projection["branch"] == "main" and projection["pipeline_event"] == "push":
                mainline_results += 1
            else:
                branch_results += 1
        latest = projections[-1]
        latest_main = next(
            (
                projection
                for projection in reversed(projections)
                if projection["branch"] == "main" and projection["pipeline_event"] == "push"
            ),
            None,
        )
        repositories.append(
            {
                "repository_id": parsed[-1][0].get("repository_id", "unknown"),
                "results_path": f"status/typed-evidence-results/{repo_dir.name}/",
                "latest_result": latest_main or latest,
                "history": projections,
            }
        )

    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": {
            "repository_count": len(repositories),
            "result_count": result_count,
            "mainline_results": mainline_results,
            "branch_results": branch_results,
            "manual_results": manual_results,
            "freshness_failures": freshness_failures,
            "trust_level_counts": trust_level_counts,
        },
        "repositories": repositories,
    }
    INDEX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {INDEX_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
