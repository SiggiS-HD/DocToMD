"""Tests für die rein lokale Batch-Planung mathematischer Dokumente."""

from __future__ import annotations

import unittest

from app.math_batch_planning import BatchPlanningError, plan_math_cloud_batches


def _pages(*contents: str) -> str:
    return "\n\n".join(
        f"<!-- doctomd:page={page_number} -->\n{content}"
        for page_number, content in enumerate(contents, start=1)
    )


class MathBatchPlanningTests(unittest.TestCase):
    def test_limits_batches_to_six_contiguous_pages(self) -> None:
        plan = plan_math_cloud_batches(markdown=_pages(*("Text" for _ in range(13))))

        self.assertEqual([batch.page_numbers for batch in plan.batches], [
            (1, 2, 3, 4, 5, 6), (7, 8, 9, 10, 11, 12), (13,),
        ])
        self.assertEqual(plan.batches[0].batch_id, "batch-001-pages-001-006")
        self.assertEqual(plan.to_contract_dict()["max_dense_pages_per_batch"], 1)

    def test_prefers_h1_or_h2_chapter_boundaries(self) -> None:
        plan = plan_math_cloud_batches(markdown=_pages(
            "# Erstes Kapitel\nText", "Text", "Text", "## Neues Kapitel\nText", "Text",
        ))

        self.assertEqual([batch.page_numbers for batch in plan.batches], [(1, 2, 3), (4, 5)])
        self.assertEqual(plan.batches[1].chapter_start_page, 4)

    def test_ignores_running_headers_and_table_of_contents_headings(self) -> None:
        plan = plan_math_cloud_batches(markdown=_pages(
            "# Kapitel Eins\nText", "## Kapitel Eins 2\nText", "# Inhalt . . . 9\nText", "# 4 Kapitel Zwei\nText", "# Kapitel Zwei\nText",
        ))

        self.assertEqual([batch.page_numbers for batch in plan.batches], [(1, 2, 3, 4), (5,)])

    def test_keeps_dense_formula_or_table_pages_in_separate_batches(self) -> None:
        plan = plan_math_cloud_batches(markdown=_pages(
            "Text", "$$a = b$$\n\n$$c = d$$", "| A | B |\n| --- | --- |\n| 1 | 2 |", "Text",
        ))

        self.assertEqual([batch.page_numbers for batch in plan.batches], [(1, 2), (3, 4)])
        self.assertEqual(plan.batches[0].dense_page_numbers, (2,))
        self.assertEqual(plan.batches[1].dense_page_numbers, (3,))

    def test_rejects_missing_or_noncanonical_page_markers(self) -> None:
        with self.assertRaises(BatchPlanningError):
            plan_math_cloud_batches(markdown="<!-- doctomd:page=1 -->\nText\n<!-- doctomd:page=3 -->\nText")


if __name__ == "__main__":
    unittest.main()
