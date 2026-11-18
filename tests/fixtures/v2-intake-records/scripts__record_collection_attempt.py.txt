#!/usr/bin/env python3
"""Persist a report-only failed or partial GitHub Actions collection attempt."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys

from intake_github_actions_run import DEFAULT_API_URL, api_repo_path, github_get_json
from lib.result_ledger import write_collection_attempt_append_only
from lib.identifiers import sanitize_timestamp, slugify_repository


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_ROOT = ROOT / "status" / "collection-attempts"
CONFLICT_ROOT = ROOT / "status" / "intake-conflicts" / "collection-attempts"


def build_attempt(*, repository_id: str, run: dict, evidence_type: str, collector_id: str,
                  collector_version: str, artifact_name: str, status: str, code: str,
                  message: str, retryable: bool, additional_errors: list[dict] | None = None) -> dict:
    attempted_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    source = {
        "provider": "github_actions",
        "run_id": str(run.get("id", "unknown")),
        "run_attempt": run.get("run_attempt"),
        "workflow_name": run.get("name", "unknown"),
        "commit_id": run.get("head_sha", "unknown"),
        "artifact_name": artifact_name,
        "source_uri": run.get("html_url", ""),
    }
    identity = {
        "repository_id": repository_id,
        "evidence_type": evidence_type,
        "collector": {"id": collector_id, "version": collector_version},
        "source": source,
    }
    attempt_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "1.0.0",
        "record_type": "evidence-collection-attempt",
        "attempt_id": attempt_id,
        "enforcement": "report_only",
        "status": status,
        "repository_id": repository_id,
        "evidence_type": evidence_type,
        "collector": {"id": collector_id, "version": collector_version},
        "attempted_at": attempted_at,
        "source": source,
        "errors": [
            {"code": code, "message": message, "retryable": retryable},
            *(additional_errors or []),
        ],
    }


def load_run_metadata(*, api_url: str, repository_id: str, run_id: str, token: str | None) -> tuple[dict, list[dict]]:
    try:
        run = github_get_json(f"{api_url.rstrip('/')}{api_repo_path(repository_id)}/actions/runs/{run_id}", token)
        return run, []
    except Exception:
        print("warning: GitHub run metadata unavailable; recording the failed attempt with fallback identity", file=sys.stderr)
        return {
            "id": str(run_id),
            "run_attempt": None,
            "name": "metadata-unavailable",
            "head_sha": "unknown",
            "html_url": f"https://github.com/{repository_id}/actions/runs/{run_id}",
        }, [{
            "code": "source_metadata_unavailable",
            "message": "Authoritative GitHub Actions run metadata could not be retrieved during failure recording.",
            "retryable": True,
        }]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-type", required=True)
    parser.add_argument("--collector-id", required=True)
    parser.add_argument("--collector-version", default="0.1.0")
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--status", choices=["partial", "failed"], default="failed")
    parser.add_argument("--error-code", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--retryable", action="store_true")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--token", default="")
    args = parser.parse_args()
    token = args.token or os.environ.get("GH_RESULT_INTAKE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    run, metadata_errors = load_run_metadata(
        api_url=args.api_url,
        repository_id=args.repository_id,
        run_id=args.run_id,
        token=token,
    )
    payload = build_attempt(
        repository_id=args.repository_id, run=run, evidence_type=args.evidence_type,
        collector_id=args.collector_id, collector_version=args.collector_version,
        artifact_name=args.artifact_name, status=args.status, code=args.error_code,
        message=args.message, retryable=args.retryable, additional_errors=metadata_errors,
    )
    output_dir = ATTEMPT_ROOT / slugify_repository(args.repository_id)
    output = output_dir / f"{sanitize_timestamp(payload['attempted_at'])}-run-{args.run_id}-{args.evidence_type}.json"
    write_collection_attempt_append_only(output, payload, conflict_root=CONFLICT_ROOT)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
