"""Tests für die explizite Übernahme von Vision-Vorschlägen."""

from __future__ import annotations

import unittest

from app.vision_merge import merge_validated_proposals


class VisionMergeTests(unittest.TestCase):
    def test_replaces_only_unique_formula_source_and_appends_table(self) -> None:
        proposal = {"page": {"page_number": 2}, "formulas": [{"source_text": "x = y", "latex": "x = y"}], "tables": [{"title": "Resultate", "headers": ["A", "B"], "rows": [["1", "2"]]}]}
        merged = merge_validated_proposals(local_markdown="Text\n\nx = y", proposals=(proposal,))
        self.assertIn("$$ x = y $$", merged)
        self.assertIn("## Resultate (Vision-Vorschlag, Seite 2)", merged)
        self.assertIn("| A | B |", merged)


if __name__ == "__main__":
    unittest.main()
