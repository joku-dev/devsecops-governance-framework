from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_portfolio_onboarding_status.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("generate_portfolio_onboarding_status", SCRIPT)
portfolio = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(portfolio)


class PortfolioOnboardingStatusTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "integrations": [{
                "repository": "owner/repo",
                "owner": "Repository Owner",
                "action_owner": "Governance Platform Lead",
                "business_or_product_area": "Demo",
                "governance_workflow_ref": "l1-baseline-v1.1.3",
                "governance_mode": "report-only",
            }]
        }
        self.devsecops = {
            "repositories": [{
                "repository_id": "owner/repo",
                "latest_result": {
                    "status": "pass",
                    "pipeline_run_id": "42",
                    "generated_at": "2026-07-01T00:00:00Z",
                },
            }]
        }
        self.architecture = {"repositories": []}

    def test_unchanged_semantic_status_preserves_generated_timestamp(self):
        first = portfolio.build_payload(
            self.registry,
            self.devsecops,
            self.architecture,
            datetime(2026, 7, 2, tzinfo=timezone.utc),
        )
        second = portfolio.build_payload(
            self.registry,
            self.devsecops,
            self.architecture,
            datetime(2026, 7, 3, tzinfo=timezone.utc),
            first,
        )
        self.assertEqual(second, first)
        self.assertEqual(second["repositories"][0]["latest_devsecops"]["freshness"]["status"], "current")

    def test_crossing_freshness_threshold_changes_status_once(self):
        current = portfolio.build_payload(
            self.registry,
            self.devsecops,
            self.architecture,
            datetime(2026, 7, 2, tzinfo=timezone.utc),
        )
        stale = portfolio.build_payload(
            self.registry,
            self.devsecops,
            self.architecture,
            datetime(2026, 8, 2, tzinfo=timezone.utc),
            current,
        )
        self.assertNotEqual(stale["generated_at"], current["generated_at"])
        self.assertTrue(stale["repositories"][0]["stale_or_missing"])
        self.assertEqual(stale["repositories"][0]["latest_devsecops"]["freshness"]["status"], "stale")


if __name__ == "__main__":
    unittest.main()
