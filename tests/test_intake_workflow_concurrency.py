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


if __name__ == "__main__":
    unittest.main()
