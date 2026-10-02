"""Control assurance is complete, conservative, bound and append-only."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.control_evidence_assurance import (
    assurance_binding,
    build_assurance,
    load_profile,
    load_snapshots,
    store_snapshot,
    validate_assurance,
    validate_assurance_source,
)


class ControlEvidenceAssuranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.measured_path = (
            ROOT
            / "status/measured-l1-results/joku-dev__ha-CPsWMS/run-35131185085-attempt-1.json"
        )
        cls.measured = json.loads(cls.measured_path.read_text(encoding="utf-8"))
        cls.verified_at = "2026-09-16T18:00:00Z"

    def build(self, typed=()):
        return build_assurance(
            self.measured,
            list(typed),
            measured_source_file=self.measured_path.relative_to(ROOT).as_posix(),
            verified_at=self.verified_at,
        )

    def test_profile_maps_every_control_to_catalogued_evidence(self):
        profile = load_profile()
        self.assertEqual(16, len(profile["controls"]))
        self.assertEqual(
            {f"DSCB-L1-REQ-{number:03}" for number in range(1, 17)},
            {row["control_id"] for row in profile["controls"]},
        )

    def test_all_controls_receive_conservative_assurance(self):
        item = self.build()
        self.assertEqual({"complete": 7, "partial": 6, "missing": 3}, item["summary"]["coverage"])
        self.assertEqual(7, item["summary"]["trust_levels"]["integrity_verified"])
        self.assertEqual(9, item["summary"]["trust_levels"]["unverified"])
        controls = {row["control_id"]: row for row in item["controls"]}
        self.assertEqual("integrity_verified", controls["DSCB-L1-REQ-004"]["effective_level"])
        self.assertEqual("findings", controls["DSCB-L1-REQ-004"]["assessment"])
        self.assertEqual("unverified", controls["DSCB-L1-REQ-005"]["effective_level"])
        self.assertEqual(["present", "missing"], [row["status"] for row in controls["DSCB-L1-REQ-005"]["evidence"]])
        self.assertEqual("not_evaluated", controls["DSCB-L1-REQ-013"]["freshness"]["result"])
        self.assertFalse(item["official_compliance_result"])
        self.assertFalse(item["production_approval"])
        self.assertFalse(item["risk_acceptance"])
        validate_assurance_source(item)

    def test_typed_sbom_and_scan_trust_are_inherited_without_filling_scope_gaps(self):
        typed = []
        for path in sorted((ROOT / "status/typed-evidence-results/joku-dev__ha-CPsWMS").glob("*35241262722*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            row["pipeline"]["pipeline_run_id"] = self.measured["run"]["id"]
            row["pipeline"]["run_attempt"] = self.measured["run"]["attempt"]
            row["repository"]["commit_id"] = self.measured["run"]["commit"]
            row["_source_file"] = path.relative_to(ROOT).as_posix()
            typed.append(row)
        item = self.build(typed)
        controls = {row["control_id"]: row for row in item["controls"]}
        self.assertEqual("integrity_verified", controls["DSCB-L1-REQ-006"]["effective_level"])
        self.assertEqual("pass", controls["DSCB-L1-REQ-006"]["replay"])
        self.assertIn("typed_source_file", controls["DSCB-L1-REQ-006"]["evidence"][0])
        self.assertEqual("unverified", controls["DSCB-L1-REQ-005"]["effective_level"])

    def test_schema_binding_and_append_only_storage_protect_claims(self):
        item = self.build()
        changed = deepcopy(item)
        changed["production_approval"] = True
        changed["assurance_binding"] = assurance_binding(changed)
        with self.assertRaises(ValidationError):
            validate_assurance(changed)
        changed = deepcopy(item)
        changed["controls"][0]["effective_level"] = "attested"
        with self.assertRaisesRegex(ValueError, "binding"):
            validate_assurance(changed)
        changed = deepcopy(item)
        changed["controls"][0]["content_integrity"] = "pass"
        changed["assurance_binding"] = assurance_binding(changed)
        with self.assertRaisesRegex(ValueError, "positive Trust dimension"):
            validate_assurance(changed)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = store_snapshot(root, item)
            self.assertEqual(path, store_snapshot(root, item))
            changed = deepcopy(item)
            changed["verified_at"] = "2026-09-16T18:00:01Z"
            changed["assurance_binding"] = assurance_binding(changed)
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                store_snapshot(root, changed)
            self.assertEqual([item], load_snapshots(root))


if __name__ == "__main__":
    unittest.main()
