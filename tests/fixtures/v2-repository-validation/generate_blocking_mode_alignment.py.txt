#!/usr/bin/env python3
"""Assess current enforcement modes against Blocking Readiness without changing them."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BLOCKING_MODES = {"block-on-error", "waiver-required"}
UNSAFE_ALIGNMENTS = {"unapproved_blocking", "legacy_risk_expired", "legacy_risk_incomplete"}


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include timezone: {value}")
    return parsed


def failed_gap_ids(readiness: dict) -> list[str]:
    return sorted(
        item["id"]
        for item in readiness.get("criteria", [])
        if item.get("required") and item.get("status") not in {"pass", "not_applicable"}
    )


def assess(*, integrations: dict, readiness: dict, alignment_model: dict, as_of: str) -> dict:
    introduced_at = parse_timestamp(alignment_model["model_introduced_at"])
    evaluated_at = parse_timestamp(as_of)
    if evaluated_at < introduced_at:
        raise ValueError("Alignment assessment cannot predate model introduction")
    readiness_by_repo = {item["repository_id"]: item for item in readiness.get("repositories", [])}
    records = {item["repository_id"]: item for item in alignment_model.get("legacy_risk_records", [])}
    rows = []
    known_repositories = set()

    for integration in sorted(integrations.get("integrations", []), key=lambda item: item["repository"]):
        repository_id = integration["repository"]
        known_repositories.add(repository_id)
        mode = integration.get("governance_mode", "unknown")
        blocking = mode in BLOCKING_MODES
        current = readiness_by_repo.get(repository_id, {})
        technical_ready = current.get("technical_ready") is True
        manual_approval = current.get("manual_approval", "pending")
        gaps = failed_gap_ids(current)
        record = records.get(repository_id)
        alignment = "nonblocking"
        activation_valid = False
        record_ref = None
        review_due = None
        reason = "Current mode does not block and requires no legacy risk record."

        if blocking and technical_ready and manual_approval == "approved":
            alignment = "aligned_blocking"
            activation_valid = True
            reason = "Blocking has technical readiness and accountable approval."
        elif blocking and record is None:
            alignment = "unapproved_blocking"
            reason = "Blocking lacks readiness and has no traceable preexisting-mode risk record."
        elif blocking:
            record_ref = f"model/enforcement/blocking-mode-alignment.yaml#{repository_id}"
            review_due = record.get("review_due")
            observed = parse_timestamp(record["mode_observed_at"])
            due = parse_timestamp(review_due)
            recorded_gaps = set(record.get("required_gap_ids", []))
            complete = (
                record.get("current_mode") == mode
                and record.get("enforcement_change_authorized") is False
                and record.get("disposition") == "preserve_without_new_approval"
                and observed < introduced_at
                and set(gaps).issubset(recorded_gaps)
            )
            if not complete:
                alignment = "legacy_risk_incomplete"
                reason = "Legacy record does not match mode, predates-model evidence, or current readiness gaps."
            elif due < evaluated_at:
                alignment = "legacy_risk_expired"
                reason = "Legacy mode risk review is overdue."
            else:
                alignment = "legacy_risk_active"
                reason = "Preexisting blocking is visible under a time-bounded risk review; this is not a new approval."

        rows.append({
            "repository_id": repository_id,
            "current_mode": mode,
            "blocking": blocking,
            "technical_ready": technical_ready,
            "manual_approval": manual_approval,
            "alignment": alignment,
            "blocking_activation_valid": activation_valid,
            "gap_ids": gaps,
            "risk_record_ref": record_ref,
            "review_due": review_due,
            "reason": reason,
        })

    orphaned = sorted(set(records) - known_repositories)
    unsafe = sum(item["alignment"] in UNSAFE_ALIGNMENTS for item in rows)
    alignment_status = "controlled" if unsafe == 0 and not orphaned else "review_required"
    return {
        "schema_version": "0.1.0",
        "projection_type": "blocking-mode-alignment",
        "generated_at": as_of,
        "enforcement": "report_only",
        "enforcement_change_authorized": False,
        "alignment_status": alignment_status,
        "summary": {
            "repositories": len(rows),
            "nonblocking": sum(item["alignment"] == "nonblocking" for item in rows),
            "aligned_blocking": sum(item["alignment"] == "aligned_blocking" for item in rows),
            "legacy_risk_active": sum(item["alignment"] == "legacy_risk_active" for item in rows),
            "unsafe_blocking": unsafe,
            "orphaned_legacy_records": len(orphaned),
        },
        "repositories": rows,
        "orphaned_legacy_records": orphaned,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", help="Timezone-aware assessment time; defaults to current UTC time")
    args = parser.parse_args()
    integrations = yaml.safe_load((ROOT / "status/application-repository-integrations.yaml").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "generated/reports/blocking-readiness.json").read_text(encoding="utf-8"))
    model = yaml.safe_load((ROOT / "model/enforcement/blocking-mode-alignment.yaml").read_text(encoding="utf-8"))
    as_of = args.as_of or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = assess(integrations=integrations, readiness=readiness, alignment_model=model, as_of=as_of)
    output = ROOT / "generated/reports/blocking-mode-alignment.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {output.relative_to(ROOT)}: {result['alignment_status']}, "
        f"{result['summary']['legacy_risk_active']} legacy risk, "
        f"{result['summary']['unsafe_blocking']} unsafe"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
