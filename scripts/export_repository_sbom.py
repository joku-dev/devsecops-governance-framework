#!/usr/bin/env python3
"""Export a commit-bound SPDX SBOM from GitHub's dependency graph API."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_SBOM_BYTES = 25 * 1024 * 1024
POLL_ATTEMPTS = 18
POLL_INTERVAL_SECONDS = 5
DOWNLOAD_HOST_SUFFIXES = (".github.com", ".githubusercontent.com", ".amazonaws.com")
DOWNLOAD_HOSTS = {"github.com", "githubusercontent.com", "amazonaws.com"}


class NoRedirect(HTTPRedirectHandler):
    """Keep temporary download redirects separate from authenticated API calls."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "governance-repository-sbom",
    }


def read_limited(response, limit: int = MAX_SBOM_BYTES) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = response.read(min(65536, limit + 1 - total))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ValueError(f"SBOM response exceeds the {limit}-byte limit")
        chunks.append(chunk)
    return b"".join(chunks)


def api_json(url: str, token: str) -> tuple[int, dict]:
    request = Request(url, headers=request_headers(token), method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(read_limited(response))
            return response.status, payload
    except HTTPError as error:
        if error.code == 202:
            return error.code, {}
        raise RuntimeError(f"GitHub SBOM API returned HTTP {error.code}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"GitHub SBOM API request failed: {error}") from error


def api_redirect(url: str, token: str) -> str:
    request = Request(url, headers=request_headers(token), method="GET")
    opener = build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            if response.status != 302:
                raise RuntimeError(f"Expected SBOM download redirect, got HTTP {response.status}")
    except HTTPError as error:
        if error.code != 302:
            raise RuntimeError(f"GitHub SBOM fetch returned HTTP {error.code}") from error
        location = error.headers.get("Location")
        if not location:
            raise RuntimeError("GitHub SBOM fetch response has no download location") from error
        return location
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"GitHub SBOM fetch failed: {error}") from error
    raise RuntimeError("GitHub SBOM fetch did not return a download location")


def validate_download_url(location: str) -> None:
    parsed = urlparse(location)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (
            host not in DOWNLOAD_HOSTS
            and not any(host.endswith(suffix) for suffix in DOWNLOAD_HOST_SUFFIXES)
        )
    ):
        # Report the hostname only. A GitHub download URL contains a temporary
        # credential in its query string, which must never enter Actions logs.
        raise ValueError(f"GitHub returned an unexpected SBOM download host or URL: {host or '<missing>'}")


