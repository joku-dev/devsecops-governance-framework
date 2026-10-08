import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_document_consistency_semantic_catalog_run import (
    CatalogRunPreparationError,
    prepare,
)


class PrepareSemanticCatalogRunTests(unittest.TestCase):
    def test_prepares_exact_provider_input_without_provider_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            package = prepare(output)
            self.assertEqual("prepared_not_run", package["status"])
            self.assertEqual("runtime_authorization_required", package["provider_binding"])
            self.assertEqual("runtime_authorization_required", package["model_binding"])
            paths = {item["path"] for item in package["provider_input"]}
            self.assertEqual({
                "provider-input/docs/governance/source-documents/SYN-SRC-A-001.md",
                "provider-input/docs/governance/source-documents/SYN-SRC-B-001.md",
                "provider-input/model/documents/source-document-register.yaml",
                "provider-input/prompt.txt",
                "provider-input/provider-projection.schema.json",
                "provider-input/source-manifest.json",
            }, paths)
            self.assertFalse((output / "provider-input/semantic-evaluation-catalog-v1.json").exists())
            self.assertEqual(package, json.loads((output / "run-package.json").read_text()))

    def test_refuses_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "existing.txt").write_text("keep")
            with self.assertRaisesRegex(CatalogRunPreparationError, "must not exist or must be empty"):
                prepare(output)


if __name__ == "__main__":
    unittest.main()
