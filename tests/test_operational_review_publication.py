from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publish_operational_update import publish, selected_paths, CHECK_WORKFLOWS


class OperationalPublicationTests(unittest.TestCase):
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
        self.write("model/control.yaml", "normative: unchanged\n")
        self.write("status/results/existing.json", '{"immutable":true}\n')
        self.write("generated/reports/portfolio-onboarding-status.json", '{"observation":1}\n')
        self.git("add", ".")
        self.git("commit", "-m", "Baseline")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.calls = []

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE)

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)

    def api(self, endpoint, payload):
        self.calls.append((endpoint, payload))
        return {"html_url": "https://github.com/owner/repo/pull/1"} if endpoint.endswith("/pulls") else {}

    def publish(self, scope="portfolio", run_id="123", attempt="1"):
        return publish(self.root, scope=scope, repository="owner/repo", run_id=run_id,
                       attempt=attempt, api=self.api)

    def test_only_review_branch_is_pushed_and_checks_are_dispatched(self):
        self.write("generated/reports/portfolio-onboarding-status.json", '{"observation":2}\n')
        self.write("generated/reports/unrelated.json", '{"timestamp":"noise"}\n')
        self.publish()
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").split()[0], self.base)
        changed = self.git("diff", "--name-only", self.base, "HEAD").splitlines()
        self.assertEqual(changed, ["generated/reports/portfolio-onboarding-status.json"])
        self.assertEqual(self.calls[0][1]["base"], "main")
        self.assertEqual(self.calls[0][1]["head"], "automation/portfolio/123-1")
        self.assertEqual(len(self.calls), 4)
        for (endpoint, payload), workflow in zip(self.calls[1:], CHECK_WORKFLOWS):
            self.assertTrue(endpoint.endswith(f"/{workflow}/dispatches"))
            self.assertEqual(payload, {"ref": "automation/portfolio/123-1"})

    def test_no_change_opens_no_pr(self):
        self.assertIsNone(self.publish())
        self.assertEqual(self.calls, [])

    def test_normative_change_is_rejected_even_when_already_staged(self):
        self.write("model/control.yaml", "normative: changed\n")
        self.git("add", "model/control.yaml")
        with self.assertRaisesRegex(ValueError, "out-of-scope"):
            self.publish()
        self.assertEqual(self.calls, [])

    def test_existing_evidence_cannot_be_rewritten_or_deleted(self):
        for deletion in (False, True):
            with self.subTest(deletion=deletion):
                path = self.root / "status/results/existing.json"
                if deletion:
                    path.unlink()
                else:
                    path.write_text('{"immutable":false}\n')
                with self.assertRaisesRegex(ValueError, "append-only"):
                    selected_paths(self.root, "devsecops")
        self.assertEqual(self.calls, [])

    def test_new_failed_attempt_and_event_can_be_proposed_together(self):
        self.write("status/collection-attempts/new.json", '{"status":"failed"}\n')
        self.write("status/intake-events/new.json", '{"status":"failed"}\n')
        self.publish("devsecops")
        self.assertEqual(self.git("diff", "--name-only", self.base, "HEAD").splitlines(),
                         ["status/collection-attempts/new.json", "status/intake-events/new.json"])
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").split()[0], self.base)

    def test_symlink_in_allowed_path_is_rejected(self):
        path = self.root / "generated/reports/portfolio-onboarding-status.json"
        path.unlink()
        path.symlink_to(self.root / "model/control.yaml")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.publish()

    def test_unreviewed_parent_commit_cannot_enter_pr(self):
        self.write("model/control.yaml", "normative: changed\n")
        self.git("add", "model/control.yaml")
        self.git("commit", "-m", "Unreviewed normative commit")
        self.write("generated/reports/portfolio-onboarding-status.json", '{"observation":2}\n')
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish()
        self.assertEqual(self.calls, [])

    def test_parallel_runs_keep_separate_branches_without_touching_main(self):
        for run_id in ("123", "124"):
            self.git("checkout", "main")
            self.write(f"status/intake-events/{run_id}.json", '{"status":"success"}\n')
            self.publish("devsecops", run_id=run_id)
        refs = self.git("ls-remote", "--heads", "origin")
        self.assertIn("refs/heads/automation/devsecops/123-1", refs)
        self.assertIn("refs/heads/automation/devsecops/124-1", refs)
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").split()[0], self.base)

    def test_invalid_run_identity_is_rejected_before_publication(self):
        with self.assertRaisesRegex(ValueError, "positive integers"):
            self.publish(run_id="../main")
        self.assertEqual(self.calls, [])


class OperationalWorkflowTests(unittest.TestCase):
    def test_writers_only_publish_review_prs_from_main(self):
        for name in ("intake-governance-result.yml", "intake-architecture-result.yml",
                     "intake-evidence-trust.yml", "portfolio-status.yml"):
            with self.subTest(workflow=name):
                text = (ROOT / ".github/workflows" / name).read_text()
                workflow = yaml.load(text, Loader=yaml.BaseLoader)
                self.assertNotIn("git push", text)
                self.assertNotIn("gh pr merge", text)
                job = next(iter(workflow["jobs"].values()))
                self.assertEqual(job["if"], "github.ref == 'refs/heads/main'")
                steps = job["steps"]
                self.assertEqual(steps[0]["with"]["ref"], "main")
                publisher = next(step for step in steps if step["name"] == "Open operational review PR")
                self.assertIn("scripts/publish_operational_update.py --scope", publisher["run"])
                self.assertEqual(publisher["env"]["GH_TOKEN"], "${{ github.token }}")
                self.assertEqual(workflow["permissions"]["pull-requests"], "write")
                self.assertEqual(workflow["permissions"]["actions"], "write")

    def test_all_required_bot_checks_can_be_dispatched(self):
        for name in CHECK_WORKFLOWS:
            workflow = yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)
            self.assertIn("workflow_dispatch", workflow["on"])


if __name__ == "__main__":
    unittest.main()
