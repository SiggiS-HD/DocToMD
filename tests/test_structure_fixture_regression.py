"""End-to-End-Regression für die Strukturqualitäts-Fixture."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.conversion_service import convert_pdf
from app.models import ConversionStatus


class StructureFixtureRegressionTests(unittest.TestCase):
    def test_preserves_supported_structure_elements_and_code_text(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "structure-elements.pdf"
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "output"
            run = convert_pdf(
                input_path=fixture,
                output_dir=output_dir,
                on_conflict="error",
                ocr_mode="off",
                ocr_language="de",
            )
            markdown = (output_dir / "structure-elements.md").read_text(encoding="utf-8")

        self.assertEqual(run.result.status, ConversionStatus.SUCCESS)
        self.assertIn("<!-- doctomd:page=1 -->", markdown)
        self.assertIn("# 1 Overview", markdown)
        self.assertIn("## 1.1 Details", markdown)
        self.assertIn("First paragraph line one. First paragraph line two.", markdown)
        self.assertIn("Second paragraph stays separate.", markdown)
        self.assertIn("- Bullet item", markdown)
        self.assertIn("1. Ordered item", markdown)
        self.assertIn("print(42)", markdown)
        self.assertNotIn("```", markdown)
        self.assertIn("| Name | Value |", markdown)
        self.assertIn("| Alpha | 1 |", markdown)
        self.assertIn("| Beta | 2 |", markdown)


if __name__ == "__main__":
    unittest.main()
