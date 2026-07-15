"""Shared helpers for additive, report-only evidence trust capture."""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy
import hashlib


MODEL_ID = "evidence-trust-model-v1"
COLLECTOR_ID = "central-governance-intake"
VERIFIER_ID = "central-governance-intake/v1"
CHECK_IDS = [
    "subject_identity_complete",
    "content_digest_verified",
    "producer_run_resolved",
    "commit_matches_run",
    "artifact_belongs_to_run",
    "baseline_ref_resolved",
    "freshness_evaluated",
    "replay_key_unique",
    "custody_recorded",
    "attestation_signature_valid",
    "attestation_issuer_trusted",
    "attestation_subject_matches",
]


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def digest_subject(subject_id: str, path: Path, evidence_ref: str) -> dict:
    return {
        "id": subject_id,
        "evidence_ref": evidence_ref,
        "algorithm": "sha256",
        "digest": compute_sha256(path),
        "size_bytes": path.stat().st_size,
    }


def build_trust_capture(
    *,
    repository_id: str,
    commit_id: str,
    workflow_name: str,
    run_id: str,
    run_attempt: int | None,
    artifact_name: str,
    source_uri: str,
    captured_at: str,
    subjects: list[dict],
) -> dict:
    subject_refs = [subject["evidence_ref"] for subject in subjects]
    return {
        "model_id": MODEL_ID,
        "capture_phase": "additive_capture",
        "effective_level": "unverified",
        "assessment_status": "not_evaluated",
        "verifier": None,
        "verified_at": None,
        "checks": [],
        "capture": {
            "collector": COLLECTOR_ID,
            "captured_at": captured_at,
            "source": {
                "repository_id": repository_id,
                "commit_id": commit_id,
                "workflow_name": workflow_name,
                "run_id": str(run_id),
                "run_attempt": run_attempt,
                "artifact_name": artifact_name,
                "source_uri": source_uri,
            },
            "subjects": subjects,
            "custody": [
                {
                    "sequence": 1,
                    "action": "download",
                    "actor": COLLECTOR_ID,
                    "at": captured_at,
                    "source_uri": source_uri,
                    "output_refs": ["artifact_metadata"],
                },
                {
                    "sequence": 2,
                    "action": "extract_and_hash",
                    "actor": COLLECTOR_ID,
                    "at": captured_at,
                    "source_uri": source_uri,
                    "output_refs": subject_refs,
                },
            ],
        },
    }


def verify_trust_capture(
    trust: dict,
    *,
    repository_id: str,
    commit_id: str,
    run_id: str,
    artifact_name: str,
    subject_paths: dict[str, Path],
    verified_at: str,
) -> dict:
    """Evaluate only checks supported by authoritative intake-time material."""
    result = deepcopy(trust)
    source = result.get("capture", {}).get("source", {})
    subjects = result.get("capture", {}).get("subjects", [])
    checks = {
        check_id: {"id": check_id, "result": "not_evaluated", "evidence_refs": []}
        for check_id in CHECK_IDS
    }

    identity_matches = (
        source.get("repository_id") == repository_id
        and source.get("commit_id") == commit_id
        and source.get("run_id") == str(run_id)
        and source.get("artifact_name") == artifact_name
        and isinstance(source.get("run_attempt"), int)
        and not isinstance(source.get("run_attempt"), bool)
        and bool(subjects)
    )
    checks["subject_identity_complete"] = {
        "id": "subject_identity_complete",
        "result": "pass" if identity_matches else "fail",
        "evidence_refs": ["trust.capture.source", "trust.capture.subjects"],
    }

    digest_matches = bool(subjects) and {subject.get("id") for subject in subjects} == set(subject_paths)
    for subject in subjects:
        path = subject_paths.get(subject.get("id"))
        if path is None or not path.is_file():
            digest_matches = False
            continue
        digest_matches = digest_matches and subject.get("algorithm") == "sha256"
        digest_matches = digest_matches and subject.get("digest") == compute_sha256(path)
        digest_matches = digest_matches and subject.get("size_bytes") == path.stat().st_size
    checks["content_digest_verified"] = {
        "id": "content_digest_verified",
        "result": "pass" if digest_matches else "fail",
        "evidence_refs": [subject.get("evidence_ref", "") for subject in subjects if subject.get("evidence_ref")],
    }

    for check_id, passed, evidence_refs in [
        ("producer_run_resolved", source.get("run_id") == str(run_id), ["trust.capture.source.run_id"]),
        ("commit_matches_run", source.get("commit_id") == commit_id, ["trust.capture.source.commit_id"]),
        (
            "artifact_belongs_to_run",
            source.get("artifact_name") == artifact_name,
            ["trust.capture.source.artifact_name"],
        ),
    ]:
        checks[check_id] = {
            "id": check_id,
            "result": "pass" if passed else "fail",
            "evidence_refs": evidence_refs,
        }

    integrity_verified = all(
        checks[check_id]["result"] == "pass"
        for check_id in ("subject_identity_complete", "content_digest_verified")
    )
    result.update(
        {
            "effective_level": "integrity_verified" if integrity_verified else "unverified",
            "assessment_status": "evaluated",
            "verifier": VERIFIER_ID,
            "verified_at": verified_at,
            "checks": [checks[check_id] for check_id in CHECK_IDS],
        }
    )
    return result


def project_trust(snapshot: dict) -> dict:
    """Create the small, outcome-independent trust projection used by indexes."""
    trust = snapshot.get("trust")
    if not isinstance(trust, dict):
        return {
            "effective_level": "unverified",
            "assessment_status": "not_available",
            "verified_at": None,
            "check_summary": {"pass": 0, "fail": 0, "not_evaluated": 0},
        }
    summary = {"pass": 0, "fail": 0, "not_evaluated": 0}
    for check in trust.get("checks", []):
        check_result = check.get("result", "not_evaluated")
        summary[check_result] = summary.get(check_result, 0) + 1
    return {
        "effective_level": trust.get("effective_level", "unverified"),
        "assessment_status": trust.get("assessment_status", "not_evaluated"),
        "verified_at": trust.get("verified_at"),
        "check_summary": summary,
    }
