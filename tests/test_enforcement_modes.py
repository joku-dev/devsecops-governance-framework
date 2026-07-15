from pathlib import Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_EVIDENCE_SCRIPT = ROOT / "scripts" / "generate_pipeline_evidence.py"
DEVSECOPS_REUSABLE_WORKFLOW = ROOT / ".github" / "workflows" / "devsecops-baseline-reusable.yml"
DEVSECOPS_RELEASED_WORKFLOW = ROOT / ".github" / "workflows" / "devsecops-baseline-l1-v1.1.3.yml"
ARCHITECTURE_RELEASED_WORKFLOW = ROOT / ".github" / "workflows" / "architecture-baseline-l1-v0.1.0.yml"


class EnforcementModeTests(unittest.TestCase):
    def generate_pipeline_evidence(self, governance_mode: str | None = None) -> dict:
        with tempfile.TemporaryDirectory() as tempdir:
            workspace = Path(tempdir)
            artifact = workspace / "application.tar.gz"
            sbom = workspace / "sbom.json"
            scan = workspace / "vulnerability-scan.json"
            evidence = workspace / "pipeline-evidence.json"
            gate = workspace / "baseline-gate-result.json"

            artifact.write_bytes(b"test artifact")
            sbom.write_text('{"bomFormat": "CycloneDX"}\n', encoding="utf-8")
            scan.write_text('{"max_severity": "none", "findings": []}\n', encoding="utf-8")

            command = [
                "python3",
                str(PIPELINE_EVIDENCE_SCRIPT),
                "--platform",
                "github-actions",
                "--artifact-path",
                str(artifact),
                "--sbom-path",
                str(sbom),
                "--vulnerability-scan-path",
                str(scan),
                "--output",
                str(evidence),
                "--gate-output",
                str(gate),
            ]
            if governance_mode is not None:
                command.extend(["--governance-mode", governance_mode])

            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            return json.loads(gate.read_text(encoding="utf-8"))

    def test_pipeline_evidence_defaults_to_report_only(self):
        gate = self.generate_pipeline_evidence()

        self.assertEqual(gate["governance_mode"], "report-only")
        self.assertFalse(gate["blocks_merge"])

    def test_pipeline_evidence_classifies_nonblocking_and_blocking_modes(self):
        expected_blocks_merge = {
            "report-only": False,
            "warn-on-error": False,
            "block-on-error": True,
            "waiver-required": True,
        }

        for governance_mode, blocks_merge in expected_blocks_merge.items():
            with self.subTest(governance_mode=governance_mode):
                gate = self.generate_pipeline_evidence(governance_mode)
                self.assertEqual(gate["governance_mode"], governance_mode)
                self.assertEqual(gate["blocks_merge"], blocks_merge)

    def test_devsecops_workflow_preserves_released_contract_and_exit_semantics(self):
        released = DEVSECOPS_RELEASED_WORKFLOW.read_text(encoding="utf-8")
        reusable = DEVSECOPS_REUSABLE_WORKFLOW.read_text(encoding="utf-8")

        input_contract = """      governance_mode:
        description: Governance enforcement mode. Use report-only for onboarding diagnostics and block-on-error for required gates.
        required: false
        default: block-on-error
        type: string"""
        self.assertIn(input_contract, released)
        self.assertIn(input_contract, reusable)
        self.assertIn("governance_mode: ${{ inputs.governance_mode }}", released)
        self.assertIn(
            '"blocks_merge": governance_mode in {"block-on-error", "waiver-required"}',
            reusable,
        )
        self.assertIn('if governance_mode in {"report-only", "warn-on-error"}:', reusable)
        self.assertIn("sys.exit(0)\n              sys.exit(1)", reusable)

    def test_architecture_workflow_remains_report_only_unless_blocking_is_enabled(self):
        workflow = ARCHITECTURE_RELEASED_WORKFLOW.read_text(encoding="utf-8")

        input_contract = """      fail_on_findings:
        description: Fail the workflow when architecture governance findings exist.
        required: false
        default: false
        type: boolean"""
        self.assertIn(input_contract, workflow)
        self.assertIn("if: ${{ inputs.fail_on_findings }}", workflow)
        self.assertIn("raise SystemExit(1)", workflow)

    def test_demo_and_onboarding_consumers_select_report_only_explicitly(self):
        devsecops_consumers = (
            "examples/github-actions/workflows/application-devsecops-baseline-template.yml",
            "examples/github-actions/workflows/application-devsecops-baseline-with-governance-input-template.yml",
        )
        for relative_path in devsecops_consumers:
            with self.subTest(relative_path=relative_path):
                content = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn("governance_mode: report-only", content)

        architecture_consumer = (
            ROOT / "adoption-package" / "workflows" / "architecture-governance.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("fail_on_findings: false", architecture_consumer)


if __name__ == "__main__":
    unittest.main()
