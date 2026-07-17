from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import sys
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_intake_health.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("generate_intake_health", SCRIPT)
health = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(health)


def event(
    *,
    status: str = "success",
    completed_at: str = "2026-07-17T12:00:03Z",
    duration_ms: int = 3000,
    repository_id: str = "owner/repo",
) -> dict:
    return {
        "status": status,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "repository_id": repository_id,
        "intake_type": "devsecops_governance",
        "evidence_type": "governance_result",
        "collector": {"id": "central-governance-intake", "version": "0.1.0"},
    }


class GenerateIntakeHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (ROOT / "schemas" / "intake-health.schema.json").read_text(encoding="utf-8")
        )

    def test_projection_is_schema_valid_and_calculates_window_metrics(self):
        events = [
            event(duration_ms=1000),
            event(status="partial", duration_ms=2000),
            event(status="failed", duration_ms=4000),
            event(completed_at="2026-06-01T12:00:00Z", duration_ms=9000),
        ]
        payload = health.build_payload(
            events=events,
            attempts=[],
            snapshots=[],
            intake_conflict_count=2,
            indexes={},
            as_of=datetime(2026, 7, 17, 13, tzinfo=timezone.utc),
            window_days=30,
        )

        Draft202012Validator(self.schema).validate(payload)
        metrics = payload["summary"]["events"]
        self.assertEqual(metrics["total"], 3)
        self.assertEqual(metrics["success_rate_pct"], 33.33)
        self.assertEqual(metrics["failure_rate_pct"], 66.67)
        self.assertEqual(metrics["duration_ms"], {
            "minimum": 1000,
            "p50": 2000,
            "p95": 4000,
            "maximum": 4000,
        })
        self.assertEqual(payload["summary"]["intake_conflicts"], 2)

    def test_projection_reports_no_data_without_in_window_events(self):
        payload = health.build_payload(
            events=[],
            attempts=[],
            snapshots=[],
            intake_conflict_count=0,
            indexes={},
            as_of=datetime(2026, 7, 17, 13, tzinfo=timezone.utc),
        )

        Draft202012Validator(self.schema).validate(payload)
        self.assertEqual(payload["observation_status"], "no_data")
        self.assertIsNone(payload["summary"]["events"]["duration_ms"]["p95"])

    def test_projection_counts_collection_lifecycle_and_latest_result_age(self):
        retryable_attempt = {
            "repository_id": "owner/repo",
            "source": {"run_id": "42", "artifact_name": "evidence"},
            "errors": [{"retryable": True}],
        }
        permanent_attempt = {
            "repository_id": "owner/repo",
            "source": {"run_id": "43", "artifact_name": "evidence"},
            "errors": [{"retryable": False}],
        }
        indexes = {
            "devsecops": {
                "repositories": [{
                    "repository_id": "owner/repo",
                    "latest_result": {
                        "pipeline_run_id": "42",
                        "generated_at": "2026-07-17T12:00:00Z",
                        "source_file": "status/results/owner__repo/result.json",
                    },
                }],
            },
        }
        payload = health.build_payload(
            events=[event()],
            attempts=[retryable_attempt, permanent_attempt],
            snapshots=[],
            intake_conflict_count=0,
            indexes=indexes,
            as_of=datetime(2026, 7, 17, 13, tzinfo=timezone.utc),
        )

        Draft202012Validator(self.schema).validate(payload)
        self.assertEqual(payload["summary"]["collection_attempts"], {
            "total": 2,
            "open": 1,
            "resolved": 0,
            "permanent": 1,
        })
        self.assertEqual(payload["latest_results"][0]["age_ms"], 3_600_000)

    def test_window_days_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            health.build_payload(
                events=[],
                attempts=[],
                snapshots=[],
                intake_conflict_count=0,
                indexes={},
                as_of=datetime(2026, 7, 17, 13, tzinfo=timezone.utc),
                window_days=0,
            )


if __name__ == "__main__":
    unittest.main()
