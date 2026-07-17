#!/usr/bin/env python3
"""Persist one report-only central intake operation event."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os

from lib.identifiers import sanitize_timestamp, slugify_repository
from lib.result_ledger import write_intake_event_append_only


ROOT = Path(__file__).resolve().parents[1]
EVENT_ROOT = ROOT / "status" / "intake-events"
CONFLICT_ROOT = ROOT / "status" / "intake-conflicts" / "intake-events"


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Intake timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_event(
    *,
    repository_id: str,
    downstream_run_id: str,
    evidence_type: str,
    collector_id: str,
    collector_version: str,
    artifact_name: str,
    intake_type: str,
    status: str,
    started_at: str,
    completed_at: str,
    intake_repository_id: str,
    intake_workflow_name: str,
    intake_run_id: str,
    intake_run_attempt: int,
    trigger_event: str,
    error_code: str | None = None,
    message: str | None = None,
) -> dict:
    started = parse_timestamp(started_at)
    completed = parse_timestamp(completed_at)
    if completed < started:
        raise ValueError("completed_at must not be earlier than started_at")
    if status == "success" and (error_code or message):
        raise ValueError("successful intake events must not contain an error")
    if status != "success" and not (error_code and message):
        raise ValueError("partial and failed intake events require an error code and message")

    identity = {
        "repository_id": repository_id,
        "intake_type": intake_type,
        "evidence_type": evidence_type,
        "collector": {"id": collector_id, "version": collector_version},
        "source": {"run_id": str(downstream_run_id), "artifact_name": artifact_name},
        "intake": {
            "repository_id": intake_repository_id,
            "workflow_name": intake_workflow_name,
            "run_id": str(intake_run_id),
            "run_attempt": intake_run_attempt,
        },
    }
    event_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    duration_ms = int((completed - started).total_seconds() * 1000)
    return {
        "schema_version": "1.0.0",
        "record_type": "intake-operation-event",
        "event_id": event_id,
        "enforcement": "report_only",
        "status": status,
        "intake_type": intake_type,
        "repository_id": repository_id,
        "evidence_type": evidence_type,
        "collector": {"id": collector_id, "version": collector_version},
        "started_at": utc_timestamp(started),
        "completed_at": utc_timestamp(completed),
        "duration_ms": duration_ms,
        "source": {
            "provider": "github_actions",
            "run_id": str(downstream_run_id),
            "artifact_name": artifact_name,
            "source_uri": f"https://github.com/{repository_id}/actions/runs/{downstream_run_id}",
        },
        "intake": {
            "provider": "github_actions",
            "repository_id": intake_repository_id,
            "workflow_name": intake_workflow_name,
            "run_id": str(intake_run_id),
            "run_attempt": intake_run_attempt,
            "trigger_event": trigger_event,
            "source_uri": f"https://github.com/{intake_repository_id}/actions/runs/{intake_run_id}",
        },
        "errors": [] if status == "success" else [{"code": error_code, "message": message}],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--run-id", required=True, help="Downstream GitHub Actions run ID")
    parser.add_argument("--evidence-type", required=True)
    parser.add_argument("--collector-id", required=True)
    parser.add_argument("--collector-version", default="0.1.0")
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument(
        "--intake-type",
        choices=["devsecops_governance", "architecture_governance", "typed_evidence"],
        required=True,
    )
    parser.add_argument("--status", choices=["success", "partial", "failed"], required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--completed-at", default="")
    parser.add_argument("--intake-repository-id", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--intake-workflow-name", default=os.environ.get("GITHUB_WORKFLOW", ""))
    parser.add_argument("--intake-run-id", default=os.environ.get("GITHUB_RUN_ID", ""))
    parser.add_argument("--intake-run-attempt", type=int, default=int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")))
    parser.add_argument("--trigger-event", default=os.environ.get("GITHUB_EVENT_NAME", "unknown"))
    parser.add_argument("--error-code")
    parser.add_argument("--message")
    args = parser.parse_args()
    for field in ("intake_repository_id", "intake_workflow_name", "intake_run_id"):
        if not getattr(args, field):
            parser.error(f"--{field.replace('_', '-')} or its GitHub environment value is required")

    completed_at = args.completed_at or utc_timestamp(datetime.now(timezone.utc))
    payload = build_event(
        repository_id=args.repository_id,
        downstream_run_id=args.run_id,
        evidence_type=args.evidence_type,
        collector_id=args.collector_id,
        collector_version=args.collector_version,
        artifact_name=args.artifact_name,
        intake_type=args.intake_type,
        status=args.status,
        started_at=args.started_at,
        completed_at=completed_at,
        intake_repository_id=args.intake_repository_id,
        intake_workflow_name=args.intake_workflow_name,
        intake_run_id=args.intake_run_id,
        intake_run_attempt=args.intake_run_attempt,
        trigger_event=args.trigger_event,
        error_code=args.error_code,
        message=args.message,
    )
    output_dir = EVENT_ROOT / slugify_repository(args.repository_id)
    output = output_dir / (
        f"{sanitize_timestamp(payload['started_at'])}-intake-"
        f"{payload['event_id'][:12]}-{args.evidence_type}.json"
    )
    write_intake_event_append_only(output, payload, conflict_root=CONFLICT_ROOT)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
