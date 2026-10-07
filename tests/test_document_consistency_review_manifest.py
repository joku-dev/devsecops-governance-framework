from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from jsonschema import Draft202012Validator

from scripts.generate_document_consistency_review_manifest import (
    ManifestError,
    build_manifest,
    repository_revision,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "document-consistency-review-manifest.schema.json"


class DocumentConsistencyReviewManifestTests(unittest.TestCase):
    def create_fixture(self, root: Path) -> tuple[Path, Path]:
        source_root = root / "docs" / "governance" / "source-documents"
        source_root.mkdir(parents=True)
        source = source_root / "SAMPLE-REQ-001.md"
        source.write_text("# Sanitized sample\n\nMUST retain this example.\n", encoding="utf-8")
        register = root / "model" / "documents" / "source-document-register.yaml"
        register.parent.mkdir(parents=True)
        register.write_text(
            """schema_version: '1.0.0'
documents:
  - id: SAMPLE-REQ-001
    title: Sanitized sample
    status: intake
    source_path: docs/governance/source-documents/SAMPLE-REQ-001.md
    governance_domains: [devsecops]
    owner: sample-owner
    version: sanitized-1
    intake_date: '2026-10-07'
    derived_artifact_areas: []
""",
            encoding="utf-8",
        )
        return register, source

    def test_manifest_binds_metadata_and_exact_file_bytes_without_copying_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            register, source = self.create_fixture(root)
            manifest = build_manifest(root, ["SAMPLE-REQ-001"])

            self.assertEqual(manifest["source_count"], 1)
            self.assertEqual(manifest["source_register_sha256"], hashlib.sha256(register.read_bytes()).hexdigest())
            item = manifest["source_documents"][0]
            self.assertEqual(item["content_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(item["status"], "intake")
            self.assertNotIn("MUST retain", json.dumps(manifest))
            self.assertNotIn("content", item)
            Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))).validate(manifest)

    def test_manifest_orders_selected_sources_deterministically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            register, source = self.create_fixture(root)
            contents = source.read_text(encoding="utf-8")
            second = root / "docs" / "governance" / "source-documents" / "SAMPLE-REQ-002.md"
            second.write_text(contents + "Second source.\n", encoding="utf-8")
            with register.open("a", encoding="utf-8") as handle:
                handle.write(
                    "  - id: SAMPLE-REQ-002\n"
                    "    title: Second sanitized sample\n"
                    "    status: intake\n"
                    "    source_path: docs/governance/source-documents/SAMPLE-REQ-002.md\n"
                    "    governance_domains: [devsecops]\n"
                    "    owner: sample-owner\n"
                    "    version: sanitized-1\n"
                    "    intake_date: '2026-10-07'\n"
                    "    derived_artifact_areas: []\n"
                )
            manifest = build_manifest(root, ["SAMPLE-REQ-002", "SAMPLE-REQ-001"])
            self.assertEqual([item["id"] for item in manifest["source_documents"]], ["SAMPLE-REQ-001", "SAMPLE-REQ-002"])

    def test_unknown_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_fixture(root)
            with self.assertRaisesRegex(ManifestError, "not registered"):
                build_manifest(root, ["OTHER-SOURCE-001"])

    def test_duplicate_requested_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.create_fixture(root)
            with self.assertRaisesRegex(ManifestError, "must be unique"):
                build_manifest(root, ["SAMPLE-REQ-001", "SAMPLE-REQ-001"])

    def test_repository_revision_is_omitted_for_a_dirty_worktree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            tracked = root / "tracked.txt"
            tracked.write_text("committed\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "commit.gpgsign=false", "commit", "-m", "fixture"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIsNotNone(repository_revision(root))
            (root / "untracked.txt").write_text("local input\n", encoding="utf-8")
            self.assertIsNone(repository_revision(root))

    def test_source_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            register, source = self.create_fixture(root)
            escaped = root / "outside.md"
            escaped.write_text("private\n", encoding="utf-8")
            register.write_text(
                register.read_text(encoding="utf-8").replace(
                    "docs/governance/source-documents/SAMPLE-REQ-001.md", "../../outside.md"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ManifestError, "outside the source directory"):
                build_manifest(root, ["SAMPLE-REQ-001"])

    def test_missing_source_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            register, source = self.create_fixture(root)
            source.unlink()
            with self.assertRaisesRegex(ManifestError, "outside the source directory"):
                build_manifest(root, ["SAMPLE-REQ-001"])


if __name__ == "__main__":
    unittest.main()
