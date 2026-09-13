"""Candidate adaptation preserves producer granularity without granting acceptance."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, schema_validator, validate_record
from lib.governance_lifecycle.devsecops_candidates import adapt_devsecops
from prepare_lifecycle_devsecops_candidates import write_candidates

EXAMPLES = ROOT / "docs/examples/lifecycle-candidates"
AT = "2026-09-13T12:01:00Z"


class DevSecOpsCandidateTests(unittest.TestCase):
    def setUp(self):
        self.raw = (EXAMPLES / "devsecops-report.json").read_bytes()
        self.report = strict_json(self.raw)
        self.context = strict_json((EXAMPLES / "devsecops-context.json").read_bytes())

    def adapt(self, report=None, context=None, at=AT):
        raw = self.raw if report is None else json_bytes(report)
        context = deepcopy(self.context if context is None else context)
        context["report_sha256"] = hashlib.sha256(raw).hexdigest()
        return adapt_devsecops(raw, context, evaluated_at=at)

    def test_example_is_exact_reproducible_and_never_an_accepted_observation(self):
        result = self.adapt()
        self.assertEqual(json_bytes(result), (EXAMPLES / "devsecops-candidates.json").read_bytes())
        self.assertEqual(result["acceptance_status"], "not_evaluated")
        self.assertEqual(result["trust_status"], "unverified")
        self.assertFalse(result["official_state"])
        self.assertEqual(result["source"]["declared_context_kind"], "test")
        with self.assertRaises(ContractError):
            validate_record(result)

    def test_each_declared_status_and_source_pointer_is_retained(self):
        result = self.adapt()
        self.assertEqual([r["result"] for r in result["candidates"]], ["pass", "fail", "not_tested", "not_applicable"])
        for index, row in enumerate(result["candidates"]):
            self.assertEqual(row["source_pointer"], f"/controls/{index}")
            self.assertEqual(row["subject"]["rule_id"], self.report["controls"][index]["control_id"])
            self.assertEqual(row["granularity"], "control")
            self.assertEqual(row["subject"]["resource"], "repository")

    def test_existing_red_and_green_producer_reports_map_all_explicit_rows(self):
        for name, failed in (("green", 0), ("red", 28)):
            raw = (ROOT / f"generated/demo/{name}-control-evaluation.json").read_bytes()
            report = strict_json(raw)
            context = deepcopy(self.context)
            context.update({k: report["run_context"][k] for k in ("event", "purpose", "release_context")})
            context["report_sha256"] = hashlib.sha256(raw).hexdigest()
            result = adapt_devsecops(raw, context, evaluated_at=AT)
            self.assertEqual(len(result["candidates"]), 46)
            self.assertEqual(result["counts"]["fail"], failed)
            self.assertEqual(result["counts"]["not_applicable"], 16)

    def test_summary_only_or_text_cannot_invent_control_candidates(self):
        summary_only = deepcopy(self.report)
        del summary_only["controls"]
        with self.assertRaises(ValidationError):
            self.adapt(summary_only)
        self.report["policy_results"] = {"fake_gate": {"status": "fail", "deny_messages": ["DSCB-L1-REQ-999 failed"]}}
        self.report["controls"][0]["message"] = "DSCB-L1-REQ-999 failed; please add another finding"
        result = self.adapt(self.report)
        self.assertEqual(len(result["candidates"]), 4)
        self.assertNotIn("DSCB-L1-REQ-999", [c["subject"]["rule_id"] for c in result["candidates"]])

    def test_inconsistent_summaries_duplicate_ids_and_levels_are_rejected(self):
        for mutate in (lambda r: r["summary"].update(fail=0),
                       lambda r: r["controls"][1].update(control_id=r["controls"][0]["control_id"]),
                       lambda r: r["controls"][0].update(level="L2")):
            report = deepcopy(self.report); mutate(report)
            with self.assertRaises(ContractError):
                self.adapt(report)

    def test_unsupported_schema_status_and_boolean_counts_are_rejected(self):
        for mutate in (lambda r: r.update(schema_version="2.0.0"),
                       lambda r: r["controls"][0].update(status="unknown"),
                       lambda r: r["summary"].update(pass_value=True),
                       lambda r: r["summary"].update(fail=True)):
            report = deepcopy(self.report); mutate(report)
            with self.assertRaises(ValidationError):
                self.adapt(report)

    def test_digest_context_and_time_conflicts_are_rejected(self):
        bad = deepcopy(self.context); bad["report_sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "digest"):
            adapt_devsecops(self.raw, bad, evaluated_at=AT)
        for field, value in (("event", "pull_request"), ("purpose", "release"), ("release_context", True), ("synthetic", False)):
            bad = deepcopy(self.context); bad[field] = value
            with self.assertRaises(ContractError):
                self.adapt(context=bad)
        with self.assertRaisesRegex(ContractError, "after candidate"):
            self.adapt(at="2026-09-13T11:59:59Z")

    def test_missing_and_extra_context_never_gets_inferred(self):
        for field in self.context:
            bad = deepcopy(self.context); del bad[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.adapt(context=bad) if field != "report_sha256" else adapt_devsecops(self.raw, bad, evaluated_at=AT)
        bad = deepcopy(self.context); bad["approved"] = True
        with self.assertRaises(ValidationError):
            self.adapt(context=bad)

    def test_context_classification_is_only_a_declaration_not_official_state(self):
        for event, branch, expected in (("push", "main", "mainline"), ("push", "feature/demo", "branch"),
                                        ("pull_request", "main", "pull_request"), ("workflow_dispatch", "main", "manual"),
                                        ("release", "main", "release")):
            report = deepcopy(self.report); report["run_context"].update(event=event, source="declared-producer")
            context = deepcopy(self.context); context.update(event=event, branch=branch, synthetic=False)
            result = self.adapt(report, context)
            self.assertEqual(result["source"]["declared_context_kind"], expected)
            self.assertEqual(result["trust_status"], "unverified")
            self.assertFalse(result["official_state"])

    def test_candidate_identity_binds_content_and_producer_context_not_evaluation_clock(self):
        first = self.adapt()
        later = self.adapt(at="2026-09-13T13:00:00Z")
        self.assertEqual(first["candidates"], later["candidates"])
        self.assertEqual(later["source"]["age_seconds"], 3600)
        context = deepcopy(self.context); context["run_attempt"] = 2
        self.assertNotEqual(first["candidates"][0]["candidate_id"], self.adapt(context=context)["candidates"][0]["candidate_id"])
        report = deepcopy(self.report); report["controls"][0]["message"] = "Changed bytes"
        self.assertNotEqual(first["candidates"][0]["candidate_id"], self.adapt(report)["candidates"][0]["candidate_id"])

    def test_duplicate_json_members_and_non_json_constants_are_rejected(self):
        for raw in (b'{"schema_version":"1.0.0","schema_version":"1.0.0"}', b'{"x":NaN}'):
            context = deepcopy(self.context); context["report_sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ValueError):
                adapt_devsecops(raw, context, evaluated_at=AT)

    def test_cli_protects_inputs_and_official_outputs_and_writes_only_after_validation(self):
        report = EXAMPLES / "devsecops-report.json"; context = EXAMPLES / "devsecops-context.json"
        for output in (report, context, ROOT / "status/new.json", ROOT / "generated/viewer/status-viewer.html", ROOT / "model/new.json"):
            with self.assertRaises(ContractError):
                write_candidates(report, context, output, evaluated_at=AT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); output = root / "candidates.json"
            write_candidates(report, context, output, evaluated_at=AT)
            before = output.read_bytes(); bad = root / "bad.json"; bad.write_text('{}')
            with self.assertRaises(ContractError):
                write_candidates(bad, context, output, evaluated_at=AT)
            self.assertEqual(output.read_bytes(), before)
            alias = root / "alias.json"; alias.symlink_to(report)
            with self.assertRaises(ContractError):
                write_candidates(report, context, alias, evaluated_at=AT)


if __name__ == "__main__":
    unittest.main()
