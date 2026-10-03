"""Tests für die lokale Extraktion nativer PDF-Link-Annotationen."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.native_pdf_links import extract_native_pdf_links, link_display_label


class _FakePage:
    def __init__(self, annots: list[dict], words: list[dict] | None = None, height: float = 800) -> None:
        self.annots = annots
        self.words = words or []
        self.height = height

    def extract_words(self, **_kwargs):
        return self.words


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


def _annotation(uri: object, *, x0: float = 10, y0: float = 20, x1: float = 30, y1: float = 40) -> dict:
    return {"uri": uri, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "data": {"Subtype": "Link"}}


def _word(text: str, x0: float, top: float, x1: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "top": top, "x1": x1, "bottom": bottom}


class NativePdfLinkExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.source_path = Path(self.directory.name) / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self.directory.cleanup()

    @patch("app.native_pdf_links.pdfplumber.open")
    def test_extracts_only_external_https_links_with_pdf_coordinates(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([
            _FakePage([_annotation("https://example.org/qr")]),
            _FakePage([_annotation("https://example.org/next", x0=1.5, y0=2.5, x1=3.5, y1=4.5)]),
        ])

        outcome = extract_native_pdf_links(self.source_path)

        self.assertEqual([(link.target_url, link.page.page_number) for link in outcome.links], [
            ("https://example.org/qr", 1),
            ("https://example.org/next", 2),
        ])
        rectangle = outcome.links[1].annotation_rect
        self.assertEqual((rectangle.left, rectangle.bottom, rectangle.right, rectangle.top), (1.5, 2.5, 3.5, 4.5))
        self.assertEqual(outcome.warnings, ())

    @patch("app.native_pdf_links.pdfplumber.open")
    def test_assigns_title_only_for_one_of_the_supported_geometric_patterns(self, open_pdf) -> None:
        below = _annotation("https://example.org/below", y0=700, y1=740)
        above_right = _annotation("https://example.org/above-right", y0=650, y1=700)
        open_pdf.return_value = _FakePdf([_FakePage(
            [below, above_right],
            [
                _word("Potenzgesetze", 12, 102, 28, 112),
                _word("Fakultäten", 42, 84, 75, 94),
                _word("kürzen", 77, 84, 105, 94),
            ],
        )])

        outcome = extract_native_pdf_links(self.source_path)

        self.assertEqual([link.visible_title for link in outcome.links], ["Potenzgesetze", "Fakultäten kürzen"])

    @patch("app.native_pdf_links.pdfplumber.open")
    def test_keeps_title_empty_for_ambiguous_geometry_and_uses_neutral_label(self, open_pdf) -> None:
        link = _annotation("https://example.org/", y0=700, y1=740)
        open_pdf.return_value = _FakePdf([_FakePage(
            [link],
            [_word("Erster Titel", 12, 102, 38, 110), _word("Zweiter Titel", 12, 117, 38, 127)],
        )])

        outcome = extract_native_pdf_links(self.source_path)

        self.assertIsNone(outcome.links[0].visible_title)
        self.assertEqual(link_display_label(outcome.links[0]), "Externer Link auf Seite 1")

    @patch("app.native_pdf_links.pdfplumber.open")
    def test_rejoins_a_directly_visible_line_end_hyphen_in_a_title(self, open_pdf) -> None:
        link = _annotation("https://example.org/", y0=700, y1=740)
        open_pdf.return_value = _FakePdf([_FakePage(
            [link],
            [_word("Logarithmus-", 12, 102, 28, 110), _word("gesetze", 12, 114, 28, 124)],
        )])

        outcome = extract_native_pdf_links(self.source_path)

        self.assertEqual(outcome.links[0].visible_title, "Logarithmusgesetze")

    @patch("app.native_pdf_links.pdfplumber.open")
    def test_warns_for_unsafe_and_local_targets_without_network_access(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage([
            _annotation("http://example.org"),
            _annotation("file:///C:/intern"),
            _annotation("https://localhost/service"),
            _annotation("https://127.0.0.1/service"),
            _annotation("https://example.org/with space"),
        ])])

        outcome = extract_native_pdf_links(self.source_path)

        self.assertEqual(outcome.links, ())
        self.assertEqual(
            [(warning.code, warning.page.page_number if warning.page else None) for warning in outcome.warnings],
            [
                ("NATIVE_PDF_LINK_UNSAFE_URL", 1),
                ("NATIVE_PDF_LINK_LOCAL_TARGET", 1),
            ],
        )
        self.assertIn("3 native PDF-Link-Annotation(en)", outcome.warnings[0].message)
        self.assertIn("2 native PDF-Link-Annotation(en)", outcome.warnings[1].message)

    @patch("app.native_pdf_links.pdfplumber.open")
    def test_warns_for_malformed_link_rectangle_and_ignores_non_link_annotations(self, open_pdf) -> None:
        malformed = _annotation("https://example.org/")
        malformed["x1"] = malformed["x0"]
        open_pdf.return_value = _FakePdf([_FakePage([
            malformed,
            {"data": {"Subtype": "Link"}},
            {"data": {"Subtype": "Text"}, "contents": "Notiz"},
        ])])

        outcome = extract_native_pdf_links(self.source_path)

        self.assertEqual(outcome.links, ())
        self.assertEqual([(warning.code, warning.page.page_number) for warning in outcome.warnings], [
            ("NATIVE_PDF_LINK_INVALID_ANNOTATION", 1),
            ("NATIVE_PDF_LINK_UNSAFE_URL", 1),
        ])


if __name__ == "__main__":
    unittest.main()
