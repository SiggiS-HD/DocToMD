"""Unit-Tests für deterministisch rekonstruierbare Display-Formeln."""

from __future__ import annotations

import unittest

from app.formula_parser import parse_display_formula, render_formula_blocks, render_formula_blocks_with_warnings
from app.models import BlockKind, DocumentBlock, PageReference


class FormulaParserTests(unittest.TestCase):
    def test_parses_the_scientific_fixture_formula_as_latex(self) -> None:
        latex = parse_display_formula("p(x) = sum_i w_i * x_i / n")

        self.assertEqual(latex, r"p(x) = \frac{\sum_i w_i x_i}{n}")

    def test_rejects_an_unsupported_formula_without_guessing(self) -> None:
        self.assertIsNone(parse_display_formula("A = [a_ij]"))

    def test_renders_only_a_standalone_paragraph_as_display_latex(self) -> None:
        formula = DocumentBlock(BlockKind.PARAGRAPH, "p(x) = sum_i w_i * x_i / n", PageReference(2))
        prose = DocumentBlock(BlockKind.PARAGRAPH, "Die Formel p(x) = sum_i w_i * x_i / n bleibt Text.", PageReference(2))

        blocks = render_formula_blocks((formula, prose))

        self.assertEqual(blocks[0].text, r"$$p(x) = \frac{\sum_i w_i x_i}{n}$$")
        self.assertEqual(blocks[0].page, PageReference(2))
        self.assertEqual(blocks[1], prose)

    def test_preserves_an_unsupported_formula_candidate_and_warns_on_its_page(self) -> None:
        candidate = DocumentBlock(BlockKind.PARAGRAPH, "A = [a_ij]", PageReference(3))

        outcome = render_formula_blocks_with_warnings((candidate,))

        self.assertEqual(outcome.blocks, (candidate,))
        self.assertEqual(outcome.warnings[0].code, "FORMULA_NOT_RECONSTRUCTED")
        self.assertEqual(outcome.warnings[0].page, PageReference(3))

    def test_does_not_mistake_prose_with_an_equals_sign_for_a_formula_block(self) -> None:
        prose = DocumentBlock(BlockKind.PARAGRAPH, "Die Aussage x = y bleibt Teil dieses Satzes.", PageReference(4))

        outcome = render_formula_blocks_with_warnings((prose,))

        self.assertEqual(outcome.warnings, ())


if __name__ == "__main__":
    unittest.main()
