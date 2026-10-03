"""Tests für den versionierten Strukturvertrag nativer PDF-Links."""

from __future__ import annotations

import math
import unittest

from app.models import (
    NATIVE_PDF_LINK_SCHEMA_VERSION,
    NativePdfLink,
    NativePdfLinkSource,
    PageReference,
    PdfAnnotationRect,
)


class NativePdfLinkContractTests(unittest.TestCase):
    def test_serializes_locally_proven_link_with_optional_visible_title(self) -> None:
        link = NativePdfLink(
            target_url="https://example.org/potenzgesetze",
            page=PageReference(10),
            annotation_rect=PdfAnnotationRect(left=72.0, bottom=120.5, right=108.0, top=156.5),
            visible_title="Potenzgesetze",
        )

        self.assertEqual(NATIVE_PDF_LINK_SCHEMA_VERSION, "1.0")
        self.assertEqual(
            link.to_contract_dict(),
            {
                "target_url": "https://example.org/potenzgesetze",
                "page": {"page_number": 10},
                "annotation_rect": {"left": 72.0, "bottom": 120.5, "right": 108.0, "top": 156.5},
                "source": "native_pdf_link_annotation",
                "visible_title": "Potenzgesetze",
            },
        )

    def test_omits_title_when_no_visible_text_was_proven(self) -> None:
        link = NativePdfLink(
            target_url="https://example.org/",
            page=PageReference(1),
            annotation_rect=PdfAnnotationRect(1, 2, 3, 4),
            source=NativePdfLinkSource.NATIVE_PDF_LINK_ANNOTATION,
        )

        self.assertNotIn("visible_title", link.to_contract_dict())

    def test_rejects_empty_url_and_non_positive_or_non_finite_rectangles(self) -> None:
        with self.assertRaises(ValueError):
            NativePdfLink(" ", PageReference(1), PdfAnnotationRect(1, 2, 3, 4))
        with self.assertRaises(ValueError):
            PdfAnnotationRect(3, 2, 3, 4)
        with self.assertRaises(ValueError):
            PdfAnnotationRect(1, 2, math.inf, 4)


if __name__ == "__main__":
    unittest.main()
