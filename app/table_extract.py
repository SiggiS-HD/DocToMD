"""Konservative Extraktion einfacher rechteckiger PDF-Tabellen."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
import re

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from app.models import ConversionWarning, DocumentTable, PageReference


@dataclass(frozen=True, slots=True)
class TableExtractionOutcome:
    """Akzeptierte Tabellen und pro Seite zusammengefasste Strukturwarnungen."""

    tables: tuple[DocumentTable, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()


def extract_simple_tables(path: Path) -> TableExtractionOutcome:
    """Liest vollständig belegte Tabellen und verbindet wiederholte Kopfzeilen."""
    source = path.expanduser().resolve(strict=False)
    tables: list[DocumentTable] = []
    warnings: list[ConversionWarning] = []
    try:
        with pdfplumber.open(source) as pdf:
            previous_table: DocumentTable | None = None
            previous_page_number = 0
            for page_number, page in enumerate(pdf.pages, start=1):
                rejected_counts: dict[str, int] = {}
                for table_number, raw_table in enumerate(page.extract_tables(), start=1):
                    normalized, rejection_code = _normalize_table(raw_table)
                    if normalized is None:
                        assert rejection_code is not None
                        rejected_counts[rejection_code] = rejected_counts.get(rejection_code, 0) + 1
                        continue
                    headers, rows = normalized
                    table = DocumentTable(
                        table_id=f"page-{page_number:03d}-table-{table_number:02d}",
                        page=PageReference(page_number),
                        headers=headers,
                        rows=rows,
                    )
                    if (
                        previous_table is not None
                        and previous_page_number == page_number - 1
                        and previous_table.headers == table.headers
                    ):
                        previous_table = replace(previous_table, rows=(*previous_table.rows, *table.rows))
                        tables[-1] = previous_table
                    else:
                        tables.append(table)
                        previous_table = table
                    previous_page_number = page_number
                unsupported_count = rejected_counts.get("UNSUPPORTED_TABLE_STRUCTURE", 0)
                if unsupported_count:
                    warnings.append(ConversionWarning(
                        code="UNSUPPORTED_TABLE_STRUCTURE",
                        message=f"{unsupported_count} Tabellenkandidat(en) konnten nicht sicher als Markdown rekonstruiert werden.",
                        page=PageReference(page_number),
                    ))
    except (OSError, PDFSyntaxError, PdfminerException) as error:
        raise ValueError(f"PDF-Tabellen konnten nicht gelesen werden: {source}") from error
    return TableExtractionOutcome(tuple(tables), tuple(warnings))


def _normalize_table(
    raw_table: list[list[str | None]],
) -> tuple[tuple[tuple[str, ...], tuple[tuple[str, ...], ...]] | None, str | None]:
    if len(raw_table) < 2:
        return None, "UNSUPPORTED_TABLE_STRUCTURE"
    normalized_rows: list[tuple[str, ...]] = []
    for raw_row in raw_table:
        if len(raw_row) < 2:
            return None, "UNSUPPORTED_TABLE_STRUCTURE"
        if any(cell is None for cell in raw_row):
            return None, "UNSUPPORTED_TABLE_STRUCTURE"
        row = tuple(_normalize_cell(cell) for cell in raw_row)
        if any(not cell or "(cid:" in cell for cell in row):
            return None, "UNSUPPORTED_TABLE_STRUCTURE"
        normalized_rows.append(row)
    headers, rows = normalized_rows[0], tuple(normalized_rows[1:])
    if any(len(row) != len(headers) for row in rows):
        return None, "UNSUPPORTED_TABLE_STRUCTURE"
    return (headers, rows), None


def _normalize_cell(cell: str) -> str:
    """Bewahrt belegbare Zeilenumbrüche innerhalb einer Markdown-Tabellenzelle."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in cell.splitlines()]
    return "<br>".join(line for line in lines if line)


__all__ = ["TableExtractionOutcome", "extract_simple_tables"]
