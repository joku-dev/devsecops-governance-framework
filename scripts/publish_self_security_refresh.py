#!/usr/bin/env python3
"""Publish a material self-security refresh to one reviewed pull request."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
BRANCH = "automation/self-security-refresh"
REPORT_JSON = "generated/reports/governance-repository-security.json"
ALLOWED_PATHS = {
    REPORT_JSON,
    "generated/reports/governance-repository-security.md",
    "generated/viewer/app/data.json",
}
CHECK_WORKFLOWS = (
    "governance-ci.yml",
    "codeql.yml",
    "governance-repository-security.yml",
    "dependency-review.yml",
)


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=check
    )


def github_api(method: str, endpoint: str, payload: dict | None = None) -> object:
    command = ["gh", "api", "--method", method, endpoint]
    if payload is not None:
        command.extend(["--input", "-"])
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def normalized_report(report: dict) -> dict:
    """Remove observation time while retaining all security-relevant values."""
    result = copy.deepcopy(report)
    result.pop("observed_at", None)
    if isinstance(result.get("observation"), dict):
        result["observation"].pop("observed_at", None)
    return result


def materially_equal(current: dict, previous: dict) -> bool:
    return normalized_report(current) == normalized_report(previous)


def changed_paths(root: Path) -> list[str]:
    changed = set(
        git(root, "diff", "--name-only", "--no-renames", "-z", "HEAD").stdout.split("\0")
    )
    changed.update(
        git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0")
    )
    changed.discard("")
    selected = []
    for path in sorted(changed):
        if path not in ALLOWED_PATHS:
            if path.startswith("generated/"):
                continue
            raise ValueError(f"Self-security refresh contains an out-of-scope change: {path}")
        candidate = root / path
        for parent in (candidate, *candidate.parents):
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError(f"Self-security refresh contains a symlink: {path}")
        selected.append(path)
    return selected


def report_at(root: Path, ref: str) -> dict | None:
    result = git(root, "show", f"{ref}:{REPORT_JSON}", check=False)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def open_refresh_pr(repository: str, api=github_api) -> dict | None:
    owner = repository.split("/", 1)[0]
    endpoint = (
        f"repos/{repository}/pulls?state=open&base=main&head="
        f"{quote(owner + ':' + BRANCH, safe='')}"
    )
    result = api("GET", endpoint)
    if not isinstance(result, list):
        raise ValueError("GitHub pull-request query returned an unexpected response")
    if len(result) > 1:
        raise ValueError("More than one open self-security refresh PR exists")
    return result[0] if result else None


def write_outputs(root: Path, outputs: dict[str, bytes]) -> None:
    for path, content in outputs.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def publish(
    root: Path,
    *,
    repository: str,
    run_id: str,
    attempt: str,
    api=github_api,
) -> dict | None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[1-9][0-9]*", run_id) or not re.fullmatch(r"[1-9][0-9]*", attempt):
        raise ValueError("Workflow run ID and attempt must be positive integers")

    paths = changed_paths(root)
    if not paths:
        print("No self-security files changed.")
        return None
    if REPORT_JSON not in paths:
        raise ValueError("Self-security report JSON was not regenerated")

    current = json.loads((root / REPORT_JSON).read_text(encoding="utf-8"))
    outputs = {path: (root / path).read_bytes() for path in paths}
    git(root, "fetch", "origin", "main")
    git(root, "merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/main")
    existing_pr = open_refresh_pr(repository, api)

    comparison_ref = "HEAD"
    if existing_pr:
        remote = git(
            root,
            "ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{BRANCH}",
            check=False,
        )
        if remote.returncode != 0:
            raise ValueError("Open self-security refresh PR has no remote branch")
        git(root, "fetch", "origin", BRANCH)
        comparison_ref = f"refs/remotes/origin/{BRANCH}"
    elif git(root, "ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{BRANCH}", check=False).returncode == 0:
        raise ValueError("Stale self-security refresh branch exists without an open PR")

    previous = report_at(root, comparison_ref)
    if previous is not None and materially_equal(current, previous):
        print("No material self-security change; observation timestamp is not proposed.")
        return None

    git(root, "reset", "--hard", "HEAD")
    git(root, "clean", "-fd", "--", "generated")
    if existing_pr:
        git(root, "switch", "-C", BRANCH, f"refs/remotes/origin/{BRANCH}")
        git(
            root,
            "-c", "user.name=github-actions[bot]",
            "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "-c", "commit.gpgsign=false",
            "merge", "--no-edit", "refs/remotes/origin/main",
        )
    else:
        git(root, "switch", "-c", BRANCH, "refs/remotes/origin/main")
    write_outputs(root, outputs)

    staged_candidates = changed_paths(root)
    if not staged_candidates or not set(staged_candidates).issubset(ALLOWED_PATHS):
        raise ValueError("Self-security refresh produced no valid allowlisted change")
    git(root, "add", "--", *staged_candidates)
    staged = set(
        git(root, "diff", "--cached", "--name-only", "-z").stdout.strip("\0").split("\0")
    )
    if staged != set(staged_candidates):
        raise ValueError("Staged self-security refresh does not match its allowlist")
    git(
        root,
        "-c", "user.name=github-actions[bot]",
        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "-c", "commit.gpgsign=false",
        "commit", "-m", "Propose self-security status refresh",
    )
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    git(root, "push", "origin", f"HEAD:refs/heads/{BRANCH}")

    run_url = f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}"
    body = (
        f"Generated by [self-security refresh run {run_id}, attempt {attempt}]({run_url}).\n\n"
        f"Proposed commit: `{head}`. Only the validated self-security report and its Viewer "
        "projection are included. Observation timestamps alone do not create or update this PR. "
        "No automatic approval, merge, settings change, or enforcement change is performed.\n\n"
        "Review every changed criterion and observation before merging. Governance CI, CodeQL, "
        "Self-Security, and Dependency Review are explicitly dispatched for this branch."
    )
    if existing_pr:
        pr = api("PATCH", f"repos/{repository}/pulls/{existing_pr['number']}", {
            "title": "Review current repository self-security status",
            "body": body,
        })
    else:
        pr = api("POST", f"repos/{repository}/pulls", {
            "title": "Review current repository self-security status",
            "head": BRANCH,
            "base": "main",
            "body": body,
        })
    if not isinstance(pr, dict) or not pr.get("html_url"):
        raise ValueError("GitHub did not return the self-security refresh PR")
    print(f"Self-security review: {pr['html_url']}", flush=True)

    for workflow in CHECK_WORKFLOWS:
        payload = {"ref": BRANCH}
        if workflow == "dependency-review.yml":
            payload["inputs"] = {"base_ref": "main", "head_ref": BRANCH}
        api("POST", f"repos/{repository}/actions/workflows/{workflow}/dispatches", payload)
    for output, value in (
        ("GITHUB_OUTPUT", f"pull_request_url={pr['html_url']}\nbranch={BRANCH}\nmaterial_change=true\n"),
        ("GITHUB_STEP_SUMMARY", f"Self-security review: {pr['html_url']}\n"),
    ):
        if os.environ.get(output):
            with Path(os.environ[output]).open("a", encoding="utf-8") as stream:
                stream.write(value)
    return pr


def main() -> int:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise SystemExit("Self-security publication must run from protected main")
    publish(
        ROOT,
        repository=os.environ["GITHUB_REPOSITORY"],
        run_id=os.environ["GITHUB_RUN_ID"],
        attempt=os.environ["GITHUB_RUN_ATTEMPT"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
