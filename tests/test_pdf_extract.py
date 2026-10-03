"""Unit-Tests für seitenweise, positionsgestützte PDF-Textextraktion."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.pdf_extract import PdfExtractionError, extract_pdf_pages


class _FakePage:
    def __init__(self, words: list[dict[str, float | str]], width: float = 600, height: float = 800, curves: list[dict[str, float | bool]] | None = None, table_bboxes: list[tuple[float, float, float, float]] | None = None) -> None:
        self.words = words
        self.width = width
        self.height = height
        self.curves = curves or []
        self.table_bboxes = table_bboxes or []

    def extract_words(self, **_kwargs):
        return self.words

    def find_tables(self):
        return [type("_FakeTable", (), {"bbox": bbox})() for bbox in self.table_bboxes]


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


def _word(text: str, x0: float, top: float, width: float = 20, size: float | None = None) -> dict[str, float | str]:
    word: dict[str, float | str] = {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 10}
    if size is not None:
        word["size"] = size
    return word


class PdfExtractTests(unittest.TestCase):
    """Prüft Seitenbezug und konservative Leseordnung ohne echte Fixture-PDF."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.source_path = Path(self.directory.name) / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self.directory.cleanup()

    @patch("app.pdf_extract.pdfplumber.open")
    def test_extracts_each_page_in_top_to_bottom_order(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf(
            [
                _FakePage([_word("zweite", 80, 40), _word("Zeile", 150, 40), _word("erste", 80, 20)]),
                _FakePage([]),
            ]
        )

        pages = extract_pdf_pages(self.source_path)

        self.assertEqual([(page.page_number, page.text) for page in pages], [(1, "erste\nzweite Zeile"), (2, "")])
        self.assertEqual(pages[0].word_count, 3)
        self.assertEqual(pages[1].word_count, 0)
        self.assertEqual(pages[0].column_count, 1)

    @patch("app.pdf_extract.pdfplumber.open")
    def test_reads_clearly_separated_columns_left_before_right(self, open_pdf) -> None:
        words = [
            _word("Titel", 280, 20, 40),
            _word("L1", 70, 100), _word("R1", 370, 100),
            _word("L2", 70, 120), _word("R2", 370, 120),
            _word("L3", 70, 140), _word("R3", 370, 140),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.text, "Titel\n\nL1\nL2\nL3\nR1\nR2\nR3")
        self.assertEqual(page.column_count, 2)

    @patch("app.pdf_extract.pdfplumber.open")
    def test_keeps_single_column_prose_crossing_the_page_midpoint_intact(self, open_pdf) -> None:
        words = [
            _word("Ein", 70, 100), _word("langer", 110, 100), _word("Satz", 170, 100), _word("über", 250, 100), _word("die", 295, 100), _word("Mitte.", 325, 100),
            _word("Noch", 70, 120), _word("eine", 120, 120), _word("normale", 180, 120), _word("Zeile", 270, 120), _word("mit", 335, 120), _word("Text.", 380, 120),
            _word("Dritte", 70, 140), _word("Zeile", 145, 140), _word("ohne", 215, 140), _word("Spaltengasse.", 280, 140),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.column_count, 1)
        self.assertEqual(
            page.text,
            "Ein langer Satz über die Mitte.\nNoch eine normale Zeile mit Text.\nDritte Zeile ohne Spaltengasse.",
        )

    @patch("app.pdf_extract.pdfplumber.open")
    def test_exposes_large_typographic_lines_as_heading_levels(self, open_pdf) -> None:
        words = [
            _word("Titel", 70, 20, size=20),
            _word("Abschnitt", 70, 60, size=16),
            _word("Fließtext", 70, 100, size=10), _word("beginnt.", 140, 100, size=10),
            _word("Er", 70, 120, size=10), _word("setzt", 100, 120, size=10), _word("sich", 150, 120, size=10), _word("fort.", 190, 120, size=10),
            _word("Noch", 70, 140, size=10), _word("eine", 120, 140, size=10), _word("Zeile.", 180, 140, size=10),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.heading_levels, (("Titel", 1), ("Abschnitt", 2)))

    @patch("app.pdf_extract.pdfplumber.open")
    def test_does_not_classify_a_large_equation_as_a_heading(self, open_pdf) -> None:
        words = [
            _word("Titel", 70, 20, size=20),
            _word("p(x)", 70, 60, size=16), _word("=", 130, 60, size=16), _word("x", 150, 60, size=16),
            _word("Fließtext", 70, 100, size=10), _word("beginnt.", 140, 100, size=10),
            _word("Er", 70, 120, size=10), _word("setzt", 100, 120, size=10), _word("sich", 150, 120, size=10), _word("fort.", 190, 120, size=10),
            _word("Noch", 70, 140, size=10), _word("eine", 120, 140, size=10), _word("Zeile.", 180, 140, size=10),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.heading_levels, (("Titel", 1),))

    @patch("app.pdf_extract.pdfplumber.open")
    def test_exposes_a_small_filled_vector_left_of_a_line_as_a_bullet(self, open_pdf) -> None:
        words = [_word("Erster", 90, 100), _word("Punkt", 150, 100)]
        curves = [{"x0": 70, "x1": 74, "top": 103, "bottom": 107, "fill": True}]
        open_pdf.return_value = _FakePdf([_FakePage(words, curves=curves)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.bullet_lines, ("Erster Punkt",))

    @patch("app.pdf_extract.pdfplumber.open")
    def test_reconstructs_a_centered_state_formula_only_with_evidenced_scripts(self, open_pdf) -> None:
        words = [
            _word("Das", 70, 60, size=10), _word("Modell", 110, 60, size=10),
            _word("berechnet:", 180, 60, size=10),
            _word("P(x", 253, 100, 19, 11.2),
            _word("t+1", 272, 104, 13, 7.9),
            _word("∣", 288, 100, 3, 11.2),
            _word("x", 294, 100, 6, 11.2),
            _word("1", 300, 104, 4, 7.9),
            _word(",…,x", 305, 100, 31, 11.2),
            _word("t", 336, 104, 3, 7.9),
            _word(")", 339, 100, 4, 11.2),
            _word("Fortsetzung.", 70, 150, size=10),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(
            page.display_formulas,
            (("P(x t+1 ∣ x 1 ,…,x t )", r"P(x^{t+1} \mid x_{1}, \ldots, x_{t})"),),
        )

    @patch("app.pdf_extract.pdfplumber.open")
    def test_does_not_reconstruct_scripts_without_smaller_offset_glyphs(self, open_pdf) -> None:
        words = [
            _word("P(x", 253, 100, 19, 11.2), _word("t+1", 272, 100, 13, 11.2),
            _word("∣", 288, 100, 3, 11.2), _word("x", 294, 100, 6, 11.2),
            _word("1", 300, 100, 4, 11.2), _word(",…,x", 305, 100, 31, 11.2),
            _word("t", 336, 100, 3, 11.2), _word(")", 339, 100, 4, 11.2),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.display_formulas, ())

    @patch("app.pdf_extract.pdfplumber.open")
    def test_exposes_centered_unreconstructed_math_layout_as_a_quality_candidate(self, open_pdf) -> None:
        words = [
            _word("Text", 255, 100, 24, 11.2), _word("→", 284, 100, 8, 11.2),
            _word("Vektor", 298, 100, 45, 11.2),
            _word("Ein", 70, 140), _word("Satz", 110, 140), _word("mit", 160, 140),
            _word("→", 195, 140), _word("bleibt", 210, 140), _word("Prosa.", 270, 140),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.formula_candidate_lines, ("Text → Vektor",))

    @patch("app.pdf_extract.pdfplumber.open")
    def test_excludes_detected_table_rows_from_multi_column_evidence(self, open_pdf) -> None:
        words = [
            _word("Einleitung", 70, 80),
            _word("A1", 70, 140), _word("B1", 370, 140),
            _word("A2", 70, 160), _word("B2", 370, 160),
            _word("A3", 70, 180), _word("B3", 370, 180),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words, table_bboxes=[(50, 130, 550, 190)])])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.column_count, 1)
        self.assertEqual(page.table_lines, ("A1 B1", "A2 B2", "A3 B3"))

    @patch("app.pdf_extract.pdfplumber.open")
    def test_keeps_header_and_footer_outside_two_column_content(self, open_pdf) -> None:
        words = [
            _word("Journal", 70, 20), _word("Page", 490, 20), _word("1", 530, 20),
            _word("Article", 70, 55),
            _word("L1", 70, 120), _word("R1", 370, 120),
            _word("L2", 70, 140), _word("R2", 370, 140),
            _word("L3", 70, 160), _word("R3", 370, 160),
            _word("Footer", 70, 760),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(
            page.text,
            "Journal Page 1\n\nArticle\n\nL1\nL2\nL3\nR1\nR2\nR3\n\nFooter",
        )
        self.assertEqual(page.column_count, 2)

    @patch("app.pdf_extract.pdfplumber.open")
    def test_preserves_a_clear_vertical_gap_as_paragraph_boundary(self, open_pdf) -> None:
        words = [
            _word("Erster", 70, 120), _word("Satz.", 130, 120),
            _word("Gleicher", 70, 136), _word("Absatz.", 140, 136),
            _word("Neuer", 70, 190), _word("Absatz.", 130, 190),
        ]
        open_pdf.return_value = _FakePdf([_FakePage(words)])

        page = extract_pdf_pages(self.source_path)[0]

        self.assertEqual(page.text, "Erster Satz.\nGleicher Absatz.\n\nNeuer Absatz.")

    def test_orders_the_versioned_scientific_fixture_with_header_and_footer(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "scientific-two-column.pdf"

        page = extract_pdf_pages(fixture)[0]

        self.assertEqual(page.column_count, 2)
        self.assertLess(page.text.index("Synthetic Methods Note Page 1"), page.text.index("Abstract"))
        self.assertLess(page.text.index("A header, two columns"), page.text.index("3 Results"))
        self.assertLess(page.text.index("4 Discussion"), page.text.index("Synthetic fixture - not a published work"))

    def test_rejects_missing_source(self) -> None:
        with self.assertRaises(PdfExtractionError):
            extract_pdf_pages(self.source_path.with_name("fehlt.pdf"))


if __name__ == "__main__":
    unittest.main()
