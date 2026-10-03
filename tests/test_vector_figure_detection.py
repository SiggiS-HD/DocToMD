"""Tests für die konservative Erkennung nicht exportierter Vektorgrafiken."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.vector_figure_detection import detect_vector_figures
from tests.fixtures.build_vector_figure_fixture import build_pdf


class VectorFigureDetectionTests(unittest.TestCase):
    def test_detects_a_caption_bound_vector_figure_from_the_local_fixture(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "vector-figure.pdf"
            build_pdf(source)

            outcome = detect_vector_figures(source_path=source, raster_asset_pages=())

        self.assertEqual(len(outcome.candidates), 1)
        self.assertEqual(outcome.candidates[0].caption, "Figure 1: Synthetic vector trend.")
        self.assertEqual(outcome.candidates[0].page.page_number, 1)
        self.assertEqual([warning.code for warning in outcome.warnings], ["VECTOR_FIGURE_NOT_EXPORTED"])

    def test_reports_an_unmatched_caption_without_guessing_a_second_vector_region(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "ambiguous.pdf"
            build_pdf(source, ambiguous=True)

            outcome = detect_vector_figures(source_path=source, raster_asset_pages=())

        self.assertEqual([candidate.caption for candidate in outcome.candidates], ["Figure 1: Synthetic vector trend."])
        self.assertEqual([warning.code for warning in outcome.warnings], ["VECTOR_FIGURE_NOT_EXPORTED"])

    def test_detects_a_compact_caption_when_the_pdf_textlayer_omits_the_space(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "compact-caption.pdf"
            build_pdf(source, compact_caption=True)

            outcome = detect_vector_figures(source_path=source, raster_asset_pages=())

        self.assertEqual([candidate.caption for candidate in outcome.candidates], ["Figure1: Synthetic vector trend."])

    def test_skips_a_page_that_already_has_an_exported_raster_asset(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "vector-figure.pdf"
            build_pdf(source)

            outcome = detect_vector_figures(source_path=source, raster_asset_pages=(1,))

        self.assertEqual(outcome.candidates, ())
        self.assertEqual(outcome.warnings, ())

    def test_assigns_two_side_by_side_vector_regions_to_their_own_captions(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "paired-figures.pdf"
            build_pdf(source, paired_figures=True)

            outcome = detect_vector_figures(source_path=source, raster_asset_pages=())

        self.assertEqual(
            [(candidate.page.page_number, candidate.caption) for candidate in outcome.candidates],
            [(1, "Figure 1: Left synthetic trend."), (1, "Figure 2: Right synthetic trend.")],
        )


if __name__ == "__main__":
    unittest.main()
