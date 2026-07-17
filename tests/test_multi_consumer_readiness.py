from pathlib import Path
import importlib.util
import json
import sys
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_multi_consumer_readiness.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("generate_multi_consumer_readiness", SCRIPT)
readiness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(readiness)


def fixtures():
    repositories = ["owner/one", "owner/two"]
    registry = {
        "integrations": [
            {"repository": repository, "governance_mode": "report-only"}
            for repository in repositories
        ],
        "summary": {"integrated_repositories": 2},
    }
    devsecops = {
        "repositories": [
            {
                "repository_id": repository,
                "results_path": f"status/results/{repository.replace('/', '__')}/",
                "latest_result": {
                    "source_file": f"status/results/{repository.replace('/', '__')}/result.json"
                },
            }
            for repository in repositories
        ]
    }
    portfolio = {
        "generated_at": "2026-07-17T12:00:00Z",
        "repositories": [{"repository_id": repository} for repository in repositories],
    }
    event = {
        "event_id": "a" * 64,
        "repository_id": "owner/one",
        "completed_at": "2026-07-17T12:00:03Z",
        "_source_file": "status/intake-events/owner__one/event.json",
    }
    concurrency = (
        "group: test-${{ github.event.client_payload.repository_id || inputs.repository_id }}-"
        "${{ github.event.client_payload.run_id || inputs.run_id }}\n"
        "cancel-in-progress: false"
    )
    return {
        "registry": registry,
        "indexes": {
            "devsecops": devsecops,
            "architecture": {"repositories": []},
            "typed_evidence": {"repositories": []},
        },
        "portfolio": portfolio,
        "intake_health": {
            "generated_at": "2026-07-17T12:00:03Z",
            "dimensions": [{"dimension": "repository_id", "value": "owner/one"}],
        },
        "events": [event],
        "workflows": {"workflow-a.yml": concurrency, "workflow-b.yml": concurrency},
    }


class MultiConsumerReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (ROOT / "schemas" / "multi-consumer-readiness.schema.json").read_text(encoding="utf-8")
        )

    def test_ready_report_is_schema_valid(self):
        report = readiness.build_report(**fixtures())

        Draft202012Validator(self.schema).validate(report)
        self.assertTrue(report["ready"])
        self.assertEqual(report["summary"]["registered_consumers"], 2)
        self.assertEqual(report["summary"]["failed_checks"], 0)
        self.assertEqual(report["repositories"][0]["telemetry_events"], 1)

    def test_missing_registered_devsecops_result_fails_readiness(self):
        values = fixtures()
        values["indexes"]["devsecops"]["repositories"].pop()

        report = readiness.build_report(**values)

        self.assertFalse(report["ready"])
        check = next(item for item in report["checks"] if item["id"] == "devsecops_registry_coverage")
        self.assertEqual(check["result"], "fail")

    def test_cross_consumer_result_path_fails_isolation(self):
        values = fixtures()
        values["indexes"]["devsecops"]["repositories"][0]["results_path"] = (
            "status/results/owner__two/"
        )

        report = readiness.build_report(**values)

        check = next(item for item in report["checks"] if item["id"] == "result_storage_isolated")
        self.assertEqual(check["result"], "fail")

    def test_unscoped_workflow_fails_concurrency_check(self):
        values = fixtures()
        values["workflows"]["workflow-a.yml"] = "group: global\ncancel-in-progress: true"

        report = readiness.build_report(**values)

        check = next(item for item in report["checks"] if item["id"] == "intake_concurrency_isolated")
        self.assertEqual(check["result"], "fail")


if __name__ == "__main__":
    unittest.main()
