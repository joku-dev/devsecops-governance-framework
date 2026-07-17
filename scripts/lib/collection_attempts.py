"""Shared lifecycle projection for append-only evidence collection attempts."""

from __future__ import annotations


def collection_identity(record: dict) -> tuple[str, str, str] | None:
    source = record.get("source", {})
    repository_id = record.get("repository_id") or source.get("repository_id")
    run_id = source.get("run_id")
    artifact_name = source.get("artifact_name")
    if not repository_id or not run_id or not artifact_name:
        return None
    return repository_id, str(run_id), artifact_name


def project_collection_attempt_lifecycle(
    attempts: list[dict],
    snapshots: list[dict],
) -> list[dict]:
    successful = {}
    for snapshot in snapshots:
        capture_source = snapshot.get("trust", {}).get("capture", {}).get("source", {})
        identity = collection_identity({
            "repository_id": snapshot.get("repository_id"),
            "source": capture_source,
        })
        if identity:
            successful[identity] = {
                "resolved_at": snapshot.get("generated_at"),
                "source_file": snapshot.get("_source_file"),
            }

    projected = []
    for attempt in attempts:
        errors = attempt.get("errors", [])
        retryable = bool(errors) and all(error.get("retryable") is True for error in errors)
        resolution = successful.get(collection_identity(attempt))
        if resolution:
            state = "resolved"
        elif retryable:
            state = "open"
        else:
            state = "permanent"
        projected.append({
            **attempt,
            "lifecycle": {
                "state": state,
                "retryable": retryable,
                "resolved_at": resolution.get("resolved_at") if resolution else None,
                "resolution_source": resolution.get("source_file") if resolution else None,
            },
        })
    return projected
