"""Neutral source-declaration collector extracted from frozen V1.

Source lineage: 6b557fefe295b58272d2271326576ca3a3687197 / scripts/collect_devsecops_release_input.py.
The caller freezes source bytes and supplies commit/CI observations explicitly.
Historical approval fields are declarations, not independent evidence or authority.
"""
from pathlib import Path

from lib.portable.runtime import read_json

def load_evidence(repo: Path) -> dict:
    path = repo / ".governance" / "devsecops" / "release-evidence.json"
    if not path.exists():
        return {}
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError('source_evidence_object_required')
    payload["_path"] = str(path.relative_to(repo))
    return payload

def any_exists(repo: Path, patterns: list[str]) -> bool:
    return any(any(repo.glob(pattern)) for pattern in patterns)

def collect(repo: Path, release_id: str, *, source_commit: str, ci_signals: dict) -> dict:
    evidence = load_evidence(repo)
    approved = evidence.get("status") == "approved"
    has_ci = ci_signals["ci_definition_present"]
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
            "commit": source_commit,
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
