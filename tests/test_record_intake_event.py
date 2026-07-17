from pathlib import Path
import importlib.util
import json
import sys
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "record_intake_event.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("record_intake_event", SCRIPT)
events = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(events)


def build(status="success", error_code=None, message=None):
    return events.build_event(
        repository_id="owner/repo",
        downstream_run_id="42",
        evidence_type="governance_result",
        collector_id="central-governance-intake",
        collector_version="0.1.0",
        artifact_name="governance-control-evaluation",
        intake_type="devsecops_governance",
        status=status,
        started_at="2026-07-17T12:00:00Z",
        completed_at="2026-07-17T12:00:03Z",
        intake_repository_id="governance/framework",
        intake_workflow_name="Intake Downstream Governance Result",
        intake_run_id="84",
        intake_run_attempt=1,
        trigger_event="repository_dispatch",
        error_code=error_code,
        message=message,
    )


class RecordIntakeEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (ROOT / "schemas" / "intake-operation-event.schema.json").read_text(encoding="utf-8")
        )

    def test_success_event_is_schema_valid_and_measures_duration(self):
        payload = build()
        jsonschema.Draft202012Validator(self.schema).validate(payload)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["duration_ms"], 3000)
        self.assertEqual(payload["errors"], [])
        self.assertEqual(len(payload["event_id"]), 64)

    def test_failed_event_is_schema_valid(self):
        payload = build(
            status="failed",
            error_code="governance_intake_failed",
            message="Intake failed.",
        )
        jsonschema.Draft202012Validator(self.schema).validate(payload)
        self.assertEqual(payload["errors"][0]["code"], "governance_intake_failed")

    def test_non_success_event_requires_error(self):
        with self.assertRaisesRegex(ValueError, "require an error"):
            build(status="failed")

    def test_completed_timestamp_cannot_precede_start(self):
        with self.assertRaisesRegex(ValueError, "must not be earlier"):
            events.build_event(
                repository_id="owner/repo",
                downstream_run_id="42",
                evidence_type="governance_result",
                collector_id="central-governance-intake",
                collector_version="0.1.0",
                artifact_name="governance-control-evaluation",
                intake_type="devsecops_governance",
                status="success",
                started_at="2026-07-17T12:00:03Z",
                completed_at="2026-07-17T12:00:00Z",
                intake_repository_id="governance/framework",
                intake_workflow_name="Intake Downstream Governance Result",
                intake_run_id="84",
                intake_run_attempt=1,
                trigger_event="repository_dispatch",
            )

    def test_example_is_schema_valid(self):
        example = json.loads(
            (ROOT / "docs" / "examples" / "intake-operation-event.example.json").read_text(encoding="utf-8")
        )
        jsonschema.Draft202012Validator(self.schema).validate(example)


if __name__ == "__main__":
    unittest.main()
