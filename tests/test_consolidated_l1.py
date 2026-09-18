"""Exact staging evidence supplements only its matching measured L1 run."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.consolidated_l1 import (
    binding,
    build_consolidated,
    load_snapshots,
    store_snapshot,
    validate_snapshot,
    validate_sources,
)
from lib.measured_l1 import load_snapshots as load_measured
from lib.staging_deployment import load_snapshots as load_staging


class ConsolidatedL1Tests(unittest.TestCase):
    def setUp(self):
        self.measured_items = load_measured(ROOT / "status/measured-l1-results")
        self.staging = load_staging(ROOT / "status/staging-deployment-results")[-1]
        self.measured = next(
            row for row in self.measured_items
            if row["run"]["id"] == self.staging["deployed_subject"]["source_run_id"]
        )
        self.measured_file = (
            f"status/measured-l1-results/joku-dev__ha-CPsWMS/"
            f"run-{self.measured['run']['id']}-attempt-{self.measured['run']['attempt']}.json"
        )
        self.item = build_consolidated(
            self.measured,
            self.staging,
            measured_source_file=self.measured_file,
            staging_source_file=self.staging["source_file"],
        )

    def test_exact_staging_supplement_closes_only_its_scope(self):
        controls = {row["control_id"]: row for row in self.item["controls"]}
        self.assertEqual("measured", controls["DSCB-L1-REQ-013"]["assessment"])
        self.assertEqual("measured", controls["DSCB-L1-REQ-014"]["assessment"])
        self.assertEqual("partial", controls["DSCB-L1-REQ-016"]["assessment"])
        self.assertEqual({"measured": 7, "partial": 6, "findings": 2, "gap": 1}, self.item["summary"])
        self.assertFalse(self.item["production_approval"])
        validate_sources(self.item)

    def test_other_measured_run_cannot_reuse_staging(self):
        other = next(row for row in reversed(self.measured_items) if row["run"]["id"] != self.measured["run"]["id"])
        with self.assertRaisesRegex(ValueError, "exactly"):
            build_consolidated(
                other, self.staging,
                measured_source_file=self.measured_file,
                staging_source_file=self.staging["source_file"],
            )

    def test_binding_and_append_only_storage_reject_changes(self):
        changed = deepcopy(self.item)
        changed["controls"][0]["assessment"] = "measured"
        with self.assertRaisesRegex(ValueError, "binding"):
            validate_snapshot(changed)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = store_snapshot(root, self.item)
            self.assertEqual(self.item, json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual([self.item], load_snapshots(root))
            changed = deepcopy(self.item)
            changed["controls"][0]["remaining"] = "changed"
            changed["evidence_binding"] = binding(changed)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                store_snapshot(root, changed)


if __name__ == "__main__":
    unittest.main()
