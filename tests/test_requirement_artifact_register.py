import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_requirement_lifecycle as validator


def catalog(authorized=("controls",)):
    return {"requirements": [{
        "id": "GRQ-000001", "active_revision": 1,
        "revisions": [{"revision": 1, "status": "effective", "authorized_derivations": list(authorized),
                       "runtime_enforcement": "none"}],
    }]}


def entry(digest, artifact_type="controls", requirement_ref="GRQ-000001@rev1"):
    return {
        "id": "RTA-000001", "requirement_ref": requirement_ref, "source_requirement_refs": ["SRC-1"],
        "artifact": {"path": "model/controls/control.yaml", "type": artifact_type,
                     "artifact_id": "CONTROL-1", "sha256": digest},
        "relationship": "adopts",
        "decision": {"kind": "adoption", "status": "effective", "decided_by": "owner",
                     "decision_role": "governance-owner", "decided_at": "2026-10-10T00:00:00Z",
                     "decision_ref": "docs/governance/change-requests/GCR.md", "equivalence": "equivalent",
                     "equivalence_evidence": ["review:1"]},
        "enforcement": "none",
    }


class RequirementArtifactRegisterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "model/controls").mkdir(parents=True)
        (self.root / "docs/governance/change-requests").mkdir(parents=True)
        self.artifact = self.root / "model/controls/control.yaml"
        self.artifact.write_text("control: stable\n", encoding="utf-8")
        (self.root / "docs/governance/change-requests/GCR.md").write_text("decision\n", encoding="utf-8")
        self.digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def tearDown(self):
        self.temp.cleanup()

    def validate(self, row, catalog_value=None):
        errors = []
        with patch.object(validator, "ROOT", self.root):
            validator.validate_artifact_register(
                {"entries": [row]}, catalog_value or catalog(), {"sources": []}, None, errors,
            )
        return errors

    def test_accepts_exact_active_authorized_revision_and_hash(self):
        self.assertEqual(self.validate(entry(self.digest)), [])

    def test_rejects_unknown_or_inactive_revision(self):
        errors = self.validate(entry(self.digest, requirement_ref="GRQ-000001@rev2"))
        self.assertTrue(any("unknown or inactive" in item for item in errors))

    def test_rejects_unauthorized_artifact_type(self):
        errors = self.validate(entry(self.digest, artifact_type="policies"))
        self.assertTrue(any("unauthorized artifact type" in item for item in errors))

    def test_detects_artifact_hash_change(self):
        errors = self.validate(entry("0" * 64))
        self.assertTrue(any("artifact hash changed" in item for item in errors))

    def test_unchanged_legacy_artifact_is_allowed_during_migration(self):
        errors = []
        with patch.object(validator, "ROOT", self.root), patch.object(validator, "changed_paths", return_value=set()):
            validator.validate_artifact_register(
                {"entries": []}, {"requirements": []},
                {"sources": [{"source_id": "SRC-1", "authority_mode": "migration_in_progress"}]},
                "base", errors,
            )
        self.assertEqual(errors, [])

    def test_changed_legacy_artifact_requires_effective_mapping(self):
        errors = []
        with patch.object(validator, "ROOT", self.root), \
                patch.object(validator, "changed_paths", return_value={"model/controls/control.yaml"}), \
                patch.object(validator, "git_path_exists", return_value=True):
            validator.validate_artifact_register({"entries": []}, {"requirements": []}, {"sources": []}, "base", errors)
        self.assertTrue(any("requires an effective GRQ mapping" in item for item in errors))

    def test_git_authoritative_source_rejects_legacy_adoption(self):
        errors = []
        with patch.object(validator, "ROOT", self.root):
            validator.validate_artifact_register(
                {"entries": [entry(self.digest)]}, catalog(),
                {"sources": [{"source_id": "DOC-1", "authority_mode": "git_authoritative"}]}, None, errors,
                {"SRC-1": "DOC-1"},
            )
        self.assertTrue(any("legacy adoption" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
