#!/usr/bin/env python3
"""Intake and centrally reverify typed Evidence Trust from a GitHub Actions run."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
import argparse
import json
import os
import sys
import tempfile
import zipfile

from intake_github_actions_run import (
    DEFAULT_API_URL,
    api_repo_path,
    artifact_size_bytes,
    conclusion_to_status,
    download_artifact_with_gh,
    github_download,
    github_get_json,
)
from lib.evidence_trust import compute_sha256, load_freshness_policy, verify_trust_capture
from lib.identifiers import sanitize_timestamp, slugify_repository
from lib.json_io import load_json, write_json


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "typed-evidence-results"
FRESHNESS_POLICY_PATH = ROOT / "model" / "evidence" / "evidence-freshness-policies.yaml"
VERIFIER_ID = "central-evidence-trust-intake/v1"


def find_unique_file(root: Path, relative_path: Path) -> Path:
    preferred = root / relative_path
    if preferred.is_file():
        return preferred
    matches = sorted(root.rglob(relative_path.name))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one {relative_path.name} in typed evidence artifact")
    return matches[0]


def find_trust_record(extract_dir: Path) -> Path:
    return find_unique_file(extract_dir, Path("governance/vulnerability-scan-trust.json"))


def resolve_subject_paths(trust: dict, extract_dir: Path) -> dict[str, Path]:
    capture = trust.get("capture", {})
    if capture.get("evidence_type") != "vulnerability_scan":
        raise ValueError("Typed evidence intake currently supports vulnerability_scan only")
    subject_ids = {subject.get("id") for subject in capture.get("subjects", [])}
    expected_ids = {"vulnerability_scan_report", "evaluated_artifact"}
    if subject_ids != expected_ids:
        raise ValueError("Vulnerability Trust must contain the scan report and evaluated artifact subjects")

    scan_path = find_unique_file(extract_dir, Path("security/vulnerability-scan.json"))
    evaluated_name = (
        capture.get("observations", {})
        .get("subject_binding", {})
        .get("evaluated_subject")
    )
    if not isinstance(evaluated_name, str) or not evaluated_name:
        raise ValueError("Vulnerability Trust must identify the evaluated subject filename")
    evaluated_matches = sorted(extract_dir.rglob(evaluated_name))
    if len(evaluated_matches) != 1:
        raise FileNotFoundError(f"Expected exactly one evaluated subject named {evaluated_name}")
    return {
        "vulnerability_scan_report": scan_path,
        "evaluated_artifact": evaluated_matches[0],
    }


def centrally_verify_trust(
    trust: dict,
    *,
    repository_id: str,
    run: dict,
    artifact_name: str,
    extract_dir: Path,
    verified_at: str,
) -> dict:
    policy = load_freshness_policy(FRESHNESS_POLICY_PATH, "freshness-vulnerability-scan-24h")
    return verify_trust_capture(
        trust,
        repository_id=repository_id,
        commit_id=run.get("head_sha", "unknown"),
        run_id=str(run.get("id")),
        artifact_name=artifact_name,
        subject_paths=resolve_subject_paths(trust, extract_dir),
        verified_at=verified_at,
        freshness_policy=policy,
        produced_at=trust.get("capture", {}).get("produced_at"),
        verifier_id=VERIFIER_ID,
    )


def write_snapshot(
    *,
    repository_id: str,
    run: dict,
    artifact: dict,
    trust: dict,
    archive_sha256: str | None,
) -> Path:
    generated_at = run.get("updated_at") or run.get("created_at")
    payload = {
        "schema_version": "1.0.0",
        "result_type": "typed-evidence-trust",
        "repository_id": repository_id,
        "evidence_type": trust.get("capture", {}).get("evidence_type", "unknown"),
        "generated_at": generated_at,
        "pipeline": {
            "pipeline_name": run.get("name", "unknown"),
            "pipeline_run_id": str(run.get("id")),
            "pipeline_url": run.get("html_url", ""),
            "event": run.get("event", "unknown"),
            "status": conclusion_to_status(run.get("conclusion")),
            "run_attempt": run.get("run_attempt"),
        },
        "repository": {
            "branch": run.get("head_branch", "unknown"),
            "commit_id": run.get("head_sha", "unknown"),
        },
        "source_artifact": {
            "name": artifact.get("name", "unknown"),
            "artifact_id": str(artifact.get("id", "unknown")),
            "size_bytes": artifact_size_bytes(artifact),
            "archive_download_url": artifact.get("archive_download_url", ""),
            "archive_sha256": archive_sha256,
        },
        "trust": trust,
    }
    output_dir = STATUS_RESULTS / slugify_repository(repository_id)
    output_path = output_dir / f"{sanitize_timestamp(generated_at)}-run-{run.get('id')}-vulnerability-scan.json"
    write_json(output_path, payload)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--artifact-name", default="application-evidence")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    token = args.token or os.environ.get("GH_RESULT_INTAKE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    api_url = args.api_url.rstrip("/")
    repo_path = api_repo_path(args.repository_id)
    run = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}", token)
    artifacts_payload = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}/artifacts?per_page=100", token)
    artifact = next(
        (item for item in artifacts_payload.get("artifacts", []) if item.get("name") == args.artifact_name),
        None,
    )
    if artifact is None:
        raise FileNotFoundError(f"Artifact {args.artifact_name!r} not found for run {args.run_id}")

    with tempfile.TemporaryDirectory(prefix="typed-evidence-intake-") as tempdir:
        temp = Path(tempdir)
        archive = temp / "artifact.zip"
        extract_dir = temp / "artifact"
        extract_dir.mkdir()
        try:
            github_download(artifact["archive_download_url"], archive, token)
        except HTTPError as error:
            if error.code not in {401, 403, 404} or not download_artifact_with_gh(
                args.repository_id,
                args.run_id,
                args.artifact_name,
                extract_dir,
                token,
            ):
                raise RuntimeError(
                    "Could not download typed evidence artifact. Configure GH_RESULT_INTAKE_TOKEN "
                    f"with Actions read access for {args.repository_id}."
                ) from error
        if archive.exists():
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(extract_dir)
        producer_trust = load_json(find_trust_record(extract_dir))
        verified_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        trust = centrally_verify_trust(
            producer_trust,
            repository_id=args.repository_id,
            run=run,
            artifact_name=args.artifact_name,
            extract_dir=extract_dir,
            verified_at=verified_at,
        )
        output = write_snapshot(
            repository_id=args.repository_id,
            run=run,
            artifact=artifact,
            trust=trust,
            archive_sha256=compute_sha256(archive) if archive.exists() else None,
        )
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
