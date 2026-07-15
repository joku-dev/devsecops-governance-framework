from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.identifiers import sanitize_timestamp, slugify_repository  # noqa: E402
from lib.json_io import load_json, write_json  # noqa: E402


class ScriptUtilityTests(unittest.TestCase):
    def test_slugify_repository_preserves_readable_repository_identity(self):
        self.assertEqual(slugify_repository("joku-dev/devsecops-governance-framework"), "joku-dev__devsecops-governance-framework")

    def test_sanitize_timestamp_removes_filename_sensitive_characters(self):
        self.assertEqual(sanitize_timestamp("2026-07-04T09:10:11+00:00"), "2026-07-04T09-10-11-00-00")

    def test_write_json_creates_parent_directories_and_loads_roundtrip(self):
        payload = {"schema_version": "1.0.0", "status": "pass"}

        with tempfile.TemporaryDirectory() as tempdir:
            output_path = Path(tempdir) / "nested" / "result.json"

            write_json(output_path, payload)

            self.assertEqual(load_json(output_path), payload)
            self.assertTrue(output_path.read_text(encoding="utf-8").endswith("\n"))
