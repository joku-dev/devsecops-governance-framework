#!/usr/bin/env python3
"""Check whether a target repository appears to integrate governance CI."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys


ROOT = Path(__file__).resolve().parents[1]


def iter_ci_files(target_repo: Path):
    patterns = [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "*.gitlab-ci.yml",
        "Jenkinsfile",
        "azure-pipelines.yml",
        "azure-pipelines.yaml",
    ]
    seen = set()
    for pattern in patterns:
        for path in target_repo.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def load_texts(paths):
    texts = []
    for path in paths:
        try:
            texts.append((path, path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return texts


def build_check(check_id: str, description: str, passed: bool, details: str):
    return {
        "check_id": check_id,
        "description": description,
        "status": "pass" if passed else "fail",
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--output-file")
    args = parser.parse_args()

    target_repo = Path(args.target_repo).resolve()
    if not target_repo.exists():
        raise SystemExit(f"Target repository not found: {target_repo}")

    ci_files = list(iter_ci_files(target_repo))
    ci_texts = load_texts(ci_files)

    governance_reference_patterns = [
        "devsecops-governance-as-code",
        "validate_governance_repo.py",
        "check_repo_governance_integration.py",
        "governance-compliance-result.json",
    ]
    governance_command_patterns = [
        "validate_governance_repo.py",
        "unittest discover -s tests",
        "opa check",
    ]
    governance_workflow_patterns = [
        "uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-reusable.yml",
        "uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-reusable.yml@",
        "application_evidence_artifact_name:",
        "artifact_path:",
        "sbom_path:",
        "vulnerability_scan_path:",
    ]

    reference_hits = []
    command_hits = []
    workflow_hits = []
    for path, text in ci_texts:
        for pattern in governance_reference_patterns:
            if pattern in text:
                reference_hits.append(f"{path.relative_to(target_repo)} -> {pattern}")
        for pattern in governance_command_patterns:
            if pattern in text:
                command_hits.append(f"{path.relative_to(target_repo)} -> {pattern}")
        for pattern in governance_workflow_patterns:
            if pattern in text:
                workflow_hits.append(f"{path.relative_to(target_repo)} -> {pattern}")

    checks = [
        build_check(
            "governance_ci_file_present",
            "A CI pipeline file is present in the target repository.",
            len(ci_files) > 0,
            "Found CI files: " + ", ".join(str(path.relative_to(target_repo)) for path in ci_files)
            if ci_files
            else "No supported CI files were found.",
        ),
        build_check(
            "governance_reference_present",
            "The target repository references the governance repository or governance templates.",
            len(reference_hits) > 0,
            "; ".join(reference_hits) if reference_hits else "No governance repository or template references found in CI files.",
        ),
        build_check(
            "governance_commands_present",
            "The target repository CI includes expected governance validation commands or a reusable governance workflow integration.",
            len(command_hits) >= 2 or len(workflow_hits) >= 2,
            "; ".join(command_hits + workflow_hits)
            if (command_hits or workflow_hits)
            else "No expected governance command references or reusable governance workflow markers found in CI files.",
        ),
    ]

    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    result = {
        "schema_version": "1.0.0",
        "governance_repo": ROOT.name,
        "target_repo": target_repo.name,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "checks": checks,
    }

    payload = json.dumps(result, indent=2) + "\n"
    if args.output_file:
        output_path = Path(args.output_file)
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        output_path.write_text(payload, encoding="utf-8")
        print(f"Wrote {output_path}")
    else:
        print(payload, end="")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
