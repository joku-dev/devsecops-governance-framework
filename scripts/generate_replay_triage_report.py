#!/usr/bin/env python3
"""Explain stored replay checks without rewriting evidence or Trust records."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from lib.result_ledger import (
    apply_replay_assessment,
    replay_context,
    replay_key,
    subject_digests,
    trust_from_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOTS = {
    "devsecops": ROOT / "status" / "results",
    "architecture": ROOT / "status" / "architecture-results",
    "typed_evidence": ROOT / "status" / "typed-evidence-results",
}


def replay_check(trust: dict) -> dict:
    return next(
        (item for item in trust.get("checks", []) if item.get("id") == "replay_key_unique"),
        {"result": "not_evaluated", "reason": "Replay check is absent."},
    )


def load_rows(snapshot_roots: dict[str, Path]) -> list[dict]:
    rows = []
    for domain, root in snapshot_roots.items():
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            trust = trust_from_snapshot(payload)
            if trust is None:
                continue
            rows.append({
                "domain": domain,
                "source_file": str(path.relative_to(ROOT)),
                "payload": payload,
                "trust": trust,
                "generated_at": payload.get("generated_at", ""),
            })
    return sorted(rows, key=lambda item: (item["generated_at"], item["source_file"]))


def latest_source_files(indexes: list[dict]) -> set[str]:
    return {
        latest["source_file"]
        for index in indexes
        for repository in index.get("repositories", [])
        for latest in [repository.get("latest_result", {})]
        if latest.get("source_file")
    }


def relationship(current: dict, prior: dict) -> dict | None:
    current_trust, prior_trust = current["trust"], prior["trust"]
    current_key, prior_key = replay_key(current_trust), replay_key(prior_trust)
    current_context, prior_context = replay_context(current_trust), replay_context(prior_trust)
    current_subjects, prior_subjects = subject_digests(current_trust), subject_digests(prior_trust)
    if current_key and current_key == prior_key:
        classification = "idempotent_reintake"
        shared_ids = sorted(set(current_subjects) & set(prior_subjects))
    else:
        shared = {
            digest
            for digest in current_subjects.values()
            if digest in set(prior_subjects.values())
        }
        if not shared and not (current_context == prior_context and current_subjects != prior_subjects):
            return None
        pairs = [
            (current_id, prior_id)
            for current_id, digest in current_subjects.items()
            for prior_id, prior_digest in prior_subjects.items()
            if digest == prior_digest
        ]
        shared_ids = sorted({item for pair in pairs for item in pair})
        if current_context == prior_context and current_subjects != prior_subjects:
            classification = "same_context_content_conflict"
        elif any(current_id != prior_id for current_id, prior_id in pairs):
            classification = "cross_subject_conflict"
        elif current_context.get("repository_id") != prior_context.get("repository_id"):
            classification = "cross_repository_reuse"
        else:
            reused_ids = {current_id for current_id, _ in pairs}
            artifact_changed = bool(
                current_context.get("artifact_digest")
                and prior_context.get("artifact_digest")
                and current_context.get("artifact_digest") != prior_context.get("artifact_digest")
            )
            legacy_artifact = bool(current_context.get("artifact_digest")) and not prior_context.get("artifact_digest")
            if reused_ids == {"control_evaluation_report"} and (artifact_changed or legacy_artifact):
                classification = "deterministic_report_reuse"
            elif current_context.get("artifact_name") != prior_context.get("artifact_name"):
                classification = "cross_artifact_reuse"
            elif current_context.get("commit_id") != prior_context.get("commit_id"):
                classification = "cross_commit_reuse"
            else:
                classification = "compatible_reuse"
    payload = prior["payload"]
    pipeline = payload.get("pipeline", {})
    repository = payload.get("repository", {})
    return {
        "classification": classification,
        "replay_key": prior_key,
        "source_file": prior["source_file"],
        "repository_id": payload.get("repository_id"),
        "commit_id": repository.get("commit_id") or replay_context(prior_trust).get("commit_id"),
        "run_id": pipeline.get("pipeline_run_id") or replay_context(prior_trust).get("run_id"),
        "artifact_name": replay_context(prior_trust).get("artifact_name"),
        "shared_subject_ids": shared_ids,
    }


def choose_classification(recorded: dict, recalculated: dict, relationships: list[dict]) -> str:
    if recalculated.get("result") == "not_evaluated":
        return "not_evaluated"
    if recorded.get("result") == "fail" and recalculated.get("result") == "pass":
        return "legacy_assessment_superseded"
    priority = [
        "same_context_content_conflict",
        "cross_repository_reuse",
        "cross_subject_conflict",
        "cross_artifact_reuse",
        "cross_commit_reuse",
        "idempotent_reintake",
        "deterministic_report_reuse",
        "compatible_reuse",
    ]
    present = {item["classification"] for item in relationships}
    for classification in priority:
        if classification in present:
            return classification
    return "new_evidence"


def guidance(classification: str) -> tuple[str, str]:
    guidance_by_classification = {
        "not_evaluated": ("collect_complete_replay_identity", "Replay identity is incomplete; collect repository, commit, run attempt, artifact, and subject digests."),
        "new_evidence": ("none", "No earlier digest reuse or conflicting replay identity was found."),
        "idempotent_reintake": ("none", "The exact replay identity was already recorded; append-only intake is idempotent."),
        "compatible_reuse": ("none", "Digest reuse remains inside the same decision context."),
        "deterministic_report_reuse": ("none", "Only the deterministic control report is reused while artifact identity distinguishes the runs."),
        "legacy_assessment_superseded": ("use_current_policy_on_new_intake", "The stored failure is retained historically, but current report-only replay logic evaluates the same evidence pattern as compatible."),
        "cross_commit_reuse": ("reverify_with_artifact_digest", "The same subject digest crosses commits without sufficient artifact binding to prove deterministic reuse."),
        "cross_repository_reuse": ("investigate_cross_repository_provenance", "A subject digest crosses repository boundaries and requires provenance review."),
        "cross_artifact_reuse": ("investigate_artifact_binding", "A subject digest crosses artifact identities and requires binding review."),
        "cross_subject_conflict": ("investigate_subject_identity", "The same digest is attributed to different subject identifiers."),
        "same_context_content_conflict": ("investigate_same_context_mutation", "The same run context has different subject content and must remain quarantined for review."),
    }
    return guidance_by_classification[classification]


def build_report(*, rows: list[dict], official_latest: set[str]) -> dict:
    assessments = []
    prior_rows = []
    for row in rows:
        trust = row["trust"]
        recorded = replay_check(trust)
        recalculated_trust = apply_replay_assessment(trust, [item["payload"] for item in prior_rows])
        recalculated = replay_check(recalculated_trust)
        related_keys = set(recalculated.get("related_replay_keys", []))
        relationships = [
            value
            for prior in prior_rows
            for value in [relationship(row, prior)]
            if value is not None and (not related_keys or value.get("replay_key") in related_keys)
        ]
        classification = choose_classification(recorded, recalculated, relationships)
        action, explanation = guidance(classification)
        payload = row["payload"]
        pipeline, repository = payload.get("pipeline", {}), payload.get("repository", {})
        context = replay_context(trust)
        assessments.append({
            "domain": row["domain"],
            "repository_id": payload.get("repository_id") or context.get("repository_id"),
            "generated_at": row["generated_at"],
            "run_id": pipeline.get("pipeline_run_id") or context.get("run_id"),
            "event": pipeline.get("event", "unknown"),
            "commit_id": repository.get("commit_id") or context.get("commit_id"),
            "artifact_name": context.get("artifact_name"),
            "artifact_digest_available": bool(context.get("artifact_digest")),
            "source_file": row["source_file"],
            "official_latest": row["source_file"] in official_latest,
            "recorded_result": recorded.get("result", "not_evaluated"),
            "recalculated_result": recalculated.get("result", "not_evaluated"),
            "classification": classification,
            "recommended_action": action,
            "explanation": explanation,
            "replay_key": recalculated.get("replay_key") or recorded.get("replay_key"),
            "relationships": relationships,
        })
        prior_rows.append(row)
    counts = Counter(item["classification"] for item in assessments)
    latest_findings = [
        item for item in assessments
        if item["official_latest"] and item["recalculated_result"] == "fail"
    ]
    return {
        "schema_version": "1.0.0",
        "projection_type": "replay-triage",
        "generated_at": max((item["generated_at"] for item in assessments), default="1970-01-01T00:00:00Z"),
        "enforcement": "report_only",
        "decision_boundary": {
            "historical_snapshots_rewritten": False,
            "latest_selection_changed": False,
            "trust_levels_changed": False,
            "enforcement_change_authorized": False,
        },
        "summary": {
            "assessments": len(assessments),
            "recorded_failures": sum(item["recorded_result"] == "fail" for item in assessments),
            "recalculated_failures": sum(item["recalculated_result"] == "fail" for item in assessments),
            "legacy_assessments_superseded": counts.get("legacy_assessment_superseded", 0),
            "official_latest_findings": len(latest_findings),
            "classification_counts": dict(sorted(counts.items())),
        },
        "official_latest_findings": [item["source_file"] for item in latest_findings],
        "assessments": assessments,
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Replay Triage Report", "", f"Generated from latest stored snapshot time: `{report['generated_at']}`", "",
        "## Summary", "",
        f"- Assessments: {summary['assessments']}",
        f"- Stored replay failures: {summary['recorded_failures']}",
        f"- Failures under current report-only interpretation: {summary['recalculated_failures']}",
        f"- Superseded legacy assessments: {summary['legacy_assessments_superseded']}",
        f"- Official latest findings: {summary['official_latest_findings']}", "",
        "No historical snapshot, latest-result pointer, Trust level, or enforcement behavior is changed.", "",
        "## Official Latest Assessments", "",
        "| Domain | Repository | Run | Recorded | Current interpretation | Classification | Action |", "|---|---|---:|---|---|---|---|",
    ]
    for item in report["assessments"]:
        if item["official_latest"]:
            lines.append(
                f"| `{item['domain']}` | `{item['repository_id']}` | `{item['run_id']}` | "
                f"`{item['recorded_result']}` | `{item['recalculated_result']}` | "
                f"`{item['classification']}` | `{item['recommended_action']}` |"
            )
    lines.extend(["", "## Classification Counts", "", "| Classification | Count |", "|---|---:|"])
    for classification, count in summary["classification_counts"].items():
        lines.append(f"| `{classification}` | {count} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = load_rows(SNAPSHOT_ROOTS)
    indexes = [
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "status/repository-results-index.json",
            "status/architecture-results-index.json",
            "status/typed-evidence-results-index.json",
        )
    ]
    report = build_report(rows=rows, official_latest=latest_source_files(indexes))
    output_json = ROOT / "generated" / "reports" / "replay-triage.json"
    output_md = ROOT / "generated" / "reports" / "replay-triage.md"
    output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    output_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        f"Wrote Replay Triage: {report['summary']['assessments']} assessments, "
        f"{report['summary']['official_latest_findings']} official latest findings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
