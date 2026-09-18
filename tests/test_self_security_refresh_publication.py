from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publish_self_security_refresh import (
    ALLOWED_PATHS,
    BRANCH,
    CHECK_WORKFLOWS,
    materially_equal,
    publish,
)


def report(observed_at: str, status: str = "findings") -> dict:
    return {
        "observed_at": observed_at,
        "overall_status": status,
        "summary": {"pass": 13, "fail": 3},
        "observation": {"observed_at": observed_at, "repository": {"protected": True}},
    }


class SelfSecurityRefreshPublicationTests(unittest.TestCase):
    def setUp(self):
        outputs = patch.dict(os.environ, {"GITHUB_OUTPUT": "", "GITHUB_STEP_SUMMARY": ""})
        outputs.start()
        self.addCleanup(outputs.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "checkout"
        self.remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.write_json("generated/reports/governance-repository-security.json", report("2026-09-17T00:00:00Z"))
        self.write("generated/reports/governance-repository-security.md", "old\n")
        self.write_json("generated/viewer/app/data.json", {"security": "old"})
        self.write("model/control.yaml", "normative: unchanged\n")
        self.git("add", ".")
        self.git("commit", "-m", "Baseline")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()
        self.calls = []
        self.open_pr = None

    def git(self, *args, check=True):
        return subprocess.run(["git", *args], cwd=self.root, text=True, capture_output=True, check=check)

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)

    def write_json(self, path, value):
        self.write(path, json.dumps(value, indent=2) + "\n")

    def api(self, method, endpoint, payload=None):
        self.calls.append((method, endpoint, payload))
        if method == "GET":
            return [self.open_pr] if self.open_pr else []
        if method == "POST" and endpoint.endswith("/pulls"):
            self.open_pr = {"number": 7, "html_url": "https://github.com/owner/repo/pull/7"}
            return self.open_pr
        if method == "PATCH":
            return self.open_pr
        return {}

    def publish(self, run_id="123"):
        return publish(
            self.root,
            repository="owner/repo",
            run_id=run_id,
            attempt="1",
            api=self.api,
        )

    def regenerate(self, *, observed_at, status):
        self.write_json("generated/reports/governance-repository-security.json", report(observed_at, status))
        self.write("generated/reports/governance-repository-security.md", f"{status} at {observed_at}\n")
        self.write_json("generated/viewer/app/data.json", {"security": status, "observed_at": observed_at})

    def test_timestamp_only_change_opens_no_pr(self):
        self.regenerate(observed_at="2026-09-18T00:00:00Z", status="findings")
        self.assertIsNone(self.publish())
        self.assertEqual([call for call in self.calls if call[0] != "GET"], [])
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").stdout.split()[0], self.base)

    def test_material_change_opens_bounded_pr_and_dispatches_every_required_check(self):
        self.regenerate(observed_at="2026-09-18T00:00:00Z", status="pass")
        self.publish()
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").stdout.split()[0], self.base)
        changed = self.git("diff", "--name-only", self.base, "HEAD").stdout.splitlines()
        self.assertEqual(set(changed), ALLOWED_PATHS)
        create = next(call for call in self.calls if call[0] == "POST" and call[1].endswith("/pulls"))
        self.assertEqual(create[2]["head"], BRANCH)
        dispatches = [call for call in self.calls if "/dispatches" in call[1]]
        self.assertEqual(len(dispatches), len(CHECK_WORKFLOWS))
        dependency = next(call for call in dispatches if "dependency-review.yml" in call[1])
        self.assertEqual(dependency[2]["inputs"], {"base_ref": "main", "head_ref": BRANCH})

    def test_second_material_change_updates_same_pr_without_force_or_main_write(self):
        self.regenerate(observed_at="2026-09-18T00:00:00Z", status="pass")
        self.publish("123")
        first_head = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("switch", "main")
        self.regenerate(observed_at="2026-09-19T00:00:00Z", status="findings-again")
        self.publish("124")
        second_head = self.git("rev-parse", "HEAD").stdout.strip()
        self.assertNotEqual(first_head, second_head)
        self.assertEqual(self.git("merge-base", "--is-ancestor", first_head, second_head).returncode, 0)
        self.assertEqual(len([call for call in self.calls if call[1].endswith("/pulls")]), 1)
        self.assertEqual(len([call for call in self.calls if call[0] == "PATCH"]), 1)
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").stdout.split()[0], self.base)

    def test_normative_change_is_rejected(self):
        self.regenerate(observed_at="2026-09-18T00:00:00Z", status="pass")
        self.write("model/control.yaml", "normative: changed\n")
        with self.assertRaisesRegex(ValueError, "out-of-scope"):
            self.publish()

    def test_open_pr_without_remote_branch_fails_closed(self):
        self.open_pr = {"number": 7, "html_url": "https://github.com/owner/repo/pull/7"}
        self.regenerate(observed_at="2026-09-18T00:00:00Z", status="pass")
        with self.assertRaisesRegex(ValueError, "no remote branch"):
            self.publish()

    def test_api_errors_fail_closed_before_versioned_publication(self):
        self.regenerate(observed_at="2026-09-18T00:00:00Z", status="pass")
        path = self.root / "generated/reports/governance-repository-security.json"
        current = json.loads(path.read_text())
        current["observation"]["api_errors"] = ["administrative setting unavailable"]
        self.write_json("generated/reports/governance-repository-security.json", current)
        with self.assertRaisesRegex(ValueError, "observation is incomplete"):
            self.publish()
        self.assertFalse(any(call[0] in {"POST", "PATCH"} for call in self.calls))

    def test_time_is_the_only_ignored_report_field(self):
        old = report("2026-09-17T00:00:00Z")
        new = report("2026-09-18T00:00:00Z")
        self.assertTrue(materially_equal(old, new))
        new["summary"]["fail"] = 2
        self.assertFalse(materially_equal(old, new))


