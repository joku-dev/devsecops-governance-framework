#!/usr/bin/env python3
"""Evaluate a validated semantic report against a bounded curated catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class SemanticEvaluationError(ValueError):
    pass


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SemanticEvaluationError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise SemanticEvaluationError(f"expected JSON object: {path}")
    return value


def require_schema(value: dict, schema_path: Path, label: str) -> None:
    errors = sorted(Draft202012Validator(read_json(schema_path)).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise SemanticEvaluationError(f"{label} schema error at {location}: {errors[0].message}")


def evidence_keys(finding: dict) -> set[tuple[str, str]]:
    return {
        (item["source_id"], item["locator"]["value"])
        for item in finding["evidence"]
    }


def evaluate(catalog: dict, report: dict) -> dict:
    scope_match = (
        report["scope"]["source_manifest_sha256"] == catalog["source_manifest_sha256"]
        and set(report["scope"]["source_ids"]) == set(catalog["source_ids"])
    )
    eligible = [
        item for item in report["findings"]
        if item["evidence_status"] == "valid" and item["disposition"] != "quarantined"
    ]
    rows = []
    required_detected = 0
    required_total = sum(case["expectation"] == "must_detect" for case in catalog["cases"])
    prohibited_triggered = 0
    if scope_match:
        for case in catalog["cases"]:
            required = {(item["source_id"], item["locator"]) for item in case["required_evidence"]}
            matches = [
                item["finding_id"] for item in eligible
                if item["category"] == case["category"] and required.issubset(evidence_keys(item))
            ]
            if case["expectation"] == "must_detect":
                passed = bool(matches)
                required_detected += int(passed)
            else:
                passed = not matches
                prohibited_triggered += int(not passed)
            rows.append({
                "case_id": case["case_id"],
                "expectation": case["expectation"],
                "result": "pass" if passed else "fail",
                "matching_finding_ids": matches,
            })
        failed = sum(item["result"] == "fail" for item in rows)
        status = "pass" if failed == 0 else "fail"
    else:
        rows = [{
            "case_id": case["case_id"],
            "expectation": case["expectation"],
            "result": "not_applicable",
            "matching_finding_ids": [],
        } for case in catalog["cases"]]
        failed = 0
        status = "not_applicable"

    result = {
        "schema_version": "1.0.0",
        "report_type": "document_consistency_semantic_evaluation_report",
        "catalog_id": catalog["catalog_id"],
        "review_id": report["review_id"],
        "status": status,
        "scope_match": scope_match,
        "summary": {
            "case_count": len(rows),
            "passed": sum(item["result"] == "pass" for item in rows),
            "failed": failed,
            "required_detected": required_detected,
            "required_total": required_total,
            "prohibited_triggered": prohibited_triggered,
            "eligible_finding_count": len(eligible),
        },
        "cases": rows,
        "limitations": list(catalog["limitations"]) + [
            "Metrics are bounded catalog counts, not population-level recall, precision or false-positive rates."
        ],
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        catalog = read_json(args.catalog)
        report = read_json(args.report)
        require_schema(catalog, ROOT / "schemas/document-consistency-semantic-evaluation-catalog.schema.json", "catalog")
        require_schema(report, ROOT / "schemas/document-consistency-semantic-report.schema.json", "semantic report")
        result = evaluate(catalog, report)
        require_schema(result, ROOT / "schemas/document-consistency-semantic-evaluation-report.schema.json", "evaluation report")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result["summary"], sort_keys=True))
    except (OSError, SemanticEvaluationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
