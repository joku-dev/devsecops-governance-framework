from pathlib import Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureGovernanceReportTests(unittest.TestCase):
    def test_findings_fixture_produces_expected_architecture_findings(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output_json = Path(tempdir) / "architecture-governance-report.json"
            output_md = Path(tempdir) / "architecture-governance-report.md"
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "generate_architecture_governance_report.py"),
                    "--input",
                    str(ROOT / "policies" / "example-input.architecture-release-candidate-findings.json"),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            report = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertEqual(report["summary"]["gate_count"], 4)
        self.assertEqual(report["summary"]["passed"], 1)
        self.assertEqual(report["summary"]["with_findings"], 3)
        self.assertEqual(report["summary"]["finding_count"], 12)
        self.assertIn("Operation readiness requires runtime evidence", markdown)
        self.assertIn("Release compatibility declaration must be approved", markdown)
        self.assertIn("Release-critical architecture marker E6 requires score 4", markdown)
        self.assertIn("Verify enterprise security guardrail evidence", markdown)

    def test_report_includes_detailed_evidence_without_changing_gate_summary(self):
        with tempfile.TemporaryDirectory() as tempdir:
            input_path = Path(tempdir) / "architecture-release-input.json"
            output_json = Path(tempdir) / "architecture-governance-report.json"
            output_md = Path(tempdir) / "architecture-governance-report.md"
            payload = json.loads(
                (ROOT / "policies" / "example-input.architecture-release-candidate.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["architecture"]["detailed_evidence"] = {
                "report_only": True,
                "declared_types": ["threat_model"],
                "by_type": {
                    "threat_model": {
                        "coarse_type": "security_evidence",
                        "status": "approved",
                        "owner": "Security Architect",
                        "path": ".governance/architecture/threat-model.json",
                        "evidence_refs": ["docs/ARCHITECTURE.md"],
                    }
                },
                "by_coarse_type": {"security_evidence": ["threat_model"]},
            }
            input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "generate_architecture_governance_report.py"),
                    "--input",
                    str(input_path),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            report = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertEqual(report["summary"]["gate_count"], 4)
        self.assertEqual(report["detailed_evidence"]["declared_types"], ["threat_model"])
        self.assertTrue(any(item["evidence_type"] == "interface_contract" for item in report["advisories"]))
        self.assertFalse(any(item["evidence_type"] == "threat_model" for item in report["advisories"]))
        self.assertIn("## Detailed Evidence", markdown)
        self.assertIn("## Report-Only Advisories", markdown)
        self.assertIn("`threat_model`", markdown)
        self.assertIn("`interface_contract`", markdown)
        self.assertIn("report-only", markdown)

    def test_report_only_advisories_are_context_sensitive(self):
        with tempfile.TemporaryDirectory() as tempdir:
            input_path = Path(tempdir) / "architecture-release-input.json"
            output_json = Path(tempdir) / "architecture-governance-report.json"
            output_md = Path(tempdir) / "architecture-governance-report.md"
            payload = {
                "release_candidate": True,
                "architecture": {
                    "marker_assessments": [],
                    "release_compatibility_declaration": {
                        "exists": False,
                        "baseline_version": "",
                        "approved": False,
                    },
                    "solution_baseline": {"exists": False},
                    "compatibility_evidence": {"exists": False},
                    "security_evidence": {"exists": False},
                    "deployment_evidence": {"exists": False},
                    "runtime_evidence": {"exists": False},
                    "review_evidence": {"exists": False},
                    "exception_evidence": {"exists": False},
                    "feedback_evidence": {"exists": False},
                    "detailed_evidence": {
                        "report_only": True,
                        "declared_types": [],
                        "by_type": {},
                        "by_coarse_type": {},
                    },
                    "exceptions": [],
                },
            }
            input_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "generate_architecture_governance_report.py"),
                    "--input",
                    str(input_path),
                    "--output-json",
                    str(output_json),
                    "--output-md",
                    str(output_md),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            report = json.loads(output_json.read_text(encoding="utf-8"))
            markdown = output_md.read_text(encoding="utf-8")

        self.assertEqual(report["advisories"], [])
        self.assertIn("No report-only advisories.", markdown)
