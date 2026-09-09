#!/usr/bin/env python3
"""Publish allowlisted operational changes as a reviewed PR, never to main."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LEDGERS = (
    "status/results/", "status/architecture-results/", "status/typed-evidence-results/",
    "status/collection-attempts/", "status/intake-events/", "status/intake-conflicts/",
)
COMMON = (
    "status/collection-attempts/", "status/intake-events/", "status/intake-conflicts/",
    "status/intake-health.json", "generated/graph/governance-graph.json",
    "generated/reports/blocking-mode-alignment.json", "generated/reports/blocking-readiness.json",
    "generated/reports/multi-consumer-readiness.json", "generated/reports/multi-consumer-readiness.md",
    "generated/reports/replay-triage.json", "generated/reports/replay-triage.md",
    "generated/viewer/status-viewer.html",
)
SCOPES = {
    "devsecops": COMMON + ("status/results/", "status/repository-results-index.json"),
    "architecture": COMMON + ("status/architecture-results/", "status/architecture-results-index.json"),
    "typed-evidence": COMMON + ("status/typed-evidence-results/", "status/typed-evidence-results-index.json"),
    "portfolio": ("generated/reports/portfolio-onboarding-status.json",
                  "generated/reports/portfolio-onboarding-status.md"),
}
CHECK_WORKFLOWS = ("governance-ci.yml", "codeql.yml", "governance-repository-security.yml")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True)
    return result.stdout


def allowed(path: str, scope: str) -> bool:
    return any(path.startswith(item) if item.endswith("/") else path == item for item in SCOPES[scope])


def selected_paths(root: Path, scope: str) -> list[str]:
    changed = set(git(root, "diff", "--name-only", "--no-renames", "-z", "HEAD").split("\0"))
    changed.update(git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    changed.discard("")
    selected = []
    for path in sorted(changed):
        if not allowed(path, scope):
            # Validators regenerate unrelated reports; they are never staged.
            if path.startswith("generated/"):
                continue
            raise ValueError(f"Operational update contains an out-of-scope change: {path}")
        candidate = root / path
        for parent in (candidate, *candidate.parents):
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError(f"Operational update contains a symlink: {path}")
        if path.startswith(LEDGERS):
            existing = subprocess.run(["git", "cat-file", "-e", f"HEAD:{path}"], cwd=root,
                                      capture_output=True, check=False)
            if existing.returncode == 0:
                raise ValueError(f"Historical evidence is append-only: {path}")
        selected.append(path)
    return selected


def github_api(endpoint: str, payload: dict) -> dict:
    result = subprocess.run(
        ["gh", "api", "--method", "POST", endpoint, "--input", "-"],
        input=json.dumps(payload), text=True, capture_output=True, check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def publish(root: Path, *, scope: str, repository: str, run_id: str, attempt: str,
            api=github_api) -> dict | None:
    if scope not in SCOPES or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid scope or repository")
    if not re.fullmatch(r"[1-9][0-9]*", run_id) or not re.fullmatch(r"[1-9][0-9]*", attempt):
        raise ValueError("Workflow run ID and attempt must be positive integers")
    paths = selected_paths(root, scope)
    if not paths:
        print("No operational changes to propose.")
        return None
    git(root, "fetch", "origin", "main")
    # Never carry an unreviewed workflow or normative commit into the PR ancestry.
    git(root, "merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/main")
    branch = f"automation/{scope}/{run_id}-{attempt}"
    git(root, "switch", "-c", branch)
    git(root, "reset", "--mixed", "HEAD")
    git(root, "add", "--", *paths)
    staged = git(root, "diff", "--cached", "--name-only", "-z").strip("\0").split("\0")
    if set(staged) != set(paths) or not all(allowed(path, scope) for path in staged):
        raise ValueError("Staged operational update does not match its allowlist")
    git(root, "-c", "user.name=github-actions[bot]",
        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "-c", "commit.gpgsign=false", "commit", "-m", f"Propose {scope} operational update")
    head = git(root, "rev-parse", "HEAD").strip()
    # Explicit destination and no force: this helper cannot update main.
    git(root, "push", "origin", f"HEAD:refs/heads/{branch}")
    run_url = f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}"
    pr = api(f"repos/{repository}/pulls", {
        "title": f"Review {scope} operational update (run {run_id}, attempt {attempt})",
        "head": branch, "base": "main",
        "body": (
            f"Generated by [workflow run {run_id}, attempt {attempt}]({run_url}).\n\n"
            f"Scope: `{scope}`. Proposed commit: `{head}`.\n\n"
            "Only allowlisted operational evidence and projections are included. "
            "The official indexes and viewer change only after review and merge. "
            "No automatic approval or merge is performed.\n\n"
            "Review new snapshots, failures, conflicts, and provenance before merging. "
            "If main advances, reconcile and regenerate the projections on the updated branch "
            "and rerun checks; do not overwrite append-only evidence.\n\n"
            "Governance CI, CodeQL, and self-security are explicitly dispatched for this branch. "
            "If GitHub also queues PR workflows for approval, a maintainer must approve those runs."
        ),
    })
    print(f"Opened operational review: {pr['html_url']}", flush=True)
    for output, text in (("GITHUB_OUTPUT", f"pull_request_url={pr['html_url']}\nbranch={branch}\n"),
                         ("GITHUB_STEP_SUMMARY", f"Operational review: {pr['html_url']}\n")):
        if os.environ.get(output):
            with Path(os.environ[output]).open("a", encoding="utf-8") as stream:
                stream.write(text)
    for workflow in CHECK_WORKFLOWS:
        api(f"repos/{repository}/actions/workflows/{workflow}/dispatches", {"ref": branch})
    return pr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, choices=SCOPES)
    args = parser.parse_args()
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        parser.error("Operational publication must run from the protected main workflow")
    publish(ROOT, scope=args.scope, repository=os.environ["GITHUB_REPOSITORY"],
            run_id=os.environ["GITHUB_RUN_ID"], attempt=os.environ["GITHUB_RUN_ATTEMPT"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
