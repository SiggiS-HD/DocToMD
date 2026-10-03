"""Lokale Regression für die vom Benutzer bereitgestellte Mathe1-Referenzquelle."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

from app.native_pdf_links import extract_native_pdf_links


MATHE1_PDF_ENVIRONMENT_VARIABLE = "DOCTOMD_MATHE1_PDF"
_configured_path = os.environ.get(MATHE1_PDF_ENVIRONMENT_VARIABLE)
MATHE1_PDF = Path(_configured_path) if _configured_path else None


@unittest.skipUnless(
    MATHE1_PDF is not None and MATHE1_PDF.is_file(),
    "DOCTOMD_MATHE1_PDF verweist nicht auf eine verfügbare lokale Referenzquelle.",
)
class Mathe1NativePdfLinkRegressionTests(unittest.TestCase):
    def test_extracts_the_four_page_ten_qr_targets_with_geometrically_proven_titles(self) -> None:
        assert MATHE1_PDF is not None
        outcome = extract_native_pdf_links(MATHE1_PDF)
        page_ten_links = tuple(link for link in outcome.links if link.page.page_number == 10)

        self.assertEqual(
            [(link.target_url, link.visible_title) for link in page_ten_links],
            [
                ("https://stdy.help/r/f974d88cbb", "Potenzgesetze"),
                ("https://stdy.help/r/cc81f53385", "Wurzelgesetze"),
                ("https://stdy.help/r/1b4c0e1047", "Logarithmusgesetze, ab 1:02"),
                ("https://stdy.help/r/9b39020f59", "Fakultäten kürzen"),
            ],
        )
        self.assertTrue(
            all(link.annotation_rect.left < link.annotation_rect.right for link in page_ten_links)
        )
        self.assertTrue(
            all(link.annotation_rect.bottom < link.annotation_rect.top for link in page_ten_links)
        )


if __name__ == "__main__":
    unittest.main()