class SafeDownloadRedirect(HTTPRedirectHandler):
    """Allow only HTTPS redirects within GitHub's temporary artifact hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_sbom(location: str) -> bytes:
    validate_download_url(location)
    opener = build_opener(SafeDownloadRedirect)
    request = Request(location, headers={"User-Agent": "governance-repository-sbom"})
    try:
        with opener.open(request, timeout=30) as response:
            return read_limited(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError("Could not download the generated SPDX SBOM") from error


def validate_spdx(raw: bytes, repository: str) -> dict:
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("GitHub returned invalid JSON for the SBOM") from error
    if isinstance(document, dict) and isinstance(document.get("sbom"), dict):
        document = document["sbom"]
    if not isinstance(document, dict):
        raise ValueError("SBOM must be an SPDX JSON object")
    if document.get("spdxVersion") not in {"SPDX-2.2", "SPDX-2.3"}:
        raise ValueError("SBOM has no supported SPDX version")
    if not isinstance(document.get("documentNamespace"), str) or not document["documentNamespace"].startswith("https://"):
        raise ValueError("SBOM has no valid SPDX document namespace")
    creation = document.get("creationInfo")
    if not isinstance(creation, dict) or not isinstance(creation.get("created"), str):
        raise ValueError("SBOM has no SPDX creation timestamp")
    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("SBOM contains no dependency packages")
    if not all(isinstance(item, dict) and item.get("name") and item.get("SPDXID") for item in packages):
        raise ValueError("SBOM contains a malformed package entry")
    identifiers = {item.get("SPDXID") for item in packages}
    if "SPDXRef-Repository" not in identifiers:
        raise ValueError("SBOM does not identify the repository root package")
    root = next(item for item in packages if item.get("SPDXID") == "SPDXRef-Repository")
    expected_root_name = f"github/{repository}".casefold()
    if str(root.get("name", "")).casefold() != expected_root_name:
        raise ValueError("SBOM repository identity does not match the requested repository")
    return document


def current_default_branch_sha(repository: str, token: str) -> tuple[str, str]:
    status, metadata = api_json(f"{API_ROOT}/repos/{repository}", token)
    if status != 200 or not isinstance(metadata.get("default_branch"), str):
        raise RuntimeError("Could not determine the repository default branch")
    branch = metadata["default_branch"]
    status, commit = api_json(f"{API_ROOT}/repos/{repository}/commits/{branch}", token)
    sha = commit.get("sha") if status == 200 else None
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("Could not determine the current default-branch commit")
    return branch, sha


def generate(repository: str, expected_sha: str, token: str, output_dir: Path) -> tuple[Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("GITHUB_REPOSITORY must be in owner/name form")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("GITHUB_SHA must be a full commit SHA")
    if not token:
        raise ValueError("GH_TOKEN is required")
    event_ref = os.environ.get("GITHUB_REF")

    branch, before_sha = current_default_branch_sha(repository, token)
    if event_ref and event_ref != f"refs/heads/{branch}":
        raise ValueError("SBOM generation must run from the default branch")
    if before_sha != expected_sha:
        raise ValueError("Workflow commit is not the current default-branch HEAD")

    status, request_payload = api_json(
        f"{API_ROOT}/repos/{repository}/dependency-graph/sbom/generate-report", token
    )
    sbom_url = request_payload.get("sbom_url") if status == 201 else None
    expected_prefix = f"{API_ROOT}/repos/{repository}/dependency-graph/sbom/fetch-report/"
    if not isinstance(sbom_url, str) or not sbom_url.startswith(expected_prefix):
        raise RuntimeError("GitHub did not return the expected SBOM report URL")
    report_id = sbom_url[len(expected_prefix):]
    if not re.fullmatch(r"[0-9a-f-]{36}", report_id):
        raise RuntimeError("GitHub returned an invalid SBOM report identifier")

    fetch_url = expected_prefix + report_id
    download_url = None
    for attempt in range(POLL_ATTEMPTS):
        try:
            download_url = api_redirect(fetch_url, token)
            break
        except RuntimeError as error:
            if "HTTP 202" not in str(error) or attempt == POLL_ATTEMPTS - 1:
                raise
            time.sleep(POLL_INTERVAL_SECONDS)
    if not download_url:
        raise RuntimeError("GitHub SBOM generation did not finish before timeout")

    raw = download_sbom(download_url)
    document = validate_spdx(raw, repository)
    after_branch, after_sha = current_default_branch_sha(repository, token)
    if after_branch != branch or after_sha != expected_sha:
        raise RuntimeError("Default branch moved while the SBOM was being generated; retry the workflow")

    output_dir.mkdir(parents=True, exist_ok=True)
    sbom_path = output_dir / "sbom.spdx.json"
    metadata_path = output_dir / "sbom-metadata.json"
    sbom_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata = {
        "schema_version": "1.0.0",
        "repository": repository,
        "default_branch": branch,
        "commit_sha": expected_sha,
        "workflow_ref": event_ref,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "format": document["spdxVersion"],
        "document_namespace": document["documentNamespace"],
        "package_count": len(document["packages"]),
        "source": "GitHub dependency graph SBOM API",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sbom_path, metadata_path


def main() -> int:
    try:
        repository = os.environ["GITHUB_REPOSITORY"]
        commit_sha = os.environ["GITHUB_SHA"]
        token = os.environ["GH_TOKEN"]
    except KeyError as error:
        print(f"Missing required environment variable: {error.args[0]}", file=sys.stderr)
        return 2
    output_dir = Path(os.environ.get("SBOM_OUTPUT_DIR", "sbom-output"))
    try:
        sbom_path, metadata_path = generate(repository, commit_sha, token, output_dir)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"SBOM generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Validated SPDX SBOM: {sbom_path} ({metadata_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
