"""Shared helpers for additive, report-only evidence trust capture."""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from datetime import datetime
import hashlib

import yaml


MODEL_ID = "evidence-trust-model-v1"
COLLECTOR_ID = "central-governance-intake"
COLLECTOR_VERSION = "0.1.0"
COLLECTOR_CONTRACT_ID = "evidence-collector-contract"
COLLECTOR_CONTRACT_VERSION = "0.1.0"
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


def load_freshness_policy(path: Path, policy_id: str) -> dict:
    policy_set = yaml.safe_load(path.read_text(encoding="utf-8"))
    policy = next((item for item in policy_set.get("policies", []) if item.get("id") == policy_id), None)
    if policy is None:
        raise ValueError(f"Unknown evidence freshness policy: {policy_id}")
    return {
        **policy,
        "policy_set_id": policy_set["policy_set_id"],
        "policy_version": policy_set["version"],
        "policy_status": policy_set["status"],
        "enforcement": policy_set["enforcement"],
        "defaults": policy_set["defaults"],
    }


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def evaluate_freshness(policy: dict, *, produced_at: str | None, evaluated_at: str) -> dict:
    defaults = policy["defaults"]
    check = {
        "id": "freshness_evaluated",
        "result": defaults["missing_metadata_result"],
        "evidence_refs": [policy["produced_at_claim"], policy["evaluated_at_claim"]],
        "policy_id": policy["id"],
        "policy_version": policy["policy_version"],
        "policy_status": policy["policy_status"],
        "produced_at": produced_at,
        "evaluated_at": evaluated_at,
        "maximum_age_seconds": policy.get("maximum_age_seconds"),
        "finding_effect": defaults["finding_effect"],
        "reason": "Required freshness timestamps are missing or invalid.",
    }
    produced = _parse_timestamp(produced_at)
    evaluated = _parse_timestamp(evaluated_at)
    if policy.get("evaluation_mode") != "max_age" or produced is None or evaluated is None:
        return check
    age_seconds = int((evaluated - produced).total_seconds())
    check["age_seconds"] = age_seconds
    maximum_age = policy["maximum_age_seconds"]
    if age_seconds < 0:
        check["result"] = defaults["future_timestamp_result"]
        check["reason"] = "Evidence production time is later than the verification time."
    elif age_seconds > maximum_age:
        check["result"] = defaults["expired_result"]
        check["reason"] = f"Evidence age {age_seconds}s exceeds the provisional maximum {maximum_age}s."
    else:
        check["result"] = "pass"
        check["reason"] = f"Evidence age {age_seconds}s is within the provisional maximum {maximum_age}s."
    return check


def build_trust_capture(
    *,
    governance_domain: str,
    repository_id: str,
    commit_id: str,
    workflow_name: str,
    run_id: str,
    run_attempt: int | None,
    artifact_name: str,
    source_uri: str,
    produced_at: str,
    captured_at: str,
    subjects: list[dict],
) -> dict:
    if governance_domain not in {"devsecops", "architecture"}:
        raise ValueError(f"Unsupported governance collector domain: {governance_domain}")
    if not isinstance(run_attempt, int) or isinstance(run_attempt, bool) or run_attempt < 1:
        raise ValueError("A positive GitHub Actions run attempt is required for collected evidence")
    if _parse_timestamp(produced_at) is None or _parse_timestamp(captured_at) is None:
        raise ValueError("Timezone-aware collector produced_at and captured_at timestamps are required")
    repository_parts = repository_id.split("/")
    source_values = [commit_id, workflow_name, str(run_id), artifact_name, source_uri]
    if (
        len(repository_parts) != 2
        or not all(repository_parts)
        or any(not value or value.strip().lower() in {"none", "null", "unknown"} for value in source_values)
    ):
        raise ValueError("Complete governance-result source identity is required for collected evidence")
    if not subjects:
        raise ValueError("At least one digested subject is required for collected evidence")
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
            "contract_id": COLLECTOR_CONTRACT_ID,
            "contract_version": COLLECTOR_CONTRACT_VERSION,
            "status": "collected",
            "enforcement": "report_only",
            "evidence_type": "governance_result",
            "governance_domain": governance_domain,
            "collector": {
                "id": COLLECTOR_ID,
                "version": COLLECTOR_VERSION,
            },
            "produced_at": produced_at,
            "captured_at": captured_at,
            "source": {
                "provider": "github_actions",
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
            "errors": [],
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
    freshness_policy: dict | None = None,
    produced_at: str | None = None,
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
    if freshness_policy is not None:
        checks["freshness_evaluated"] = evaluate_freshness(
            freshness_policy,
            produced_at=produced_at,
            evaluated_at=verified_at,
        )

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
