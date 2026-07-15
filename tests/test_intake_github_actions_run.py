from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "intake_github_actions_run.py"


sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("intake_github_actions_run", SCRIPT)
intake = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(intake)


class GitHubActionsRunIntakeTests(unittest.TestCase):
    def test_infers_tagged_baseline_ref(self):
        run = {
            "referenced_workflows": [
                {
                    "path": "joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3",
                    "ref": "refs/tags/l1-baseline-v1.1.3",
                }
            ]
        }

        self.assertEqual(intake.infer_baseline_ref(run), "l1-baseline-v1.1.3")

    def test_evidence_flags_are_derived_from_governance_input(self):
        governance_input = {
            "traceability": {
                "requirements_linked": True,
                "testcases_linked": True,
                "reports_linked": True,
            },
            "static_analysis": {
                "performed": True,
            },
            "evidence": {
                "sbom": {"exists": True},
                "vulnerability_scan": {"exists": True},
            },
            "artifact": {
                "digest": {"exists": True},
            },
            "operations": {
                "deployed_versions_recorded": True,
                "security_events_recorded": True,
            },
        }

        flags = intake.evidence_flags(
            governance_input,
            {"governance-control-evaluation", "devsecops-governance-run-input"},
        )

        self.assertTrue(flags["sbom"])
        self.assertTrue(flags["vulnerability_scan"])
        self.assertTrue(flags["artifact_digest"])
        self.assertTrue(flags["governance_control_report"])
        self.assertTrue(flags["governance_run_input"])
        self.assertTrue(flags["static_analysis_summary"])
        self.assertTrue(flags["traceability_mapping"])
        self.assertTrue(flags["operations_evidence"])

    def test_find_job_status_matches_fragments(self):
        jobs = [
            {"name": "Prepare DevSecOps Evidence", "conclusion": "success"},
            {"name": "Central DevSecOps Baseline / Released DevSecOps L1 Baseline v1.1.3 / DevSecOps Baseline Gate", "conclusion": "success"},
        ]

        self.assertEqual(intake.find_job_status(jobs, "baseline", "gate"), "success")

    def test_compute_sha256_returns_expected_hash(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "sample.txt"
            path.write_text("hello world", encoding="utf-8")
            self.assertEqual(
                intake.compute_sha256(path),
                "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
            )

    def test_artifact_size_bytes_uses_github_api_field(self):
        self.assertEqual(intake.artifact_size_bytes({"size_in_bytes": 5438}), 5438)
        self.assertEqual(intake.artifact_size_bytes({"size": 1234}), 1234)

    def test_find_governance_input_returns_payload_and_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            nested = directory / "governance"
            nested.mkdir()
            data = {"evidence": {"sbom": {"exists": True}}}
            payload_path = nested / "governance-run-input.json"
            payload_path.write_text(json.dumps(data), encoding="utf-8")

            payload, path = intake.find_governance_input(directory)
            self.assertEqual(payload, data)
            self.assertEqual(path, payload_path)

    def test_write_snapshot_includes_downloaded_artifact_metadata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            old_status_results = intake.STATUS_RESULTS
            intake.STATUS_RESULTS = temp_root / "status" / "results"
            try:
                report_path = temp_root / "control-evaluation-report.json"
                report_path.write_text(json.dumps({"summary": {"fail": 0}}), encoding="utf-8")
                governance_input_path = temp_root / "governance-run-input.json"
                governance_input_path.write_text(json.dumps({"evidence_refs": ["ref1"]}), encoding="utf-8")
                report_sha256 = intake.compute_sha256(report_path)
                governance_input_sha256 = intake.compute_sha256(governance_input_path)
                report_path.unlink()
                governance_input_path.unlink()
                run = {"id": 1, "conclusion": "success", "updated_at": "2026-07-04T00:00:00Z", "head_branch": "main", "head_sha": "abc123", "html_url": "https://example.com/run/1", "name": "DevSecOps Baseline", "event": "push"}
                jobs = []
                artifacts = [{"name": "governance-control-evaluation", "size_in_bytes": 5438}]
                selected_artifact = artifacts[0]
                output_path = intake.write_snapshot(
                    repository_id="owner/repo",
                    baseline_level="L1",
                    governance_baseline_ref="l1-baseline-v1.1.3",
                    run=run,
                    jobs=jobs,
                    report={"summary": {"fail": 0}},
                    governance_input={"evidence_refs": ["ref1"]},
                    report_sha256=report_sha256,
                    governance_input_sha256=governance_input_sha256,
                    branch_protected=True,
                    artifacts=artifacts,
                    selected_artifact=selected_artifact,
                    artifact_names={"governance-control-evaluation"},
                    notes="test",
                )
                data = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(data["governance_repository"], "joku-dev/devsecops-governance-framework")
                self.assertEqual(data["downloaded_artifact"]["downloaded"], True)
                self.assertEqual(data["downloaded_artifact"]["artifact_size_bytes"], 5438)
                self.assertEqual(data["downloaded_artifact"]["control_evaluation_report_sha256"], report_sha256)
                self.assertEqual(data["downloaded_artifact"]["governance_run_input_sha256"], governance_input_sha256)
                self.assertEqual(data["artifact_metadata"]["artifact_sizes"]["governance-control-evaluation"], 5438)
            finally:
                intake.STATUS_RESULTS = old_status_results
