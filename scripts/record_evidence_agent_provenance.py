#!/usr/bin/env python3
"""Record an explicit report-only agent-to-evidence provenance association."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json

from lib.result_ledger import canonical_digest, _write_exclusive, _portable_status_path
from lib.identifiers import sanitize_timestamp, slugify_repository


ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_ROOT = ROOT / "status" / "evidence-agent-provenance"
CONFLICT_ROOT = ROOT / "status" / "intake-conflicts" / "evidence-agent-provenance"


def build_record(args: argparse.Namespace) -> dict:
    recorded_at = args.recorded_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    identity = {
        "repository_id": args.repository_id,
        "evidence_type": args.evidence_type,
        "subject_id": args.subject_id,
        "subject_digest": args.subject_digest,
        "agent_id": args.agent_id,
        "dispatch_id": args.dispatch_id,
        "involvement": args.involvement,
    }
    provenance_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "1.0.0",
        "record_type": "evidence-agent-provenance",
        "provenance_id": provenance_id,
        "enforcement": "report_only",
        "recorded_at": recorded_at,
        "evidence": {
            "repository_id": args.repository_id,
            "evidence_type": args.evidence_type,
            "subject_id": args.subject_id,
            "subject_digest": args.subject_digest,
            "source_file": args.source_file,
        },
        "agent": {
            "id": args.agent_id,
            "role_version": args.role_version,
            **({"skill": args.skill} if args.skill else {}),
            **({"provider": args.provider} if args.provider else {}),
            **({"model": args.model} if args.model else {}),
        },
        "involvement": args.involvement,
        "dispatch": {
            "id": args.dispatch_id,
            "run_type": args.run_type,
            "source": args.dispatch_source,
            **({"timestamp": args.dispatch_timestamp} if args.dispatch_timestamp else {}),
        },
        **({"notes": args.notes} if args.notes else {}),
    }


def write_record(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    for existing_path in sorted(path.parent.glob("*.json")):
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if existing.get("provenance_id") != payload["provenance_id"]:
            continue
        if canonical_digest(existing) == canonical_digest(payload):
            return existing_path
        conflict = CONFLICT_ROOT / f"{path.stem}-conflict-{canonical_digest(payload)[:12]}.json"
        if not conflict.exists():
            _write_exclusive(conflict, {
                "schema_version": "1.0.0",
                "conflict_type": "append_only_snapshot_conflict",
                "enforcement": "report_only",
                "detected_at": payload["recorded_at"],
                "target_path": _portable_status_path(existing_path),
                "existing_payload_sha256": canonical_digest(existing),
                "incoming_payload_sha256": canonical_digest(payload),
                "existing_evidence_identity": {"provenance_id": payload["provenance_id"]},
                "incoming_evidence_identity": {"provenance_id": payload["provenance_id"]},
            })
        return existing_path
    _write_exclusive(path, payload)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--evidence-type", required=True)
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--subject-digest", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--role-version", default="1.0.0")
    parser.add_argument("--skill", default="")
    parser.add_argument("--provider", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--involvement", choices=["selected", "executed", "reviewed", "approved"], required=True)
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--run-type", choices=["dispatch", "provider_review", "manual"], default="manual")
    parser.add_argument("--dispatch-source", required=True)
    parser.add_argument("--dispatch-timestamp", default="")
    parser.add_argument("--recorded-at", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    payload = build_record(args)
    output_dir = PROVENANCE_ROOT / slugify_repository(args.repository_id)
    output = output_dir / f"{sanitize_timestamp(payload['recorded_at'])}-{payload['provenance_id'][:12]}.json"
    write_record(output, payload)
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
