#!/usr/bin/env python3
"""Generate a report-only blocking-readiness decision aid."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(identifier: str, status: str, observed, expected, *refs: str, required: bool = True) -> dict:
    return {"id": identifier, "status": status, "required": required, "observed": observed,
            "expected": expected, "evidence_refs": list(refs)}


def repo_map(index: dict) -> dict[str, dict]:
    return {item["repository_id"]: item for item in index.get("repositories", [])}


def assess(*, integrations: dict, devsecops: dict, architecture: dict, typed: dict,
           health: dict, model: dict, conflict_root: Path) -> dict:
    dev_map, arch_map, typed_map = repo_map(devsecops), repo_map(architecture), repo_map(typed)
    health_by_repo = {item["value"]: item["metrics"] for item in health.get("dimensions", [])
                      if item.get("dimension") == "repository_id"}
    ranks = {"unverified": 0, "integrity_verified": 1, "provenance_verified": 2, "attested": 3}
    threshold = model["thresholds"]
    assessments = []
    for integration in sorted(integrations.get("integrations", []), key=lambda item: item["repository"]):
        repository_id = integration["repository"]
        encoded = repository_id.replace("/", "__")
        dev = dev_map.get(repository_id, {})
        latest = dev.get("latest_result") or {}
        history = [item for item in dev.get("history", []) if item.get("pipeline_event") == "push" and item.get("branch") == "main"]
        recent = history[-threshold["minimum_mainline_successes"]:]
        baseline = latest.get("governance_baseline_ref", "")
        trust = latest.get("trust", {})
        typed_latest = (typed_map.get(repository_id, {}).get("latest_result") or {})
        arch_latest = (arch_map.get(repository_id, {}).get("latest_result") or {})
        metrics = health_by_repo.get(repository_id, {})
        conflicts = [path for path in conflict_root.rglob("*.json") if encoded in path.as_posix()] if conflict_root.exists() else []
        open_attempts = health.get("summary", {}).get("collection_attempts", {}).get("open", 0)
        has_architecture = bool(arch_latest)
        checks = [
            criterion("released_baseline_pinned", "pass" if baseline.startswith("l1-baseline-v") else "fail", baseline, "l1-baseline-v*", "status/repository-results-index.json"),
            criterion("latest_devsecops_result_clean", "pass" if latest.get("status") == "pass" else "fail", latest.get("status"), "pass", "status/repository-results-index.json"),
            criterion("stable_mainline_sample", "pass" if len(recent) == threshold["minimum_mainline_successes"] and all(item.get("status") == "pass" for item in recent) else "fail", {"sample": len(recent), "passing": sum(item.get("status") == "pass" for item in recent)}, {"sample": threshold["minimum_mainline_successes"], "passing": threshold["minimum_mainline_successes"]}, "status/repository-results-index.json"),
            criterion("minimum_trust_level", "pass" if ranks.get(trust.get("effective_level"), 0) >= ranks[threshold["minimum_trust_level"]] else "fail", trust.get("effective_level", "unverified"), threshold["minimum_trust_level"], "status/repository-results-index.json"),
            criterion("trust_checks_clean", "pass" if trust.get("check_summary", {}).get("fail", 0) == 0 else "fail", trust.get("check_summary", {}).get("fail", 0), 0, "status/repository-results-index.json"),
            criterion("replay_check_clean", "pass" if trust.get("replay") == "pass" else "fail", trust.get("replay", "not_evaluated"), "pass", "status/repository-results-index.json"),
            criterion("typed_evidence_current_and_clean", "pass" if typed_latest and typed_latest.get("commit_id") == latest.get("commit_id") and typed_latest.get("collector_status") == "collected" and typed_latest.get("freshness") == "pass" and typed_latest.get("content_integrity") == "pass" and typed_latest.get("replay") == "pass" else "fail", {"available": bool(typed_latest), "same_commit": bool(typed_latest) and typed_latest.get("commit_id") == latest.get("commit_id"), "freshness": typed_latest.get("freshness")}, {"available": True, "same_commit": True, "freshness": "pass"}, "status/typed-evidence-results-index.json"),
            criterion("architecture_result_clean", "pass" if has_architecture and arch_latest.get("status") == "pass" else ("fail" if has_architecture else "not_applicable"), arch_latest.get("status") if has_architecture else None, "pass", "status/architecture-results-index.json", required=has_architecture),
            criterion("intake_observation_sample", "pass" if metrics.get("total", 0) >= threshold["minimum_intake_events"] and metrics.get("success_rate_pct", 0) >= threshold["minimum_intake_success_rate_pct"] else "fail", {"events": metrics.get("total", 0), "success_rate_pct": metrics.get("success_rate_pct", 0)}, {"minimum_events": threshold["minimum_intake_events"], "minimum_success_rate_pct": threshold["minimum_intake_success_rate_pct"]}, "status/intake-health.json"),
            criterion("no_intake_conflicts", "pass" if not conflicts else "fail", len(conflicts), 0, "status/intake-conflicts/"),
            criterion("no_open_collection_attempts_global", "pass" if open_attempts == 0 else "fail", open_attempts, 0, "status/intake-health.json"),
            criterion("waiver_path_defined", "pass", True, True, "schemas/waiver.schema.json", "docs/operations/processes/waiver-management-standard.md"),
            criterion("rollback_runbook_defined", "pass", True, True, "docs/operations/processes/blocking-enforcement-migration-guide.md"),
            criterion("accountable_approval", "pass" if model.get("manual_approvals", {}).get(repository_id, {}).get("status") == "approved" else "manual_review", model.get("manual_approvals", {}).get(repository_id, {}).get("status", "pending"), "approved", "model/enforcement/blocking-readiness.yaml"),
        ]
        technical_ready = all(item["status"] in {"pass", "not_applicable"} for item in checks if item["required"] and item["id"] != "accountable_approval")
        approval = "approved" if checks[-1]["status"] == "pass" else "pending"
        decision = "ready_for_approval" if technical_ready else "not_ready"
        blocking = integration.get("governance_mode") in {"block-on-error", "waiver-required"}
        assessments.append({
            "repository_id": repository_id, "current_mode": integration.get("governance_mode", "unknown"),
            "decision": decision, "technical_ready": technical_ready, "manual_approval": approval,
            "mode_alignment": "already_blocking_but_not_ready" if blocking and not technical_ready else "aligned",
            "criteria": checks,
        })
    return {
        "schema_version": "0.1.0", "projection_type": "blocking-readiness",
        "generated_at": max(devsecops.get("generated_at", ""), architecture.get("generated_at", ""), typed.get("generated_at", "")),
        "enforcement": "report_only", "enforcement_change_authorized": False,
        "summary": {"repositories": len(assessments), "ready": sum(item["technical_ready"] for item in assessments),
                    "not_ready": sum(not item["technical_ready"] for item in assessments),
                    "already_blocking_but_not_ready": sum(item["mode_alignment"] == "already_blocking_but_not_ready" for item in assessments)},
        "repositories": assessments,
    }


def main() -> int:
    result = assess(
        integrations=yaml.safe_load((ROOT / "status/application-repository-integrations.yaml").read_text()),
        devsecops=load_json(ROOT / "status/repository-results-index.json"),
        architecture=load_json(ROOT / "status/architecture-results-index.json"),
        typed=load_json(ROOT / "status/typed-evidence-results-index.json"),
        health=load_json(ROOT / "status/intake-health.json"),
        model=yaml.safe_load((ROOT / "model/enforcement/blocking-readiness.yaml").read_text()),
        conflict_root=ROOT / "status/intake-conflicts",
    )
    output = ROOT / "generated/reports/blocking-readiness.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}: {result['summary']['ready']} ready, {result['summary']['not_ready']} not ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
