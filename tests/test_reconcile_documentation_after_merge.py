from __future__ import annotations

import argparse
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts import reconcile_documentation_after_merge as refresh


class DocumentationRefreshTests(unittest.TestCase):
    def test_summary_extracts_and_sanitizes_bullets(self) -> None:
        body = """## Summary
- Add `scripts/new_feature.py` for [bounded processing](https://example.test).
- <b>Keep</b> this human reviewed.

## Change Type
- Documentation-only
"""
        self.assertEqual(
            refresh.clean_summary(body, "fallback"),
            ["Add scripts/new_feature.py for bounded processing.", "Keep this human reviewed."],
        )

    def test_fallback_title_is_one_bounded_plain_text_line(self) -> None:
        self.assertEqual(refresh.clean_summary("", "<img>Feature\ncontinued `literal`"), ["Feature continued `literal`"])

    def test_functional_scope_ignores_document_only_files(self) -> None:
        paths = [
            "README.md", "docs/guide.md", "generated/reports/report.md",
            "scripts/new_feature.py", ".github/workflows/new.yml", "model/controls/example.yaml",
        ]
        self.assertEqual(
            refresh.functional(paths),
            ["scripts/new_feature.py", ".github/workflows/new.yml", "model/controls/example.yaml"],
        )

    def test_replace_block_is_idempotent(self) -> None:
        first = refresh.replace_block("Header\n", "TEST", "Initial")
        second = refresh.replace_block(first, "TEST", "Updated")
        self.assertEqual(second.count("<!-- TEST:start -->"), 1)
        self.assertIn("Updated", second)
        self.assertNotIn("Initial", second)

    def test_render_updates_all_document_surfaces_for_functional_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme, catalog, inventory, audit = (root / name for name in ("README.md", "catalog.md", "inventory.md", "audit.md"))
            for file in (readme, catalog, inventory):
                file.write_text("Existing content\n", encoding="utf-8")
            args = argparse.Namespace(
                base="base", merge="0123456789abcdef", pr=42, title="Add feature",
                body="## Summary\n- Add bounded feature processing.\n",
                docs_build_status="passed",
            )
            with (
                patch.object(refresh, "README", readme),
                patch.object(refresh, "CATALOG", catalog),
                patch.object(refresh, "INVENTORY", inventory),
                patch.object(refresh, "AUDIT", audit),
                patch.object(refresh, "changed_paths", return_value=["scripts/new_feature.py", "docs/guide.md"]),
                patch.object(refresh, "link_audit", return_value=[]),
            ):
                self.assertTrue(refresh.render(args))
            for file in (readme, catalog, inventory, audit):
                self.assertIn("PR #42", file.read_text(encoding="utf-8"))
            self.assertIn("scripts/new_feature.py", inventory.read_text(encoding="utf-8"))
            self.assertIn("mkdocs build --strict", audit.read_text(encoding="utf-8"))

    def test_render_skips_documentation_only_merge(self) -> None:
        args = argparse.Namespace(base="base", merge="merge", pr=3, title="Fix typo", body="", docs_build_status="")
        with patch.object(refresh, "changed_paths", return_value=["README.md", "docs/guide.md"]):
            self.assertFalse(refresh.render(args))

    def test_link_audit_reports_missing_local_targets_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "docs/page.md"
            source.parent.mkdir()
            source.write_text(
                "[present](../README.md) [missing](missing.md) [web](https://example.test)\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("home\n", encoding="utf-8")
            with (
                patch.object(refresh, "ROOT", root),
                patch.object(refresh.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "docs/page.md\n", "")),
            ):
                self.assertEqual(refresh.link_audit(), [("docs/page.md", "missing.md")])


if __name__ == "__main__":
    unittest.main()
