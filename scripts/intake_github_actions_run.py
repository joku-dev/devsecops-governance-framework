#!/usr/bin/env python3
"""Intake a downstream GitHub Actions governance run into central status."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from lib.identifiers import sanitize_timestamp, slugify_repository
from lib.evidence_trust import (
    build_trust_capture,
    compute_sha256,
    digest_subject,
    load_freshness_policy,
    verify_trust_capture,
)
from lib.json_io import load_json
from lib.result_ledger import apply_replay_assessment, load_snapshot_payloads, write_snapshot_append_only


ROOT = Path(__file__).resolve().parents[1]
STATUS_RESULTS = ROOT / "status" / "results"
INTAKE_CONFLICTS = ROOT / "status" / "intake-conflicts" / "devsecops"
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
    if matches:
        return matches[0]
    fallback = extract_dir / "generated" / "evidence" / "baseline-gate-result.json"
    if fallback.is_file():
        return fallback
    fallback_matches = sorted(extract_dir.rglob("baseline-gate-result.json"))
    if fallback_matches:
        return fallback_matches[0]
    raise FileNotFoundError(
        "Neither control-evaluation-report.json nor baseline-gate-result.json "
        "was found in the governance artifact"
    )


def normalize_governance_report(report: dict, report_path: Path) -> dict:
    """Normalize the released report or the consumer's report-only gate output."""
    if report_path.name != "baseline-gate-result.json":
        return report
    failed = report.get("status") == "fail"
    return {
        "summary": {
            "applicable_controls": 1,
            "pass": 0 if failed else 1,
            "fail": 1 if failed else 0,
            "not_tested": 0,
        },
        "baseline_gate_result": report,
    }


def artifact_size_bytes(artifact: dict) -> int:
    return int(artifact.get("size_in_bytes", artifact.get("size", 0)))


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
    report_sha256: str,
    governance_input_sha256: str | None,
    branch_protected: bool,
    artifacts: list[dict],
    selected_artifact: dict | None,
    artifact_names: set[str],
    trust: dict,
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

    artifact_sizes = {artifact.get("name", "unknown"): artifact_size_bytes(artifact) for artifact in artifacts}
    downloaded_artifact_info = None
    if selected_artifact is not None:
        downloaded_artifact_info = {
            "downloaded": True,
            "artifact_size_bytes": artifact_size_bytes(selected_artifact),
            "control_evaluation_report_sha256": report_sha256,
            "governance_run_input_sha256": governance_input_sha256,
            "governance_run_input_refs": governance_input.get("evidence_refs", []),
        }

    payload = {
        "schema_version": "1.0.0",
        "repository_id": repository_id,
        "baseline_level": baseline_level,
        "governance_baseline_ref": governance_baseline_ref,
        "governance_repository": "joku-dev/devsecops-governance-framework",
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
        "trust": trust,
        "control_evaluation_summary": control_summary,
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
    freshness_policy = load_freshness_policy(FRESHNESS_POLICY_PATH, "freshness-governance-result-24h")
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
        report = normalize_governance_report(load_json(report_path), report_path)
        governance_input, governance_input_path = find_governance_input(extract_dir)
        report_sha256 = compute_sha256(report_path)
        governance_input_sha256 = compute_sha256(governance_input_path) if governance_input_path is not None else None
        subjects = [
            digest_subject(
                "control_evaluation_report",
                report_path,
                "downloaded_artifact.control_evaluation_report_sha256",
            )
        ]
        if governance_input_path is not None:
            subjects.append(
                digest_subject(
                    "governance_run_input",
                    governance_input_path,
                    "downloaded_artifact.governance_run_input_sha256",
                )
            )
        if archive.exists():
            subjects.append(digest_subject("artifact_archive", archive, "trust.capture.subjects.artifact_archive"))
        subject_paths = {"control_evaluation_report": report_path}
        if governance_input_path is not None:
            subject_paths["governance_run_input"] = governance_input_path
        if archive.exists():
            subject_paths["artifact_archive"] = archive

        captured_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        trust = build_trust_capture(
            governance_domain="devsecops",
            repository_id=args.repository_id,
            commit_id=run.get("head_sha", "unknown"),
            workflow_name=run.get("name", "DevSecOps Baseline"),
            run_id=str(run.get("id")),
            run_attempt=run.get("run_attempt"),
            artifact_name=args.artifact_name,
            source_uri=selected_artifact.get("archive_download_url", run.get("html_url", "")),
            produced_at=run.get("updated_at") or run.get("created_at"),
            captured_at=captured_at,
            subjects=subjects,
        )
        artifact_digest = selected_artifact.get("digest")
        if artifact_digest:
            trust["capture"]["source"]["artifact_digest"] = artifact_digest.removeprefix("sha256:")
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

    baseline_ref = args.governance_baseline_ref or infer_baseline_ref(run)
    protected = branch_protection(api_url, args.repository_id, run.get("head_branch", ""), token)
    output_path = write_snapshot(
        repository_id=args.repository_id,
        baseline_level=args.baseline_level,
        governance_baseline_ref=baseline_ref,
        run=run,
        jobs=jobs,
        report=report,
        governance_input=governance_input,
        report_sha256=report_sha256,
        governance_input_sha256=governance_input_sha256,
        branch_protected=protected,
        artifacts=artifacts,
        selected_artifact=selected_artifact,
        artifact_names=artifact_names,
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
