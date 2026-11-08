"""Read supported governance source formats without changing source bytes.

The adapter keeps source locators for review. DOCX tracked changes and comments
are surfaced as warnings; PDF pages without extractable text require OCR and
are never silently treated as empty, reviewed content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET


class SourceDocumentExtractionError(ValueError):
    """Raised when a source cannot be extracted without guessing."""


@dataclass(frozen=True)
class SourceLine:
    number: int
    locator: str
    text: str


@dataclass(frozen=True)
class ExtractedSourceDocument:
    format: str
    lines: tuple[SourceLine, ...]
    warnings: tuple[str, ...]


def _lines(format_name: str, values: list[tuple[str, str]], warnings: list[str]) -> ExtractedSourceDocument:
    normalized = []
    for index, (locator, text) in enumerate(values, start=1):
        text = " ".join(text.replace("\x00", " ").split())
        if text:
            markdown_line = re.fullmatch(r"line:(\d+)", locator)
            normalized.append((int(markdown_line.group(1)) if markdown_line else index, locator, text))
    return ExtractedSourceDocument(
        format=format_name,
        lines=tuple(
            SourceLine(number=number, locator=locator, text=text)
            for number, locator, text in normalized
        ),
        warnings=tuple(sorted(set(warnings))),
    )


def _extract_markdown(path: Path) -> ExtractedSourceDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SourceDocumentExtractionError("Markdown source is not valid UTF-8") from exc
    return _lines("markdown", [(f"line:{number}", line) for number, line in enumerate(text.splitlines(), 1)], [])


def _paragraph_text(paragraph: ET.Element, namespace: dict[str, str]) -> str:
    parts = []
    for child in paragraph.iter():
        if child.tag == f"{{{namespace['w']}}}t" and child.text:
            parts.append(child.text)
        elif child.tag == f"{{{namespace['w']}}}tab":
            parts.append(" ")
        elif child.tag == f"{{{namespace['w']}}}br":
            parts.append(" ")
    return "".join(parts)


def _extract_docx(path: Path) -> ExtractedSourceDocument:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    document_name = "word/document.xml"
    warnings: list[str] = []
    values: list[tuple[str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if document_name not in names:
                raise SourceDocumentExtractionError("DOCX package has no word/document.xml")
            document = ET.fromstring(archive.read(document_name))
            if "word/comments.xml" in names:
                warnings.append("docx_comments_present_not_included")
            if any(element.tag in {f"{{{namespace['w']}}}ins", f"{{{namespace['w']}}}del"} for element in document.iter()):
                warnings.append("docx_tracked_changes_present_review_required")
            body = document.find(".//w:body", namespace)
            if body is None:
                raise SourceDocumentExtractionError("DOCX package has no document body")
            paragraph_number = 0
            table_number = 0
            for block in list(body):
                if block.tag == f"{{{namespace['w']}}}p":
                    paragraph_number += 1
                    values.append((f"paragraph:{paragraph_number}", _paragraph_text(block, namespace)))
                    continue
                if block.tag != f"{{{namespace['w']}}}tbl":
                    continue
                table_number += 1
                for row_number, row in enumerate(block.findall("w:tr", namespace), start=1):
                    cells = []
                    for cell in row.findall("w:tc", namespace):
                        cell_paragraphs = [
                            _paragraph_text(paragraph, namespace)
                            for paragraph in cell.findall(".//w:p", namespace)
                        ]
                        cells.append(" ".join(item for item in cell_paragraphs if item))
                    if cells:
                        values.append((f"table:{table_number}/row:{row_number}", " | ".join(cells)))
    except zipfile.BadZipFile as exc:
        raise SourceDocumentExtractionError("DOCX source is not a valid Office Open XML package") from exc
    except (OSError, ET.ParseError) as exc:
        raise SourceDocumentExtractionError("DOCX source could not be parsed") from exc
    return _lines("docx", values, warnings)


def _extract_pdf(path: Path) -> ExtractedSourceDocument:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise SourceDocumentExtractionError(
            "PDF extraction requires the optional source-document intake environment (pypdf)"
        ) from exc
    try:
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted:
            raise SourceDocumentExtractionError("encrypted PDF requires an explicitly handled source copy")
        values = []
        empty_pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            # A valid blank page may omit its content stream entirely. Treat
            # it as an OCR/extraction gap instead of a malformed PDF.
            if "/Contents" not in page:
                empty_pages.append(page_number)
                continue
            text = page.extract_text(extraction_mode="layout") or ""
            if not text.strip():
                empty_pages.append(page_number)
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                values.append((f"page:{page_number}/line:{line_number}", line))
    except SourceDocumentExtractionError:
        raise
    except Exception as exc:  # pypdf exposes multiple parser exception types
        raise SourceDocumentExtractionError("PDF source could not be parsed") from exc
    warnings = [f"pdf_text_not_extractable_ocr_required_pages:{','.join(map(str, empty_pages))}"] if empty_pages else []
    if not values:
        warnings.append("pdf_contains_no_extractable_text")
    return _lines("pdf", values, warnings)


def extract_source_document(path: Path) -> ExtractedSourceDocument:
    """Extract reviewable text lines from Markdown, PDF or DOCX input."""
    if not path.is_file():
        raise SourceDocumentExtractionError("source document does not exist or is not a file")
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return _extract_markdown(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    raise SourceDocumentExtractionError(f"unsupported source document format: {suffix or '<none>'}")


def line_for_markdown_parser(source_line: SourceLine) -> str:
    """Render an extracted table row into the Markdown form existing parsers expect."""
    text = source_line.text.strip()
    if source_line.locator.startswith("table:") and "|" in text:
        cells = [cell.strip() for cell in text.split("|")]
        if cells and re.fullmatch(r"[A-Z][A-Z0-9-]*-REQ-\d{3,}", cells[0]):
            cells[0] = f"`{cells[0]}`"
        return "| " + " | ".join(cells) + " |"
    return text
