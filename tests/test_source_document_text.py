from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.lib.source_document_text import (
    SourceDocumentExtractionError,
    extract_source_document,
    line_for_markdown_parser,
)


class SourceDocumentTextTests(unittest.TestCase):
    def test_markdown_keeps_physical_line_locators(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.md"
            path.write_text("# Policy\n\nThe source shall keep evidence available.\n", encoding="utf-8")
            result = extract_source_document(path)
        self.assertEqual(result.format, "markdown")
        self.assertEqual([line.locator for line in result.lines], ["line:1", "line:3"])
        self.assertEqual(result.lines[1].number, 3)
        self.assertEqual(result.warnings, ())

    def test_docx_extracts_paragraphs_tables_and_revision_warnings(self):
        document_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body>
            <w:p><w:r><w:t>A policy shall preserve evidence.</w:t></w:r></w:p>
            <w:tbl><w:tr><w:tc><w:p><w:r><w:t>DSCB-REQ-001</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>MUST</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>Evidence</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>The system shall retain evidence.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
            <w:p><w:ins><w:r><w:t>Inserted wording remains reviewable.</w:t></w:r></w:ins></w:p>
          </w:body>
        </w:document>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", document_xml)
                archive.writestr("word/comments.xml", "<w:comments xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>")
            result = extract_source_document(path)
        self.assertEqual(result.format, "docx")
        self.assertEqual(result.lines[0].locator, "paragraph:1")
        self.assertEqual(result.lines[1].locator, "table:1/row:1")
        self.assertEqual(
            line_for_markdown_parser(result.lines[1]),
            "| `DSCB-REQ-001` | MUST | Evidence | The system shall retain evidence. |",
        )
        self.assertIn("docx_comments_present_not_included", result.warnings)
        self.assertIn("docx_tracked_changes_present_review_required", result.warnings)

    def test_unsupported_extension_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pptx"
            path.write_bytes(b"not parsed")
            with self.assertRaisesRegex(SourceDocumentExtractionError, "unsupported source document format"):
                extract_source_document(path)

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "optional pypdf parser is not installed")
    def test_pdf_page_locators_and_empty_page_warning(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with path.open("wb") as handle:
                writer.write(handle)
            result = extract_source_document(path)
        self.assertEqual(result.format, "pdf")
        self.assertIn("pdf_text_not_extractable_ocr_required_pages:1", result.warnings)
        self.assertIn("pdf_contains_no_extractable_text", result.warnings)


if __name__ == "__main__":
    unittest.main()
