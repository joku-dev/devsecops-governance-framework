from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_operations_report import build_report, collect, render_markdown, INTAKES


class OperationsReportTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
        self.config = json.loads((ROOT / ".github/operations-report.json").read_text())
        self.schema = json.loads((ROOT / "schemas/governance-operations-report.schema.json").read_text())
        self.run = {"id": 123, "head_sha": "a" * 40, "created_at": "2026-09-09T11:00:00Z",
                    "status": "completed", "conclusion": "success", "html_url": "https://github.com/owner/repo/actions/runs/123"}
        self.latest = {"generated_at": "2026-09-09T11:00:00Z", "status": "pass", "pipeline_event": "push", "branch": "main"}
        self.observation = {
            "errors": [], "main_head": "a" * 40,
            "workflow_runs": {name: [deepcopy(self.run)] for name in ("governance-ci.yml", "publish-docs.yml", *self.config["scheduled_workflows"], *INTAKES)},
            "registry": {"integrations": [{"repository": "owner/consumer", "action_owner": "Consumer Owner"}]},
            "indexes": {"devsecops": {"repositories": [{"repository_id": "owner/consumer", "latest_result": self.latest}]},
                        "architecture": {"repositories": []}, "typed_evidence": {"repositories": []}},
            "intake_health": {"summary": {"collection_attempts": {"open": 0, "permanent": 0, "resolved": 2}, "events": {"total": 10}}},
            "pull_requests": [],
            "security": {"criteria": [{"id": "GRS-001", "title": "Protected", "status": "pass", "detail": "True"}], "next_steps": [], "observation": {"api_errors": []}},
        }
        self.observation["security"]["observation"].update({
            "repository": {"visibility": "public", "default_branch": "main"},
            "security_features": {"secret_scanning": "enabled", "secret_scanning_push_protection": "enabled",
                                  "dependabot_security_updates": "enabled", "private_vulnerability_reporting": True},
            "actions": {"allowed_actions": "selected", "sha_pinning_required": False, "default_workflow_permissions": "read"},
        })

    def report(self):
        report = build_report(self.observation, self.config, self.now, "b" * 40)
        Draft202012Validator(self.schema).validate(report)
        return report

    def check(self, subject):
        return next(check for check in self.report()["checks"] if check["subject"] == subject)

    def test_healthy_state_is_read_only_and_deterministic(self):
        original = deepcopy(self.observation)
        first = self.report()
        self.assertEqual(first, self.report())
        self.assertEqual(first["overall_status"], "ok")
        self.assertEqual(self.observation, original)
        self.assertFalse(any(first["decision_boundary"].values()))
        self.assertEqual(sum(first["summary"].values()), len(first["checks"]))

    def test_new_intake_does_not_refresh_old_source_evidence(self):
        self.latest["generated_at"] = "2026-07-15T17:07:40Z"
        self.observation["indexes"]["devsecops"]["generated_at"] = self.now.isoformat()
        check = self.check("owner/consumer: devsecops")
        self.assertEqual(check["status"], "attention")
        self.assertIn("days old", check["detail"])

    def test_fresh_branch_result_is_never_official_mainline(self):
        self.latest.update(branch="feature", pipeline_event="pull_request")
        self.assertIn("fallback remains diagnostic", self.check("owner/consumer: devsecops")["detail"])

    def test_compact_latest_context_comes_only_from_matching_history(self):
        self.latest.update(source_file="status/results/accepted.json", pipeline_run_id="10", commit_id="abc")
        accepted = dict(self.latest)
        del self.latest["pipeline_event"]
        del self.latest["branch"]
        row = self.observation["indexes"]["devsecops"]["repositories"][0]
        row["history"] = [dict(accepted, source_file="status/results/diagnostic.json", branch="feature"), accepted]
        self.assertEqual(self.check("owner/consumer: devsecops")["status"], "ok")
        row["history"] = row["history"][:1]
        self.assertEqual(self.check("owner/consumer: devsecops")["status"], "attention")

    def test_architecture_findings_are_distinct_from_successful_jobs(self):
        self.observation["indexes"]["architecture"]["repositories"] = [{"repository_id": "owner/consumer", "latest_result": dict(self.latest, status="findings")}]
        self.assertEqual(self.check("owner/consumer: architecture")["status"], "attention")
        self.assertEqual(self.check("governance-ci.yml")["status"], "ok")

    def test_future_or_missing_evidence_timestamp_never_passes(self):
        for value in (None, "2027-01-01T00:00:00Z", "2026-09-09T00:00:00"):
            with self.subTest(value=value):
                self.latest["generated_at"] = value
                self.assertEqual(self.check("owner/consumer: devsecops")["status"], "attention")

    def test_freshness_boundary_and_review_warning_boundary(self):
        self.latest["generated_at"] = (self.now - timedelta(days=30)).isoformat()
        self.assertEqual(self.check("owner/consumer: devsecops")["status"], "ok")
        self.observation["pull_requests"] = [{"number": 60, "createdAt": (self.now-timedelta(hours=24)).isoformat(),
            "reviewDecision": "REVIEW_REQUIRED", "mergeStateStatus": "BLOCKED", "isDraft": False, "url": "https://github.com/owner/repo/pull/60"}]
        self.assertEqual(self.check("PR #60")["status"], "ok")
        self.now += timedelta(seconds=1)
        self.assertEqual(self.check("owner/consumer: devsecops")["status"], "attention")
        self.assertEqual(self.check("PR #60")["status"], "attention")

    def test_main_ci_must_match_current_main_commit(self):
        self.observation["main_head"] = "c" * 40
        self.assertEqual(self.check("governance-ci.yml")["status"], "attention")
        self.observation["main_head"] = None
        self.assertEqual(self.check("governance-ci.yml")["status"], "unknown")

    def test_missing_stale_failed_and_stuck_scheduled_runs(self):
        runs = self.observation["workflow_runs"]
        runs["portfolio-status.yml"] = []
        self.assertEqual(self.check("portfolio-status.yml")["status"], "attention")
        for changes in ({"created_at": "2026-09-07T00:00:00Z"}, {"conclusion": "failure"},
                        {"status": "queued", "conclusion": None, "created_at": "2026-09-09T01:00:00Z"}):
            runs["portfolio-status.yml"] = [dict(self.run, **changes)]
            self.assertEqual(self.check("portfolio-status.yml")["status"], "attention")

    def test_unknown_api_and_empty_pr_queue_are_different(self):
        self.assertEqual(self.check("PR queue")["status"], "ok")
        self.observation["pull_requests"] = None
        self.assertEqual(self.check("PR queue")["status"], "unknown")
        self.observation["errors"] = [{"source": "pull_requests", "error": "ResultLimitReached"}]
        self.assertGreater(self.report()["summary"]["unknown"], 0)

    def test_failure_survives_newer_success_in_observation_window(self):
        self.observation["workflow_runs"][INTAKES[0]].append(dict(self.run, id=122, conclusion="failure"))
        self.assertEqual(self.check(INTAKES[0])["status"], "attention")
        self.observation["intake_health"]["summary"]["collection_attempts"]["permanent"] = 1
        self.assertEqual(self.check("Collection recovery")["status"], "attention")

    def test_self_security_findings_do_not_inherit_job_success(self):
        self.observation["security"]["criteria"][0]["status"] = "fail"
        self.observation["security"]["observation"]["api_errors"] = ["HTTP 403"]
        self.assertEqual(self.check("GRS-001: Protected")["status"], "attention")
        self.assertEqual(self.check("Security API observations")["status"], "unknown")
        self.assertEqual(self.check("governance-repository-security.yml")["status"], "ok")

    def test_expected_classic_protection_404_is_not_itself_an_access_gap(self):
        observed = self.observation["security"]["observation"]
        observed["api_errors"] = ["gh: Branch not protected (HTTP 404)"]
        self.assertEqual(self.report()["summary"]["unknown"], 0)
        observed["security_features"]["secret_scanning"] = None
        self.assertEqual(self.check("Security API observations")["status"], "unknown")

    def test_schema_rejects_claimed_enforcement_or_approval(self):
        report = self.report()
        report["decision_boundary"]["approves_prs"] = True
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.schema).validate(report)

    def test_markdown_escapes_untrusted_table_cells(self):
        self.observation["security"]["criteria"][0]["detail"] = '<script>alert(1)</script>|fake\nrow'
        markdown = render_markdown(self.report())
        self.assertNotIn("<script>", markdown)
        self.assertIn("&#124;fake row", markdown)

    def test_collector_uses_schedule_event_and_preserves_access_errors(self):
        calls = []
        def fake(args):
            calls.append(args)
            if args[1:3] == ["pr", "list"]:
                raise subprocess.CalledProcessError(1, args)
            if "git/ref" in args[-1]:
                return {"object": {"sha": "a"*40}}
            return {"workflow_runs": []}
        with tempfile.TemporaryDirectory() as directory:
            with patch("generate_operations_report.command_json", side_effect=fake), patch("generate_operations_report.collect_live", return_value={}):
                observed = collect(self.config, Path(directory), self.now)
        self.assertIsNone(observed["pull_requests"])
        self.assertTrue(any(error["source"] == "pull_requests" for error in observed["errors"]))
        self.assertTrue(any("event=schedule" in args[-1] for args in calls))
        self.assertTrue(any("event=push" in args[-1] for args in calls))
        self.assertTrue(all(args[0] == "gh" and args[1] in ("api", "pr") for args in calls))

    def test_workflow_only_reads_and_retains_observations(self):
        workflow = yaml.load((ROOT / ".github/workflows/governance-operations.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertTrue(all(value == "read" for value in workflow["permissions"].values()))
        self.assertIn("schedule", workflow["on"])
        self.assertIn("workflow_dispatch", workflow["on"])
        steps = workflow["jobs"]["report"]["steps"]
        self.assertTrue(any(step.get("with", {}).get("name") == "governance-operations" for step in steps))
        self.assertFalse(any("git push" in step.get("run", "") or "gh pr" in step.get("run", "") for step in steps))


if __name__ == "__main__":
    unittest.main()
