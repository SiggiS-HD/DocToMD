"""Unit-Tests für konservativ extrahierte einfache Tabellen."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.table_extract import extract_simple_tables


class _FakePage:
    def __init__(self, tables: list[list[list[str | None]]]) -> None:
        self.tables = tables

    def extract_tables(self) -> list[list[list[str | None]]]:
        return self.tables


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


class TableExtractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.source = Path(self.directory.name) / "Quelle.pdf"
        self.source.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self.directory.cleanup()

    @patch("app.table_extract.pdfplumber.open")
    def test_extracts_complete_simple_table(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage([[['Name', 'Wert'], ['Alpha', '1'], ['Beta', '2']]])])
        outcome = extract_simple_tables(self.source)
        self.assertEqual(outcome.tables[0].headers, ('Name', 'Wert'))
        self.assertEqual(outcome.tables[0].rows, (('Alpha', '1'), ('Beta', '2')))
        self.assertEqual(outcome.tables[0].page.page_number, 1)
        self.assertEqual(outcome.warnings, ())

    @patch("app.table_extract.pdfplumber.open")
    def test_extracts_complete_three_column_table(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage([[['Metrik', 'Wert', 'Einheit'], ['Genauigkeit', '0.97', '%'], ['Verlust', '0.02', 'Anteil']]])])

        outcome = extract_simple_tables(self.source)

        self.assertEqual(outcome.tables[0].headers, ('Metrik', 'Wert', 'Einheit'))
        self.assertEqual(outcome.tables[0].rows, (('Genauigkeit', '0.97', '%'), ('Verlust', '0.02', 'Anteil')))
        self.assertEqual(outcome.warnings, ())

    @patch("app.table_extract.pdfplumber.open")
    def test_keeps_multiline_cells_and_warns_for_incomplete_tables(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage([[['Name', 'Wert'], ['Alpha\nBeta', '1']], [['Name', None], ['Alpha', '1']], [['Name', 'Wert'], ['(cid:42)', '1']]])])
        outcome = extract_simple_tables(self.source)
        self.assertEqual(outcome.tables[0].rows, (("Alpha<br>Beta", "1"),))
        self.assertEqual(
            [(warning.code, warning.page.page_number) for warning in outcome.warnings],
            [("UNSUPPORTED_TABLE_STRUCTURE", 1)],
        )

    @patch("app.table_extract.pdfplumber.open")
    def test_merges_adjacent_pages_with_the_same_table_header(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([
            _FakePage([[['Name', 'Wert'], ['Alpha', '1']]]),
            _FakePage([[['Name', 'Wert'], ['Beta', '2']]]),
        ])

        outcome = extract_simple_tables(self.source)

        self.assertEqual(len(outcome.tables), 1)
        self.assertEqual(outcome.tables[0].rows, (("Alpha", "1"), ("Beta", "2")))
