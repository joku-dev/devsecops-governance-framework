"""Generate confidential, reproducible filesystem experiments and raw evidence."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from experiments.state_binding import prototype as p


def capture(root, target):
    target.mkdir(parents=True)
    for name in ("EXPERIMENT.json", "provider.json", "executor-config.json"):
        shutil.copyfile(root / name, target / name)
    files = root / "ledger/transactions"
    (target / "transactions").mkdir()
    if files.exists():
        for path in sorted(files.glob("*.json")):
            shutil.copyfile(path, target / "transactions" / path.name)
    state = p.snapshot(root)
    p.write_json(target / "snapshot.json", state)
    return state


def setup(parent, name):
    root = p.initialize(parent / name)
    p.record(root, "evidence", {"run": "fixture-run-1", "result": "fail"})
    request = p.prepare(root)
    grant = p.fixture_approve(root, request)
    return root, grant


def attempt(root, grant, omit=()):
    start = time.perf_counter_ns()
    try:
        tx = p.execute(root, grant, omit=omit)
        result = {"outcome": "published", "transaction_id": tx["transaction_id"], "reason": None}
    except p.Rejected as error:
        result = {"outcome": "rejected", "transaction_id": None, "reason": str(error)}
    result["duration_ns"] = time.perf_counter_ns() - start
    result["process_id"] = os.getpid()
    return result


def race_worker(root, grant, gate, queue):
    try:
        gate.wait(timeout=30)
        queue.put(attempt(Path(root), grant))
    except Exception as error:
        queue.put({"outcome": "worker_error", "reason": repr(error)})


def comparison(output):
    """Execute genuine existing tests; do not substitute a weakened comparator."""
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_lifecycle_pilot_actions.py", "-v"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_lifecycle_operating_acceptance.py", "-v"],
    ]
    results = []
    for index, command in enumerate(commands):
        run = subprocess.run(command, cwd=REPO, capture_output=True, text=True, timeout=120)
        name = f"existing-pilot-{index + 1}.log"
        (output / name).write_text(run.stdout + run.stderr, encoding="utf-8")
        results.append({"command": command[1:], "returncode": run.returncode, "log": name})
    return {"kind": "existing_unmodified_regression_suites", "runs": results,
            "interpretation": "Existing head/revision/content/provider/manifest protections already reject relevant changes. "
                              "This is regression comparison, not an identical-protocol benchmark or proof of novelty."}


def run(output, *, include_comparison=True):
    output = p.no_symlinks(output)
    # Evidence is confidential and never generated into docs, status or site.
    if output.resolve().is_relative_to(REPO):
        p.need(output.resolve().is_relative_to(REPO / "experiments/state_binding/runs"), "unsafe_evidence_output")
    output.mkdir(parents=True, exist_ok=False)
    work = output / "workspaces"
    work.mkdir()
    cases = output / "cases"
    cases.mkdir()
    results = []
    cases_spec = [
        ("unchanged", "published", ()),
        ("new_evidence", "rejected", ()),
        ("audit_only_history", "rejected", ()),
        ("implementation_changed", "rejected", ()),
        ("role_changed", "rejected", ()),
        ("profile_changed", "rejected", ()),
        ("action_changed", "rejected", ()),
        ("provider_revoked", "rejected", ()),
        ("provider_edited", "rejected", ()),
        ("provider_deleted", "rejected", ()),
        ("state_root_changed", "rejected", ()),
        ("implementation_without_binding", "published", ("implementation",)),
        ("history_without_history_root", "rejected", ("history",)),
        ("history_without_history_preconditions", "published", ("history", "head", "revision")),
        ("state_without_state_root", "published", ("state",)),
    ]
    for name, expected, omit in cases_spec:
        root, grant = setup(work, name)
        case = cases / name
        case.mkdir()
        capture(root, case / "prepared")
        if name == "new_evidence":
            p.record(root, "evidence", {"run": "fixture-run-2", "result": "pass"})
        if name.startswith("audit_only") or name.startswith("history_without"):
            p.record(root, "audit_note", "History-only annotation; no semantic change")
        if name.startswith("implementation_"):
            p.write_json(root / "executor-config.json", {"media_type": "application/json"})
        if name == "role_changed":
            p.record(root, "role", {"subject": p.SUBJECT, "active": False})
        if name == "profile_changed":
            p.record(root, "profile", {"id": "private-research", "version": "2"})
        if name == "action_changed":
            grant["request"]["action"]["content"] = "Changed AFTER fixture approval"
        if name.startswith("provider_"):
            p.update_fixture_provider(root, grant, name.split("_", 1)[1])
        if name in ("state_root_changed", "state_without_state_root"):
            # A deliberately faulty state commitment is approved by the TEST provider.
            # Other roots remain correct, isolating independent semantic validation.
            grant["request"]["roots"]["state"] = "0" * 64
            grant = p.fixture_approve(root, grant["request"])
        before = capture(root, case / "before")
        p.write_json(case / "grant.json", grant)
        observed = attempt(root, grant, omit)
        after = capture(root, case / "after")
        delta = len(after["transactions"]) - len(before["transactions"])
        result = {"id": name, "kind": "attempt", "expected": expected,
                  "omitted_checks": list(omit), **observed, "transaction_delta": delta,
                  "passed": observed["outcome"] == expected and delta == int(expected == "published")}
        p.write_json(case / "result.json", result)
        results.append(result)

    for name in ("retry", "revocation_after_change", "concurrent_publication"):
        root, grant = setup(work, name)
        case = cases / name
        case.mkdir()
        p.write_json(case / "grant.json", grant)
        before = capture(root, case / "before")
        if name == "retry":
            attempts = [attempt(root, grant), attempt(root, grant)]
            expected = ["published", "rejected"]
        elif name == "concurrent_publication":
            ctx = multiprocessing.get_context("spawn")
            gate, queue = ctx.Barrier(2), ctx.Queue()
            workers = [ctx.Process(target=race_worker, args=(str(root), grant, gate, queue)) for _ in range(2)]
            try:
                for worker in workers:
                    worker.start()
                attempts = [queue.get(timeout=40) for _ in workers]
                for worker in workers:
                    worker.join(timeout=5)
                    p.need(worker.exitcode == 0, "concurrency_worker_failed")
            finally:
                for worker in workers:
                    if worker.is_alive():
                        worker.terminate()
                        worker.join(timeout=5)
                queue.close()
            expected = ["published", "rejected"]
        else:
            attempts = [attempt(root, grant)]
            p.record(root, "audit_note", "New history before correction")
            p.update_fixture_provider(root, grant, "revoked")
            correction = p.revoke(root, grant)
            attempts.append(attempt(root, grant))
            p.write_json(case / "correction.json", correction)
            expected = ["published", "rejected"]
        after = capture(root, case / "after")
        publications = [t for t in after["transactions"] if t["event"]["kind"] == "publish"]
        passed = sorted(a["outcome"] for a in attempts) == sorted(expected) and len(publications) == 1
        if name == "concurrent_publication":
            passed = passed and len({a["process_id"] for a in attempts}) == 2
        if name == "revocation_after_change":
            passed = passed and after["state"]["publication"] is None and bool(after["state"]["revoked_requests"])
        result = {"id": name, "kind": name, "attempts": attempts,
                  "transaction_delta": len(after["transactions"]) - len(before["transactions"]), "passed": passed}
        p.write_json(case / "result.json", result)
        results.append(result)

    identity = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    git_status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=REPO, text=True)
    sources = p.source_manifest()
    source_matches = True
    for name, expected_sha in sources.items():
        stored = subprocess.run(["git", "show", f"{identity}:{name}"], cwd=REPO, capture_output=True)
        source_matches = source_matches and stored.returncode == 0 and p.raw_digest(stored.stdout) == expected_sha
    report = {"contract": "1", "classification": "confidential_test_evidence", "official_state": False,
              "human_authorization_proven": False, "patentability_assessed": False,
              "generated_at": datetime.now(timezone.utc).isoformat(), "source_commit": identity,
              "tracked_worktree_dirty": bool(git_status), "source_manifest": sources,
              "source_files_match_commit": source_matches,
              "toolchain": {"python": platform.python_version(), "platform": platform.platform()},
              "results": results, "comparison": comparison(output) if include_comparison else None}
    report["passed"] = all(r["passed"] for r in results) and (
        report["comparison"] is None or all(r["returncode"] == 0 for r in report["comparison"]["runs"]))
    p.write_json(output / "results.json", report)
    text = ["# Confidential prototype experiment results", "", f"Source commit: `{identity}`.",
            "Exact source bytes are additionally bound by the source manifest.", "",
            f"Experiments: {len(results)}; passed: {sum(r['passed'] for r in results)}.",
            "All automated authorizations are test fixtures. Patentability is not assessed.", "",
            "| Experiment | Outcome |", "|---|---|"]
    text.extend(f"| {r['id']} | {'PASS' if r['passed'] else 'FAIL'} |" for r in results)
    text += ["", "## Interpretation", "",
             "History roots overlap existing head/sequence safeguards: removing only the history root still rejects stale history.",
             "Removing all history preconditions admits a history-only change despite an equal semantic state.",
             "Implementation binding rejects changed configured execution semantics; omitting it admits that change.",
             "State-root checking independently rejects an incorrectly claimed semantic root. This does not prove a novel security property over a validated head plus deterministic replay.",
             "Existing pilot regression suites are retained as comparison, not relabelled as a weaker baseline.",
             "The publication is an actual atomic JSON artifact in the local ledger. No consumer deployment was performed.", ""]
    (output / "REPORT.md").write_text("\n".join(text), encoding="utf-8")
    # Workspaces contain locks and mutable files; copied cases are the durable evidence.
    shutil.rmtree(work)
    files = {path.relative_to(output).as_posix(): p.raw_digest(path.read_bytes())
             for path in sorted(output.rglob("*")) if path.is_file()}
    manifest = {"contract": "1", "classification": "confidential_test_evidence", "files": files}
    p.write_json(output / "MANIFEST.json", manifest)
    bundle_digest = p.raw_digest((output / "MANIFEST.json").read_bytes())
    return report, bundle_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report, digest = run(args.output)
    print(json.dumps({"passed": report["passed"], "experiments": len(report["results"]),
                      "bundle_manifest_sha256": digest, "output": str(args.output)}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
