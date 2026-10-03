"""Tests für lokal zugeschnittene Vektor-PNG-Assets."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image

from app.conversion_service import convert_pdf
from app.models import PageReference
from app.vector_figure_detection import VectorFigureCandidate, detect_vector_figures
from app.vector_figure_export import export_vector_figures
from tests.fixtures.build_vector_figure_fixture import build_pdf


class VectorFigureExportTests(unittest.TestCase):
    def test_exports_only_the_confirmed_vector_crop_with_sidecar(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "vector-figure.pdf"
            build_pdf(source)
            candidate = VectorFigureCandidate(PageReference(1), "Figure 1: Synthetic vector trend.", (72.0, 292.0, 430.0, 542.0), 5)

            assets, warnings = export_vector_figures(source_path=source, asset_directory=root / "vector-figure.assets", candidates=(candidate,))

            image_path = root / "vector-figure.assets" / "page-001-figure-01.png"
            self.assertEqual(warnings, ())
            self.assertEqual(assets[0].relative_path.as_posix(), "vector-figure.assets/page-001-figure-01.png")
            self.assertEqual(assets[0].caption, "Figure 1: Synthetic vector trend.")
            self.assertTrue((root / "vector-figure.assets" / "page-001-figure-01-description.md").is_file())
            with Image.open(image_path) as image:
                self.assertEqual(image.size, (716, 500))
                self.assertLess(image.width, 1224)
                self.assertLess(image.height, 1584)

    def test_rejects_a_full_page_crop_without_creating_an_asset(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "vector-figure.pdf"
            build_pdf(source)
            candidate = VectorFigureCandidate(PageReference(1), "Figure 1: Synthetic vector trend.", (0.0, 0.0, 612.0, 792.0), 5)

            assets, warnings = export_vector_figures(source_path=source, asset_directory=root / "vector-figure.assets", candidates=(candidate,))

            self.assertEqual(assets, ())
            self.assertEqual([warning.code for warning in warnings], ["VECTOR_FIGURE_NOT_EXPORTED"])
            self.assertFalse((root / "vector-figure.assets").exists())

    def test_conversion_publishes_crop_in_markdown_and_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "vector-figure.pdf"
            build_pdf(source)

            run = convert_pdf(input_path=source, output_dir=root / "output", on_conflict="error", ocr_mode="off", ocr_language="en")

            markdown = (root / "output" / "vector-figure.md").read_text(encoding="utf-8")
            self.assertEqual([asset.asset_id for asset in run.result.assets], ["page-001-figure-01"])
            self.assertIn("![Figure 1: Synthetic vector trend.](vector-figure.assets/page-001-figure-01.png)", markdown)
            self.assertEqual(run.manifest["artifacts"]["assets"][0]["path"], "vector-figure.assets/page-001-figure-01.png")
            self.assertFalse(any(warning.code == "VECTOR_FIGURE_NOT_EXPORTED" for warning in run.result.warnings))

    def test_exports_side_by_side_figures_with_stable_per_page_numbers(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "paired-figures.pdf"
            build_pdf(source, paired_figures=True)
            candidates = detect_vector_figures(source_path=source, raster_asset_pages=()).candidates

            assets, warnings = export_vector_figures(source_path=source, asset_directory=root / "paired-figures.assets", candidates=candidates)

            self.assertEqual(warnings, ())
            self.assertEqual(
                [(asset.asset_id, asset.caption, asset.page.page_number) for asset in assets],
                [
                    ("page-001-figure-01", "Figure 1: Left synthetic trend.", 1),
                    ("page-001-figure-02", "Figure 2: Right synthetic trend.", 1),
                ],
            )
            self.assertTrue((root / "paired-figures.assets" / "page-001-figure-01.png").is_file())
            self.assertTrue((root / "paired-figures.assets" / "page-001-figure-02.png").is_file())

    def test_paired_conversion_keeps_markdown_and_manifest_asset_lists_consistent(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "paired-figures.pdf"
            build_pdf(source, paired_figures=True)

            run = convert_pdf(input_path=source, output_dir=root / "output", on_conflict="error", ocr_mode="off", ocr_language="en")

            markdown = (root / "output" / "paired-figures.md").read_text(encoding="utf-8")
            manifest_assets = run.manifest["artifacts"]["assets"]
            self.assertEqual(
                [(asset["asset_id"], asset["path"], asset["page"]["page_number"]) for asset in manifest_assets],
                [
                    ("page-001-figure-01", "paired-figures.assets/page-001-figure-01.png", 1),
                    ("page-001-figure-02", "paired-figures.assets/page-001-figure-02.png", 1),
                ],
            )
            for asset in manifest_assets:
                self.assertIn(f"<!-- doctomd:asset={asset['asset_id']} page=1 -->", markdown)
                self.assertIn(f"]({asset['path']})", markdown)

    @patch("app.vector_figure_export.render_vector_crop", side_effect=OSError("Renderer nicht verfügbar."))
    def test_reports_a_render_failure_without_creating_assets(self, _render_crop) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "vector-figure.pdf"
            build_pdf(source)
            candidate = VectorFigureCandidate(PageReference(1), "Figure 1: Synthetic vector trend.", (72.0, 292.0, 430.0, 542.0), 5)

            assets, warnings = export_vector_figures(source_path=source, asset_directory=root / "vector-figure.assets", candidates=(candidate,))

            self.assertEqual(assets, ())
            self.assertEqual([warning.code for warning in warnings], ["VECTOR_FIGURE_NOT_EXPORTED"])
            self.assertFalse((root / "vector-figure.assets").exists())


if __name__ == "__main__":
    unittest.main()
