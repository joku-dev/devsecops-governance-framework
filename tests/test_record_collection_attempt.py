from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import sys
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "record_collection_attempt.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("record_collection_attempt", SCRIPT)
attempts = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(attempts)


class RecordCollectionAttemptTests(unittest.TestCase):
    def test_run_metadata_is_used_when_available(self):
        run = {"id": 42, "run_attempt": 1, "name": "Governance", "head_sha": "abc", "html_url": "https://example.test/42"}
        with patch.object(attempts, "github_get_json", return_value=run):
            actual, errors = attempts.load_run_metadata(
                api_url="https://api.github.test",
                repository_id="owner/repo",
                run_id="42",
                token="token",
            )
        self.assertEqual(actual, run)
        self.assertEqual(errors, [])

    def test_metadata_failure_still_produces_valid_fallback_attempt(self):
        with patch.object(attempts, "github_get_json", side_effect=OSError("offline")):
            run, errors = attempts.load_run_metadata(
                api_url="https://api.github.test",
                repository_id="owner/repo",
                run_id="42",
                token="token",
            )
        payload = attempts.build_attempt(
            repository_id="owner/repo",
            run=run,
            evidence_type="governance_result",
            collector_id="central-governance-intake",
            collector_version="0.1.0",
            artifact_name="governance-control-evaluation",
            status="failed",
            code="devsecops_governance_intake_failed",
            message="Intake failed.",
            retryable=True,
            additional_errors=errors,
        )
        self.assertEqual(payload["source"]["run_id"], "42")
        self.assertEqual(payload["source"]["workflow_name"], "metadata-unavailable")
        self.assertEqual([error["code"] for error in payload["errors"]], [
            "devsecops_governance_intake_failed",
            "source_metadata_unavailable",
        ])
        schema = json.loads((ROOT / "schemas" / "evidence-collection-attempt.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)


if __name__ == "__main__":
    unittest.main()
