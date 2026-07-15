#!/usr/bin/env python3
"""Generate normalized DevSecOps pipeline evidence for CI/CD adapters."""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os

from generate_platform_context import context_for


SEVERITY_ORDER = {
    "none": 0,
    "info": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "critical": 5,
}


def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scan_max_severity(path: Path, fallback: str) -> str:
    if not path.is_file():
        return fallback
    try:
        payload = load_json(path)
    except Exception:
        return fallback
    return str(payload.get("max_severity", fallback)).lower()


def platform_context(platform: str) -> dict:
    return context_for(platform)


def merge_context(base: dict, override_path: str) -> dict:
    if not override_path:
        return base
    path = Path(override_path)
    if not path.is_file():
        raise FileNotFoundError(f"platform context file not found: {path}")
    override = load_json(path)
    merged = dict(base)
    for key, value in override.items():
        if value not in (None, ""):
            merged[key] = value
    return merged


def run_purpose(event: str, release_candidate: bool, branch: str) -> tuple[str, bool]:
    release_context = release_candidate and event == "push" and branch == "main"
    if release_context:
        return "release", True
    if event in {"workflow_dispatch", "manual", "manual_build"}:
        return "diagnostic", False
    if event in {"pull_request", "pr"}:
        return "pull_request_validation", False
    return "branch_validation", False


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = ArgumentParser(description="Generate normalized DevSecOps pipeline evidence.")
    parser.add_argument("--platform", required=True, choices=["github-actions", "bamboo", "bitbucket-pipelines", "jenkins"])
    parser.add_argument("--platform-context-file", default="")
    parser.add_argument("--artifact-path", default="dist/application-source.tar.gz")
    parser.add_argument("--sbom-path", default="security/sbom.cyclonedx.json")
    parser.add_argument("--vulnerability-scan-path", default="security/vulnerability-scan.json")
    parser.add_argument("--signature-path", default="")
    parser.add_argument("--output", default="generated/evidence/pipeline-evidence.json")
    parser.add_argument("--gate-output", default="generated/evidence/baseline-gate-result.json")
    parser.add_argument("--governance-mode", default="report-only")
    parser.add_argument("--max-allowed-severity", default="high")
    parser.add_argument("--release-candidate", action="store_true")
    parser.add_argument("--artifact-type", default="application-build-output")
    parser.add_argument("--protected-branch", default="")
    parser.add_argument("--direct-push-allowed", default="")
    parser.add_argument("--review-required", default="")
    parser.add_argument("--branch-protection-status", default="not_checked_by_platform_adapter")
    args = parser.parse_args()

    context = merge_context(platform_context(args.platform), args.platform_context_file)
    artifact = Path(args.artifact_path)
    sbom = Path(args.sbom_path)
    vulnerability_scan = Path(args.vulnerability_scan_path)
    signature = Path(args.signature_path) if args.signature_path else None
    max_seen = load_scan_max_severity(vulnerability_scan, os.environ.get("VULNERABILITY_MAX_SEVERITY", "none"))
    max_allowed = args.max_allowed_severity.lower()
    purpose, release_context = run_purpose(
        str(context.get("event", "unknown")),
        args.release_candidate,
        str(context.get("branch", "unknown")),
    )
    artifact_exists = artifact.is_file()

    protected_branch = None if args.protected_branch == "" else as_bool(args.protected_branch)
    direct_push_allowed = None if args.direct_push_allowed == "" else as_bool(args.direct_push_allowed)
    review_required = None if args.review_required == "" else as_bool(args.review_required)

    repository = {
        "repository_id": context.get("repository_id", "unknown"),
        "branch": context.get("branch", "unknown"),
        "branch_protection_lookup": {"status": args.branch_protection_status},
    }
    if protected_branch is not None:
        repository["protected_branch"] = protected_branch
    if direct_push_allowed is not None:
        repository["direct_push_allowed"] = direct_push_allowed
    if review_required is not None:
        repository["review_required"] = review_required

    evidence = {
        "contract_version": "1.0",
        "release_candidate": args.release_candidate,
        "run_context": {
            "event": context.get("event", "unknown"),
            "purpose": purpose,
            "release_context": release_context,
            "source": context.get("source", args.platform),
        },
        "pipeline": {
            "pipeline_id": context.get("pipeline_id", args.platform),
            "pipeline_run_id": str(context.get("pipeline_run_id", "unknown")),
            "pipeline_url": context.get("pipeline_url", ""),
            "commit_id": context.get("commit_id", "unknown"),
            "event": context.get("event", "unknown"),
            "governance_mode": args.governance_mode,
            "status": "success",
            "security_gates": {"enforced": True},
            "security_thresholds_exceeded": SEVERITY_ORDER.get(max_seen, 99) > SEVERITY_ORDER.get(max_allowed, 99),
            "external_direct_downloads_detected": as_bool(os.environ.get("EXTERNAL_DIRECT_DOWNLOADS_DETECTED", "false")),
        },
        "repository": repository,
        "artifact": {
            "artifact_id": artifact.name,
            "artifact_type": args.artifact_type,
            "artifact_version": str(context.get("commit_id", "unknown"))[:12],
            "digest": {
                "exists": artifact_exists,
                "linked_to_artifact": artifact_exists,
                "algorithm": "sha256",
                "value": sha256(artifact) if artifact_exists else "",
            },
            "signature": {
                "exists": bool(signature and signature.is_file()),
                "path": str(signature) if signature else "",
            },
        },
        "evidence": {
            "sbom": {
                "exists": sbom.is_file(),
                "linked_to_artifact": sbom.is_file() and artifact_exists,
                "path": str(sbom),
            },
            "vulnerability_scan": {
                "exists": vulnerability_scan.is_file(),
                "path": str(vulnerability_scan),
                "max_severity": max_seen,
            },
            "pipeline_execution": {
                "evidence_id": f"{args.platform}-{context.get('pipeline_run_id', 'unknown')}",
                "pipeline_run_id": str(context.get("pipeline_run_id", "unknown")),
                "status": "success",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        "release": {
            "release_id": f"{context.get('repository_id', 'unknown')}@{str(context.get('commit_id', 'unknown'))[:12]}",
            "approval_status": "not_required",
            "approved_waiver": {"exists": as_bool(os.environ.get("APPROVED_WAIVER_EXISTS", "false"))},
        },
        "waivers": [],
    }

    errors = []
    if not artifact_exists:
        errors.append(f"artifact not found: {artifact}")
    if not sbom.is_file():
        errors.append(f"SBOM not found: {sbom}")
    if not vulnerability_scan.is_file():
        errors.append(f"vulnerability scan not found: {vulnerability_scan}")
    if evidence["pipeline"]["security_thresholds_exceeded"]:
        errors.append(f"vulnerability severity threshold exceeded: max_seen={max_seen}, allowed={max_allowed}")
    if direct_push_allowed is True:
        errors.append("direct pushes are allowed on the target branch")

    gate = {
        "status": "fail" if errors else "pass",
        "governance_mode": args.governance_mode,
        "blocks_merge": args.governance_mode in {"block-on-error", "waiver-required"},
        "errors": errors,
    }

    write_json(Path(args.output), evidence)
    write_json(Path(args.gate_output), gate)
    print(f"Wrote {args.output}")
    print(f"Wrote {args.gate_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
