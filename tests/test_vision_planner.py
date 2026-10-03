"""Unit-Tests für die lokale, datensparsame Vision-Seitenauswahl."""

from __future__ import annotations

import unittest

from app.models import ConversionWarning, PageReference
from app.pdf_extract import ExtractedPage
from app.vision_config import VisionConfig, VisionMode, VisionProvider
from app.vision_planner import plan_vision_pages


class VisionPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = (
            ExtractedPage(1, "erste Seite", 2, 2),
            ExtractedPage(2, "zweite Seite", 2, 1),
            ExtractedPage(3, "dritte Seite", 2, 1),
        )

    def test_default_and_off_never_select_pages(self) -> None:
        self.assertEqual(plan_vision_pages(config=VisionConfig(), pages=self.pages, warnings=()).page_numbers, ())
        config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.OFF)
        self.assertEqual(plan_vision_pages(config=config, pages=self.pages, warnings=()).page_numbers, ())

    def test_auto_selects_only_pages_with_local_scientific_risks(self) -> None:
        config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.AUTO, model_id="gpt-5.6-terra")
        warnings = (
            ConversionWarning("MULTI_COLUMN_LAYOUT", "Spaltenrisiko", page=PageReference(1)),
            ConversionWarning("UNSUPPORTED_TABLE_STRUCTURE", "Tabellenrisiko", page=PageReference(3)),
            ConversionWarning("UNRELATED", "nicht relevant", page=PageReference(2)),
        )

        plan = plan_vision_pages(config=config, pages=self.pages, warnings=warnings)

        self.assertEqual(plan.page_numbers, (1, 3))

    def test_auto_selects_page_with_multiline_table_warning(self) -> None:
        config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.AUTO, model_id="gpt-5.6-terra")
        warnings = (ConversionWarning("MULTILINE_TABLE_CELLS", "Mehrzeilige Zelle", page=PageReference(2)),)

        plan = plan_vision_pages(config=config, pages=self.pages, warnings=warnings)

        self.assertEqual(plan.page_numbers, (2,))

    def test_force_selects_every_existing_page(self) -> None:
        config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.FORCE, model_id="gpt-5.6-terra")

        self.assertEqual(plan_vision_pages(config=config, pages=self.pages, warnings=()).page_numbers, (1, 2, 3))


if __name__ == "__main__":
    unittest.main()
