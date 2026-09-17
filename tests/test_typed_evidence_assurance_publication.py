"""The assurance publisher extends only the typed-evidence operational scope."""
import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class TypedEvidenceAssurancePublicationTests(unittest.TestCase):
    def test_extension_allows_new_ledgers_but_not_application_code(self):
        publisher = importlib.import_module("publish_operational_update")
        extension = importlib.import_module("publish_typed_evidence_assurance_update")
        old_ledgers = publisher.LEDGERS
        old_scope = publisher.SCOPES["typed-evidence"]
        self.addCleanup(setattr, publisher, "LEDGERS", old_ledgers)
        self.addCleanup(publisher.SCOPES.__setitem__, "typed-evidence", old_scope)
        extension.configure()
        self.assertTrue(publisher.allowed(
            "status/control-evidence-assurance/org__repo/run-1-attempt-1.json",
            "typed-evidence",
        ))
        self.assertTrue(publisher.allowed(
            "status/measured-l1-results/org__repo/run-1-attempt-1.json",
            "typed-evidence",
        ))
        self.assertFalse(publisher.allowed("apps/governance-viewer/app.js", "typed-evidence"))
        for prefix in extension.ADDITIONAL_LEDGERS:
            self.assertIn(prefix, publisher.LEDGERS)


if __name__ == "__main__":
    unittest.main()
