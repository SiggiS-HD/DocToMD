"""Tests für die lokale RAG-Folgebewertung."""

from __future__ import annotations

import unittest

from app.models import ConversionWarning, PageReference
from app.rag_readiness import assess_rag_readiness


class RagReadinessTests(unittest.TestCase):
    def test_marks_local_derivative_unsuitable_and_suggests_opt_in_paths(self) -> None:
        readiness = assess_rag_readiness(
            warnings=(
                ConversionWarning("UNREADABLE_PDF_GLYPHS", "Zeichen unklar.", page=PageReference(1)),
                ConversionWarning("MULTI_COLUMN_LAYOUT", "Mehrspaltig.", page=PageReference(1)),
                ConversionWarning("UNSUPPORTED_TABLE_STRUCTURE", "Tabelle unsicher.", page=PageReference(7)),
            ),
            rag_indexing={"recommended_markdown_path": "Quelle.md"},
        )

        self.assertEqual(readiness["status"], "local_not_suitable")
        self.assertFalse(readiness["local_derivative_suitable"])
        self.assertEqual(readiness["reasons"][0], {"code": "MULTI_COLUMN_LAYOUT", "count": 1, "pages": [1]})
        self.assertEqual([item["kind"] for item in readiness["suggested_next_steps"]], ["force_ocr", "cloud_document"])
        self.assertTrue(all(item["requires_explicit_opt_in"] for item in readiness["suggested_next_steps"]))
        self.assertEqual(readiness["recommended_next_step"]["kind"], "cloud_document")
        self.assertIn("nicht RAG-geeignet", readiness["recommended_next_step"]["message"])

    def test_marks_clean_local_derivative_ready(self) -> None:
        readiness = assess_rag_readiness(warnings=(), rag_indexing={"recommended_markdown_path": "Quelle.md"})

        self.assertEqual(readiness["status"], "ready")
        self.assertTrue(readiness["local_derivative_suitable"])
        self.assertEqual(readiness["suggested_next_steps"], [])
        self.assertEqual(readiness["recommended_next_step"]["kind"], "none")

    def test_marks_confirmed_multi_column_layout_unsuitable_for_local_rag(self) -> None:
        readiness = assess_rag_readiness(
            warnings=(ConversionWarning("MULTI_COLUMN_LAYOUT", "Mehrspaltig.", page=PageReference(1)),),
            rag_indexing={"recommended_markdown_path": "Quelle.md"},
        )

        self.assertEqual(readiness["status"], "local_not_suitable")
        self.assertFalse(readiness["local_derivative_suitable"])
        self.assertEqual(readiness["suggested_next_steps"][0]["kind"], "cloud_document")
        self.assertTrue(readiness["suggested_next_steps"][0]["requires_explicit_opt_in"])

    def test_marks_unreconstructed_display_math_as_a_cloud_candidate(self) -> None:
        readiness = assess_rag_readiness(
            warnings=(ConversionWarning("DISPLAY_FORMULA_LAYOUT_NOT_RECONSTRUCTED", "Formel unsicher.", page=PageReference(3)),),
            rag_indexing={"recommended_markdown_path": "Quelle.md"},
        )

        self.assertEqual(readiness["status"], "local_not_suitable")
        self.assertEqual(readiness["reasons"], [{"code": "DISPLAY_FORMULA_LAYOUT_NOT_RECONSTRUCTED", "count": 1, "pages": [3]}])
        self.assertEqual(readiness["recommended_next_step"]["kind"], "cloud_document")

    def test_marks_unstructured_ocr_layout_as_a_cloud_candidate(self) -> None:
        readiness = assess_rag_readiness(
            warnings=(ConversionWarning("OCR_LAYOUT_FALLBACK", "Layoutblock ohne Struktur.", page=PageReference(2)),),
            rag_indexing={"recommended_markdown_path": "Quelle.md"},
        )

        self.assertEqual(readiness["status"], "local_not_suitable")
        self.assertEqual(readiness["recommended_next_step"]["kind"], "cloud_document")

    def test_requires_review_when_cloud_is_recommended_after_local_blockers(self) -> None:
        readiness = assess_rag_readiness(
            warnings=(ConversionWarning("UNREADABLE_PDF_GLYPHS", "Zeichen unklar.", page=PageReference(1)),),
            rag_indexing={"recommended_markdown_path": "Quelle.cloud.md"},
        )

        self.assertEqual(readiness["status"], "review_required")
        self.assertEqual(readiness["suggested_next_steps"][0]["kind"], "review_recommended_derivative")
        self.assertEqual(readiness["recommended_next_step"]["kind"], "review_recommended_derivative")


if __name__ == "__main__":
    unittest.main()
