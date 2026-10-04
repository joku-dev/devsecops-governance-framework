import json
import tempfile
import unittest
from unittest.mock import patch

from scripts import export_repository_sbom as sbom


def valid_document(repository="joku-dev/devsecops-governance-framework"):
    return {
        "SPDXID": "SPDXRef-DOCUMENT",
        "spdxVersion": "SPDX-2.3",
        "name": f"github/{repository}",
        "dataLicense": "CC0-1.0",
        "documentNamespace": "https://spdx.org/spdxdocs/example",
        "creationInfo": {"created": "2026-10-01T00:00:00Z", "creators": ["Tool: GitHub.com-Dependency-Graph"]},
        "packages": [
            {"SPDXID": "SPDXRef-Repository", "name": f"github/{repository}", "versionInfo": "main"},
            {"SPDXID": "SPDXRef-Package", "name": "jsonschema", "versionInfo": "4.26.0"},
        ],
        "relationships": [],
    }


class RepositorySbomTests(unittest.TestCase):
    def test_accepts_valid_spdx_document(self):
        source = json.dumps({"sbom": valid_document()}).encode()
        result = sbom.validate_spdx(source, "joku-dev/devsecops-governance-framework")
        self.assertEqual(result["spdxVersion"], "SPDX-2.3")
        self.assertEqual(len(result["packages"]), 2)

    def test_rejects_non_spdx_or_unrelated_repository(self):
        document = valid_document()
        document["spdxVersion"] = "CycloneDX-1.6"
        with self.assertRaisesRegex(ValueError, "SPDX version"):
            sbom.validate_spdx(json.dumps(document).encode(), "joku-dev/devsecops-governance-framework")

        document = valid_document("someone/else")
        with self.assertRaisesRegex(ValueError, "identity"):
            sbom.validate_spdx(json.dumps(document).encode(), "joku-dev/devsecops-governance-framework")

    def test_rejects_incomplete_or_empty_component_inventory(self):
        document = valid_document()
        document["packages"] = []
        with self.assertRaisesRegex(ValueError, "no dependency packages"):
            sbom.validate_spdx(json.dumps(document).encode(), "joku-dev/devsecops-governance-framework")

        document = valid_document()
        document["packages"].pop(0)
        with self.assertRaisesRegex(ValueError, "repository root"):
            sbom.validate_spdx(json.dumps(document).encode(), "joku-dev/devsecops-governance-framework")

    def test_download_urls_require_trusted_https_hosts_without_credentials(self):
        for url in (
            "http://example.amazonaws.com/sbom",
            "https://attacker.example/sbom",
            "https://user:password@github.com/sbom",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                sbom.validate_download_url(url)
        sbom.validate_download_url("https://github.s3.amazonaws.com/private/sbom?sig=secret")
        sbom.validate_download_url("https://github.com/private/sbom?sig=secret")

    def test_download_url_host_allowlist_does_not_accept_suffix_lookalikes(self):
        for url in (
            "https://github.com.attacker.example/sbom",
            "https://attacker-github.com/sbom",
            "https://githubusercontent.com.attacker.example/sbom",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                sbom.validate_download_url(url)

    def test_limited_reader_rejects_oversized_content(self):
        class FakeResponse:
            def __init__(self):
                self.content = b"12345"

            def read(self, size):
                value, self.content = self.content[:size], self.content[size:]
                return value

        with self.assertRaisesRegex(ValueError, "exceeds"):
            sbom.read_limited(FakeResponse(), limit=4)

    def test_generation_refuses_stale_or_non_default_branch_commits(self):
        with patch.object(sbom, "current_default_branch_sha", return_value=("main", "a" * 40)), patch.object(
            sbom, "api_json", side_effect=AssertionError("must not request an SBOM")
        ), patch.dict("os.environ", {"GITHUB_REF": ""}):
            with self.assertRaisesRegex(ValueError, "not the current default-branch HEAD"):
                sbom.generate("joku-dev/devsecops-governance-framework", "b" * 40, "token", sbom.Path("unused"))

        with patch.object(sbom, "current_default_branch_sha", return_value=("main", "a" * 40)), patch.dict(
            "os.environ", {"GITHUB_REF": "refs/heads/topic"}
        ):
            with self.assertRaisesRegex(ValueError, "default branch"):
                sbom.generate("joku-dev/devsecops-governance-framework", "a" * 40, "token", sbom.Path("unused"))

    def test_generation_writes_sbom_and_metadata_only_when_branch_is_stable(self):
        document = valid_document()
        sbom_url = (
            "https://api.github.com/repos/joku-dev/devsecops-governance-framework/"
            "dependency-graph/sbom/fetch-report/12345678-1234-1234-1234-123456789012"
        )
        api_results = [
            (201, {"sbom_url": sbom_url}),
        ]
        with tempfile.TemporaryDirectory() as directory, patch.object(
            sbom, "current_default_branch_sha", side_effect=[("main", "a" * 40), ("main", "a" * 40)]
        ), patch.object(sbom, "api_json", side_effect=api_results), patch.object(
            sbom, "api_redirect", return_value="https://github.s3.amazonaws.com/sbom?token=secret"
        ), patch.object(sbom, "download_sbom", return_value=json.dumps(document).encode()), patch.dict(
            "os.environ", {"GITHUB_REF": "refs/heads/main"}
        ):
            sbom_path, metadata_path = sbom.generate(
                "joku-dev/devsecops-governance-framework", "a" * 40, "token", sbom.Path(directory)
            )
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual(metadata["commit_sha"], "a" * 40)
            self.assertEqual(metadata["package_count"], 2)
            self.assertEqual(json.loads(sbom_path.read_text())["spdxVersion"], "SPDX-2.3")

    def test_generation_fails_if_default_branch_moves_before_artifact_write(self):
        document = valid_document()
        sbom_url = (
            "https://api.github.com/repos/joku-dev/devsecops-governance-framework/"
            "dependency-graph/sbom/fetch-report/12345678-1234-1234-1234-123456789012"
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            sbom, "current_default_branch_sha", side_effect=[("main", "a" * 40), ("main", "b" * 40)]
        ), patch.object(sbom, "api_json", return_value=(201, {"sbom_url": sbom_url})), patch.object(
            sbom, "api_redirect", return_value="https://github.s3.amazonaws.com/sbom"
        ), patch.object(sbom, "download_sbom", return_value=json.dumps(document).encode()), patch.dict(
            "os.environ", {"GITHUB_REF": "refs/heads/main"}
        ):
            with self.assertRaisesRegex(RuntimeError, "branch moved"):
                sbom.generate("joku-dev/devsecops-governance-framework", "a" * 40, "token", sbom.Path(directory))
            self.assertEqual(list(sbom.Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
