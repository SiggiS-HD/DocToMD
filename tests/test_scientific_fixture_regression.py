"""End-to-End-Regression für die versionierte wissenschaftliche PDF-Fixture."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.conversion_service import convert_pdf
from app.models import ConversionStatus


class ScientificFixtureRegressionTests(unittest.TestCase):
    def test_fixture_preserves_verified_scientific_content_and_quality_signal(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "scientific-two-column.pdf"
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "output"
            run = convert_pdf(
                input_path=fixture,
                output_dir=output_dir,
                on_conflict="error",
                ocr_mode="off",
                ocr_language="de",
            )
            markdown = (output_dir / "scientific-two-column.md").read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "scientific-two-column.conversion.json").read_text(encoding="utf-8"))

        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertIn("<!-- doctomd:page=1 -->", markdown)
        self.assertIn("Synthetic Methods Note Page 1", markdown)
        self.assertIn(r"$$p(x) = \frac{\sum_i w_i x_i}{n}$$", markdown)
        self.assertIn("| Metric | Value |", markdown)
        self.assertIn("| precision | 0.80 |", markdown)
        self.assertIn("| recall | 0.75 |", markdown)
        self.assertLess(markdown.index("Synthetic Methods Note Page 1"), markdown.index("# Abstract"))
        self.assertLess(markdown.index("# 4 Discussion"), markdown.index("Synthetic fixture - not a published work"))
        self.assertEqual(
            manifest["artifacts"]["references"],
            [{
                "kind": "table",
                "label": "Table 1",
                "page": {"page_number": 1},
                "target_page": {"page_number": 1},
                "target_id": "page-001-table-01",
            }],
        )
        self.assertEqual(
            [(warning["code"], warning["page"]["page_number"])
            for warning in manifest["quality"]["warnings"]],
            [("MULTI_COLUMN_LAYOUT", 1)],
        )


if __name__ == "__main__":
    unittest.main()
