"""Unit-Tests für Markdown-Seitenmarker."""

from __future__ import annotations

import unittest

from pathlib import PurePosixPath

from app.markdown_writer import MarkdownRenderingError, format_page_marker, render_document, render_pages
from app.models import Asset, AssetKind, BlockKind, DocumentBlock, DocumentTable, NativePdfLink, PageMarker, PageReference, PdfAnnotationRect
from app.pdf_extract import ExtractedPage


class MarkdownWriterTests(unittest.TestCase):
    """Prüft den stabilen und nachvollziehbaren Seitenmarker-Vertrag."""

    def test_formats_invisible_page_marker(self) -> None:
        marker = format_page_marker(PageMarker(PageReference(page_number=12)))

        self.assertEqual(marker, "<!-- doctomd:page=12 -->")

    def test_renders_each_page_with_its_original_page_marker(self) -> None:
        markdown = render_pages(
            (
                ExtractedPage(page_number=1, text="Erste Seite", word_count=2, column_count=1),
                ExtractedPage(page_number=2, text="", word_count=0, column_count=1),
                ExtractedPage(page_number=3, text="Dritte Seite", word_count=2, column_count=2),
            )
        )

        self.assertEqual(
            markdown,
            "<!-- doctomd:page=1 -->\nErste Seite\n\n"
            "<!-- doctomd:page=2 -->\n\n"
            "<!-- doctomd:page=3 -->\nDritte Seite",
        )

    def test_rejects_duplicate_or_descending_page_numbers(self) -> None:
        pages = (
            ExtractedPage(page_number=2, text="Zweite", word_count=1, column_count=1),
            ExtractedPage(page_number=2, text="Doppelt", word_count=1, column_count=1),
        )

        with self.assertRaises(MarkdownRenderingError):
            render_pages(pages)

    def test_renders_image_reference_with_page_and_caption(self) -> None:
        asset = Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.jpg"), PageReference(1), caption="Bedienblende", description_path=PurePosixPath("Quelle.assets/page-001-figure-01-description.md"))
        markdown = render_document((ExtractedPage(1, "", 0, 1),), (), (asset,))
        self.assertEqual(markdown, "<!-- doctomd:page=1 -->\n<!-- doctomd:asset=page-001-figure-01 page=1 -->\n![Bedienblende](Quelle.assets/page-001-figure-01.jpg)\n\n[Bildbeschreibung bearbeiten](Quelle.assets/page-001-figure-01-description.md)")

    def test_renders_simple_table_with_page_reference(self) -> None:
        table = DocumentTable("page-001-table-01", PageReference(1), ("Name", "Wert"), (("Alpha", "1"),))
        markdown = render_document((ExtractedPage(1, "", 0, 1),), (), tables=(table,))
        self.assertEqual(markdown, "<!-- doctomd:page=1 -->\n<!-- doctomd:table=page-001-table-01 page=1 -->\n| Name | Wert |\n| --- | --- |\n| Alpha | 1 |")

    def test_continues_an_ordered_list_across_page_markers(self) -> None:
        pages = (ExtractedPage(1, "", 0, 1), ExtractedPage(2, "", 0, 1))
        blocks = (
            DocumentBlock(BlockKind.LIST_ITEM, "Erster", PageReference(1), ordered=True),
            DocumentBlock(BlockKind.LIST_ITEM, "Zweiter", PageReference(1), ordered=True),
            DocumentBlock(BlockKind.LIST_ITEM, "Dritter", PageReference(2), ordered=True),
        )

        markdown = render_document(pages, blocks)

        self.assertEqual(markdown, "<!-- doctomd:page=1 -->\n1. Erster\n2. Zweiter\n\n<!-- doctomd:page=2 -->\n3. Dritter")

    def test_keeps_a_wrapped_list_item_open_across_a_page_marker(self) -> None:
        pages = (ExtractedPage(1, "", 0, 1), ExtractedPage(2, "", 0, 1))
        blocks = (
            DocumentBlock(BlockKind.LIST_ITEM, "Beginn", PageReference(1)),
            DocumentBlock(BlockKind.PARAGRAPH, "Fortsetzung.", PageReference(2)),
            DocumentBlock(BlockKind.LIST_ITEM, "Nächster Punkt", PageReference(2)),
        )

        markdown = render_document(pages, blocks)

        self.assertEqual(
            markdown,
            "<!-- doctomd:page=1 -->\n- Beginn\n  <!-- doctomd:page=2 -->\n  Fortsetzung.\n- Nächster Punkt",
        )

    def test_renders_local_native_links_after_the_page_chapter_content(self) -> None:
        page = ExtractedPage(10, "", 0, 1)
        blocks = (
            DocumentBlock(BlockKind.HEADING, "Rechengesetze", PageReference(10), heading_level=3),
            DocumentBlock(BlockKind.PARAGRAPH, "Lokaler Kapitelinhalt.", PageReference(10)),
        )
        links = (
            NativePdfLink("https://example.org/potenz", PageReference(10), PdfAnnotationRect(1, 2, 3, 4), visible_title="Potenzgesetze"),
            NativePdfLink("https://example.org/ohne-titel", PageReference(10), PdfAnnotationRect(4, 5, 6, 7)),
        )

        markdown = render_document((page,), blocks, native_pdf_links=links)

        self.assertEqual(
            markdown,
            "<!-- doctomd:page=10 -->\n### Rechengesetze\n\nLokaler Kapitelinhalt.\n\n"
            "<!-- doctomd:native-pdf-links page=10 -->\n**Lokale PDF-Links**\n"
            "- [Potenzgesetze](<https://example.org/potenz>)\n"
            "- [Externer Link auf Seite 10](<https://example.org/ohne-titel>)",
        )

    def test_keeps_native_links_in_a_chapter_that_continues_across_pages(self) -> None:
        pages = (ExtractedPage(9, "", 0, 1), ExtractedPage(10, "", 0, 1))
        blocks = (
            DocumentBlock(BlockKind.HEADING, "Rechengesetze", PageReference(9), heading_level=3),
            DocumentBlock(BlockKind.PARAGRAPH, "Kapitelfortsetzung auf Seite zehn.", PageReference(10)),
        )
        links = (
            NativePdfLink(
                "https://example.org/potenz",
                PageReference(10),
                PdfAnnotationRect(1, 2, 3, 4),
                visible_title="Potenzgesetze",
            ),
        )

        markdown = render_document(pages, blocks, native_pdf_links=links)

        self.assertLess(markdown.index("### Rechengesetze"), markdown.index("<!-- doctomd:page=10 -->"))
        self.assertLess(markdown.index("Kapitelfortsetzung auf Seite zehn."), markdown.index("native-pdf-links page=10"))
        self.assertIn("[Potenzgesetze](<https://example.org/potenz>)", markdown)


if __name__ == "__main__":
    unittest.main()
