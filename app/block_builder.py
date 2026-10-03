"""Konservative Erkennung grundlegender Markdown-Blöcke."""

from __future__ import annotations

import re
from dataclasses import replace

from app.models import BlockKind, DocumentBlock, PageReference
from app.pdf_extract import ExtractedPage


_NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)*\s+\S")
_BULLET_ITEM = re.compile(r"^[*+\-•▪◦]\s+(?P<text>.+)$")
_ORDERED_ITEM = re.compile(r"^\d+[.)]\s+(?P<text>.+)$")
_NAMED_HEADINGS = frozenset({"abstract", "references", "acknowledgements"})


def build_page_blocks(page: ExtractedPage) -> tuple[DocumentBlock, ...]:
    """Erzeugt Überschriften, Absätze und Listen für genau eine PDF-Seite."""
    page_reference = PageReference(page.page_number)
    blocks: list[DocumentBlock] = []
    paragraph_lines: list[str] = []
    typographic_heading_levels = dict(page.heading_levels)
    graphic_bullet_lines = frozenset(page.bullet_lines)
    table_lines = frozenset(page.table_lines)
    display_formulas = dict(page.display_formulas)
    paragraph_continues_list = False
    previous_line_was_blank = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = _join_paragraph_lines(paragraph_lines)
            if paragraph_continues_list and blocks and blocks[-1].kind is BlockKind.LIST_ITEM:
                blocks[-1] = replace(blocks[-1], text=f"{blocks[-1].text} {text}")
            else:
                blocks.append(
                    DocumentBlock(
                        kind=BlockKind.PARAGRAPH,
                        text=text,
                        page=page_reference,
                    )
                )
            paragraph_lines.clear()

    for line in page.text.splitlines():
        if not line.strip():
            flush_paragraph()
            paragraph_continues_list = False
            previous_line_was_blank = True
            continue
        if line in table_lines:
            flush_paragraph()
            previous_line_was_blank = False
            continue
        formula = display_formulas.get(line)
        if formula is not None:
            flush_paragraph()
            blocks.append(
                DocumentBlock(
                    kind=BlockKind.PARAGRAPH,
                    text=f"$${formula}$$",
                    page=page_reference,
                )
            )
            previous_line_was_blank = False
            continue
        heading_level = _heading_level(line, typographic_heading_levels)
        if heading_level is not None:
            flush_paragraph()
            blocks.append(
                DocumentBlock(
                    kind=BlockKind.HEADING,
                    text=line,
                    page=page_reference,
                    heading_level=heading_level,
                )
            )
            previous_line_was_blank = False
            continue
        list_item = _list_item(line, graphic_bullet_lines)
        if list_item is not None:
            flush_paragraph()
            text, ordered = list_item
            blocks.append(
                DocumentBlock(
                    kind=BlockKind.LIST_ITEM,
                    text=text,
                    page=page_reference,
                    ordered=ordered,
                )
            )
            previous_line_was_blank = False
            continue
        if not paragraph_lines:
            paragraph_continues_list = (
                bool(blocks)
                and blocks[-1].kind is BlockKind.LIST_ITEM
                and not previous_line_was_blank
            )
        paragraph_lines.append(line)
        previous_line_was_blank = False

    flush_paragraph()
    return tuple(blocks)


def _join_paragraph_lines(lines: list[str]) -> str:
    """Verbindet Zeilen eines Absatzes ohne explizite weiche Trennung zu verlieren."""
    joined = lines[0]
    for line in lines[1:]:
        if joined.endswith("\u00ad"):
            joined = joined[:-1] + line.lstrip()
        else:
            joined += " " + line
    return joined


def _heading_level(line: str, typographic_heading_levels: dict[str, int]) -> int | None:
    if line in typographic_heading_levels:
        return typographic_heading_levels[line]
    if line.casefold() in _NAMED_HEADINGS:
        return 1
    match = _NUMBERED_HEADING.match(line)
    if match is None:
        return None
    number = line.split(maxsplit=1)[0]
    return min(number.count(".") + 1, 6)


def _list_item(line: str, graphic_bullet_lines: frozenset[str]) -> tuple[str, bool] | None:
    if line in graphic_bullet_lines:
        return line, False
    bullet_match = _BULLET_ITEM.match(line)
    if bullet_match is not None:
        return bullet_match.group("text"), False
    ordered_match = _ORDERED_ITEM.match(line)
    if ordered_match is not None:
        return ordered_match.group("text"), True
    return None


__all__ = ["build_page_blocks"]
