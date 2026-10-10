#!/usr/bin/env python3
"""Create a one-time, redacted public projection from private DCR inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.document_consistency_view import PUBLIC_SNAPSHOT, build_redacted_snapshot


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_decisions(report: dict, manifest: dict, manifest_path: Path, paths: list[Path]) -> None:
    schema = load_json(ROOT / "schemas/document-consistency-human-decision.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if not paths:
        raise ValueError("no human decision artifacts supplied")
    found = set()
    for path in paths:
        decision = load_json(path)
        validator.validate(decision)
        finding = next((item for item in report["findings"] if item["finding_id"] == decision["finding_id"]), None)
        if finding is None:
            raise ValueError(f"decision references unknown finding: {decision['finding_id']}")
        finding_hash = hashlib.sha256(
            json.dumps(finding, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if decision["review_id"] != report["review_id"]:
            raise ValueError("decision review ID does not match report")
        if decision["source_manifest_sha256"] != manifest_hash:
            raise ValueError("decision source manifest hash does not match supplied manifest")
        if decision["finding_sha256"] != finding_hash:
            raise ValueError(f"decision finding hash does not match: {decision['finding_id']}")
        if decision["finding_id"] in found:
            raise ValueError(f"duplicate decision for finding: {decision['finding_id']}")
        found.add(decision["finding_id"])
    if found != {item["finding_id"] for item in report["findings"]}:
        raise ValueError("human decisions do not cover every report finding")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="Private validated semantic report JSON")
    parser.add_argument("--manifest", type=Path, required=True, help="Private source manifest JSON")
    parser.add_argument("--decision", type=Path, action="append", required=True, help="Hash-bound decision JSON; repeat per finding")
    parser.add_argument("--comparison-count", type=int, required=True, help="Number of targeted comparisons; no exhaustive denominator")
    args = parser.parse_args()
    report = load_json(args.report)
    manifest = load_json(args.manifest)
    validate_decisions(report, manifest, args.manifest, args.decision)
    snapshot = build_redacted_snapshot(ROOT, report, manifest, args.manifest.read_bytes(), args.comparison_count)
    target = ROOT / PUBLIC_SNAPSHOT
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote redacted projection: {target.relative_to(ROOT)}")
    print(f"Review: {snapshot['review_id']} · status: {snapshot['overall_status']} · freshness: {snapshot['freshness']['status']}")
    print("Private report, manifest and decisions were not copied.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"projection refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
