"""Shared helpers for additive, report-only evidence trust capture."""

from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import hashlib
import json

import yaml


MODEL_ID = "evidence-trust-model-v1"
COLLECTOR_ID = "central-governance-intake"
COLLECTOR_VERSION = "0.1.0"
COLLECTOR_CONTRACT_ID = "evidence-collector-contract"
COLLECTOR_CONTRACT_VERSION = "0.1.0"
VERIFIER_ID = "central-governance-intake/v1"
ROOT = Path(__file__).resolve().parents[2]
TRUST_MODEL_PATH = ROOT / "model" / "evidence" / "evidence-trust-model.yaml"
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


def canonical_sha256(value: dict) -> str:
    """Hash a JSON object using stable UTF-8 canonical serialization."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _trust_levels() -> list[dict]:
    model = yaml.safe_load(TRUST_MODEL_PATH.read_text(encoding="utf-8"))
    return sorted(model["trust_levels"], key=lambda item: item["rank"])


def derive_effective_level(checks: list[dict]) -> str:
    """Assign the highest trust level whose complete model requirements pass."""
    results = {check.get("id"): check.get("result") for check in checks}
    level = "unverified"
    for candidate in _trust_levels():
        if all(results.get(check_id) == "pass" for check_id in candidate["required_checks"]):
            level = candidate["id"]
    return level


def promote_effective_level(current_level: str, checks: list[dict]) -> str:
    """Promote an evaluated record when checks justify it, without reclassifying history downward."""
    levels = _trust_levels()
    ranks = {candidate["id"]: candidate["rank"] for candidate in levels}
    derived = derive_effective_level(checks)
    if current_level not in ranks:
        current_level = "unverified"
    return derived if ranks[derived] > ranks[current_level] else current_level


def _evaluate_custody(capture: dict) -> dict:
    source = capture.get("source", {})
    subjects = capture.get("subjects", [])
    collector = capture.get("collector", {})
    collector_id = collector.get("id") if isinstance(collector, dict) else collector
    steps = capture.get("custody", [])
    source_uri = source.get("source_uri")
    archive = next((subject for subject in subjects if subject.get("id") == "artifact_archive"), None)
    if archive is None:
        return {
            "id": "custody_recorded",
            "result": "not_evaluated",
            "evidence_refs": [],
            "reason": "This collector capture has no downloaded archive subject for the custody verifier to bind.",
        }
    artifact_digest = source.get("artifact_digest")
    step_times = [_parse_timestamp(step.get("at")) for step in steps if isinstance(step, dict)]
    ordered_records = len(steps) == 2 and all(isinstance(step, dict) for step in steps)
    valid = (
        ordered_records
        and [step.get("sequence") for step in steps] == [1, 2]
        and [step.get("action") for step in steps] == ["download", "extract_and_hash"]
        and bool(collector_id)
        and bool(source_uri)
        and all(step.get("actor") == collector_id for step in steps)
        and all(step.get("source_uri") == source_uri for step in steps)
        and len(step_times) == 2
        and all(timestamp is not None for timestamp in step_times)
        and step_times[0] <= step_times[1]
        and "artifact_metadata" in steps[0].get("output_refs", [])
        and bool(subjects)
        and all(subject.get("evidence_ref") in steps[1].get("output_refs", []) for subject in subjects)
        and isinstance(archive.get("digest"), str)
        and len(archive["digest"]) == 64
        and all(char in "0123456789abcdef" for char in archive["digest"])
        and (artifact_digest is None or artifact_digest == archive.get("digest"))
        and all(_parse_timestamp(value) is not None for value in (capture.get("captured_at"), capture.get("produced_at")))
        and not capture.get("errors")
    )
    return {
        "id": "custody_recorded",
        "result": "pass" if valid else "fail",
        "evidence_refs": ["trust.capture.custody", "trust.capture.source.artifact_digest", "trust.capture.subjects"],
        "reason": "Ordered download and extraction steps bind the downloaded archive to the hashed subjects."
        if valid
        else "Custody steps, timestamps, archive digest, or subject bindings are incomplete or inconsistent.",
    }


def _evaluate_baseline(baseline: dict | None, selected_ref: str | None) -> dict:
    valid = (
        isinstance(baseline, dict)
        and isinstance(baseline.get("ref"), str)
        and baseline["ref"].startswith("refs/tags/")
        and baseline["ref"].removeprefix("refs/tags/") == selected_ref
        and isinstance(baseline.get("sha"), str)
        and len(baseline["sha"]) == 40
        and all(char in "0123456789abcdef" for char in baseline["sha"].lower())
    )
    return {
        "id": "baseline_ref_resolved",
        "result": "pass" if valid else "fail",
        "evidence_refs": (baseline.get("evidence_refs") or [
            "run.referenced_workflows[].ref", "run.referenced_workflows[].sha"
        ]) if baseline else [],
        "reason": "Selected governance baseline matches an immutable tagged workflow reference and resolved commit."
        if valid
        else "Governance baseline is missing, unpinned, unresolved, or differs from authoritative run metadata.",
    }


def evaluate_freshness(
    policy: dict,
    *,
    produced_at: str | None,
    evaluated_at: str,
    subject_bound: bool | None = None,
) -> dict:
    defaults = policy["defaults"]
    mode = policy.get("evaluation_mode")
    evidence_refs = (
        [policy["subject_claim"]]
        if mode == "subject_bound"
        else [policy.get("produced_at_claim", "trust.capture.produced_at"), policy.get("evaluated_at_claim", "trust.verified_at")]
    )
    check = {
        "id": "freshness_evaluated",
        "result": defaults["missing_metadata_result"],
        "evidence_refs": evidence_refs,
        "policy_id": policy["id"],
        "policy_version": policy["policy_version"],
        "policy_status": policy["policy_status"],
        "produced_at": produced_at,
        "evaluated_at": evaluated_at,
        "maximum_age_seconds": policy.get("maximum_age_seconds"),
        "finding_effect": defaults["finding_effect"],
        "reason": "Required freshness timestamps are missing or invalid.",
    }
    if mode == "subject_bound":
        if subject_bound is not None:
            check["result"] = "pass" if subject_bound else "fail"
            check["reason"] = (
                "Evidence is bound to the centrally verified immutable subject."
                if subject_bound
                else "Evidence is not bound to the centrally verified immutable subject."
            )
        return check
    produced = _parse_timestamp(produced_at)
    evaluated = _parse_timestamp(evaluated_at)
    if mode != "max_age" or produced is None or evaluated is None:
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
    return build_typed_trust_capture(
        evidence_type="governance_result",
        governance_domain=governance_domain,
        collector_id=COLLECTOR_ID,
        collector_version=COLLECTOR_VERSION,
        source_provider="github_actions",
        repository_id=repository_id,
        commit_id=commit_id,
        workflow_name=workflow_name,
        run_id=run_id,
        run_attempt=run_attempt,
        artifact_name=artifact_name,
        source_uri=source_uri,
        produced_at=produced_at,
        captured_at=captured_at,
        subjects=subjects,
    )


def build_typed_trust_capture(
    *,
    evidence_type: str,
    governance_domain: str,
    collector_id: str,
    collector_version: str,
    source_provider: str,
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
    observations: dict | None = None,
) -> dict:
    if governance_domain not in {"devsecops", "architecture"}:
        raise ValueError(f"Unsupported governance collector domain: {governance_domain}")
    if not evidence_type or not collector_id or not collector_version or not source_provider:
        raise ValueError("Evidence type, collector identity, version, and source provider are required")
    if not isinstance(run_attempt, int) or isinstance(run_attempt, bool) or run_attempt < 1:
        raise ValueError("A positive CI run attempt is required for collected evidence")
    if _parse_timestamp(produced_at) is None or _parse_timestamp(captured_at) is None:
        raise ValueError("Timezone-aware collector produced_at and captured_at timestamps are required")
    repository_parts = repository_id.split("/")
    source_values = [commit_id, workflow_name, str(run_id), artifact_name, source_uri]
    if (
        len(repository_parts) != 2
        or not all(repository_parts)
        or any(not value or value.strip().lower() in {"none", "null", "unknown"} for value in source_values)
    ):
        raise ValueError("Complete source identity is required for collected evidence")
    if not subjects:
        raise ValueError("At least one digested subject is required for collected evidence")
    subject_refs = [subject["evidence_ref"] for subject in subjects]
    capture = {
        "contract_id": COLLECTOR_CONTRACT_ID,
        "contract_version": COLLECTOR_CONTRACT_VERSION,
        "status": "collected",
        "enforcement": "report_only",
        "evidence_type": evidence_type,
        "governance_domain": governance_domain,
        "collector": {
            "id": collector_id,
            "version": collector_version,
        },
        "produced_at": produced_at,
        "captured_at": captured_at,
        "source": {
            "provider": source_provider,
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
                "actor": collector_id,
                "at": captured_at,
                "source_uri": source_uri,
                "output_refs": ["artifact_metadata"],
            },
            {
                "sequence": 2,
                "action": "extract_and_hash",
                "actor": collector_id,
                "at": captured_at,
                "source_uri": source_uri,
                "output_refs": subject_refs,
            },
        ],
        "errors": [],
    }
    if observations is not None:
        capture["observations"] = observations
    return {
        "model_id": MODEL_ID,
        "capture_phase": "additive_capture",
        "effective_level": "unverified",
        "assessment_status": "not_evaluated",
        "verifier": None,
        "verified_at": None,
        "checks": [],
        "capture": capture,
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
    freshness_subject_bound: bool | None = None,
    baseline: dict | None = None,
    baseline_ref: str | None = None,
    custody_record: dict | None = None,
    verifier_id: str = VERIFIER_ID,
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

    checks["custody_recorded"] = _evaluate_custody(result.get("capture", {}))
    if baseline is not None or baseline_ref is not None:
        checks["baseline_ref_resolved"] = _evaluate_baseline(baseline, baseline_ref)

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
            subject_bound=freshness_subject_bound,
        )

    if baseline is not None or baseline_ref is not None:
        checks["baseline_ref_resolved"] = _evaluate_baseline(baseline, baseline_ref)

    if custody_record is not None:
        result["capture"]["custody_record"] = deepcopy(custody_record)
        expected_transformations = {
            "download_github_actions_artifacts",
            "verify_zip_metadata_and_sha256",
            "extract_selected_members",
            "verify_subject_hashes",
            "normalize_typed_evidence",
        }
        transformations = custody_record.get("transformations")
        capture = result["capture"]
        expected_normalized_digest = canonical_sha256({
            "profile": capture.get("observations", {}).get("profile"),
            "repository_id": source.get("repository_id"),
            "commit_id": source.get("commit_id"),
            "run_id": source.get("run_id"),
            "subjects": subjects,
            "observations": capture.get("observations", {}),
        })
        custody_valid = (
            isinstance(custody_record.get("collector"), str)
            and bool(custody_record.get("collector"))
            and _parse_timestamp(custody_record.get("collected_at")) is not None
            and all(
                isinstance(custody_record.get(key), str)
                and len(custody_record[key]) == 64
                and all(character in "0123456789abcdef" for character in custody_record[key])
                for key in ("raw_digest", "normalized_digest")
            )
            and isinstance(custody_record.get("raw_artifacts"), dict)
            and custody_record.get("raw_digest") == canonical_sha256(custody_record["raw_artifacts"])
            and custody_record.get("normalized_digest") == expected_normalized_digest
            and isinstance(transformations, list)
            and set(transformations) == expected_transformations
        )
        checks["custody_recorded"] = {
            "id": "custody_recorded",
            "result": "pass" if custody_valid else "fail",
            "evidence_refs": ["trust.capture.custody_record", "trust.capture.custody"],
            "reason": "Collector, acquisition time, raw and normalized digests, and transformation steps are recorded."
            if custody_valid
            else "Chain-of-custody record is incomplete or invalid.",
        }

    integrity_verified = all(
        checks[check_id]["result"] == "pass"
        for check_id in ("subject_identity_complete", "content_digest_verified")
    )
    result.update(
        {
            "effective_level": "integrity_verified" if integrity_verified else "unverified",
            "assessment_status": "evaluated",
            "verifier": verifier_id,
            "verified_at": verified_at,
            "checks": [checks[check_id] for check_id in CHECK_IDS],
        }
    )
    result["effective_level"] = derive_effective_level(result["checks"])
    return result


def project_trust(snapshot: dict) -> dict:
    """Create the small, outcome-independent trust projection used by indexes."""
    trust = snapshot.get("trust")
    if not isinstance(trust, dict):
        return {
            "effective_level": "unverified",
            "assessment_status": "not_available",
            "verified_at": None,
            "replay": "not_evaluated",
            "check_summary": {"pass": 0, "fail": 0, "not_evaluated": 0},
        }
    summary = {"pass": 0, "fail": 0, "not_evaluated": 0}
    replay = "not_evaluated"
    for check in trust.get("checks", []):
        check_result = check.get("result", "not_evaluated")
        summary[check_result] = summary.get(check_result, 0) + 1
        if check.get("id") == "replay_key_unique":
            replay = check_result
    return {
        "effective_level": trust.get("effective_level", "unverified"),
        "assessment_status": trust.get("assessment_status", "not_evaluated"),
        "verified_at": trust.get("verified_at"),
        "replay": replay,
        "check_summary": summary,
    }
