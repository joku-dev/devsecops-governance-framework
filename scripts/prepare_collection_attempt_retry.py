#!/usr/bin/env python3
"""Validate a collection-attempt record and prepare a controlled intake retry."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import re

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
ATTEMPT_ROOT = ROOT / "status" / "collection-attempts"
SCHEMA_PATH = ROOT / "schemas" / "evidence-collection-attempt.schema.json"
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
RUN_ID_PATTERN = re.compile(r"^[0-9]+$")
ARTIFACT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

RETRY_ROUTES = {
    ("governance_result", "central-governance-intake", "governance-control-evaluation"): "intake-governance-result.yml",
    ("governance_result", "central-governance-intake", "architecture-governance-evidence"): "intake-architecture-result.yml",
    ("vulnerability_scan", "central-vulnerability-scan-collector", "application-evidence"): "intake-evidence-trust.yml",
}


def load_attempt(attempt_path: str, *, attempt_root: Path = ATTEMPT_ROOT) -> dict:
    root = attempt_root.resolve()
    requested = Path(attempt_path)
    path = requested.resolve() if requested.is_absolute() else (ROOT / requested).resolve()
    if not path.is_relative_to(root) or path.suffix != ".json":
        raise ValueError("attempt_path must name a JSON record below status/collection-attempts")
    if not path.is_file():
        raise ValueError(f"collection-attempt record does not exist: {attempt_path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
    return payload


def build_retry_plan(attempt: dict) -> dict:
    errors = attempt.get("errors", [])
    if not errors or not all(error.get("retryable") is True for error in errors):
        raise ValueError("collection attempt contains a non-retryable error")

    repository_id = attempt["repository_id"]
    run_id = str(attempt["source"]["run_id"])
    artifact_name = attempt["source"]["artifact_name"]
    collector_id = attempt["collector"]["id"]
    route_key = (attempt["evidence_type"], collector_id, artifact_name)
    workflow = RETRY_ROUTES.get(route_key)
    if workflow is None:
        raise ValueError("collection attempt does not match a supported retry route")
    if not REPOSITORY_PATTERN.fullmatch(repository_id):
        raise ValueError("repository_id is not safe for workflow dispatch")
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id is not safe for workflow dispatch")
    if not ARTIFACT_PATTERN.fullmatch(artifact_name):
        raise ValueError("artifact_name is not safe for workflow dispatch")

    return {
        "workflow": workflow,
        "repository_id": repository_id,
        "run_id": run_id,
        "artifact_name": artifact_name,
        "attempt_id": attempt["attempt_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-path", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args()
    plan = build_retry_plan(load_attempt(args.attempt_path))
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as output:
            for key, value in plan.items():
                output.write(f"{key}={value}\n")
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
