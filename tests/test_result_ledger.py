from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.result_ledger import (  # noqa: E402
    AppendOnlyConflictError,
    apply_replay_assessment,
    write_snapshot_append_only,
)


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


repository_index = load_script("generate_repository_results_index")
architecture_index = load_script("generate_architecture_results_index")
viewer = load_script("generate_status_viewer")


def trust_record(*, repository="owner/repo", commit="abc123", run="42", attempt=1, artifact="evidence", digest="a" * 64):
    return {
        "model_id": "evidence-trust-model-v1",
        "capture_phase": "additive_capture",
        "effective_level": "integrity_verified",
        "assessment_status": "evaluated",
        "verifier": "test/v1",
        "verified_at": "2026-07-17T12:01:00Z",
        "checks": [
            {"id": "replay_key_unique", "result": "not_evaluated", "evidence_refs": []}
        ],
        "capture": {
            "source": {
                "repository_id": repository,
                "commit_id": commit,
                "workflow_name": "Governance",
                "run_id": run,
                "run_attempt": attempt,
                "artifact_name": artifact,
            },
            "subjects": [{"id": "report", "digest": digest}],
        },
    }


class ResultLedgerTests(unittest.TestCase):
    def test_snapshot_write_is_idempotent_for_same_evidence_identity(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "results" / "snapshot.json"
            first = {"generated_at": "2026-07-17T12:00:00Z", "trust": trust_record()}
            second = {"generated_at": "2026-07-17T12:00:00Z", "trust": trust_record()}
            second["trust"]["verified_at"] = "2026-07-17T13:00:00Z"
            write_snapshot_append_only(path, first, conflict_root=root / "conflicts")
            write_snapshot_append_only(path, second, conflict_root=root / "conflicts")

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), first)
            self.assertFalse((root / "conflicts").exists())

    def test_snapshot_write_is_idempotent_when_generated_timestamp_changes(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            first_path = root / "results" / "2026-07-17T12-00-00Z-run-42.json"
            retry_path = root / "results" / "2026-07-17T12-05-00Z-run-42.json"
            first = {"generated_at": "2026-07-17T12:00:00Z", "trust": trust_record()}
            retry = {"generated_at": "2026-07-17T12:05:00Z", "trust": trust_record()}
            write_snapshot_append_only(first_path, first, conflict_root=root / "conflicts")
            selected = write_snapshot_append_only(retry_path, retry, conflict_root=root / "conflicts")

            self.assertEqual(selected, first_path)
            self.assertFalse(retry_path.exists())
            self.assertFalse((root / "conflicts").exists())

    def test_snapshot_conflict_is_quarantined_without_overwrite(self):
        schema = json.loads((ROOT / "schemas" / "intake-conflict.schema.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "results" / "owner__repo" / "snapshot.json"
            first = {"generated_at": "2026-07-17T12:00:00Z", "trust": trust_record()}
            changed = {"generated_at": "2026-07-17T12:00:00Z", "trust": trust_record(digest="b" * 64)}
            write_snapshot_append_only(path, first, conflict_root=root / "conflicts")

            with self.assertRaises(AppendOnlyConflictError) as raised:
                write_snapshot_append_only(
                    path,
                    changed,
                    conflict_root=root / "conflicts",
                    raise_on_conflict=True,
                )

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), first)
            conflict = json.loads(raised.exception.conflict_path.read_text(encoding="utf-8"))
            Draft202012Validator(schema).validate(conflict)
            self.assertEqual(conflict["enforcement"], "report_only")

    def test_replay_assessment_distinguishes_safe_and_conflicting_reuse(self):
        current = trust_record()
        unseen = apply_replay_assessment(current, [])
        exact = apply_replay_assessment(current, [{"trust": trust_record()}])
        compatible = apply_replay_assessment(
            current,
            [{"trust": trust_record(run="41", attempt=2)}],
        )
        conflicting_context = apply_replay_assessment(
            current,
            [{"trust": trust_record(digest="b" * 64)}],
        )
        incompatible = apply_replay_assessment(
            current,
            [{"trust": trust_record(repository="other/repo")}],
        )

        def replay_check(value):
            return next(check for check in value["checks"] if check["id"] == "replay_key_unique")

        self.assertEqual(replay_check(unseen)["result"], "pass")
        self.assertIn("idempotent", replay_check(exact)["reason"])
        self.assertEqual(replay_check(compatible)["result"], "pass")
        self.assertEqual(replay_check(conflicting_context)["result"], "fail")
        self.assertEqual(replay_check(incompatible)["result"], "fail")
        self.assertEqual(incompatible["effective_level"], "integrity_verified")

    def test_result_indexes_keep_payload_and_source_path_paired(self):
        for module, domain in (
            (repository_index, "devsecops"),
            (architecture_index, "architecture"),
        ):
            with self.subTest(domain=domain), tempfile.TemporaryDirectory() as tempdir:
                root = Path(tempdir)
                results_root = root / "results"
                repo_dir = results_root / "owner__repo"
                repo_dir.mkdir(parents=True)
                common = {
                    "repository_id": "owner/repo",
                    "pipeline": {"event": "push", "status": "success", "pipeline_url": "https://example.test"},
                    "repository": {"branch": "main", "commit_id": "abc123"},
                    "overall_status": "pass",
                }
                early = {
                    **common,
                    "generated_at": "2026-07-17T10:00:00Z",
                    "pipeline": {**common["pipeline"], "pipeline_run_id": "10"},
                }
                late = {
                    **common,
                    "generated_at": "2026-07-17T11:00:00Z",
                    "pipeline": {**common["pipeline"], "pipeline_run_id": "11"},
                }
                if domain == "devsecops":
                    early["governance_baseline_ref"] = late["governance_baseline_ref"] = "baseline"
                else:
                    early["architecture_baseline_ref"] = late["architecture_baseline_ref"] = "architecture-baseline"
                    early["architecture_summary"] = late["architecture_summary"] = {"finding_count": 0}
                (repo_dir / "a-late.json").write_text(json.dumps(late), encoding="utf-8")
                (repo_dir / "z-early.json").write_text(json.dumps(early), encoding="utf-8")

                old_values = module.ROOT, module.STATUS_RESULTS, module.INDEX_PATH
                module.ROOT, module.STATUS_RESULTS, module.INDEX_PATH = root, results_root, root / "index.json"
                try:
                    module.main()
                    index = json.loads(module.INDEX_PATH.read_text(encoding="utf-8"))
                finally:
                    module.ROOT, module.STATUS_RESULTS, module.INDEX_PATH = old_values

                history = {item["pipeline_run_id"]: item["source_file"] for item in index["repositories"][0]["history"]}
                self.assertEqual(history["10"], "results/owner__repo/z-early.json")
                self.assertEqual(history["11"], "results/owner__repo/a-late.json")
                self.assertEqual(index["repositories"][0]["latest_result"]["source_file"], "results/owner__repo/a-late.json")

    def test_viewer_exposes_report_only_conflict_quarantine(self):
        section = viewer.build_intake_conflicts_section(
            [
                {
                    "enforcement": "report_only",
                    "detected_at": "2026-07-17T12:00:00Z",
                    "target_path": "status/results/owner__repo/result.json",
                    "existing_payload_sha256": "a" * 64,
                    "incoming_payload_sha256": "b" * 64,
                }
            ]
        )
        self.assertIn("Intake Conflict Quarantine", section)
        self.assertIn("report_only", section)
        self.assertIn("status/results/owner__repo/result.json", section)


if __name__ == "__main__":
    unittest.main()
