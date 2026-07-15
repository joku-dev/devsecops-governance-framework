from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


repository_index = load_script("generate_repository_results_index")
architecture_index = load_script("generate_architecture_results_index")


VERIFIED_TRUST = {
    "model_id": "evidence-trust-model-v1",
    "effective_level": "integrity_verified",
    "assessment_status": "evaluated",
    "verified_at": "2026-07-15T15:00:00Z",
    "checks": [
        {"id": "subject_identity_complete", "result": "pass", "evidence_refs": []},
        {"id": "content_digest_verified", "result": "pass", "evidence_refs": []},
    ],
}


class EvidenceTrustIndexTests(unittest.TestCase):
    def write_result(self, directory: Path, name: str, payload: dict) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_devsecops_latest_selection_is_unchanged_and_trust_is_projected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            results = root / "results" / "owner__repo"
            self.write_result(
                results,
                "1-main.json",
                {
                    "repository_id": "owner/repo",
                    "baseline_level": "L1",
                    "governance_baseline_ref": "baseline-v1",
                    "generated_at": "2026-07-15T14:00:00Z",
                    "pipeline": {"pipeline_run_id": "1", "event": "push", "pipeline_url": ""},
                    "repository": {"branch": "main", "commit_id": "aaa"},
                    "overall_status": "pass",
                },
            )
            self.write_result(
                results,
                "2-manual.json",
                {
                    "repository_id": "owner/repo",
                    "baseline_level": "L1",
                    "governance_baseline_ref": "baseline-v1",
                    "generated_at": "2026-07-15T15:00:00Z",
                    "pipeline": {"pipeline_run_id": "2", "event": "workflow_dispatch", "pipeline_url": ""},
                    "repository": {"branch": "main", "commit_id": "bbb"},
                    "overall_status": "fail",
                    "trust": VERIFIED_TRUST,
                },
            )
            old_root, old_results, old_index = repository_index.ROOT, repository_index.STATUS_RESULTS, repository_index.INDEX_PATH
            repository_index.ROOT = root
            repository_index.STATUS_RESULTS, repository_index.INDEX_PATH = root / "results", root / "index.json"
            try:
                repository_index.main()
                payload = json.loads(repository_index.INDEX_PATH.read_text(encoding="utf-8"))
            finally:
                repository_index.ROOT = old_root
                repository_index.STATUS_RESULTS, repository_index.INDEX_PATH = old_results, old_index

        latest = payload["repositories"][0]["latest_result"]
        self.assertEqual(latest["pipeline_run_id"], "1")
        self.assertEqual(latest["status"], "pass")
        self.assertEqual(latest["trust"]["assessment_status"], "not_available")
        self.assertEqual(payload["repositories"][0]["history"][1]["trust"]["effective_level"], "integrity_verified")
        schema = json.loads((ROOT / "schemas" / "governance-results-index.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(payload)

    def test_architecture_index_projects_historical_trust_without_reclassification(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            results = root / "results" / "owner__repo"
            self.write_result(
                results,
                "1-main.json",
                {
                    "repository_id": "owner/repo",
                    "architecture_baseline_ref": "architecture-v1",
                    "generated_at": "2026-07-15T14:00:00Z",
                    "pipeline": {"pipeline_run_id": "1", "event": "push", "pipeline_url": ""},
                    "repository": {"branch": "main", "commit_id": "aaa"},
                    "overall_status": "pass",
                    "architecture_summary": {"finding_count": 0},
                },
            )
            old_root, old_results, old_index = architecture_index.ROOT, architecture_index.STATUS_RESULTS, architecture_index.INDEX_PATH
            architecture_index.ROOT = root
            architecture_index.STATUS_RESULTS, architecture_index.INDEX_PATH = root / "results", root / "index.json"
            try:
                architecture_index.main()
                payload = json.loads(architecture_index.INDEX_PATH.read_text(encoding="utf-8"))
            finally:
                architecture_index.ROOT = old_root
                architecture_index.STATUS_RESULTS, architecture_index.INDEX_PATH = old_results, old_index

        latest = payload["repositories"][0]["latest_result"]
        self.assertEqual(latest["status"], "pass")
        self.assertEqual(latest["trust"]["effective_level"], "unverified")
        schema = json.loads((ROOT / "schemas" / "architecture-results-index.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
