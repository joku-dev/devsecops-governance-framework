"""Shared helpers for additive, report-only evidence trust capture."""

from __future__ import annotations

from pathlib import Path
import hashlib


MODEL_ID = "evidence-trust-model-v1"
COLLECTOR_ID = "central-governance-intake"


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
