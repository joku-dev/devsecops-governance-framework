#!/usr/bin/env python3
"""Collect DevSecOps release-readiness input from an application repository."""

from argparse import ArgumentParser
from pathlib import Path
import json
import subprocess


def git_commit(repo: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def load_evidence(repo: Path) -> dict:
    path = repo / ".governance" / "devsecops" / "release-evidence.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_path"] = str(path.relative_to(repo))
    return payload


def any_exists(repo: Path, patterns: list[str]) -> bool:
    return any(any(repo.glob(pattern)) for pattern in patterns)


def collect(repo: Path, release_id: str) -> dict:
    evidence = load_evidence(repo)
    approved = evidence.get("status") == "approved"
    has_ci = (repo / ".github" / "workflows" / "ci.yml").exists()
    has_iac = (repo / "docker-compose.yml").exists()
    requirements = sorted(str(path.relative_to(repo)) for path in repo.glob("**/requirements.txt"))

    repository_evidence = evidence.get("repository", {})
    sbom_evidence = evidence.get("sbom", {})
    vulnerability_evidence = evidence.get("vulnerability_scan", {})
    artifact_evidence = evidence.get("artifact", {})
    pipeline_evidence = evidence.get("pipeline", {})

    return {
        "release_candidate": True,
        "target_repository": {
            "path": str(repo),
            "commit": git_commit(repo),
            "release_id": release_id,
        },
        "repository": {
            "protected_branch": repository_evidence.get("protected_branch", approved),
            "direct_push_allowed": repository_evidence.get("direct_push_allowed", False if approved else True),
            "review_required": repository_evidence.get("review_required", approved),
        },
        "evidence": {
            "sbom": {
                "exists": sbom_evidence.get("exists", approved),
                "linked_to_artifact": sbom_evidence.get("linked_to_artifact", approved),
            },
            "vulnerability_scan": {
                "exists": vulnerability_evidence.get("exists", approved),
            },
        },
        "artifact": {
            "digest": {
                "exists": artifact_evidence.get("digest_exists", approved),
                "linked_to_artifact": artifact_evidence.get("digest_linked_to_artifact", approved),
            },
            "signature": {
                "exists": artifact_evidence.get("signature_exists", False),
            },
        },
        "pipeline": {
            "security_gates": {
                "enforced": pipeline_evidence.get("security_gates_enforced", approved and has_ci),
            },
            "security_thresholds_exceeded": pipeline_evidence.get("security_thresholds_exceeded", False),
            "external_direct_downloads_detected": pipeline_evidence.get("external_direct_downloads_detected", False),
        },
        "dependencies": [
            {
                "name": path,
                "source_approved": approved,
            }
            for path in requirements
        ],
        "infrastructure": {
            "iac_repository": {
                "exists": has_iac,
                "version_controlled": has_iac,
            }
        },
        "deployment": {
            "required": has_iac,
        },
        "release": {
            "release_id": release_id,
            "approval_status": "approved" if approved else "draft",
            "approved_waiver": {
                "exists": False,
            },
        },
        "vulnerabilities": [],
        "waivers": [],
        "evidence_refs": [evidence.get("_path")] + evidence.get("evidence_refs", []) if evidence else [],
    }


def main() -> int:
    parser = ArgumentParser(description="Collect DevSecOps release-readiness input from a target repository.")
    parser.add_argument("--repo", required=True, help="Target repository path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--release-id", default="demo-release-candidate", help="Release candidate identifier")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = collect(repo, args.release_id)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Generated {output}")
    print(f"- target repo: {repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
