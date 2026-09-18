"""Staging deployment evidence remains bound, append-only and report-only."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.staging_deployment import binding, load_snapshots, store_snapshot, validate_approval, validate_snapshot


class StagingDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.items = load_snapshots(ROOT / "status/staging-deployment-results")
        self.assertTrue(self.items)
        self.item = self.items[-1]

    def test_current_snapshot_is_bound_to_real_staging_run(self):
        item = self.item
        self.assertEqual("joku-dev/ha-CPsWMS", item["repository_id"])
        self.assertEqual("35351493542", item["deployed_subject"]["source_run_id"])
        self.assertEqual("pass", item["deployment"]["status"])
        self.assertEqual({"query-api", "neo4j"}, set(item["components"]))
        self.assertEqual(19, item["tests"]["pass"])
        self.assertEqual(0, item["tests"]["fail"])
        self.assertEqual("integrity_verified", item["trust"]["effective_level"])
        self.assertFalse(item["deployment"]["production_approval"])
        self.assertFalse(item["deployment"]["risk_acceptance"])
        self.assertEqual(item["evidence_binding"], binding(item))

    def test_security_boundary_and_binding_changes_are_rejected(self):
        changed = deepcopy(self.item)
        changed["security_boundaries"]["api_loopback_only"] = False
        changed["evidence_binding"] = binding(changed)
        with self.assertRaises((ValidationError, ValueError)):
            validate_snapshot(changed)
        changed = deepcopy(self.item)
        changed["tests"]["pass"] += 1
        with self.assertRaises(ValueError):
            validate_snapshot(changed)

    def test_store_is_append_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = store_snapshot(root, self.item)
            self.assertEqual(self.item, json.loads(path.read_text(encoding="utf-8")))
            store_snapshot(root, self.item)
            changed = deepcopy(self.item)
            changed["observations"].append({"severity": "low", "id": "changed", "summary": "changed"})
            changed["evidence_binding"] = binding(changed)
            with self.assertRaises(ValueError):
                store_snapshot(root, changed)

    def test_approval_must_match_subject_target_images_and_acknowledged_risk(self):
        item = self.item
        receipt = {
            "context": {
                "repository": item["repository_id"],
                "commit": item["deployed_subject"]["commit"],
                "source_run_id": item["deployed_subject"]["source_run_id"],
                "environment": "staging",
            },
            "target": item["environment"],
            "components": item["components"],
            "approval": {
                "decision": "approved_for_staging",
                "record": "deployment-approval.json",
                "critical_findings_acknowledged": item["approval"]["critical_findings_acknowledged"],
                "high_findings_acknowledged": item["approval"]["high_findings_acknowledged"],
            },
        }
        approval = {
            "schema_version": "1.0",
            "decision": "approved_for_staging",
            "risk_context": {
                "scope": "staging_only",
                "enforcement": "report_only",
                "critical_findings": item["approval"]["critical_findings_acknowledged"],
                "high_findings": item["approval"]["high_findings_acknowledged"],
            },
            "subject": {
                "repository": item["repository_id"],
                "commit": item["deployed_subject"]["commit"],
                "evidence_run_id": item["deployed_subject"]["source_run_id"],
            },
            "target": {
                "hostname": item["environment"]["hostname"],
                "address": item["environment"]["address"],
                "environment": "staging",
            },
            "components": {
                name: {"runtime_image_id": component["runtime_image_id"]}
                for name, component in item["components"].items()
            },
        }
        validate_approval(receipt, approval)
        changed = deepcopy(approval)
        changed["target"]["address"] = "192.0.2.1"
        with self.assertRaises(ValueError):
            validate_approval(receipt, changed)


if __name__ == "__main__":
    unittest.main()
