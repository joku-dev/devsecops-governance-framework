#!/usr/bin/env python3
"""Generate normalized CI/CD platform context from native environment variables."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import os


def github_actions_context() -> dict:
    repository_id = os.environ.get("GITHUB_REPOSITORY", "unknown")
    branch = os.environ.get("GITHUB_BASE_REF") or os.environ.get("GITHUB_REF_NAME") or "unknown"
    run_id = os.environ.get("GITHUB_RUN_ID", "unknown")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    context = {
        "source": "github-actions",
        "repository_id": repository_id,
        "branch": branch,
        "commit_id": os.environ.get("GITHUB_SHA", "unknown"),
        "pipeline_id": os.environ.get("GITHUB_WORKFLOW", "GitHub Actions"),
        "pipeline_run_id": run_id,
        "pipeline_url": f"{server_url}/{repository_id}/actions/runs/{run_id}" if repository_id != "unknown" else "",
        "event": os.environ.get("GITHUB_EVENT_NAME", "unknown"),
    }
    if os.environ.get("GITHUB_BASE_REF"):
        context["pull_request_target"] = os.environ["GITHUB_BASE_REF"]
    return context


def bamboo_context() -> dict:
    repository_id = (
        os.environ.get("bamboo_planRepository_repositoryUrl")
        or os.environ.get("bamboo_repository_id")
        or "unknown"
    )
    run_id = os.environ.get("bamboo_buildResultKey") or os.environ.get("bamboo_buildNumber") or "unknown"
    return {
        "source": "bamboo",
        "repository_id": repository_id,
        "branch": os.environ.get("bamboo_planRepository_branchName", "unknown"),
        "commit_id": os.environ.get("bamboo_planRepository_revision", "unknown"),
        "pipeline_id": os.environ.get("bamboo_planName", "Bamboo"),
        "pipeline_run_id": str(run_id),
        "pipeline_url": os.environ.get("bamboo_resultsUrl", ""),
        "event": os.environ.get("bamboo_buildTriggerReason", "bamboo"),
    }


def bitbucket_pipelines_context() -> dict:
    repository_full_name = os.environ.get("BITBUCKET_REPO_FULL_NAME", "")
    repository_slug = os.environ.get("BITBUCKET_REPO_SLUG", "unknown")
    workspace = os.environ.get("BITBUCKET_WORKSPACE", "")
    repository_id = repository_full_name or f"{workspace}/{repository_slug}".strip("/") or "unknown"
    event = "pull_request" if os.environ.get("BITBUCKET_PR_ID") else "branch_build"
    context = {
        "source": "bitbucket-pipelines",
        "repository_id": repository_id,
        "branch": os.environ.get("BITBUCKET_BRANCH") or os.environ.get("BITBUCKET_PR_DESTINATION_BRANCH") or "unknown",
        "commit_id": os.environ.get("BITBUCKET_COMMIT", "unknown"),
        "pipeline_id": os.environ.get("BITBUCKET_PIPELINE_UUID", "Bitbucket Pipelines"),
        "pipeline_run_id": os.environ.get("BITBUCKET_BUILD_NUMBER", "unknown"),
        "pipeline_url": os.environ.get("BITBUCKET_PIPELINE_URL", ""),
        "event": event,
    }
    if os.environ.get("BITBUCKET_PR_ID"):
        context["pull_request_id"] = os.environ["BITBUCKET_PR_ID"]
    if os.environ.get("BITBUCKET_PR_DESTINATION_BRANCH"):
        context["pull_request_target"] = os.environ["BITBUCKET_PR_DESTINATION_BRANCH"]
    return context


def jenkins_context() -> dict:
    run_id = os.environ.get("BUILD_TAG") or os.environ.get("BUILD_NUMBER") or "unknown"
    event = "pull_request" if os.environ.get("CHANGE_ID") else "branch_build"
    context = {
        "source": "jenkins",
        "repository_id": os.environ.get("GOVERNANCE_REPOSITORY_ID") or os.environ.get("GIT_URL", "unknown"),
        "branch": os.environ.get("CHANGE_TARGET") or os.environ.get("BRANCH_NAME", "unknown"),
        "commit_id": os.environ.get("GIT_COMMIT", "unknown"),
        "pipeline_id": os.environ.get("JOB_NAME", "Jenkins"),
        "pipeline_run_id": str(run_id),
        "pipeline_url": os.environ.get("BUILD_URL", ""),
        "event": event,
    }
    if os.environ.get("CHANGE_ID"):
        context["pull_request_id"] = os.environ["CHANGE_ID"]
    if os.environ.get("CHANGE_TARGET"):
        context["pull_request_target"] = os.environ["CHANGE_TARGET"]
    return context


def context_for(platform: str) -> dict:
    if platform == "github-actions":
        return github_actions_context()
    if platform == "bamboo":
        return bamboo_context()
    if platform == "bitbucket-pipelines":
        return bitbucket_pipelines_context()
    if platform == "jenkins":
        return jenkins_context()
    raise ValueError(f"Unsupported platform: {platform}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = ArgumentParser(description="Generate normalized CI/CD platform context.")
    parser.add_argument("--platform", required=True, choices=["github-actions", "bamboo", "bitbucket-pipelines", "jenkins"])
    parser.add_argument("--output", default="generated/evidence/platform-context.json")
    args = parser.parse_args()

    payload = context_for(args.platform)
    write_json(Path(args.output), payload)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
