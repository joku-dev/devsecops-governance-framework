from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MISTRAL_DIR = ROOT / ".agents" / "providers" / "mistral"


class ProviderAdapterTests(unittest.TestCase):
    def test_mistral_provider_adapter_files_exist(self):
        expected_files = {
            "README.md",
            "governance-agent-dispatch.prompt.md",
            "role-execution-contract.md",
        }

        actual_files = {path.name for path in MISTRAL_DIR.glob("*") if path.is_file()}

        self.assertTrue(MISTRAL_DIR.exists(), msg="Mistral provider adapter directory is required")
        self.assertTrue(expected_files.issubset(actual_files))

    def test_mistral_adapter_references_model_neutral_contracts(self):
        required_references = (
            ".agents/roles/",
            ".agents/skills/",
            ".agents/routing/governance-agent-routing.yaml",
            "docs/governance/governance-roles-and-agent-profiles.md",
        )

        for path in sorted(MISTRAL_DIR.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                for reference in required_references:
                    self.assertIn(reference, content)

    def test_mistral_adapter_stays_provider_only(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in sorted(MISTRAL_DIR.glob("*.md")))
        lowered = combined.lower()

        self.assertIn("not a governance source of truth", lowered)
        self.assertIn("do not introduce mistral-only governance rules", lowered)
        self.assertIn("mistral as the provider value", lowered)
        self.assertIn("bitbucket", lowered)
        self.assertIn("bamboo", lowered)

    def test_mistral_dispatch_preserves_shared_output_shape(self):
        content = (MISTRAL_DIR / "governance-agent-dispatch.prompt.md").read_text(encoding="utf-8")

        for phrase in (
            "Selected agents:",
            "Impact:",
            "Required validation:",
            "Findings:",
            "Commit readiness:",
            "provider: mistral",
            "platform:",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, content)
