from __future__ import annotations

import unittest

from app.ocr_config import resolve_ocr_pages, validate_min_word_confidence


class OcrConfigTests(unittest.TestCase):
    def test_resolves_all_and_compact_page_ranges(self) -> None:
        self.assertEqual(resolve_ocr_pages("all", page_count=3), frozenset({1, 2, 3}))
        self.assertEqual(resolve_ocr_pages("1-2,4", page_count=4), frozenset({1, 2, 4}))

    def test_rejects_invalid_ranges_and_confidence(self) -> None:
        with self.assertRaises(ValueError): resolve_ocr_pages("0", page_count=2)
        with self.assertRaises(ValueError): validate_min_word_confidence(101)


if __name__ == "__main__":
    unittest.main()
