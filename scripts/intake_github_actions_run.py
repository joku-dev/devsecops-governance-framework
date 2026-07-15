#!/usr/bin/env python3
"""Intake a downstream GitHub Actions governance run into central status."""

from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from lib.identifiers import sanitize_timestamp, slugify_repository
from lib.json_io import load_json, write_json


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "results"
DEFAULT_API_URL = "https://api.github.com"


def github_get_json(url: str, token: str | None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "devsecops-governance-result-intake",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def github_download(url: str, destination: Path, token: str | None) -> None:
    headers = {
        "User-Agent": "devsecops-governance-result-intake",
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


def infer_baseline_ref(run: dict) -> str:
    for workflow in run.get("referenced_workflows", []):
        ref = workflow.get("ref", "")
        path = workflow.get("path", "")
        if ref.startswith("refs/tags/"):
            tag = ref.removeprefix("refs/tags/")
            if "baseline" in tag:
                return tag
        match = re.search(r"devsecops-baseline-l1-(v[0-9]+(?:\.[0-9]+)+)\.yml@([^/]+)$", path)
        if match:
            return match.group(2)
    return "unknown"


def find_job_status(jobs: list[dict], *name_fragments: str) -> str:
    normalized_fragments = [fragment.lower() for fragment in name_fragments]
    for job in jobs:
        name = job.get("name", "").lower()
        if all(fragment in name for fragment in normalized_fragments):
            return conclusion_to_status(job.get("conclusion"))
    return ""


def bool_from_path(payload: dict, path: list[str]) -> bool:
    value = payload
    for key in path:
        if not isinstance(value, dict):
            return False
        value = value.get(key)
    return bool(value)


def evidence_flags(governance_input: dict, artifact_names: set[str]) -> dict:
    traceability_ok = all(
        bool_from_path(governance_input, ["traceability", key])
        for key in ("requirements_linked", "testcases_linked", "reports_linked")
    )
    operations_ok = all(
        bool_from_path(governance_input, ["operations", key])
        for key in ("deployed_versions_recorded", "security_events_recorded")
    )
    return {
        "sbom": bool_from_path(governance_input, ["evidence", "sbom", "exists"]),
        "vulnerability_scan": bool_from_path(governance_input, ["evidence", "vulnerability_scan", "exists"]),
        "artifact_digest": bool_from_path(governance_input, ["artifact", "digest", "exists"]),
        "governance_control_report": "governance-control-evaluation" in artifact_names,
        "governance_run_input": bool(governance_input) or "devsecops-governance-run-input" in artifact_names,
        "static_analysis_summary": bool_from_path(governance_input, ["static_analysis", "performed"]),
        "traceability_mapping": traceability_ok,
        "operations_evidence": operations_ok,
    }


def branch_protection(api_url: str, repository_id: str, branch: str, token: str | None) -> bool:
    url = f"{api_url}{api_repo_path(repository_id)}/branches/{quote(branch, safe='')}"
    try:
        payload = github_get_json(url, token)
    except Exception:
        return False
    return bool(payload.get("protected"))


def find_report(extract_dir: Path) -> Path:
    preferred = extract_dir / "generated" / "control-evaluation-report.json"
    if preferred.is_file():
        return preferred
    matches = sorted(extract_dir.rglob("control-evaluation-report.json"))
    if not matches:
        raise FileNotFoundError("control-evaluation-report.json not found in governance-control-evaluation artifact")
    return matches[0]


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def find_governance_input(extract_dir: Path) -> tuple[dict, Path | None]:
    preferred = extract_dir / "governance" / "governance-run-input.json"
    if preferred.is_file():
        return load_json(preferred), preferred
    matches = sorted(extract_dir.rglob("governance-run-input.json"))
    if matches:
        return load_json(matches[0]), matches[0]
    return {}, None


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
    return result.returncode == 0


def write_snapshot(
    *,
    repository_id: str,
    baseline_level: str,
    governance_baseline_ref: str,
    run: dict,
    jobs: list[dict],
    report: dict,
    governance_input: dict,
    report_path: Path,
    governance_input_path: Path | None,
    branch_protected: bool,
    artifacts: list[dict],
    selected_artifact: dict | None,
    artifact_names: set[str],
    notes: str,
) -> Path:
    control_summary = report.get("summary", report)
    baseline_gate_status = find_job_status(jobs, "baseline", "gate") or conclusion_to_status(run.get("conclusion"))
    governance_control_status = find_job_status(jobs, "governance", "control", "evaluation")
    overall_status = "pass" if run.get("conclusion") == "success" and control_summary.get("fail", 0) == 0 else "fail"
    generated_at = run.get("updated_at") or run.get("created_at")
    branch = run.get("head_branch", "unknown")

    checks = {"baseline_gate": baseline_gate_status}
    if governance_control_status:
        checks["governance_control_evaluation"] = governance_control_status

    artifact_sizes = {artifact.get("name", "unknown"): artifact.get("size", 0) for artifact in artifacts}
    downloaded_artifact_info = None
    if selected_artifact is not None:
        downloaded_artifact_info = {
            "downloaded": True,
            "artifact_size_bytes": selected_artifact.get("size", 0),
            "control_evaluation_report_sha256": compute_sha256(report_path),
            "governance_run_input_sha256": compute_sha256(governance_input_path) if governance_input_path is not None else None,
            "governance_run_input_refs": governance_input.get("evidence_refs", []),
        }

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repository_id,
        "baseline_level": baseline_level,
        "governance_baseline_ref": governance_baseline_ref,
        "governance_repository": "joku-dev/devsecops-governance-as-code",
        "result_type": "governance-baseline-run",
        "generated_at": generated_at,
        "pipeline": {
            "pipeline_name": run.get("name", "DevSecOps Baseline"),
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
        "checks": checks,
        "evidence": evidence_flags(governance_input, artifact_names),
        "artifact_metadata": {
            "artifact_names": sorted(artifact_names),
            "artifact_sizes": artifact_sizes,
        },
        "downloaded_artifact": downloaded_artifact_info,
        "control_evaluation_summary": control_summary,
        "overall_status": overall_status,
        "notes": notes,
    }

    repo_dir = STATUS_RESULTS / slugify_repository(repository_id)
    output_path = repo_dir / f"{sanitize_timestamp(generated_at)}-run-{run.get('id')}.json"
    write_json(output_path, payload)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline-level", default="L1")
    parser.add_argument("--governance-baseline-ref", default="")
    parser.add_argument("--artifact-name", default="governance-control-evaluation")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--token", default="")
    parser.add_argument(
        "--notes",
        default="Intaken automatically from downstream GitHub Actions governance run.",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("GH_RESULT_INTAKE_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    api_url = args.api_url.rstrip("/")
    repo_path = api_repo_path(args.repository_id)

    run = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}", token)
    jobs_payload = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}/jobs?per_page=100", token)
    artifacts_payload = github_get_json(f"{api_url}{repo_path}/actions/runs/{args.run_id}/artifacts?per_page=100", token)
    jobs = jobs_payload.get("jobs", [])
    artifacts = artifacts_payload.get("artifacts", [])
    artifact_names = {artifact.get("name", "") for artifact in artifacts}
    selected_artifact = next((artifact for artifact in artifacts if artifact.get("name") == args.artifact_name), None)
    if not selected_artifact:
        raise FileNotFoundError(f"Artifact {args.artifact_name!r} not found for run {args.run_id}")

    with tempfile.TemporaryDirectory(prefix="governance-result-intake-") as tempdir:
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
        report_path = find_report(extract_dir)
        report = load_json(report_path)
        governance_input, governance_input_path = find_governance_input(extract_dir)

    baseline_ref = args.governance_baseline_ref or infer_baseline_ref(run)
    protected = branch_protection(api_url, args.repository_id, run.get("head_branch", ""), token)
    output_path = write_snapshot(
        repository_id=args.repository_id,
        baseline_level=args.baseline_level,
        governance_baseline_ref=baseline_ref,
        run=run,
        jobs=jobs,
        report=report,
        report_path=report_path,
        governance_input=governance_input,
        governance_input_path=governance_input_path,
        branch_protected=protected,
        artifacts=artifacts,
        selected_artifact=selected_artifact,
        artifact_names=artifact_names,
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
