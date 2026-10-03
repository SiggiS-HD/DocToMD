"""Tests für die sichtbare Vision-Review-Datei."""

from __future__ import annotations

from pathlib import PurePosixPath
import unittest

from app.models import ConversionWarning, PageReference
from app.vision_review import render_vision_review


class VisionReviewTests(unittest.TestCase):
    def test_lists_accepted_and_rejected_pages(self) -> None:
        review = render_vision_review(selected_pages=(1, 2), proposal_paths=(PurePosixPath("Quelle.vision-proposals/page-001.proposal.json"),), warnings=(ConversionWarning("VISION_INVALID_JSON", "Ungültig.", page=PageReference(2)),))
        self.assertIn("- Seite 1: akzeptierter Vorschlag vorhanden", review)
        self.assertIn("- Seite 2: kein automatisch übernehmbarer Vorschlag", review)
        self.assertIn("`VISION_INVALID_JSON`", review)


if __name__ == "__main__":
    unittest.main()
