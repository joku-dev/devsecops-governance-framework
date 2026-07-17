from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_collection_attempt_retry.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("prepare_collection_attempt_retry", SCRIPT)
retry = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(retry)


def attempt(*, evidence_type="governance_result", collector_id="central-governance-intake",
            artifact_name="governance-control-evaluation", retryable=True):
    return {
        "attempt_id": "attempt-1",
        "repository_id": "owner/repo",
        "evidence_type": evidence_type,
        "collector": {"id": collector_id, "version": "0.1.0"},
        "source": {"run_id": "42", "artifact_name": artifact_name},
        "errors": [{"code": "intake_failed", "message": "failed", "retryable": retryable}],
    }


class PrepareCollectionAttemptRetryTests(unittest.TestCase):
    def test_routes_supported_attempt_types(self):
        cases = (
            (attempt(), "intake-governance-result.yml"),
            (attempt(artifact_name="architecture-governance-evidence"), "intake-architecture-result.yml"),
            (attempt(
                evidence_type="vulnerability_scan",
                collector_id="central-vulnerability-scan-collector",
                artifact_name="application-evidence",
            ), "intake-evidence-trust.yml"),
        )
        for payload, expected in cases:
            with self.subTest(workflow=expected):
                self.assertEqual(retry.build_retry_plan(payload)["workflow"], expected)

    def test_rejects_any_non_retryable_error(self):
        payload = attempt()
        payload["errors"].append({"code": "permanent", "message": "permanent", "retryable": False})
        with self.assertRaisesRegex(ValueError, "non-retryable"):
            retry.build_retry_plan(payload)

    def test_rejects_unknown_route_and_unsafe_dispatch_values(self):
        with self.assertRaisesRegex(ValueError, "supported retry route"):
            retry.build_retry_plan(attempt(artifact_name="unknown-artifact"))
        payload = attempt()
        payload["source"]["run_id"] = "42; rm"
        with self.assertRaisesRegex(ValueError, "run_id"):
            retry.build_retry_plan(payload)

    def test_attempt_path_cannot_escape_collection_attempt_root(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "collection-attempts"
            root.mkdir()
            outside = Path(tempdir) / "outside.json"
            outside.write_text(json.dumps(attempt()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "below status/collection-attempts"):
                retry.load_attempt(str(outside), attempt_root=root)

    def test_retry_workflow_has_minimal_permissions_and_dispatches_existing_intake(self):
        content = (ROOT / ".github" / "workflows" / "retry-collection-attempt.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", content)
        self.assertIn("actions: write", content)
        self.assertIn("prepare_collection_attempt_retry.py", content)
        self.assertIn("ATTEMPT_PATH: ${{ inputs.attempt_path }}", content)
        self.assertNotIn('--attempt-path "${{ inputs.attempt_path }}"', content)
        self.assertIn('gh workflow run "${WORKFLOW}"', content)


if __name__ == "__main__":
    unittest.main()
