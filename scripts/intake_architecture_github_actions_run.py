#!/usr/bin/env python3
"""Intake a downstream Architecture Runtime Governance GitHub Actions run."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from lib.identifiers import sanitize_timestamp, slugify_repository
from lib.evidence_trust import (
    build_trust_capture,
    digest_subject,
    load_freshness_policy,
    verify_trust_capture,
)
from lib.json_io import load_json
from lib.result_ledger import apply_replay_assessment, load_snapshot_payloads, write_snapshot_append_only


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "architecture-results"
INTAKE_CONFLICTS = ROOT / "status" / "intake-conflicts" / "architecture"
TRUST_RESULT_ROOTS = (
    ROOT / "status" / "results",
    ROOT / "status" / "architecture-results",
    ROOT / "status" / "typed-evidence-results",
)
DEFAULT_API_URL = "https://api.github.com"
FRESHNESS_POLICY_PATH = ROOT / "model" / "evidence" / "evidence-freshness-policies.yaml"


def github_get_json(url: str, token: str | None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "architecture-governance-result-intake",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def github_download(url: str, destination: Path, token: str | None) -> None:
    headers = {
        "User-Agent": "architecture-governance-result-intake",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        destination.write_bytes(response.read())


def api_repo_path(repository_id: str) -> str:
    owner, repo = repository_id.split("/", 1)
    return f"/repos/{quote(owner)}/{quote(repo)}"


def conclusion_to_status(value: str | None) -> str:
    if value == "success":
        return "success"
    if value in {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}:
        return "failure"
    if value:
        return value
    return "unknown"


def branch_protection(api_url: str, repository_id: str, branch: str, token: str | None) -> bool:
    url = f"{api_url}{api_repo_path(repository_id)}/branches/{quote(branch, safe='')}"
    try:
        payload = github_get_json(url, token)
    except Exception:
        return False
    return bool(payload.get("protected"))


def find_json(extract_dir: Path, filename: str) -> Path:
    preferred = extract_dir / filename
    if preferred.is_file():
        return preferred
    matches = sorted(extract_dir.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"{filename} not found in architecture governance artifact")
    return matches[0]


def download_artifact_with_gh(repository_id: str, run_id: str, artifact_name: str, destination: Path, token: str | None) -> bool:
    if not shutil.which("gh"):
        return False
    destination.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if token:
        env.setdefault("GH_TOKEN", token)
    result = subprocess.run(
        [
            "gh",
            "run",
            "download",
            run_id,
            "--repo",
            repository_id,
            "--name",
            artifact_name,
            "--dir",
            str(destination),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return True


def architecture_evidence_flags(release_input: dict) -> dict:
    architecture = release_input.get("architecture", {})
    return {
        "release_input": True,
        "architecture_report": True,
        "marker_assessments": len(architecture.get("marker_assessments", [])),
        "release_compatibility_declaration": bool(architecture.get("release_compatibility_declaration", {}).get("exists")),
        "solution_baseline": bool(architecture.get("solution_baseline", {}).get("exists")),
        "compatibility_evidence": bool(architecture.get("compatibility_evidence", {}).get("exists")),
        "security_evidence": bool(architecture.get("security_evidence", {}).get("exists")),
        "deployment_evidence": bool(architecture.get("deployment_evidence", {}).get("exists")),
        "runtime_evidence": bool(architecture.get("runtime_evidence", {}).get("exists")),
        "review_evidence": bool(architecture.get("review_evidence", {}).get("exists")),
        "exception_evidence": bool(architecture.get("exception_evidence", {}).get("exists")),
        "feedback_evidence": bool(architecture.get("feedback_evidence", {}).get("exists")),
        "exceptions": len(architecture.get("exceptions", [])),
    }


def write_snapshot(
    *,
    repository_id: str,
    architecture_baseline_ref: str,
    run: dict,
    report: dict,
    release_input: dict,
    branch_protected: bool,
    artifact_metadata: dict,
    trust: dict,
    notes: str,
) -> Path:
    summary = report.get("summary", {})
    finding_count = summary.get("finding_count", 0)
    overall_status = "pass" if run.get("conclusion") == "success" and finding_count == 0 else "findings"
    generated_at = run.get("updated_at") or run.get("created_at")
    branch = run.get("head_branch", "unknown")

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repository_id,
        "architecture_baseline_ref": architecture_baseline_ref,
        "governance_repository": "joku-dev/devsecops-governance-framework",
        "result_type": "architecture-runtime-governance-run",
        "generated_at": generated_at,
        "pipeline": {
            "pipeline_name": run.get("name", "Architecture Runtime Governance"),
            "pipeline_run_id": str(run.get("id")),
            "pipeline_url": run.get("html_url", ""),
            "event": run.get("event", "unknown"),
            "status": conclusion_to_status(run.get("conclusion")),
        },
        "repository": {
            "branch": branch,
            "branch_protected": branch_protected,
            "commit_id": run.get("head_sha", "unknown"),
        },
        "target": report.get("target", {}),
        "checks": {
            "architecture_runtime_governance": conclusion_to_status(run.get("conclusion")),
        },
        "evidence": architecture_evidence_flags(release_input),
        "artifact_metadata": artifact_metadata,
        "trust": trust,
        "architecture_summary": summary,
        "gates": report.get("gates", []),
        "overall_status": overall_status,
        "notes": notes,
    }

    repo_dir = STATUS_RESULTS / slugify_repository(repository_id)
    output_path = repo_dir / f"{sanitize_timestamp(generated_at)}-run-{run.get('id')}.json"
    write_snapshot_append_only(output_path, payload, conflict_root=INTAKE_CONFLICTS)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--architecture-baseline-ref", default="architecture-baseline-l1-v0.1.0")
    parser.add_argument("--artifact-name", default="architecture-governance-evidence")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--token", default="")
    parser.add_argument(
        "--notes",
        default="Intaken automatically from downstream Architecture Runtime Governance run.",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("GH_RESULT_INTAKE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    api_url = args.api_url.rstrip("/")
    repo_path = api_repo_path(args.repository_id)

    run = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}", token)
    freshness_policy = load_freshness_policy(FRESHNESS_POLICY_PATH, "freshness-governance-result-24h")
    artifacts_payload = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}/artifacts?per_page=100", token)
    artifacts = artifacts_payload.get("artifacts", [])
    selected_artifact = next((artifact for artifact in artifacts if artifact.get("name") == args.artifact_name), None)
    if not selected_artifact:
        raise FileNotFoundError(f"Artifact {args.artifact_name!r} not found for run {args.run_id}")

    with tempfile.TemporaryDirectory(prefix="architecture-result-intake-") as tempdir:
        temp = Path(tempdir)
        archive = temp / "artifact.zip"
        extract_dir = temp / "artifact"
        extract_dir.mkdir()
        try:
            github_download(selected_artifact["archive_download_url"], archive, token)
        except HTTPError as error:
            if error.code in {401, 403, 404}:
                if not download_artifact_with_gh(args.repository_id, args.run_id, args.artifact_name, extract_dir, token):
                    raise RuntimeError(
                        "Could not download the GitHub Actions artifact. "
                        "Set GH_RESULT_INTAKE_TOKEN to a token with Actions artifact read access "
                        f"for {args.repository_id}."
                    ) from error
            else:
                raise
        if archive.exists():
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(extract_dir)
        report_path = find_json(extract_dir, "architecture-governance-report.json")
        release_input_path = find_json(extract_dir, "architecture-release-input.json")
        report = load_json(report_path)
        release_input = load_json(release_input_path)
        subjects = [
            digest_subject(
                "architecture_governance_report",
                report_path,
                "artifact_metadata.architecture_governance_report_sha256",
            ),
            digest_subject(
                "architecture_release_input",
                release_input_path,
                "artifact_metadata.architecture_release_input_sha256",
            ),
        ]
        if archive.exists():
            subjects.append(digest_subject("artifact_archive", archive, "artifact_metadata.artifact_archive_sha256"))
        subject_paths = {
            "architecture_governance_report": report_path,
            "architecture_release_input": release_input_path,
        }
        if archive.exists():
            subject_paths["artifact_archive"] = archive

        subject_digests = {subject["id"]: subject["digest"] for subject in subjects}
        artifact_metadata = {
            "artifact_name": args.artifact_name,
            "artifact_size_bytes": int(selected_artifact.get("size_in_bytes", selected_artifact.get("size", 0))),
            "architecture_governance_report_sha256": subject_digests["architecture_governance_report"],
            "architecture_release_input_sha256": subject_digests["architecture_release_input"],
            "artifact_archive_sha256": subject_digests.get("artifact_archive"),
        }
        captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        trust = build_trust_capture(
            governance_domain="architecture",
            repository_id=args.repository_id,
            commit_id=run.get("head_sha", "unknown"),
            workflow_name=run.get("name", "Architecture Runtime Governance"),
            run_id=str(run.get("id")),
            run_attempt=run.get("run_attempt"),
            artifact_name=args.artifact_name,
            source_uri=selected_artifact.get("archive_download_url", run.get("html_url", "")),
            produced_at=run.get("updated_at") or run.get("created_at"),
            captured_at=captured_at,
            subjects=subjects,
        )
        trust = verify_trust_capture(
            trust,
            repository_id=args.repository_id,
            commit_id=run.get("head_sha", "unknown"),
            run_id=str(run.get("id")),
            artifact_name=args.artifact_name,
            subject_paths=subject_paths,
            verified_at=captured_at,
            freshness_policy=freshness_policy,
            produced_at=run.get("updated_at") or run.get("created_at"),
        )
        trust = apply_replay_assessment(trust, load_snapshot_payloads(TRUST_RESULT_ROOTS))

    protected = branch_protection(api_url, args.repository_id, run.get("head_branch", ""), token)
    output_path = write_snapshot(
        repository_id=args.repository_id,
        architecture_baseline_ref=args.architecture_baseline_ref,
        run=run,
        report=report,
        release_input=release_input,
        branch_protected=protected,
        artifact_metadata=artifact_metadata,
        trust=trust,
        notes=args.notes,
    )
    print(output_path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
