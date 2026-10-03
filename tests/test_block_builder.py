"""Unit-Tests für grundlegende strukturierte Markdown-Blöcke."""

from __future__ import annotations

import unittest

from app.block_builder import build_page_blocks
from app.markdown_writer import render_blocks
from app.models import BlockKind
from app.pdf_extract import ExtractedPage


class BlockBuilderTests(unittest.TestCase):
    """Prüft konservative Überschriften-, Absatz- und Listenerkennung."""

    def test_builds_headings_paragraphs_and_lists_with_page_reference(self) -> None:
        page = ExtractedPage(
            page_number=4,
            text=(
                "1 Einführung\n"
                "Dieser Absatz beginnt hier\n"
                "und endet hier.\n"
                "- Erster Punkt\n"
                "2. Zweiter Punkt\n"
                "2.1 Details\n"
                "Weiterer Absatz"
            ),
            word_count=18,
            column_count=1,
        )

        blocks = build_page_blocks(page)

        self.assertEqual([block.kind for block in blocks], [
            BlockKind.HEADING,
            BlockKind.PARAGRAPH,
            BlockKind.LIST_ITEM,
            BlockKind.LIST_ITEM,
            BlockKind.HEADING,
            BlockKind.PARAGRAPH,
        ])
        self.assertEqual(blocks[0].text, "1 Einführung")
        self.assertEqual(blocks[0].heading_level, 1)
        self.assertEqual(blocks[1].text, "Dieser Absatz beginnt hier und endet hier.")
        self.assertEqual(blocks[2].text, "Erster Punkt")
        self.assertFalse(blocks[2].ordered)
        self.assertEqual(blocks[3].text, "Zweiter Punkt")
        self.assertTrue(blocks[3].ordered)
        self.assertEqual(blocks[4].heading_level, 2)
        self.assertTrue(all(block.page.page_number == 4 for block in blocks))

    def test_recognizes_named_heading_without_rewriting_it(self) -> None:
        page = ExtractedPage(
            page_number=1,
            text="Abstract\nDer unveränderte Text.",
            word_count=4,
            column_count=1,
        )

        blocks = build_page_blocks(page)

        self.assertEqual(blocks[0].kind, BlockKind.HEADING)
        self.assertEqual(blocks[0].text, "Abstract")
        self.assertEqual(blocks[1].text, "Der unveränderte Text.")

    def test_recognizes_typographic_heading_levels_from_the_extraction(self) -> None:
        page = ExtractedPage(
            page_number=1,
            text="Dokumenttitel\nAbschnitt\nDer Text beginnt.",
            word_count=5,
            column_count=1,
            heading_levels=(("Dokumenttitel", 1), ("Abschnitt", 2)),
        )

        blocks = build_page_blocks(page)

        self.assertEqual([block.kind for block in blocks], [BlockKind.HEADING, BlockKind.HEADING, BlockKind.PARAGRAPH])
        self.assertEqual([block.heading_level for block in blocks[:2]], [1, 2])

    def test_renders_basic_blocks_as_markdown(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text="Abstract\nEin Satz.\n- Ein Punkt",
                word_count=5,
                column_count=1,
            )
        )

        self.assertEqual(render_blocks(blocks), "# Abstract\n\nEin Satz.\n\n- Ein Punkt")

    def test_renders_consecutive_ordered_items_without_blank_lines(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text="1. Erster Punkt\n1. Zweiter Punkt\n1. Dritter Punkt",
                word_count=9,
                column_count=1,
            )
        )

        self.assertEqual(render_blocks(blocks), "1. Erster Punkt\n2. Zweiter Punkt\n3. Dritter Punkt")

    def test_joins_unmarked_wrapped_lines_to_the_preceding_list_item(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text=(
                    "1. Erster Punkt mit Umbruch\n"
                    "und Fortsetzung.\n"
                    "2. Zweiter Punkt\n"
                    "mit Fortsetzung."
                ),
                word_count=12,
                column_count=1,
            )
        )

        self.assertEqual([block.kind for block in blocks], [BlockKind.LIST_ITEM, BlockKind.LIST_ITEM])
        self.assertEqual([block.text for block in blocks], [
            "Erster Punkt mit Umbruch und Fortsetzung.",
            "Zweiter Punkt mit Fortsetzung.",
        ])
        self.assertEqual(
            render_blocks(blocks),
            "1. Erster Punkt mit Umbruch und Fortsetzung.\n2. Zweiter Punkt mit Fortsetzung.",
        )

    def test_keeps_a_paragraph_after_an_explicit_list_gap_separate(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text="1. Ein Punkt\n\nEigenständiger Absatz.",
                word_count=5,
                column_count=1,
            )
        )

        self.assertEqual([block.kind for block in blocks], [BlockKind.LIST_ITEM, BlockKind.PARAGRAPH])

    def test_recognizes_a_graphic_pdf_bullet_and_its_wrapped_line(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text="Erster Punkt\nmit Fortsetzung.\nZweiter Punkt",
                word_count=6,
                column_count=1,
                bullet_lines=("Erster Punkt", "Zweiter Punkt"),
            )
        )

        self.assertEqual([block.kind for block in blocks], [BlockKind.LIST_ITEM, BlockKind.LIST_ITEM])
        self.assertEqual([block.ordered for block in blocks], [False, False])
        self.assertEqual(render_blocks(blocks), "- Erster Punkt mit Fortsetzung.\n- Zweiter Punkt")

    def test_omits_table_text_that_is_rendered_as_a_separate_table(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text="Einleitung\nSpalte A Spalte B\nWeiterer Text",
                word_count=6,
                column_count=1,
                table_lines=("Spalte A Spalte B",),
            )
        )

        self.assertEqual([block.text for block in blocks], ["Einleitung", "Weiterer Text"])

    def test_keeps_a_verified_display_formula_separate_from_surrounding_prose(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=2,
                text="Das Modell berechnet dann:\nP(x t+1 ∣ x 1 ,…,x t )\nund könnte fortsetzen.",
                word_count=12,
                column_count=1,
                display_formulas=(("P(x t+1 ∣ x 1 ,…,x t )", r"P(x^{t+1} \mid x_{1}, \ldots, x_{t})"),),
            )
        )

        self.assertEqual([block.text for block in blocks], [
            "Das Modell berechnet dann:",
            r"$$P(x^{t+1} \mid x_{1}, \ldots, x_{t})$$",
            "und könnte fortsetzen.",
        ])

    def test_joins_an_explicit_soft_hyphen_at_a_line_break(self) -> None:
        blocks = build_page_blocks(
            ExtractedPage(
                page_number=1,
                text="Abschlie\u00ad\nßend folgt der Satz.",
                word_count=4,
                column_count=1,
            )
        )

        self.assertEqual(blocks[0].text, "Abschließend folgt der Satz.")


if __name__ == "__main__":
    unittest.main()