class SelfSecurityRefreshWorkflowTests(unittest.TestCase):
    def test_refresh_is_trusted_main_only_and_never_merges(self):
        path = ROOT / ".github/workflows/refresh-governance-repository-security.yml"
        text = path.read_text()
        workflow = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(workflow["jobs"]["refresh"]["if"], "github.ref == 'refs/heads/main'")
        self.assertEqual(workflow["jobs"]["refresh"]["steps"][0]["with"]["ref"], "main")
        self.assertIn("scripts/publish_self_security_refresh.py", text)
        self.assertIn(
            "open-policy-agent/setup-opa@b2b258e089860efaadaaf71bf6e3aecb4a3eeff1",
            text,
        )
        self.assertIn("secrets.GH_SELF_SECURITY_READ_TOKEN || github.token", text)
        self.assertNotIn("secrets.GH_RESULT_INTAKE_TOKEN", text)
        self.assertEqual(
            workflow["jobs"]["refresh"]["steps"][2]["with"]["version"],
            "1.18.2",
        )
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("git push", text)
        self.assertEqual(workflow["permissions"]["pull-requests"], "write")
        self.assertEqual(workflow["permissions"]["actions"], "write")

    def test_live_viewer_projection_matches_live_security_report(self):
        report = json.loads(
            (ROOT / "generated/reports/governance-repository-security.json").read_text()
        )
        projection = json.loads((ROOT / "generated/viewer/app/data.json").read_text())[
            "repository_security"
        ]
        projected_keys = (
            "repository_id",
            "observed_at",
            "profile_version",
            "enforcement",
            "overall_status",
            "summary",
            "risk_statement",
            "criteria",
            "next_steps",
            "decision_boundary",
        )
        self.assertEqual(
            {key: report[key] for key in projected_keys},
            {key: projection[key] for key in projected_keys},
        )
        self.assertEqual(
            projection["source_file"],
            "generated/reports/governance-repository-security.json",
        )

    def test_daily_schedule_has_one_writer_and_read_only_assessment_stays_event_driven(self):
        refresh = yaml.load(
            (ROOT / ".github/workflows/refresh-governance-repository-security.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        assessment = yaml.load(
            (ROOT / ".github/workflows/governance-repository-security.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertEqual(refresh["on"]["schedule"][0]["cron"], "31 4 * * *")
        self.assertNotIn("schedule", assessment["on"])
        self.assertIn("pull_request", assessment["on"])
        self.assertIn("push", assessment["on"])
        self.assertIn("workflow_dispatch", assessment["on"])

    def test_dependency_review_supports_dispatched_automation_branches(self):
        workflow = yaml.load(
            (ROOT / ".github/workflows/dependency-review.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertIn("workflow_dispatch", workflow["on"])
        action = workflow["jobs"]["dependency-review"]["steps"][0]
        self.assertIn("inputs.base_ref", action["with"]["base-ref"])
        self.assertIn("inputs.head_ref", action["with"]["head-ref"])


if __name__ == "__main__":
    unittest.main()
