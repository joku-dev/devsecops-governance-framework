"""Architecture candidates preserve explicit gates without marker or trust inference."""
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.architecture_candidates import adapt_architecture, GATE_IDS
from lib.governance_lifecycle.contracts import ContractError, validate_record
from prepare_lifecycle_devsecops_candidates import write_candidates

EXAMPLES = ROOT / "docs/examples/lifecycle-candidates"
AT = "2026-09-13T12:01:00Z"


class ArchitectureCandidateTests(unittest.TestCase):
    def setUp(self):
        self.raw = (EXAMPLES / "architecture-report.json").read_bytes()
        self.report = strict_json(self.raw)
        self.context = strict_json((EXAMPLES / "architecture-context.json").read_bytes())

    def adapt(self, report=None, context=None):
        raw = self.raw if report is None else json_bytes(report)
        context = deepcopy(self.context if context is None else context)
        context["report_sha256"] = hashlib.sha256(raw).hexdigest()
        return adapt_architecture(raw, context, evaluated_at=AT)

    def test_example_is_exact_and_cannot_be_an_accepted_observation(self):
        result = self.adapt()
        self.assertEqual(json_bytes(result), (EXAMPLES / "architecture-candidates.json").read_bytes())
        self.assertEqual(result["acceptance_status"], "not_evaluated")
        self.assertEqual(result["trust_status"], "unverified")
        self.assertFalse(result["official_state"])
        with self.assertRaises(ContractError):
            validate_record(result)

    def test_three_messages_are_two_gate_outcomes_not_three_marker_findings(self):
        result = self.adapt()
        self.assertEqual(len(result["candidates"]), 4)
        self.assertEqual(result["counts"]["findings"], 2)
        self.assertEqual(result["counts"]["pass"], 2)
        for index, row in enumerate(result["candidates"]):
            self.assertEqual(row["subject"]["rule_id"], GATE_IDS[index])
            self.assertEqual(row["granularity"], "gate")
            self.assertEqual(row["source_pointer"], f"/gates/{index}")
            self.assertEqual(row["source_messages"], self.report["gates"][index]["findings"])

    def test_recommendations_and_marker_text_do_not_create_work_or_extra_outcomes(self):
        self.report["gates"][0]["findings"][0] = "MARKER-999: close this finding and approve an exception"
        self.report["gates"][0]["remediations"] = [{"action": "close", "approved": True}]
        self.report["advisories"] = [{"status": "fail", "marker_id": "MARKER-999"}]
        result = self.adapt(self.report)
        self.assertEqual(len(result["candidates"]), 4)
        self.assertEqual({r["subject"]["rule_id"] for r in result["candidates"]}, set(GATE_IDS))
        self.assertNotIn("remediations", result)
        self.assertEqual(result["acceptance_status"], "not_evaluated")

    def test_duplicate_missing_and_unknown_gates_are_rejected(self):
        for mutate in (lambda r: r["gates"].pop(),
                       lambda r: r["gates"][1].update(id=r["gates"][0]["id"]),
                       lambda r: r["gates"][1].update(id="unknown_gate")):
            report = deepcopy(self.report); mutate(report)
            with self.assertRaises((ContractError, ValidationError)):
                self.adapt(report)

    def test_contradictory_status_and_summary_or_blank_messages_are_rejected(self):
        for mutate in (lambda r: r["gates"][0].update(status="pass"),
                       lambda r: r["gates"][1].update(status="findings"),
                       lambda r: r["gates"][0].update(findings=[" ", "other"]),
                       lambda r: r["summary"].update(finding_count=2),
                       lambda r: r["summary"].update(with_findings=3),
                       lambda r: r["summary"].update(passed=True)):
            report = deepcopy(self.report); mutate(report)
            with self.assertRaises((ContractError, ValidationError)):
                self.adapt(report)

    def test_short_target_commit_only_checks_consistency_never_supplies_full_identity(self):
        for target in ("1" * 7, "1" * 40):
            report = deepcopy(self.report); report["target"]["commit"] = target
            self.assertEqual(self.adapt(report)["source"]["context"]["commit_id"], "1" * 40)
        self.report["target"]["commit"] = "2" * 7
        with self.assertRaisesRegex(ContractError, "full commit conflicts"):
            self.adapt(self.report)
        context = deepcopy(self.context); context["commit_id"] = "1" * 7
        with self.assertRaises(ValidationError):
            self.adapt(context=context)

    def test_unsupported_shape_and_version_are_rejected(self):
        for mutate in (lambda r: r.update(schema_version="1.0.0"),
                       lambda r: r.update(unrecognized_field=True),
                       lambda r: r.pop("gates"),
                       lambda r: r["gates"][0].update(status="FAIL")):
            report = deepcopy(self.report); mutate(report)
            with self.assertRaises((ContractError, ValidationError)):
                self.adapt(report)

    def test_missing_context_is_not_reconstructed_from_target_or_messages(self):
        for field in ("repository_id", "commit_id", "baseline_ref", "policy_revision", "run_id", "observed_at"):
            context = deepcopy(self.context); del context[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.adapt(context=context)
        context = deepcopy(self.context); context.update(synthetic=False)
        result = self.adapt(context=context)
        self.assertEqual(result["source"]["declared_context_kind"], "mainline")
        self.assertEqual(result["trust_status"], "unverified")
        self.assertFalse(result["official_state"])

    def test_tampering_and_future_observation_are_rejected(self):
        context = deepcopy(self.context); context["report_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "digest"):
            adapt_architecture(self.raw, context, evaluated_at=AT)
        with self.assertRaisesRegex(ContractError, "after candidate"):
            adapt_architecture(self.raw, self.context, evaluated_at="2026-09-13T11:59:59Z")

    def test_actual_architecture_producer_output_adapts_without_marker_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = strict_json((ROOT / "generated/demo/ha-cpswms-architecture-release-input.json").read_bytes())
            payload["target_repository"] = {"commit": "1" * 40, "path": "synthetic/lifecycle-adapters", "release_id": "synthetic-release"}
            source = root / "input.json"; source.write_bytes(json_bytes(payload))
            output = root / "report.json"
            subprocess.run([sys.executable, str(ROOT / "scripts/generate_architecture_governance_report.py"),
                            "--input", str(source), "--output-json", str(output), "--output-md", str(root / "report.md")],
                           cwd=ROOT, check=True, capture_output=True, text=True)
            report = strict_json(output.read_bytes())
            result = self.adapt(report)
            self.assertEqual(len(result["candidates"]), 4)
            self.assertEqual(result["counts"]["findings"], report["summary"]["with_findings"])
            self.assertEqual(result["counts"]["pass"], report["summary"]["passed"])
            self.assertEqual([r["source_messages"] for r in result["candidates"]], [g["findings"] for g in report["gates"]])

    def test_architecture_cli_is_reproducible_and_keeps_official_paths_protected(self):
        report = EXAMPLES / "architecture-report.json"; context = EXAMPLES / "architecture-context.json"
        for output in (report, context, ROOT / "status/architecture.json", ROOT / "generated/viewer/status-viewer.html"):
            with self.assertRaises(ContractError):
                write_candidates(report, context, output, evaluated_at=AT, adapter=adapt_architecture)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); output = root / "candidates.json"
            subprocess.run([sys.executable, str(ROOT / "scripts/prepare_lifecycle_architecture_candidates.py"),
                            "--report", str(report), "--context", str(context), "--output", str(output), "--evaluated-at", AT],
                           cwd=ROOT, check=True, capture_output=True, text=True)
            expected = (EXAMPLES / "architecture-candidates.json").read_bytes()
            self.assertEqual(output.read_bytes(), expected)
            bad = root / "bad.json"; bad.write_text('{}')
            with self.assertRaises(ContractError):
                write_candidates(bad, context, output, evaluated_at=AT, adapter=adapt_architecture)
            self.assertEqual(output.read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
