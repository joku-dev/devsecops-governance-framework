from pathlib import Path
import tempfile
import unittest
import importlib.util
import zipfile

from scripts.lib.explicit_requirements import extract_explicit_requirements
from scripts.lib.source_document_text import ExtractedSourceDocument, SourceLine, extract_source_document


class ExplicitRequirementTests(unittest.TestCase):
    def extract(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.md"
            path.write_text(text, encoding="utf-8")
            return extract_explicit_requirements(extract_source_document(path))

    def test_prose_and_generated_row_ids_never_create_requirements(self):
        text = """# Requirements are required
The system SHALL retain evidence.
All engineers MUST review changes.
| ID | Strength | Context | Requirement |
|---|---|---|---|
| `DSCB-STD-SRC-001-REQ-001` | REQUIREMENT | Version history | 0.2 aligned requirements |
| `DSCB-STD-SRC-001-REQ-002` | MUST | Purpose | The system shall retain evidence. |
"""
        self.assertEqual(self.extract(text), [])

    def test_declarations_need_no_modal_keyword_or_minimum_text_length(self):
        for label in ("[DSCB-L1-REQ-001]", "**DSCB-L2-REQ-001**:",
                      "`DSCB-L3-REQ-001`", "DSCB-GOV-REQ-001 —", "ARCH-SEC-REQ-001:"):
            with self.subTest(label=label):
                result = self.extract(f"- {label} Retain logs.")
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0].statement, "Retain logs.")

    def test_normalized_row_uses_embedded_requirement_label_and_keeps_locator(self):
        result = self.extract("""| ID | Strength | Context | Requirement |
|---|---|---|---|
| `DSCB-STD-SRC-001-REQ-010` | MUST | Control objective | [DSCB-L1-REQ-001]All software SHALL be traceable. |
""")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].identifier, "DSCB-L1-REQ-001")
        self.assertEqual(result[0].extraction_row_id, "DSCB-STD-SRC-001-REQ-010")
        self.assertEqual(result[0].source_line.locator, "line:3")

    def test_explicit_id_in_requirement_table(self):
        result = self.extract("""| Requirement ID | Requirement |
|---|---|
| **DSCB-L1-REQ-001** | Retain logs. |
""")
        self.assertEqual([r.identifier for r in result], ["DSCB-L1-REQ-001"])

    def test_reference_mentions_and_mapping_tables_are_excluded(self):
        self.assertEqual(self.extract("""See DSCB-L1-REQ-001 for requirements.
The system must comply with DSCB-L1-REQ-001.
| DSCB requirement | Platform | Evidence |
|---|---|---|
| **DSCB-L1-REQ-001** | C2.1 | Requirements to test links |
| Control Baseline Referenzen | DSCB-L1-REQ-002 |
| DSCB-L1-REQ-003 | Platform reference |
"""), [])

    def test_table_headers_do_not_leak_into_following_mapping_tables(self):
        result = self.extract("""| ID | Requirement |
|---|---|
| DSCB-L1-REQ-001 | Retain logs. |

| ID | Platform |
|---|---|
| DSCB-L1-REQ-002 | Source control |
""")
        self.assertEqual([r.identifier for r in result], ["DSCB-L1-REQ-001"])

    def test_docx_requirement_headers_do_not_leak_into_next_table(self):
        document = ExtractedSourceDocument("docx", (
            SourceLine(1, "table:1/row:1", "ID | Requirement"),
            SourceLine(2, "table:1/row:2", "DSCB-L1-REQ-001 | Retain logs."),
            SourceLine(3, "table:2/row:1", "ID | Platform"),
            SourceLine(4, "table:2/row:2", "DSCB-L1-REQ-002 | Source control"),
        ), ())
        result = extract_explicit_requirements(document)
        self.assertEqual([r.identifier for r in result], ["DSCB-L1-REQ-001"])

    def test_labelled_statement_can_contain_escaped_table_delimiters(self):
        text = r"| `DSCB-STD-SRC-001-REQ-010` | MUST | Control | [DSCB-L1-REQ-001] Accept A\|B. |"
        result = self.extract(text)
        self.assertEqual(result[0].statement, "Accept A|B.")

    def test_wrapped_statement_stops_at_next_paragraph(self):
        result = self.extract("[DSCB-L1-REQ-001] Retain logs\nfor twelve months.\n\nThe system SHALL do other things.")
        self.assertEqual(result[0].statement, "Retain logs for twelve months.")

    def test_docx_uses_explicit_labels_and_preserves_paragraph_locator(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
                <w:p><w:r><w:t>The system SHALL retain logs.</w:t></w:r></w:p>
                <w:p><w:r><w:t>[DSCB-L1-REQ-001] Retain logs.</w:t></w:r></w:p>
                </w:body></w:document>''')
            result = extract_explicit_requirements(extract_source_document(path))
        self.assertEqual([r.identifier for r in result], ["DSCB-L1-REQ-001"])
        self.assertEqual(result[0].source_line.locator, "paragraph:2")

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "optional PDF parser not installed")
    def test_pdf_uses_explicit_labels_and_preserves_page_locator(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.pdf"
            writer = PdfWriter()
            page = writer.add_blank_page(width=600, height=800)
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
            stream = DecodedStreamObject()
            stream.set_data(b"BT /F1 12 Tf 50 700 Td (The system SHALL retain logs.) Tj 0 -20 Td ([DSCB-L1-REQ-001] Retain logs.) Tj ET")
            page[NameObject("/Contents")] = writer._add_object(stream)
            with path.open("wb") as handle:
                writer.write(handle)
            result = extract_explicit_requirements(extract_source_document(path))
        self.assertEqual([r.identifier for r in result], ["DSCB-L1-REQ-001"])
        self.assertTrue(result[0].source_line.locator.startswith("page:1/line:"))

    def test_flattened_traceability_rows_are_excluded(self):
        text = r"| `PRA-STD-SRC-001-REQ-046` | REQUIREMENT | Traceability | DSCB-L1-REQ-001 Traceability \| PRA-Level 1 \| Evidence |"
        self.assertEqual(self.extract(text), [])

    def test_labelled_heading_followed_by_statement(self):
        result = self.extract("## DSCB-L1-REQ-001\n\nRetain logs.")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].statement, "Retain logs.")
        self.assertEqual(result[0].source_line.locator, "line:1")

    def test_code_examples_and_unlabelled_headings_are_excluded(self):
        self.assertEqual(self.extract("```\nDSCB-L1-REQ-001 Retain logs.\n```\n# Requirements\nThe system shall be safe."), [])

    def test_invalid_or_incomplete_identifiers_are_excluded(self):
        for label in ("DSCB-L1-REQ-01", "dscb-L1-REQ-001", "DSCB-L1-REQ-001-extra", "DSCB-STD-SRC-001-REQ-001"):
            with self.subTest(label=label):
                self.assertEqual(self.extract(f"{label} The system shall retain logs."), [])
