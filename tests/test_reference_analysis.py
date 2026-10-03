"""Tests für konservativ extrahierte wissenschaftliche Dokumentverweise."""

from __future__ import annotations

from pathlib import PurePosixPath
import unittest

from app.models import Asset, AssetKind, BlockKind, DocumentBlock, DocumentTable, PageReference
from app.reference_analysis import analyze_references


class ReferenceAnalysisTests(unittest.TestCase):
    def test_resolves_citation_and_footnote_to_definition_page(self) -> None:
        blocks = (
            DocumentBlock(BlockKind.PARAGRAPH, "Frühere Arbeit [1] und eine Anmerkung[^2].", PageReference(1)),
            DocumentBlock(BlockKind.PARAGRAPH, "[^2]: Erläuternde Fußnote.", PageReference(3)),
            DocumentBlock(BlockKind.PARAGRAPH, "[1] Nachvollziehbare Referenz.", PageReference(4)),
        )

        outcome = analyze_references(blocks=blocks, assets=(), tables=())

        self.assertEqual([(reference.kind.value, reference.label, reference.page.page_number, reference.target_page.page_number if reference.target_page else None) for reference in outcome.references], [("citation", "[1]", 1, 4), ("footnote", "[^2]", 1, 3)])
        self.assertEqual(outcome.warnings, ())

    def test_resolves_figure_and_table_by_stable_export_order(self) -> None:
        blocks = (DocumentBlock(BlockKind.PARAGRAPH, "Figure 1 ergänzt Table 1.", PageReference(2)),)
        asset = Asset("page-003-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/figure.jpg"), PageReference(3))
        table = DocumentTable("page-004-table-01", PageReference(4), ("Metrik", "Wert"), (("A", "1"),))

        outcome = analyze_references(blocks=blocks, assets=(asset,), tables=(table,))

        self.assertEqual([(reference.kind.value, reference.target_id, reference.target_page.page_number if reference.target_page else None) for reference in outcome.references], [("figure", "page-003-figure-01", 3), ("table", "page-004-table-01", 4)])
        self.assertEqual(outcome.warnings, ())

    def test_warns_when_visible_marker_has_no_safe_target(self) -> None:
        blocks = (DocumentBlock(BlockKind.PARAGRAPH, "Siehe Figure 2 und [7].", PageReference(5)),)

        outcome = analyze_references(blocks=blocks, assets=(), tables=())

        self.assertEqual([(reference.kind.value, reference.label, reference.target_page) for reference in outcome.references], [("citation", "[7]", None), ("figure", "Figure 2", None)])
        self.assertEqual([(warning.code, warning.page.page_number) for warning in outcome.warnings], [("UNRESOLVED_DOCUMENT_REFERENCE", 5), ("UNRESOLVED_DOCUMENT_REFERENCE", 5)])


if __name__ == "__main__":
    unittest.main()
