from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_agent_usage_snapshot.py"

spec = importlib.util.spec_from_file_location("generate_agent_usage_snapshot", SCRIPT)
snapshot_cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["generate_agent_usage_snapshot"] = snapshot_cli
spec.loader.exec_module(snapshot_cli)


def usage_event(timestamp: str, changed_paths: list[str], selected_agents: list[str]) -> dict:
    return {
        "timestamp": timestamp,
        "run_type": "dispatch",
        "provider": "none",
        "platform": "local",
        "source": "unit-test",
        "changed_paths": changed_paths,
        "selected_agents": selected_agents,
        "skills": selected_agents,
        "release_impact": "candidate",
        "required_validations": ["git diff --check"],
        "warnings": [],
    }


class GenerateAgentUsageSnapshotTests(unittest.TestCase):
    def test_build_snapshot_counts_usage_and_change_areas(self):
        events = [
            usage_event(
                "2026-07-06T10:00:00Z",
                ["scripts/dispatch_governance_agents.py", "tests/test_dispatch_governance_agents.py"],
                ["repo-steward"],
            ),
            usage_event(
                "2026-07-06T10:01:00Z",
                ["docs/operations/agents/agent-usage-tracking.md"],
                ["repo-steward", "release-manager"],
            ),
        ]

        snapshot = snapshot_cli.build_snapshot(
            events,
            usage_log=ROOT / "generated" / "agent-usage" / "agent-usage.jsonl",
            generated_at="2026-07-06T10:02:00Z",
            latest_count=1,
        )

        self.assertEqual(snapshot["event_count"], 2)
        self.assertEqual(snapshot["agent_counts"]["repo-steward"], 2)
        self.assertEqual(snapshot["agent_counts"]["release-manager"], 1)
        self.assertEqual(snapshot["change_area_counts"]["scripts"], 1)
        self.assertEqual(snapshot["change_area_counts"]["docs/operations"], 1)
        self.assertEqual(len(snapshot["latest_events"]), 1)
        self.assertEqual(snapshot["latest_events"][0]["timestamp"], "2026-07-06T10:01:00Z")

    def test_main_writes_json_and_markdown_snapshot(self):
        event = usage_event(
            "2026-07-06T10:00:00Z",
            ["pipeline-baseline/templates/bitbucket/README.md"],
            ["devsecops-baseline", "release-manager", "repo-steward"],
        )

        with tempfile.TemporaryDirectory() as tempdir:
            usage_log = Path(tempdir) / "agent-usage.jsonl"
            output_json = Path(tempdir) / "summary.json"
            output_md = Path(tempdir) / "snapshot.md"
            usage_log.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")

            result = snapshot_cli.main(
                [
                    "--usage-log",
                    str(usage_log),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                    "--generated-at",
                    "2026-07-06T10:01:00Z",
                ]
            )

            summary = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        self.assertEqual(summary["event_count"], 1)
        self.assertEqual(summary["provider_counts"]["none"], 1)
        self.assertIn("# Agent Usage Snapshot Latest", markdown)
        self.assertIn("pipeline-baseline/templates", markdown)
        self.assertIn("metadata-only", markdown)


if __name__ == "__main__":
    unittest.main()
