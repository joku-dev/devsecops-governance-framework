#!/usr/bin/env python3
"""Verify one evidence attestation against the report-only pilot registry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from lib.evidence_attestation import assess_attestation, load_trust_roots

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attestation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trust-roots", type=Path, default=ROOT / "model/evidence/evidence-trust-roots.yaml")
    parser.add_argument("--evaluated-at")
    args = parser.parse_args()
    attestation = json.loads(args.attestation.read_text(encoding="utf-8"))
    statement = attestation["statement"]
    result = assess_attestation(
        attestation=attestation, registry=load_trust_roots(args.trust_roots),
        expected_context={key: statement[key] for key in ("repository_id", "commit_id", "run_id", "run_attempt", "artifact_name")},
        expected_subject=statement["subject"],
        evaluated_at=args.evaluated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        attestation_ref=str(args.attestation),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Attestation pilot assessment: {result['status']} ({result['candidate_level']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
