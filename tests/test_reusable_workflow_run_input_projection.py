import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/devsecops-baseline-reusable.yml"


def collect_pipeline_evidence_script() -> str:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["devsecops-baseline"]["steps"]
    step = next(item for item in steps if item.get("name") == "Collect pipeline evidence")
    script = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    replacements = {
        "${{ inputs.artifact_path }}": "dist/application.bin",
        "${{ inputs.sbom_path }}": "security/sbom.json",
        "${{ inputs.vulnerability_scan_path }}": "security/scan.json",
        "${{ inputs.signature_path }}": "",
        "${{ inputs.max_allowed_severity }}": "high",
        "${{ inputs.release_candidate }}": "false",
        "${{ inputs.governance_mode }}": "report-only",
    }
    for source, value in replacements.items():
        script = script.replace(source, value)
    if "${{" in script:
        raise AssertionError("Unresolved GitHub expression in pipeline evidence script fixture")
    return script


class ReusableWorkflowRunInputProjectionTests(unittest.TestCase):
    def run_collector(self, run_input_value, *, create_run_input=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "generated/evidence").mkdir(parents=True)
            (root / "dist").mkdir()
            (root / "security").mkdir()
            (root / "generated/evidence/governance-context.json").write_text("{}\n", encoding="utf-8")
            (root / "dist/application.bin").write_bytes(b"pilot artifact")
            (root / "security/sbom.json").write_text("{}\n", encoding="utf-8")
            (root / "security/scan.json").write_text('{"max_severity":"none"}\n', encoding="utf-8")

            run_input_path = root / "governance/governance-run-input.json"
            if create_run_input:
                run_input_path.parent.mkdir(parents=True)
                run_input_path.write_text(
                    json.dumps({"pipeline": {"external_direct_downloads_detected": run_input_value}}) + "\n",
                    encoding="utf-8",
                )

            environment = os.environ.copy()
            environment.update(
                {
                    "GOVERNANCE_RUN_INPUT_PATH": str(run_input_path),
                    "GITHUB_EVENT_NAME": "pull_request",
                    "GITHUB_REF_NAME": "pilot-branch",
                    "GITHUB_REPOSITORY": "joku-dev/governance-eval-fixture",
                    "GITHUB_SHA": "a" * 40,
                    "GITHUB_RUN_ID": "12345",
                }
            )
            completed = subprocess.run(
                [sys.executable, "-c", collect_pipeline_evidence_script()],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            evidence_path = root / "generated/evidence/pipeline-evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else None
            return completed, evidence

    def test_pipeline_evidence_copies_true_producer_declaration(self):
        completed, evidence = self.run_collector(True)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIs(evidence["pipeline"]["external_direct_downloads_detected"], True)

    def test_pipeline_evidence_copies_false_producer_declaration(self):
        completed, evidence = self.run_collector(False)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIs(evidence["pipeline"]["external_direct_downloads_detected"], False)

    def test_configured_but_missing_run_input_fails_closed(self):
        completed, evidence = self.run_collector(True, create_run_input=False)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Configured governance run input not found", completed.stderr)
        self.assertIsNone(evidence)

    def test_non_boolean_producer_declaration_fails_closed(self):
        completed, evidence = self.run_collector("unknown")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("must declare external_direct_downloads_detected as a boolean", completed.stderr)
        self.assertIsNone(evidence)


if __name__ == "__main__":
    unittest.main()
