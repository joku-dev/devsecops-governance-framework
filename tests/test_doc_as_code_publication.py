import importlib.util
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "doc-as-code/scripts/build_publication.py"
SPEC = importlib.util.spec_from_file_location("build_publication", MODULE_PATH)
build_publication = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = build_publication
SPEC.loader.exec_module(build_publication)


class DocAsCodePublicationTests(unittest.TestCase):
    def test_default_publication_is_valid_and_ordered(self):
        manifest, sections = build_publication.load_publication(build_publication.DEFAULT_MANIFEST)
        requirements = [section for section in sections if section["kind"] == "requirement"]
        self.assertEqual(manifest["id"], "DOC-AS-CODE-PILOT-001")
        self.assertEqual([item["metadata"]["id"] for item in requirements], [
            "DAC-REQ-001", "DAC-REQ-002", "DAC-REQ-003", "DAC-REQ-004", "DAC-REQ-005"
        ])

    def test_assembled_markdown_contains_each_requirement_once(self):
        manifest, sections = build_publication.load_publication(build_publication.DEFAULT_MANIFEST)
        assembled = build_publication.assembled_markdown(manifest, sections)
        for requirement_id in ("DAC-REQ-001", "DAC-REQ-002", "DAC-REQ-003", "DAC-REQ-004", "DAC-REQ-005"):
            self.assertEqual(assembled.count(f"# {requirement_id}:"), 1)

    def test_requirement_schema_rejects_unknown_metadata(self):
        _, sections = build_publication.load_publication(build_publication.DEFAULT_MANIFEST)
        metadata = deepcopy(next(section["metadata"] for section in sections if section["kind"] == "requirement"))
        metadata["uncontrolled_field"] = True
        with self.assertRaisesRegex(ValueError, "Additional properties"):
            build_publication.validate_schema(metadata, build_publication.REQUIREMENT_SCHEMA, "test")


if __name__ == "__main__":
    unittest.main()
