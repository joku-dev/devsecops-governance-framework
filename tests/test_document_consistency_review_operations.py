"""Phase 4 operations contracts remain conservative and provider-neutral."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_document_consistency_review_operations import (
    FILES, OperationsValidationError, classify_transition, plan_scope, validate,
)


class DocumentConsistencyOperationsTests(unittest.TestCase):
    def setUp(self):
        self.matrix = json.loads((ROOT / FILES["triggers"][0]).read_text())

    def test_checked_in_operations_package_is_valid_and_pending(self):
        result = validate(ROOT)
        self.assertEqual({"status":"pass", "artifacts":8, "rollout":"pending", "provider":"not_configured"}, result)

    def test_continuity_states_do_not_resolve_unassessed_findings(self):
        previous = {"state":"unchanged", "severity":"medium", "source_ids":["A"]}
        self.assertEqual("not_reassessed", classify_transition(previous, None, reassessed=False))
        self.assertEqual("resolved", classify_transition(previous, None, reassessed=True))
        self.assertEqual("reopened", classify_transition({**previous,"state":"resolved"}, previous, reassessed=True))

    def test_worsening_uses_severity_or_expanded_source_scope(self):
        previous = {"state":"unchanged", "severity":"low", "source_ids":["A"]}
        self.assertEqual("worsened", classify_transition(previous, {"severity":"high","source_ids":["A"]}, reassessed=True))
        self.assertEqual("worsened", classify_transition(previous, {"severity":"low","source_ids":["A","B"]}, reassessed=True))
        self.assertEqual("unchanged", classify_transition(previous, {"severity":"low","source_ids":["A"]}, reassessed=True))

    def test_trigger_matrix_expands_unknown_and_methodology_scope(self):
        self.assertEqual("incremental", plan_scope(self.matrix,["source_document"])["mode"])
        self.assertEqual("full_review", plan_scope(self.matrix,["topic_authority"])["mode"])
        self.assertEqual("full_review", plan_scope(self.matrix,["relationship"],impact_known=False)["mode"])
        self.assertEqual("methodology_comparison", plan_scope(self.matrix,["prompt"])["mode"])
        self.assertEqual("full_review", plan_scope(self.matrix,["unexpected"])["mode"])

    def test_unconfigured_provider_cannot_claim_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT,root,dirs_exist_ok=True)
            path=root/FILES["configuration"][0]
            value=json.loads(path.read_text());value["provider"]["model"]="secret-model";path.write_text(json.dumps(value))
            with self.assertRaisesRegex(OperationsValidationError,"unconfigured provider"):
                validate(root)

    def test_package_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT,root,dirs_exist_ok=True)
            path=root/FILES["package"][0]
            value=json.loads(path.read_text());value["artifacts"][0]["sha256"]="0"*64;path.write_text(json.dumps(value))
            with self.assertRaisesRegex(OperationsValidationError,"digest mismatch"):
                validate(root)

    def test_scope_limited_false_positive_retains_rationale(self):
        ledger=json.loads((ROOT/FILES["ledger"][0]).read_text())
        decision=ledger["findings"][1]["triage"]
        self.assertEqual("false_positive",decision["decision"])
        self.assertIn("synthetic",decision["decision_scope"])
        self.assertTrue(decision["rationale"])


if __name__ == "__main__":
    unittest.main()
