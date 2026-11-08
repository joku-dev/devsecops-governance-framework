"""Read explicitly labelled requirements; never infer obligations from prose."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .source_document_text import ExtractedSourceDocument, SourceLine, line_for_markdown_parser


IDENTIFIER = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-REQ-[0-9]{3,}"
IDENTIFIER_PATTERN = re.compile(rf"^{IDENTIFIER}$")
EXTRACTION_ID_PATTERN = re.compile(r"-SRC-[0-9]+-REQ-")
DECLARATION_PATTERN = re.compile(
    rf"^(?:\[(?P<bracket>{IDENTIFIER})\]|(?P<plain>{IDENTIFIER})(?![A-Z0-9-]))"
    r"(?:\s*[:\u2013\u2014-]\s*|\s+|(?<=\]))(?P<body>.*)$"
)
STRENGTHS = {"MUST", "SHALL", "SHOULD", "MAY", "REQUIREMENT"}
TEXT_COLUMNS = {"requirement", "requirement text", "statement", "anforderung", "anforderungstext"}
ID_COLUMNS = {"id", "requirement id", "requirement identifier", "kennung", "anforderungs-id"}


@dataclass(frozen=True)
class ExplicitRequirement:
    identifier: str
    statement: str
    source_line: SourceLine
    extraction_row_id: str | None = None
    strength: str | None = None
    context: str = ""


def plain(text: str) -> str:
    return text.replace("**", "").replace("__", "").replace("`", "").strip()


def is_requirement_id(value: str) -> bool:
    return bool(IDENTIFIER_PATTERN.fullmatch(value)) and not EXTRACTION_ID_PATTERN.search(value)


def declaration(text: str) -> tuple[str, str] | None:
    text = plain(re.sub(r"^(?:#{1,6}\s+|[-*+]\s+|[0-9]+[.)]\s+)", "", text.strip()))
    if is_requirement_id(text) or (text.startswith("[") and text.endswith("]") and is_requirement_id(text[1:-1])):
        return text.strip("[]"), ""
    match = DECLARATION_PATTERN.match(text)
    if not match:
        return None
    identifier = match.group("bracket") or match.group("plain")
    if not is_requirement_id(identifier):
        return None
    return identifier, match.group("body").strip()


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def extract_explicit_requirements(document: ExtractedSourceDocument) -> list[ExplicitRequirement]:
    """Accept labelled statements and requirement-table declarations, not ID references.

    Synthetic ``*-SRC-001-REQ-001`` row IDs are locators only. In a normalized
    source table the statement must contain its own explicit requirement label.
    Table headers distinguish requirement definitions from traceability mappings.
    """
    result = []
    columns: list[str] = []
    pending: ExplicitRequirement | None = None
    fenced = False
    previous_line: SourceLine | None = None
    continuation_index: int | None = None
    for source_line in document.lines:
        consecutive = previous_line is not None and source_line.number == previous_line.number + 1
        if document.format == "markdown" and not consecutive:
            columns = []
            continuation_index = None
        if document.format == "docx" and previous_line is not None and source_line.locator.split("/")[0] != previous_line.locator.split("/")[0]:
            columns = []
        can_continue = consecutive and (
            document.format == "markdown"
            or (document.format == "pdf" and source_line.locator.split("/")[0] == previous_line.locator.split("/")[0])
        )
        previous_line = source_line
        line = line_for_markdown_parser(source_line).strip()
        if line.startswith(("```", "~~~")):
            fenced = not fenced
            pending = None
            continuation_index = None
            continue
        if fenced:
            continue
        if line.startswith("|"):
            pending = None
            continuation_index = None
            cells = table_cells(line)
            names = [plain(cell).lower() for cell in cells]
            if any(name in TEXT_COLUMNS for name in names) and any(name in ID_COLUMNS for name in names):
                columns = names
                continue
            if all(re.fullmatch(r":?-+:?", cell.strip()) for cell in cells):
                continue
            text_index = next((i for i, name in enumerate(columns) if name in TEXT_COLUMNS), None)
            id_index = next((i for i, name in enumerate(columns) if name in ID_COLUMNS), None)
            strength = None
            context = ""
            row_id = plain(cells[0]) if cells else ""
            if text_index is not None and id_index is not None and max(text_index, id_index) < len(cells):
                text = cells[text_index]
                row_id = plain(cells[id_index])
                if "strength" in columns and columns.index("strength") < len(cells):
                    strength = plain(cells[columns.index("strength")]).upper()
                if "context" in columns and columns.index("context") < len(cells):
                    context = plain(cells[columns.index("context")])
            elif len(cells) == 4 and plain(cells[1]).upper() in STRENGTHS:
                text, strength, context = cells[3], plain(cells[1]).upper(), plain(cells[2])
            else:
                continue
            label = (row_id, plain(text)) if is_requirement_id(row_id) else declaration(text)
            # Flattened traceability rows have multiple cells inside the statement.
            if not label or not label[1]:
                continue
            if "\\|" in text and not is_requirement_id(row_id) and not plain(text).startswith(f"[{label[0]}]"):
                continue
            result.append(ExplicitRequirement(label[0], label[1].replace("\\|", "|"), source_line,
                                               row_id if row_id != label[0] else None,
                                               strength if strength in STRENGTHS else None, context))
            continue
        columns = []
        label = declaration(line)
        if label:
            pending = ExplicitRequirement(label[0], label[1], source_line)
            continuation_index = None
            if label[1]:
                result.append(pending)
                pending = None
                continuation_index = len(result) - 1
        elif pending is not None and not line.startswith(("#", ">", "- ", "* ")):
            result.append(ExplicitRequirement(pending.identifier, line, pending.source_line))
            pending = None
            continuation_index = len(result) - 1
        elif continuation_index is not None and can_continue and not line.startswith(("#", ">", "- ", "* ")):
            current = result[continuation_index]
            result[continuation_index] = ExplicitRequirement(
                current.identifier, current.statement + " " + line, current.source_line,
                current.extraction_row_id, current.strength, current.context,
            )
        else:
            pending = None
            continuation_index = None
    return result
