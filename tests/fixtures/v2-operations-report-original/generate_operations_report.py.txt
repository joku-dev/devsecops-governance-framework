#!/usr/bin/env python3
"""Read-only daily operational report; findings never authorize enforcement."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import subprocess

import yaml
from jsonschema import Draft202012Validator

from assess_governance_repository_security import assess, collect_live
from generate_intake_health import build_payload as intake_health

ROOT = Path(__file__).resolve().parents[1]
INDEXES = {"devsecops": "repository-results-index.json",
           "architecture": "architecture-results-index.json",
           "typed_evidence": "typed-evidence-results-index.json"}
INTAKES = ("intake-governance-result.yml", "intake-architecture-result.yml", "intake-evidence-trust.yml")


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def age_hours(value: str, now: datetime) -> float:
    age = (now - timestamp(value)).total_seconds() / 3600
    if age < 0:
        raise ValueError("Observation timestamp is in the future")
    return age


def command_json(args: list[str]):
    result = subprocess.run(args, text=True, capture_output=True, check=True, timeout=60)
    return json.loads(result.stdout)


def collect(config: dict, root: Path, now: datetime) -> dict:
    repository = config["repository"]
    observation = {"observed_at": now.isoformat(), "errors": [], "workflow_runs": {}, "indexes": {}}

    def capture(source, operation):
        try:
            return operation()
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
            # Never print token-bearing environments or unrestricted command output.
            observation["errors"].append({"source": source, "error": type(error).__name__})
            return None

    def api(endpoint):
        return command_json(["gh", "api", f"repos/{repository}/{endpoint}"])

    observation["main_head"] = capture("main_head", lambda: api("git/ref/heads/main")["object"]["sha"])
    queries = {"governance-ci.yml": "push", "publish-docs.yml": None,
               **{name: "schedule" for name in config["scheduled_workflows"]},
               **{name: None for name in INTAKES}}
    for name, event in queries.items():
        query = f"actions/workflows/{name}/runs?branch=main&per_page=100"
        if event:
            query += f"&event={event}"
        runs = capture(f"workflow:{name}", lambda: api(query)["workflow_runs"])
        observation["workflow_runs"][name] = runs
        if runs is not None and len(runs) == 100:
            observation["errors"].append({"source": f"workflow:{name}", "error": "ResultLimitReached"})
    observation["pull_requests"] = capture("pull_requests", lambda: command_json([
        "gh", "pr", "list", "--repo", repository, "--base", "main", "--state", "open", "--limit", "1000",
        "--json", "number,url,title,createdAt,isDraft,reviewDecision,mergeStateStatus,author,headRefName",
    ]))
    if observation["pull_requests"] is not None and len(observation["pull_requests"]) == 1000:
        observation["errors"].append({"source": "pull_requests", "error": "ResultLimitReached"})
    observation["registry"] = capture("registry", lambda: yaml.safe_load(
        (root / "status/application-repository-integrations.yaml").read_text()))
    for domain, path in INDEXES.items():
        observation["indexes"][domain] = capture(f"index:{domain}", lambda: json.loads((root / "status" / path).read_text()))

    def records(directory):
        return [dict(json.loads(path.read_text()), _source_file=str(path.relative_to(root)))
                for path in sorted((root / "status" / directory).rglob("*.json"))]

    def health():
        if any(index is None for index in observation["indexes"].values()):
            raise ValueError("Missing result index")
        return intake_health(events=records("intake-events"), attempts=records("collection-attempts"),
                             snapshots=records("results") + records("architecture-results") + records("typed-evidence-results"),
                             intake_conflict_count=len(records("intake-conflicts")),
                             indexes=observation["indexes"], as_of=now)
    observation["intake_health"] = capture("intake_health", health)
    observation["security"] = capture("security", lambda: assess(
        yaml.safe_load((root / "model/controls/governance-repository-security.yaml").read_text()),
        collect_live(repository, now.isoformat())))
    return observation


def build_report(observation: dict, config: dict, now: datetime, checkout_sha: str) -> dict:
    checks = []
    repo_url = f"https://github.com/{config['repository']}"

    def add(category, subject, status, detail, action, owner="Governance Platform Lead", url=""):
        checks.append({"category": category, "subject": subject, "status": status, "detail": detail,
                       "action": action, "owner": owner, "source_url": url})

    for error in observation.get("errors", []):
        add("observation", error["source"], "unknown", error["error"],
            "Inspect collection logs, API access and input validity; rerun the report.")

    def run_check(name, runs, max_age=None, head=None):
        url = f"{repo_url}/actions/workflows/{name}"
        if runs is None or (name == "governance-ci.yml" and not head):
            add("workflow", name, "unknown", "Run metadata or main SHA unavailable.", "Restore Actions read access.", url=url)
            return
        candidates = [run for run in runs if not head or run.get("head_sha") == head]
        if not candidates:
            add("workflow", name, "attention", "No matching main push / scheduled run was observed.",
                "Check trigger delivery and workflow enablement; investigate the missing run.", url=url)
            return
        run = candidates[0]
        try:
            age = age_hours(run["created_at"], now)
        except (KeyError, ValueError, TypeError):
            add("workflow", name, "unknown", "Invalid run timestamp.", "Inspect run metadata.", url=url)
            return
        completed = run.get("status") == "completed"
        ok = completed and run.get("conclusion") == "success" and (max_age is None or age <= max_age)
        detail = f"Run {run.get('id')}: {run.get('status')}/{run.get('conclusion')}; age {age:.1f}h."
        if not completed and age > config["run_warning_hours"]:
            detail += " Execution/queue time exceeds the warning threshold."
        if max_age is not None and age > max_age:
            detail += " Scheduled heartbeat overdue."
        add("workflow", name, "ok" if ok else "attention", detail,
            "None." if ok else "Inspect run logs/queue; fix the cause and rerun. Manual reruns do not replace the scheduled heartbeat.",
            url=run.get("html_url", url))

    runs = observation.get("workflow_runs", {})
    run_check("governance-ci.yml", runs.get("governance-ci.yml"), head=observation.get("main_head"))
    # Docs are path-filtered: a successful older deployment need not match every main commit.
    run_check("publish-docs.yml", runs.get("publish-docs.yml"))
    for name, threshold in config["scheduled_workflows"].items():
        run_check(name, runs.get(name), max_age=threshold)
    for name in INTAKES:
        items = runs.get(name)
        if items is None:
            add("intake", name, "unknown", "Intake runs unavailable.", "Restore Actions read access.")
            continue
        failed = []
        invalid = False
        for run in items:
            try:
                age = age_hours(run["created_at"], now)
            except (KeyError, ValueError, TypeError):
                invalid = True
                continue
            if age <= config["intake_failure_window_hours"] and (
                (run.get("status") == "completed" and run.get("conclusion") != "success") or
                (run.get("status") != "completed" and age > config["run_warning_hours"])
            ):
                failed.append(run)
        add("intake", name, "unknown" if invalid else "attention" if failed else "ok",
            f"{len(failed)} failed, cancelled, skipped or overdue runs in the observation window.",
            "Inspect failed runs and any unmerged evidence PRs; retry after correcting the cause." if failed or invalid else "None.",
            url=f"{repo_url}/actions/workflows/{name}")

    registry = observation.get("registry")
    if not registry or not registry.get("integrations"):
        add("evidence", "Consumer inventory", "unknown", "No consumer inventory available.", "Restore/complete the integration registry.")
    for entry in (registry or {}).get("integrations", []):
        repository = entry["repository"]
        owner = entry.get("action_owner") or entry.get("owner") or "Repository Owner (assignment required)"
        for domain in INDEXES:
            index = observation.get("indexes", {}).get(domain)
            if index is None:
                add("evidence", f"{repository}: {domain}", "unknown", "Result index unavailable.", "Restore and validate the result index.", owner)
                continue
            row = next((row for row in index.get("repositories", []) if row["repository_id"] == repository), None)
            # Optional domains are monitored where already represented; no new scope is inferred.
            if row is None and domain != "devsecops":
                continue
            latest = dict((row or {}).get("latest_result") or {})
            # The compact DevSecOps latest projection omits context; its matching
            # history entry retains it. Do not choose a newer diagnostic history row.
            matching = next((item for item in (row or {}).get("history", [])
                             if latest.get("source_file") and item.get("source_file") == latest["source_file"]
                             and item.get("pipeline_run_id") == latest.get("pipeline_run_id")
                             and item.get("commit_id") == latest.get("commit_id")), {})
            for key in ("pipeline_event", "branch", "pipeline_url"):
                if key not in latest and key in matching:
                    latest[key] = matching[key]
            problems = []
            try:
                age_days = age_hours(latest["generated_at"], now) / 24
                if age_days > config["evidence_max_age_days"]:
                    problems.append(f"Evidence is {age_days:.1f} days old")
            except (KeyError, ValueError, TypeError):
                age_days = None
                problems.append("Missing/invalid source result timestamp")
            if latest.get("pipeline_event") != "push" or latest.get("branch") != "main":
                problems.append("No official mainline push result; fallback remains diagnostic")
            if domain == "typed_evidence":
                if (latest.get("collector_status") != "collected" or latest.get("finding_count", 0) > 0 or
                        any(latest.get(key) != "pass" for key in ("freshness", "content_integrity", "replay"))):
                    problems.append("Typed evidence contains findings or incomplete verification")
            elif str(latest.get("status", "missing")).lower() not in ("pass", "success"):
                problems.append(f"Recorded evaluation: {latest.get('status', 'missing')}")
            add("evidence", f"{repository}: {domain}", "attention" if problems else "ok",
                "; ".join(problems) if problems else f"Current passing mainline evidence ({age_days:.1f} days old).",
                "Produce a new consumer mainline result, investigate findings, and review its intake PR." if problems else "None.",
                owner, latest.get("pipeline_url", f"https://github.com/{repository}/actions"))

    health = observation.get("intake_health")
    if health is None:
        add("intake", "Collection recovery", "unknown", "Telemetry could not be recomputed.", "Validate intake records and regenerate the health projection.")
    else:
        attempts = health["summary"]["collection_attempts"]
        unresolved = attempts.get("open", 0) + attempts.get("permanent", 0)
        add("intake", "Collection recovery", "attention" if unresolved else "ok",
            f"{attempts.get('open', 0)} open, {attempts.get('permanent', 0)} permanent, {attempts.get('resolved', 0)} resolved attempts.",
            "Triage open/permanent attempts using the retry runbook; preserve historical records." if unresolved else "None.")
        events = health["summary"]["events"]
        add("intake", "Intake observation sample", "ok" if events["total"] else "attention",
            f"{events['total']} events in the rolling 30-day window; this is not a blocking-readiness approval.",
            "None." if events["total"] else "Verify expected consumer activity and dispatch delivery; obtain current evidence.")

    prs = observation.get("pull_requests")
    if prs is None:
        add("review", "PR queue", "unknown", "PR metadata unavailable.", "Restore pull-request read access.", "Repository Owner")
    elif not prs:
        add("review", "PR queue", "ok", "No open PRs targeting main.", "None.", "Repository Owner")
    for pr in prs or []:
        try:
            age = age_hours(pr["createdAt"], now)
            overdue = age > config["review_warning_hours"]
            detail = f"Age {age:.1f}h; review {pr.get('reviewDecision') or 'none'}; merge {pr.get('mergeStateStatus')}; draft {pr.get('isDraft')}."
        except (KeyError, ValueError, TypeError):
            overdue, detail = True, "Invalid PR creation timestamp."
        needs_work = overdue or pr.get("mergeStateStatus") in ("DIRTY", "BEHIND", "UNSTABLE") or pr.get("reviewDecision") == "CHANGES_REQUESTED"
        add("review", f"PR #{pr['number']}", "attention" if needs_work else "ok", detail,
            "Assign an independent reviewer; inspect checks/conflicts and regenerate operational projections after reconciliation. Do not bypass review."
            if needs_work else "Review within the warning window; approval and merge remain explicit maintainer decisions.",
            "Repository Owner", pr["url"])

    security = observation.get("security")
    if not security or not security.get("criteria"):
        add("security", "Self-security assessment", "unknown", "Live assessment unavailable.", "Restore assessment inputs and read access.", "Repository Owner / Security")
    else:
        security_observation = security.get("observation", {})
        errors = security_observation.get("api_errors", [])
        missing_settings = [f"{section}.{key}" for section, keys in {
            "repository": ("visibility", "default_branch"),
            "security_features": ("secret_scanning", "secret_scanning_push_protection", "dependabot_security_updates", "private_vulnerability_reporting"),
            "actions": ("allowed_actions", "sha_pinning_required", "default_workflow_permissions"),
        }.items() for key in keys if security_observation.get(section, {}).get(key) is None]
        # A 404 for optional classic protection/signatures is expected with a ruleset.
        # Missing observed settings or other API failures still prevent a full assessment.
        unexpected_errors = [error for error in errors if "HTTP 404" not in error]
        if missing_settings or unexpected_errors:
            add("observation", "Security API observations", "unknown",
                f"Unavailable settings: {', '.join(missing_settings) or 'none'}; {len(unexpected_errors)} other API errors. Full errors retained in the observation artifact.",
                "Use the self-security report to distinguish confirmed gaps from inaccessible settings; arrange a scoped authenticated verification.", "Repository Owner / Security")
        for criterion in security["criteria"]:
            action = next((step["action"] for step in security.get("next_steps", []) if criterion["id"] in step["addresses"]),
                          "Inspect the self-security evidence and resolve the finding or missing observation.")
            add("security", f"{criterion['id']}: {criterion['title']}", "ok" if criterion["status"] == "pass" else "attention",
                criterion["detail"], "None." if criterion["status"] == "pass" else action,
                "Repository Owner / Security", f"{repo_url}/actions/workflows/governance-repository-security.yml")
    summary = {status: sum(check["status"] == status for check in checks) for status in ("ok", "attention", "unknown")}
    return {"schema_version": "1.0.0", "generated_at": now.isoformat().replace("+00:00", "Z"),
            "repository": config["repository"], "checkout_sha": checkout_sha, "main_head": observation.get("main_head"),
            "enforcement": "report_only", "overall_status": "attention" if summary["attention"] else "unknown" if summary["unknown"] else "ok",
            "summary": summary, "thresholds": config, "checks": checks,
            "decision_boundary": {"changes_official_results": False, "approves_prs": False, "changes_enforcement": False}}


def render_markdown(report: dict) -> str:
    def cell(value):
        return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")
    lines = ["# Daily Governance Operations", "", f"Observed: `{report['generated_at']}`",
             f"Status: **{report['overall_status']}** — {report['summary']['ok']} OK, {report['summary']['attention']} attention, {report['summary']['unknown']} unknown.",
             f"Checkout: `{report['checkout_sha']}`; observed main: `{report['main_head']}`.", "",
             "A successful workflow means this report was produced; it does not mean governance criteria passed.",
             "Thresholds are operational warnings, not approved SLAs. Owners are accountable roles; name the assignee during triage.", "",
             "| Status | Area | Subject | Observation | Owner | Next action | Source |",
             "|---|---|---|---|---|---|---|"]
    order = {"attention": 0, "unknown": 1, "ok": 2}
    for check in sorted(report["checks"], key=lambda check: (order[check["status"]], check["category"], check["subject"])):
        lines.append("| " + " | ".join(cell(check[key]) for key in ("status", "category", "subject", "detail", "owner", "action", "source_url")) + " |")
    lines += ["", "Read-only observation. Pending PRs do not update official results. No PR approval, merge, waiver or enforcement activation is performed.",
              "API failures and capped result sets are visible as unknown; raw observations accompany this report."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / ".github/operations-report.json")
    parser.add_argument("--observation", type=Path, help="Replay a captured observation without API calls")
    parser.add_argument("--as-of")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated/reports/operations")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    schema = json.loads((ROOT / "schemas/governance-operations-report.schema.json").read_text())
    Draft202012Validator(schema["properties"]["thresholds"]).validate(config)
    observation = json.loads(args.observation.read_text()) if args.observation else None
    as_of = args.as_of or (observation or {}).get("observed_at")
    now = timestamp(as_of) if as_of else datetime.now(timezone.utc).replace(microsecond=0)
    if observation is None:
        observation = collect(config, ROOT, now)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = build_report(observation, config, now, sha)
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (("governance-operations.json", report), ("operations-observation.json", observation)):
        (args.output_dir / name).write_text(json.dumps(payload, indent=2) + "\n")
    (args.output_dir / "governance-operations.md").write_text(render_markdown(report))
    print(f"Operations report: {report['overall_status']} {report['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
