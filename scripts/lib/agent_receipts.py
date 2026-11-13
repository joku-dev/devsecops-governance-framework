"""Explicitly publishable review metadata, never private review text or authority."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .agent_review import check_results, digest, git_output
from .agent_routing import normalize_path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas/agent-review-receipt.schema.json").read_text())


def private_destination(root: Path, path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_relative_to(root.resolve()):
        raise ValueError("Keep review outputs outside the repository checkout")
    return path


def validate_receipt(receipt: dict) -> None:
    Draft202012Validator(SCHEMA, format_checker=FormatChecker()).validate(receipt)
    unsigned = {k: v for k, v in receipt.items() if k != "receipt_digest"}
    if receipt["receipt_digest"] != digest(unsigned):
        raise ValueError("Receipt digest mismatch")
    if receipt["receipt_id"] != digest({k: receipt[k] for k in ("plan_digest", "results_digest")}):
        raise ValueError("Receipt identity mismatch")
    if any(normalize_path(p) != p for p in receipt["changed_paths"]):
        raise ValueError("Receipt paths must be canonical repository paths")
    ids = [r["role_id"] for r in receipt["roles"]]
    if len(ids) != len(set(ids)) or ids[-1] != "repo-steward":
        raise ValueError("Receipt requires unique roles and final repo-steward")
    commands = [v["command"] for v in receipt["validations"]]
    if len(commands) != len(set(commands)):
        raise ValueError("Duplicate receipt validation")
    if any(r["execution_declared"] and r["status"] not in ("completed", "failed") for r in receipt["roles"]):
        raise ValueError("Pending or skipped roles cannot declare execution")
    if receipt["eligible_for_human_review"] and (
        any(r["status"] != "completed" or not r["execution_declared"] for r in receipt["roles"])
        or any(v["status"] != "passed" for v in receipt["validations"])
        or any(receipt["finding_counts"]["open"][s] for s in ("high", "critical"))
    ):
        raise ValueError("Receipt readiness contradicts its declared outcomes")


def build_receipt(root: Path, plan: dict, results: dict, *, recorded_at: str | None = None) -> dict:
    if plan.get("selection_mode") != "working_tree" or not plan.get("base_commit"):
        raise ValueError("Publication requires a full branch review with a base commit")
    if git_output(root, "status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("Commit the reviewed source and use a clean checkout before publication")
    report = check_results(root, plan, results)
    receipt = {
        "schema_version": "1.0.0", "plan_digest": plan["plan_digest"],
        "results_digest": digest(results), "head_commit": plan["head_commit"],
        "base_commit": plan["base_commit"], "changed_paths": plan["changed_files"],
        "roles": [{**{k: r[k] for k in ("role_id", "status", "execution_kind")},
                   "execution_declared": r["status"] in ("completed", "failed") and bool(r["executor"].strip() and r["provider"].strip())}
                  for r in results["reviews"]],
        "validations": [{k: v[k] for k in ("command", "status")} for v in results["validations"]],
        "finding_counts": {state: {severity: sum(f["status"] == state and f["severity"] == severity
            for f in report["findings"]) for severity in ("low", "medium", "high", "critical")}
            for state in ("open", "resolved")},
        "eligible_for_human_review": report["eligible_for_human_review"],
        "evidence_kind": report["evidence_kind"], "independent_human_approval": False,
        "recorded_at": recorded_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    receipt["receipt_id"] = digest({k: receipt[k] for k in ("plan_digest", "results_digest")})
    receipt["receipt_digest"] = digest(receipt)
    validate_receipt(receipt)
    return receipt


def write_receipt(root: Path, path: Path, receipt: dict) -> dict:
    validate_receipt(receipt)
    path = private_destination(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = json.loads(path.read_text())
        validate_receipt(existing)
        if {k: v for k, v in existing.items() if k not in ("recorded_at", "receipt_digest")} != {
            k: v for k, v in receipt.items() if k not in ("recorded_at", "receipt_digest")
        }:
            raise ValueError("Existing receipt belongs to a different review; never overwrite it")
        return existing
    with os.fdopen(fd, "w") as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def append_review_usage(root: Path, path: Path, receipt: dict) -> bool:
    """An exclusive lock avoids duplicate snapshots across concurrent exporters."""
    validate_receipt(receipt)
    path = private_destination(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("Review usage log is locked; retry after the current exporter finishes") from exc
    try:
        os.close(fd)
        events = load_review_usage(path)
        for event in events:
            if event["receipt_id"] == receipt["receipt_id"]:
                if {k: v for k, v in event.items() if k not in ("recorded_at", "receipt_digest")} != {
                    k: v for k, v in receipt.items() if k not in ("recorded_at", "receipt_digest")
                }:
                    raise ValueError("Conflicting projection for the same review receipt")
                return False
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as handle:
            handle.write(json.dumps(receipt, sort_keys=True) + "\n")
        return True
    finally:
        lock.unlink()


def load_review_usage(path: Path) -> list[dict]:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    seen = set()
    for event in events:
        validate_receipt(event)
        if event["receipt_id"] in seen:
            raise ValueError("Duplicate receipt in review usage log")
        seen.add(event["receipt_id"])
    return events


def summarize_review_usage(receipts: list[dict]) -> dict:
    selected, executed, completed, kinds = Counter(), Counter(), Counter(), Counter()
    for receipt in receipts:
        validate_receipt(receipt)
        for role in receipt["roles"]:
            selected[role["role_id"]] += 1
            if role["execution_declared"]:
                executed[role["role_id"]] += 1
                kinds[role["execution_kind"]] += 1
            if role["status"] == "completed":
                completed[role["role_id"]] += 1
    return {"receipt_count": len(receipts), "selected_roles": dict(selected),
            "declared_executed_roles": dict(executed), "completed_roles": dict(completed),
            "declared_execution_kinds": dict(kinds), "evidence_kind": "self_reported_review_evidence",
            "independent_human_approval": False}
