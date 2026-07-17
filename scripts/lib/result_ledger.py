"""Append-only storage and report-only replay assessment for result snapshots."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Iterable
import hashlib
import json
import sys


REPLAY_CONTEXT_FIELDS = (
    "repository_id",
    "commit_id",
    "workflow_name",
    "run_id",
    "run_attempt",
    "artifact_name",
)


class AppendOnlyConflictError(RuntimeError):
    """Raised when an existing snapshot path would receive different evidence."""

    def __init__(self, target_path: Path, conflict_path: Path) -> None:
        self.target_path = target_path
        self.conflict_path = conflict_path
        super().__init__(
            f"Append-only conflict for {target_path}; conflict recorded at {conflict_path}"
        )


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def trust_from_snapshot(snapshot: dict) -> dict | None:
    if snapshot.get("model_id") == "evidence-trust-model-v1":
        return snapshot
    trust = snapshot.get("trust")
    return trust if isinstance(trust, dict) else None


def replay_context(trust: dict) -> dict:
    source = trust.get("capture", {}).get("source", {})
    context = {field: source.get(field) for field in REPLAY_CONTEXT_FIELDS}
    if source.get("artifact_digest"):
        context["artifact_digest"] = source["artifact_digest"]
    return context


def subject_digests(trust: dict) -> dict[str, str]:
    return {
        str(subject.get("id")): str(subject.get("digest"))
        for subject in trust.get("capture", {}).get("subjects", [])
        if subject.get("id") and subject.get("digest")
    }


def replay_key(trust: dict) -> str | None:
    context = replay_context(trust)
    subjects = subject_digests(trust)
    if any(value in {None, ""} for value in context.values()) or not subjects:
        return None
    return canonical_digest({"context": context, "subjects": subjects})


def load_snapshot_payloads(roots: Iterable[Path]) -> list[dict]:
    payloads = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if trust_from_snapshot(payload) is not None:
                payloads.append(payload)
    return payloads


def apply_replay_assessment(trust: dict, prior_snapshots: Iterable[dict]) -> dict:
    """Evaluate replay context without changing the evidence integrity level."""
    result = deepcopy(trust)
    current_context = replay_context(result)
    current_subjects = subject_digests(result)
    current_key = replay_key(result)
    check = {
        "id": "replay_key_unique",
        "result": "not_evaluated",
        "evidence_refs": ["trust.capture.source", "trust.capture.subjects"],
        "finding_effect": "report_only",
        "reason": "Replay identity is incomplete and cannot be evaluated.",
    }
    if current_key is not None:
        exact_matches = []
        context_conflicts = []
        incompatible_reuse = []
        compatible_reuse = []
        current_decision_context = {
            field: current_context.get(field)
            for field in ("repository_id", "commit_id", "artifact_name")
        }
        current_digest_values = set(current_subjects.values())
        for snapshot in prior_snapshots:
            prior = trust_from_snapshot(snapshot)
            if prior is None:
                continue
            prior_key = replay_key(prior)
            prior_context = replay_context(prior)
            prior_subjects = subject_digests(prior)
            if prior_key == current_key:
                exact_matches.append(prior_key)
                continue
            if prior_context == current_context and prior_subjects != current_subjects:
                context_conflicts.append(prior_key or canonical_digest(prior_context))
                continue
            reused = current_digest_values.intersection(prior_subjects.values())
            if not reused:
                continue
            prior_decision_context = {
                field: prior_context.get(field)
                for field in ("repository_id", "commit_id", "artifact_name")
            }
            artifact_changed = bool(
                current_context.get("artifact_digest")
                and prior_context.get("artifact_digest")
                and current_context.get("artifact_digest") != prior_context.get("artifact_digest")
            )
            reused_subject_ids = {
                subject_id
                for subject_id, digest in current_subjects.items()
                if digest in reused
            }
            deterministic_report_reuse = reused_subject_ids == {"control_evaluation_report"} and artifact_changed
            if prior_decision_context == current_decision_context or deterministic_report_reuse:
                compatible_reuse.append(prior_key or canonical_digest(prior_context))
            else:
                incompatible_reuse.append(prior_key or canonical_digest(prior_context))

        check["replay_key"] = current_key
        related = sorted(set(exact_matches + context_conflicts + incompatible_reuse + compatible_reuse))
        if related:
            check["related_replay_keys"] = related
        if context_conflicts:
            check["result"] = "fail"
            check["reason"] = "The same run context was previously recorded with different subject digests."
        elif incompatible_reuse:
            check["result"] = "fail"
            check["reason"] = "A subject digest was reused across an incompatible repository, commit, or artifact context."
        elif exact_matches:
            check["result"] = "pass"
            check["reason"] = "An identical replay key already exists; intake is idempotent."
        elif compatible_reuse:
            check["result"] = "pass"
            check["reason"] = "Digest reuse is confined to the same repository, commit, and artifact context."
        else:
            check["result"] = "pass"
            check["reason"] = "No prior replay key or incompatible digest reuse was found."

    checks = result.get("checks", [])
    replaced = False
    for index, existing in enumerate(checks):
        if existing.get("id") == "replay_key_unique":
            checks[index] = check
            replaced = True
            break
    if not replaced:
        checks.append(check)
    result["checks"] = checks
    return result


def evidence_identity(payload: dict) -> dict:
    trust = trust_from_snapshot(payload)
    if trust is None:
        return payload
    return {
        "context": replay_context(trust),
        "subjects": subject_digests(trust),
    }


def _write_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")


def _portable_status_path(path: Path) -> str:
    parts = path.parts
    if "status" in parts:
        return str(Path(*parts[parts.index("status") :]))
    return str(path)


def write_snapshot_append_only(
    path: Path,
    payload: dict,
    *,
    conflict_root: Path,
    raise_on_conflict: bool = False,
) -> Path:
    """Create a snapshot once, accept identical evidence, and quarantine conflicts."""
    if not path.exists() and path.parent.exists():
        for existing_path in sorted(path.parent.glob("*.json")):
            try:
                existing = json.loads(existing_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if evidence_identity(existing) == evidence_identity(payload):
                return existing_path
    if not path.exists():
        _write_exclusive(path, payload)
        return path

    existing = json.loads(path.read_text(encoding="utf-8"))
    if evidence_identity(existing) == evidence_identity(payload):
        return path

    existing_digest = canonical_digest(existing)
    incoming_digest = canonical_digest(payload)
    conflict = {
        "schema_version": "1.0.0",
        "conflict_type": "append_only_snapshot_conflict",
        "enforcement": "report_only",
        "detected_at": (
            payload.get("trust", {}).get("verified_at")
            or payload.get("generated_at")
            or "unknown"
        ),
        "target_path": _portable_status_path(path),
        "existing_payload_sha256": existing_digest,
        "incoming_payload_sha256": incoming_digest,
        "existing_evidence_identity": evidence_identity(existing),
        "incoming_evidence_identity": evidence_identity(payload),
    }
    conflict_path = conflict_root / path.parent.name / f"{path.stem}-conflict-{incoming_digest[:12]}.json"
    if not conflict_path.exists():
        _write_exclusive(conflict_path, conflict)
    error = AppendOnlyConflictError(path, conflict_path)
    if raise_on_conflict:
        raise error
    print(f"warning: {error}", file=sys.stderr)
    return path


def write_collection_attempt_append_only(
    path: Path,
    payload: dict,
    *,
    conflict_root: Path,
) -> Path:
    """Persist a failed/partial collection attempt without overwriting history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    attempt_id = payload.get("attempt_id")
    for existing_path in sorted(path.parent.glob("*.json")):
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if existing.get("attempt_id") == attempt_id:
            if canonical_digest(existing) == canonical_digest(payload):
                return existing_path
            conflict_path = conflict_root / f"{path.stem}-conflict-{canonical_digest(payload)[:12]}.json"
            if not conflict_path.exists():
                _write_exclusive(conflict_path, {
                    "schema_version": "1.0.0",
                    "conflict_type": "append_only_snapshot_conflict",
                    "enforcement": "report_only",
                    "detected_at": payload.get("attempted_at", "unknown"),
                    "target_path": _portable_status_path(existing_path),
                    "existing_payload_sha256": canonical_digest(existing),
                    "incoming_payload_sha256": canonical_digest(payload),
                    "existing_evidence_identity": {"attempt_id": attempt_id},
                    "incoming_evidence_identity": {"attempt_id": attempt_id},
                })
            return existing_path
    if not path.exists():
        _write_exclusive(path, payload)
        return path
    return write_collection_attempt_append_only(
        path.with_name(f"{path.stem}-retry{path.suffix}"),
        payload,
        conflict_root=conflict_root,
    )
