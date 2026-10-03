"""Unit-Tests für verlustarme Textnormalisierung."""

from __future__ import annotations

import unittest

from app.models import BlockKind, DocumentBlock, PageReference
from app.text_normalization import normalize_blocks, normalize_text


class TextNormalizationTests(unittest.TestCase):
    """Prüft sichere Umformungen und sichtbare Unsicherheiten."""

    def test_normalizes_line_endings_and_canonical_unicode(self) -> None:
        result = normalize_text("A\r\na\u0308rger", page=PageReference(2))

        self.assertEqual(result.text, "A\närger")
        self.assertEqual(result.transformations, ("line_endings_to_lf", "unicode_nfc"))
        self.assertEqual(result.warnings, ())

    def test_preserves_ambiguous_characters_and_reports_them(self) -> None:
        original = "Wort\u00adtrennung und Anwen-\ndung mit \ufffd"

        result = normalize_text(original, page=PageReference(5))

        self.assertEqual(result.text, original)
        self.assertEqual(
            [warning.code for warning in result.warnings],
            [
                "TEXT_REPLACEMENT_CHARACTER",
                "SOFT_HYPHEN_PRESERVED",
                "POSSIBLE_HYPHENATION_PRESERVED",
            ],
        )
        self.assertTrue(all(warning.page == PageReference(5) for warning in result.warnings))

    def test_normalizes_blocks_without_losing_structure(self) -> None:
        block = DocumentBlock(
            kind=BlockKind.PARAGRAPH,
            text="e\u0308rster Absatz",
            page=PageReference(3),
        )

        blocks, warnings = normalize_blocks((block,))

        self.assertEqual(blocks[0].text, "ërster Absatz")
        self.assertEqual(blocks[0].kind, BlockKind.PARAGRAPH)
        self.assertEqual(blocks[0].page, PageReference(3))
        self.assertEqual(warnings, ())

    def test_reports_a_hard_hyphen_separated_by_block_joining(self) -> None:
        result = normalize_text("Anwen- dung", page=PageReference(6))

        self.assertEqual(result.text, "Anwen- dung")
        self.assertEqual([warning.code for warning in result.warnings], ["POSSIBLE_HYPHENATION_PRESERVED"])

    def test_does_not_mistake_a_spaced_dash_for_hyphenation(self) -> None:
        result = normalize_text("Fixture - nicht veröffentlicht", page=PageReference(6))

        self.assertEqual(result.warnings, ())


if __name__ == "__main__":
    unittest.main()
