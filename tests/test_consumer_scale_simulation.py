import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "simulate_consumer_scale", ROOT / "scripts" / "simulate_consumer_scale.py"
)
scale = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(scale)


class ConsumerScaleSimulationTests(unittest.TestCase):
    def test_simulation_is_isolated_and_counts_consumers(self):
        protected = [
            ROOT / "status" / "repository-results-index.json",
            ROOT / "status" / "architecture-results-index.json",
            ROOT / "status" / "typed-evidence-results-index.json",
            ROOT / "generated" / "viewer" / "status-viewer.html",
        ]
        before = {path: path.read_bytes() for path in protected}

        result = scale.run_simulation(ROOT, [2], detailed_materialize_limit=0)

        self.assertFalse(result["official_state_modified"])
        scenario = result["scenarios"]["2"]
        self.assertEqual(scenario["generation"]["devsecops"]["repositories"], 2)
        self.assertEqual(scenario["generation"]["architecture"]["repositories"], 2)
        self.assertEqual(scenario["generation"]["typed_evidence"]["repositories"], 2)
        self.assertEqual(scenario["generation"]["typed_evidence"]["results"], 4)
        self.assertEqual(scenario["generation"]["portfolio"]["repositories"], 2)
        self.assertEqual(scenario["viewer_detailed"]["mode"], "lower_bound_estimate")
        self.assertEqual(before, {path: path.read_bytes() for path in protected})

    def test_synthetic_repository_identity_is_stable_and_unique(self):
        self.assertEqual(scale.synthetic_repository_id(0), "synthetic/team-00-repo-0000")
        self.assertEqual(scale.synthetic_repository_id(100), "synthetic/team-01-repo-0100")
        self.assertNotEqual(scale.synthetic_repository_id(1498), scale.synthetic_repository_id(1499))

    def test_optional_output_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tempdir:
            target = Path(tempdir) / "result.json"
            result = scale.run_simulation(ROOT, [1], detailed_materialize_limit=0)
            target.write_text(json.dumps(result), encoding="utf-8")
            self.assertEqual(json.loads(target.read_text())["simulation_type"], "isolated_consumer_scale")

    def test_cli_rejects_official_status_output(self):
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "simulate_consumer_scale.py"),
                "--repositories",
                "1",
                "--output",
                str(ROOT / "status" / "scale-simulation.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be written below status/ or generated/", result.stderr)
        self.assertFalse((ROOT / "status" / "scale-simulation.json").exists())


if __name__ == "__main__":
    unittest.main()
