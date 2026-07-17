from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class IntakeWorkflowConcurrencyTests(unittest.TestCase):
    def test_intake_concurrency_is_scoped_to_repository_and_run(self):
        workflows = {
            "intake-governance-result.yml": "downstream-governance-result-intake-",
            "intake-architecture-result.yml": "downstream-architecture-result-intake-",
            "intake-evidence-trust.yml": "typed-evidence-trust-intake-",
        }

        for filename, prefix in workflows.items():
            with self.subTest(workflow=filename):
                content = (WORKFLOWS / filename).read_text(encoding="utf-8")
                group_line = next(
                    line.strip() for line in content.splitlines()
                    if line.strip().startswith("group:")
                )
                self.assertIn(prefix, group_line)
                self.assertIn("github.event.client_payload.repository_id || inputs.repository_id", group_line)
                self.assertIn("github.event.client_payload.run_id || inputs.run_id", group_line)
                self.assertIn("cancel-in-progress: false", content)

    def test_recomputable_portfolio_refresh_keeps_static_group(self):
        content = (WORKFLOWS / "portfolio-status.yml").read_text(encoding="utf-8")
        self.assertIn("group: portfolio-status", content)

    def test_all_intake_workflows_record_failures_before_failing(self):
        for filename in (
            "intake-governance-result.yml",
            "intake-architecture-result.yml",
            "intake-evidence-trust.yml",
        ):
            with self.subTest(workflow=filename):
                content = (WORKFLOWS / filename).read_text(encoding="utf-8")
                self.assertIn("id: intake", content)
                self.assertIn("continue-on-error: true", content)
                self.assertIn("Record failed collection attempt", content)
                self.assertIn("status/collection-attempts", content)
                self.assertIn("Start intake telemetry", content)
                self.assertIn("Stop intake telemetry clock", content)
                self.assertIn("Record intake telemetry", content)
                self.assertIn("scripts/record_intake_event.py", content)
                self.assertIn("status/intake-events", content)
                self.assertIn("Fail workflow after intake or telemetry failure", content)
                self.assertIn("steps.regenerate.outcome == 'success'", content)
                self.assertIn("steps.validation.outcome == 'success'", content)


if __name__ == "__main__":
    unittest.main()
