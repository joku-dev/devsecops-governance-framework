from pathlib import Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepoValidationTests(unittest.TestCase):
    @staticmethod
    def run_command(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(args),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    @classmethod
    def setUpClass(cls):
        cls.run_command("python3", str(ROOT / "scripts" / "generate_traceability_csv.py"))
        cls.run_command("python3", str(ROOT / "scripts" / "generate_document_control_matrix.py"))
        cls.run_command("python3", str(ROOT / "scripts" / "generate_open_gap_report.py"))
        cls.run_command("python3", str(ROOT / "scripts" / "render_governance_documents.py"))
        cls.run_command(
            "python3",
            str(ROOT / "scripts" / "generate_control_evaluation_report.py"),
            "--input-file",
            str(ROOT / "demo" / "inputs" / "release-candidate-green.json"),
            "--output-file",
            str(ROOT / "generated" / "control-evaluation-report.json"),
            "--markdown-file",
            str(ROOT / "generated" / "control-evaluation-report.md"),
        )
        cls.run_command("python3", str(ROOT / "scripts" / "generate_status_viewer.py"))

    def test_validator_passes(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "validate_governance_repo.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("Validation passed", result.stdout)

    def test_opa_check_passes(self):
        result = self.run_command("opa", "check", str(ROOT / "policies" / "opa"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_branch_protection_policy_allows_example_input(self):
        result = self.run_command(
            "opa",
            "eval",
            "-f",
            "json",
            "-d",
            str(ROOT / "policies" / "opa"),
            "-i",
            str(ROOT / "policies" / "example-input.release-candidate.json"),
            "data.devsecops.branch_protection.deny",
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"][0]["expressions"][0]["value"], [])

    def test_traceability_csv_includes_authority_documents(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_traceability_csv.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        csv_path = ROOT / "generated" / "xlsx" / "traceability_matrix.csv"
        content = csv_path.read_text(encoding="utf-8")
        self.assertIn("authority_documents", content.splitlines()[0])
        self.assertIn("DEVSECOPS-POL-001", content)

    def test_document_control_matrix_is_generated(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_document_control_matrix.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        csv_path = ROOT / "generated" / "xlsx" / "document_control_matrix.csv"
        md_path = ROOT / "generated" / "reports" / "document-control-matrix.md"
        self.assertTrue(csv_path.exists())
        self.assertTrue(md_path.exists())
        self.assertIn("document_id", csv_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertIn("DEVSECOPS-DIR-001", md_path.read_text(encoding="utf-8"))

    def test_open_gap_report_is_generated(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_open_gap_report.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        csv_path = ROOT / "generated" / "xlsx" / "open_gap_report.csv"
        md_path = ROOT / "generated" / "reports" / "open-gap-report.md"
        self.assertTrue(csv_path.exists())
        self.assertTrue(md_path.exists())
        self.assertIn("gap_id", csv_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertIn("GAP-DOC-DEVSECOPS-POL-001", md_path.read_text(encoding="utf-8"))

    def test_governance_documents_are_rendered(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "render_governance_documents.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        policy_md = ROOT / "generated" / "documents" / "devsecops-pol-001.rendered.md"
        policy_html = ROOT / "generated" / "documents" / "devsecops-pol-001.html"
        directive_md = ROOT / "generated" / "documents" / "devsecops-dir-001.rendered.md"
        directive_html = ROOT / "generated" / "documents" / "devsecops-dir-001.html"
        self.assertTrue(policy_md.exists())
        self.assertTrue(policy_html.exists())
        self.assertTrue(directive_md.exists())
        self.assertTrue(directive_html.exists())
        self.assertIn("Document ID: `DEVSECOPS-POL-001`", policy_md.read_text(encoding="utf-8"))
        self.assertIn("<html", policy_html.read_text(encoding="utf-8"))

    def test_status_viewer_is_generated(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "generate_status_viewer.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        viewer = ROOT / "generated" / "viewer" / "status-viewer.html"
        self.assertTrue(viewer.exists())
        content = viewer.read_text(encoding="utf-8")
        self.assertIn("Governance Status Viewer", content)
        self.assertIn("Open Gap Report", content)
        self.assertIn("Operational Integration Status", content)
        self.assertIn("joku-dev/ha-CPsWMS", content)
        self.assertIn("Latest Control Evaluation Snapshot", content)
        self.assertIn("DSCB-L1-REQ-003", content)
        self.assertIn("block-on-error", content)
        self.assertIn("report-only", content)
        self.assertIn("blocks merge:", content)
        self.assertIn("Repository Governance Status", content)
        self.assertIn("Architecture Runtime Gates", content)
        self.assertIn("architecture-baseline-l1-v0.1.0", content)
        self.assertIn("Source Document Intake", content)
        self.assertIn("Requirement Delta Summary", content)
        self.assertIn("ARCH-GOV-SRC-002", content)
        self.assertIn("source-document-requirement-delta.md", content)

    def test_demo_run_succeeds(self):
        result = self.run_command("python3", str(ROOT / "scripts" / "run_demo.py"))
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        overview = ROOT / "generated" / "demo" / "demo-run.md"
        green = ROOT / "generated" / "demo" / "green-summary.json"
        red = ROOT / "generated" / "demo" / "red-summary.json"
        self.assertTrue(overview.exists())
        self.assertTrue(green.exists())
        self.assertTrue(red.exists())
        self.assertIn("Governance Demo Run", overview.read_text(encoding="utf-8"))

    def test_repo_governance_integration_scanner(self):
        with tempfile.TemporaryDirectory() as tempdir:
            repo = Path(tempdir)
            workflows = repo / ".github" / "workflows"
            workflows.mkdir(parents=True, exist_ok=True)
            workflow = workflows / "governance.yml"
            workflow.write_text(
                "\n".join(
                    [
                        "name: Governance",
                        "jobs:",
                        "  governance:",
                        "    steps:",
                        "      - run: git clone https://github.com/example/devsecops-governance-as-code.git governance",
                        "      - run: python3 governance/scripts/validate_governance_repo.py",
                        "      - run: python3 -m unittest discover -s governance/tests",
                        "      - run: opa check governance/policies/opa",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            result_path = repo / "governance-compliance-result.json"
            result = self.run_command(
                "python3",
                str(ROOT / "scripts" / "check_repo_governance_integration.py"),
                "--target-repo",
                str(repo),
                "--output-file",
                str(result_path),
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(len(payload["checks"]), 3)

    def test_repository_onboarding_readiness_report_is_generated(self):
        with tempfile.TemporaryDirectory() as tempdir:
            repo = Path(tempdir)
            (repo / "README.md").write_text("# Example App\n", encoding="utf-8")
            (repo / "pyproject.toml").write_text("[project]\nname = \"example-app\"\n", encoding="utf-8")
            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            (repo / "tests").mkdir()
            (repo / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
            workflows = repo / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "quality-gates.yml").write_text(
                "\n".join(
                    [
                        "name: quality-gates",
                        "jobs:",
                        "  validate:",
                        "    steps:",
                        "      - run: python -m pytest",
                        "      - run: python scripts/regenerate_governance_evidence.py --check",
                        "      - run: python -m ruff check .",
                        "      - run: python -m mypy src",
                        "      - run: python scripts/check_pr_execution_evidence.py --base-ref origin/main",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (repo / "docs" / "governance").mkdir(parents=True)
            (repo / "docs" / "governance" / "README.md").write_text("# Governance\n", encoding="utf-8")
            (repo / "docs" / "security").mkdir(parents=True)
            (repo / "docs" / "security" / "security.md").write_text("Secrets handling and SBOM plan.\n", encoding="utf-8")
            (repo / ".agent-executions").mkdir()
            (repo / ".agent-executions" / "AER-example.yaml").write_text("id: AER-example\n", encoding="utf-8")
            (repo / "examples" / "governance_runtime").mkdir(parents=True)
            (repo / "examples" / "governance_runtime" / "demo.json").write_text("{}\n", encoding="utf-8")
            output_json = repo / "readiness.json"
            output_md = repo / "readiness.md"

            result = self.run_command(
                "python3",
                str(ROOT / "scripts" / "check_repository_onboarding_readiness.py"),
                "--target-repo",
                str(repo),
                "--repository-id",
                "example/app",
                "--output-json",
                str(output_json),
                "--output-md",
                str(output_md),
            )

            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ready_with_gaps")
            self.assertEqual(payload["summary"]["checks"], 5)
            self.assertTrue(output_md.exists())

    def test_extended_governance_compliance_result_is_generated(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "governance-compliance-result.json"
            result = self.run_command(
                "python3",
                str(ROOT / "scripts" / "generate_governance_compliance_result.py"),
                "--target-repo",
                str(ROOT),
                "--input-file",
                str(ROOT / "demo" / "inputs" / "release-candidate-green.json"),
                "--skip-unit-tests",
                "--output-file",
                str(output),
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("execution", payload)
            self.assertIn("policy_evaluations", payload)
            self.assertIn("artifacts", payload)
            self.assertIn("control_evaluations", payload)
            self.assertIn("controls", payload["control_evaluations"])

    def test_control_evaluation_report_is_generated(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "control-evaluation-report.json"
            markdown = Path(tempdir) / "control-evaluation-report.md"
            result = self.run_command(
                "python3",
                str(ROOT / "scripts" / "generate_control_evaluation_report.py"),
                "--input-file",
                str(ROOT / "demo" / "inputs" / "release-candidate-green.json"),
                "--output-file",
                str(output),
                "--markdown-file",
                str(markdown),
            )
            self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["fail"], 0)
            self.assertGreater(payload["summary"]["tested_controls"], 0)
            self.assertIn("DSCB-L1-REQ-003", output.read_text(encoding="utf-8"))
            self.assertIn("Control Evaluation Report", markdown.read_text(encoding="utf-8"))

    def test_reusable_workflow_derives_governance_signals(self):
        workflow = (ROOT / ".github" / "workflows" / "devsecops-baseline-reusable.yml").read_text(encoding="utf-8")
        self.assertIn("Resolve repository governance context", workflow)
        self.assertIn("signature_path:", workflow)
        self.assertIn("security_thresholds_exceeded = severity_order.get(max_seen, 99)", workflow)
        self.assertNotIn('DIRECT_PUSH_ALLOWED: "false"', workflow)
        self.assertNotIn('REVIEW_REQUIRED: "true"', workflow)
        self.assertNotIn('ARTIFACT_SIGNATURE_EXISTS: "false"', workflow)

    def test_onboarding_examples_pin_governance_workflow(self):
        onboarding = (ROOT / "docs" / "onboarding" / "application-repo-onboarding.md").read_text(encoding="utf-8")
        template = (
            ROOT
            / "examples"
            / "github-actions"
            / "workflows"
            / "application-devsecops-baseline-template.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("devsecops-baseline-reusable.yml@main", onboarding)
        self.assertNotIn("devsecops-baseline-reusable.yml@main", template)
        self.assertIn("pull-requests: read", onboarding)
        self.assertIn("pull-requests: read", template)


if __name__ == "__main__":
    unittest.main()
