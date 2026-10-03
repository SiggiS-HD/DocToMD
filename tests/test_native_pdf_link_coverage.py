"""Tests für die Vollständigkeit lokal ermittelter Native-PDF-Links."""

from __future__ import annotations

import unittest

from app.markdown_writer import render_native_pdf_links
from app.models import NativePdfLink, PageReference, PdfAnnotationRect
from app.native_pdf_link_coverage import NativePdfLinkCoverageError, verify_native_pdf_link_coverage


class NativePdfLinkCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.links = (
            NativePdfLink(
                "https://example.org/belegt",
                PageReference(2),
                PdfAnnotationRect(1, 2, 3, 4),
                visible_title="Belegter Titel",
            ),
            NativePdfLink(
                "https://example.org/neutral",
                PageReference(2),
                PdfAnnotationRect(5, 6, 7, 8),
            ),
        )

    def test_accepts_the_exact_local_page_list_once(self) -> None:
        markdown = "<!-- doctomd:page=2 -->\n\n" + render_native_pdf_links(self.links)

        verify_native_pdf_link_coverage(markdown=markdown, links=self.links)

    def test_rejects_a_missing_or_changed_local_page_list(self) -> None:
        markdown = "<!-- doctomd:page=2 -->\n\n" + render_native_pdf_links(self.links).replace(
            "https://example.org/neutral", "https://example.org/erfunden"
        )

        with self.assertRaisesRegex(NativePdfLinkCoverageError, "Seite 2"):
            verify_native_pdf_link_coverage(markdown=markdown, links=self.links)

    def test_rejects_duplicate_local_page_lists(self) -> None:
        rendered = render_native_pdf_links(self.links)

        with self.assertRaisesRegex(NativePdfLinkCoverageError, "2-mal statt genau einmal"):
            verify_native_pdf_link_coverage(markdown=f"{rendered}\n\n{rendered}", links=self.links)


if __name__ == "__main__":
    unittest.main()
