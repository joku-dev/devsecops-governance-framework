"""Live preflight rejects ambiguous bindings and never promotes captured data into state."""
from copy import deepcopy
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, validate_record
from lib.governance_lifecycle.live_preparation import validate_preparation
from lib.governance_lifecycle.live_evidence import collect_preflight, replay_capture, sha, verify_capture

AT = "2026-09-13T13:00:00Z"
REPO = "joku-dev/devsecops-governance-framework"


class LiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.profile = validate_preparation()["profile"]
        self.files = {p:(ROOT / p).read_bytes() for p in self.profile["source"]["reference_files"]}
        self.report = strict_json((ROOT / "generated/reports/governance-repository-security.json").read_bytes())
        self.report["observed_at"] = "2026-09-13T12:59:05Z"
        self.report["observation"]["observed_at"] = self.report["observed_at"]
        self.repository = {"id":1301369468, "full_name":REPO, "default_branch":"main"}
        self.run = {"id":123, "run_attempt":1, "workflow_id":315792416,
            "repository":{"id":1301369468}, "head_repository":{"id":1301369468},
            "head_branch":"main", "event":"push", "status":"completed", "conclusion":"success",
            "head_sha":self.profile["source"]["reference_commit"],
            "path":self.profile["source"]["workflow_path"], "run_started_at":"2026-09-13T12:59:00Z",
            "updated_at":"2026-09-13T12:59:20Z"}
        self.workflow = {"id":self.run["workflow_id"], "path":self.run["path"]}
        self.artifact = {"id":456, "name":"governance-repository-security", "expired":False,
            "created_at":"2026-09-13T12:59:10Z", "expires_at":"2026-12-12T12:59:10Z",
            "workflow_run":{"id":123, "repository_id":1301369468, "head_repository_id":1301369468,
                            "head_sha":self.run["head_sha"], "head_branch":"main"}}
        self.repack()

    def repack(self, names=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("governance-repository-security.json", json_bytes(self.report))
            z.writestr("governance-repository-security.md", "Synthetic transport fixture\n")
            for name in names or []:
                z.writestr(name, "unsupported")
        self.archive = buffer.getvalue()
        self.artifact.update(digest="sha256:" + sha(self.archive), size_in_bytes=len(self.archive))

    def verify(self):
        return verify_capture(self.profile, repository=self.repository, run=self.run, workflow=self.workflow,
            artifact=self.artifact, archive=self.archive, files=self.files, captured_at=AT)[0]

    def fake_fetch(self, endpoint, *, raw=False):
        prefix = "repos/" + REPO
        mapping = {prefix:self.repository, prefix+"/actions/runs/123":self.run,
            prefix+"/actions/workflows/315792416":self.workflow,
            prefix+"/actions/runs/123/artifacts?per_page=100&page=1":{"total_count":1,"artifacts":[self.artifact]},
            prefix+"/actions/artifacts/456":self.artifact}
        if endpoint in mapping:
            return json_bytes(mapping[endpoint])
        if endpoint == prefix+"/actions/artifacts/456/zip":
            return self.archive
        for path, data in self.files.items():
            if endpoint == prefix+"/contents/"+path+"?ref="+self.run["head_sha"]:
                self.assertTrue(raw)
                return data
        self.fail("Unexpected request: " + endpoint)

    def test_consistent_capture_keeps_acceptance_and_freshness_unapproved(self):
        result = self.verify()
        self.assertEqual(len(result["checks"]), 10)
        self.assertEqual(result["acceptance_status"], "not_evaluated")
        self.assertFalse(result["official_state"])
        self.assertEqual(result["verification_scope"], "captured_metadata_and_bytes")
        self.assertEqual(result["source"]["age_seconds"], 55)
        self.assertNotIn("freshness_evaluated", result["checks"])
        with self.assertRaises(ContractError):
            validate_record(result)

    def test_pr_manual_schedule_branch_fork_and_rerun_are_rejected(self):
        for mutate in (lambda r:r.update(event="pull_request"), lambda r:r.update(event="workflow_dispatch"),
                       lambda r:r.update(event="schedule"), lambda r:r.update(head_branch="feature/test"),
                       lambda r:r["head_repository"].update(id=42), lambda r:r.update(run_attempt=2),
                       lambda r:r.update(run_attempt=True), lambda r:r.update(conclusion="failure")):
            before = deepcopy(self.run); mutate(self.run)
            with self.assertRaises(ContractError):
                self.verify()
            self.run = before

    def test_artifact_association_digest_expiration_and_workflow_mismatches(self):
        for mutate in (lambda a:a["workflow_run"].update(id=999), lambda a:a["workflow_run"].update(head_sha="f"*40),
                       lambda a:a.update(digest="sha256:"+"0"*64), lambda a:a.update(expired=True),
                       lambda a:a.update(name="other"), lambda a:a.update(expires_at="2026-09-13T12:59:59Z")):
            before = deepcopy(self.artifact); mutate(self.artifact)
            with self.assertRaises(ContractError):
                self.verify()
            self.artifact = before
        self.workflow["path"] = ".github/workflows/untrusted.yml"
        with self.assertRaises(ContractError):
            self.verify()

    def test_pinned_source_bytes_and_missing_file_are_rejected(self):
        path = "scripts/assess_governance_repository_security.py"
        self.files[path] += b"\n"
        with self.assertRaisesRegex(ContractError, "Producer revision"):
            self.verify()
        del self.files[path]
        with self.assertRaisesRegex(ContractError, "file set"):
            self.verify()

    def test_criterion_profile_review_count_and_summary_conflicts_are_rejected(self):
        for mutate in (lambda r:r.update(profile_version="99"),
                       lambda r:r["observation"]["repository"].update(required_approving_reviews=True),
                       lambda r:r["summary"].update(fail=999),
                       lambda r:r["criteria"].append(deepcopy(r["criteria"][0])),
                       lambda r:r["observation"].update(synthetic=True),
                       lambda r:r["observation"].update(repository_id="other/repo")):
            before = deepcopy(self.report); mutate(self.report); self.repack()
            with self.assertRaises(ContractError):
                self.verify()
            self.report = before
        criterion = next(c for c in self.report["criteria"] if c["id"] == "GRS-002")
        criterion["status"] = "fail" if criterion["status"] == "pass" else "pass"
        self.repack()
        with self.assertRaisesRegex(ContractError, "GRS-002 contradicts"):
            self.verify()

    def test_invalid_archive_paths_are_not_extracted(self):
        self.repack(["../outside.json"])
        with self.assertRaisesRegex(ContractError, "archive member"):
            self.verify()

    def test_future_or_outside_run_observation_is_rejected(self):
        self.report["observed_at"] = "2026-09-13T12:58:59Z"
        self.report["observation"]["observed_at"] = self.report["observed_at"]
        self.repack()
        with self.assertRaisesRegex(ContractError, "timeline"):
            self.verify()

    def test_collector_and_replay_preserve_bytes_but_not_offline_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            result = collect_preflight("123", root, fetch=self.fake_fetch, captured_at=AT)
            self.assertEqual(result["capture"]["method"], "injected_test_transport")
            self.assertEqual(replay_capture(root), {k:v for k,v in result.items() if k != "capture"})
            subprocess.run([sys.executable, str(ROOT / "scripts/preflight_lifecycle_live_evidence.py"),
                            "--verify-bundle", str(root)], check=True, capture_output=True)
            before = (root / "preflight.json").read_bytes()
            with self.assertRaisesRegex(ContractError, "already exists"):
                collect_preflight("123", root, fetch=self.fake_fetch, captured_at=AT)
            self.assertEqual((root / "preflight.json").read_bytes(), before)
            (root / "report.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ContractError, "Captured bytes differ"):
                replay_capture(root)

    def test_output_paths_and_failed_capture_preserve_official_state(self):
        for output in (ROOT / "status/new-live.json", ROOT / "governance/lifecycle/new", ROOT / "model/new"):
            with self.assertRaises(ContractError):
                collect_preflight("123", output, fetch=self.fake_fetch, captured_at=AT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            self.artifact["digest"] = "sha256:" + "0" * 64
            with self.assertRaises(ContractError):
                collect_preflight("123", root, fetch=self.fake_fetch, captured_at=AT)
            self.assertFalse(root.exists())

    def test_metadata_race_or_duplicate_named_artifact_prevents_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = 0
            def race(endpoint, *, raw=False):
                nonlocal calls
                result = self.fake_fetch(endpoint, raw=raw)
                if endpoint.endswith("/actions/runs/123"):
                    calls += 1
                    if calls == 2:
                        changed = strict_json(result); changed["run_attempt"] = 2; result = json_bytes(changed)
                return result
            root = Path(directory) / "race"
            with self.assertRaisesRegex(ContractError, "changed during capture"):
                collect_preflight("123", root, fetch=race, captured_at=AT)
            self.assertFalse(root.exists())
            def duplicate(endpoint, *, raw=False):
                if "artifacts?" in endpoint:
                    return json_bytes({"total_count":2,"artifacts":[self.artifact,self.artifact]})
                return self.fake_fetch(endpoint, raw=raw)
            with self.assertRaisesRegex(ContractError, "Exactly one"):
                collect_preflight("123", root, fetch=duplicate, captured_at=AT)
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
