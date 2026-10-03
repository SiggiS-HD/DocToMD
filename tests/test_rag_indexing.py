"""Tests für die konservative RAG-Indexempfehlung."""

from __future__ import annotations

from pathlib import PurePosixPath
import unittest

from app.rag_indexing import recommend_markdown_for_rag


class RagIndexingTests(unittest.TestCase):
    def test_recommends_local_markdown_without_cloud_derivative(self) -> None:
        recommendation = recommend_markdown_for_rag(
            markdown_path=PurePosixPath("Quelle.md"),
            markdown="<!-- doctomd:page=1 -->\n# Titel\n\nText.",
        )

        self.assertEqual(recommendation["recommended_markdown_path"], "Quelle.md")
        self.assertEqual(recommendation["selection_reason"], "cloud_derivative_not_available")

    def test_recommends_validated_cloud_when_it_has_more_structure(self) -> None:
        recommendation = recommend_markdown_for_rag(
            markdown_path=PurePosixPath("Quelle.md"),
            markdown="<!-- doctomd:page=1 -->\n# Titel\n\nA = [a_ij]\n(cid:42)",
            cloud_markdown_path=PurePosixPath("Quelle.cloud.md"),
            cloud_markdown="<!-- doctomd:page=1 -->\n# Titel\n\n$$A = [a_{ij}]$$\n\n<!-- doctomd:table=page-001-table-01 page=1 -->\n| A | B |\n| --- | --- |\n| 1 | 2 |",
        )

        self.assertEqual(recommendation["recommended_markdown_path"], "Quelle.cloud.md")
        self.assertEqual(recommendation["selection_reason"], "validated_cloud_has_more_structure")
        self.assertEqual(recommendation["candidates"][1]["table_count"], 1)
        self.assertEqual(recommendation["candidates"][1]["display_formula_count"], 1)

    def test_keeps_local_markdown_when_cloud_structure_is_not_better(self) -> None:
        recommendation = recommend_markdown_for_rag(
            markdown_path=PurePosixPath("Quelle.md"),
            markdown="<!-- doctomd:page=1 -->\n# Titel\n\n<!-- doctomd:table=page-001-table-01 page=1 -->\n| A | B |",
            cloud_markdown_path=PurePosixPath("Quelle.cloud.md"),
            cloud_markdown="<!-- doctomd:page=1 -->\n# Titel\n\nText.",
        )

        self.assertEqual(recommendation["recommended_markdown_path"], "Quelle.md")
        self.assertEqual(recommendation["selection_reason"], "local_structure_is_equal_or_better")

    def test_counts_gfm_tables_without_a_doctomd_marker(self) -> None:
        recommendation = recommend_markdown_for_rag(
            markdown_path=PurePosixPath("Quelle.md"),
            markdown="<!-- doctomd:page=1 -->\n# Titel\n\nText.",
            cloud_markdown_path=PurePosixPath("Quelle.cloud.md"),
            cloud_markdown="<!-- doctomd:page=1 -->\n# Titel\n\n| Name | Wert |\n| --- | ---: |\n| Alpha | 1 |",
        )

        self.assertEqual(recommendation["candidates"][1]["table_count"], 1)
        self.assertEqual(recommendation["recommended_markdown_path"], "Quelle.cloud.md")


if __name__ == "__main__":
    unittest.main()
