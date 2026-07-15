from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import collect_vulnerability_scan_evidence as collector
import intake_evidence_trust_github_actions_run as intake


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


typed_index = load_script("generate_typed_evidence_results_index")


class TypedEvidenceIntakeTests(unittest.TestCase):
    def create_capture(self, directory: Path) -> tuple[dict, dict]:
        scan = directory / "security" / "vulnerability-scan.json"
        scan.parent.mkdir(parents=True)
        scan.write_text(
            json.dumps(
                {
                    "scanner": {"name": "trivy", "version": "v0.70.0"},
                    "produced_at": "2026-07-15T16:00:00Z",
                    "artifact": "application-source.tar.gz",
                    "max_severity": "none",
                    "findings": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        subject = directory / "dist" / "application-source.tar.gz"
        subject.parent.mkdir(parents=True)
        subject.write_bytes(b"application evidence\n")
        trust = collector.collect(
            scan_path=scan,
            evaluated_subject_path=subject,
            repository_id="owner/repo",
            commit_id="abc123",
            workflow_name="DevSecOps Baseline",
            run_id="42",
            run_attempt=1,
            artifact_name="application-evidence",
            source_uri="https://github.test/owner/repo/actions/runs/42",
            source_provider="ci_artifact",
            produced_at=None,
            captured_at="2026-07-15T16:01:00Z",
        )
        run = {
            "id": 42,
            "name": "DevSecOps Baseline",
            "event": "push",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "abc123",
            "run_attempt": 1,
            "html_url": "https://github.test/owner/repo/actions/runs/42",
            "created_at": "2026-07-15T16:00:00Z",
            "updated_at": "2026-07-15T16:02:00Z",
        }
        return trust, run

    def test_central_intake_reverifies_subjects_and_replaces_verifier(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            trust, run = self.create_capture(directory)
            verified = intake.centrally_verify_trust(
                trust,
                repository_id="owner/repo",
                run=run,
                artifact_name="application-evidence",
                extract_dir=directory,
                verified_at="2026-07-15T16:03:00Z",
            )

        self.assertEqual(verified["verifier"], intake.VERIFIER_ID)
        self.assertEqual(verified["effective_level"], "integrity_verified")
        checks = {check["id"]: check["result"] for check in verified["checks"]}
        self.assertEqual(checks["content_digest_verified"], "pass")
        self.assertEqual(checks["freshness_evaluated"], "pass")

    def test_central_intake_makes_tampered_subject_visible(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir)
            trust, run = self.create_capture(directory)
            (directory / "dist" / "application-source.tar.gz").write_bytes(b"tampered\n")
            verified = intake.centrally_verify_trust(
                trust,
                repository_id="owner/repo",
                run=run,
                artifact_name="application-evidence",
                extract_dir=directory,
                verified_at="2026-07-15T16:03:00Z",
            )

        self.assertEqual(verified["effective_level"], "unverified")
        checks = {check["id"]: check["result"] for check in verified["checks"]}
        self.assertEqual(checks["content_digest_verified"], "fail")

    def test_typed_index_preserves_mainline_latest_selection(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            results = root / "results" / "owner__repo"
            results.mkdir(parents=True)
            trust, run = self.create_capture(root / "evidence")
            common = {
                "schema_version": "1.0.0",
                "result_type": "typed-evidence-trust",
                "repository_id": "owner/repo",
                "evidence_type": "vulnerability_scan",
                "repository": {"branch": "main", "commit_id": "abc123"},
                "source_artifact": {},
                "trust": trust,
            }
            main = {
                **common,
                "generated_at": "2026-07-15T16:02:00Z",
                "pipeline": {
                    "pipeline_run_id": "42",
                    "pipeline_event": "push",
                    "event": "push",
                    "pipeline_url": run["html_url"],
                },
            }
            manual = {
                **common,
                "generated_at": "2026-07-15T17:02:00Z",
                "pipeline": {
                    "pipeline_run_id": "43",
                    "event": "workflow_dispatch",
                    "pipeline_url": "https://github.test/owner/repo/actions/runs/43",
                },
            }
            (results / "1-main.json").write_text(json.dumps(main), encoding="utf-8")
            (results / "2-manual.json").write_text(json.dumps(manual), encoding="utf-8")
            old_values = typed_index.ROOT, typed_index.STATUS_RESULTS, typed_index.INDEX_PATH
            typed_index.ROOT, typed_index.STATUS_RESULTS, typed_index.INDEX_PATH = root, root / "results", root / "index.json"
            try:
                typed_index.main()
                payload = json.loads(typed_index.INDEX_PATH.read_text(encoding="utf-8"))
            finally:
                typed_index.ROOT, typed_index.STATUS_RESULTS, typed_index.INDEX_PATH = old_values

        self.assertEqual(payload["repositories"][0]["latest_result"]["pipeline_run_id"], "42")
        self.assertEqual(payload["summary"]["mainline_results"], 1)
        self.assertEqual(payload["summary"]["manual_results"], 1)
        schema = json.loads((ROOT / "schemas" / "typed-evidence-results-index.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
