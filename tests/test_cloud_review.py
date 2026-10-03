"""Tests für sichtbare lokale Prüfhinweise im Cloud-Derivat."""

from __future__ import annotations

import unittest

from pathlib import PurePosixPath

from app.cloud_review import inject_cloud_assets, inject_cloud_native_pdf_links, inject_cloud_review_warnings
from app.models import Asset, AssetKind, ConversionWarning, NativePdfLink, PageReference, PdfAnnotationRect, WarningSeverity


class CloudReviewTests(unittest.TestCase):
    def test_inserts_page_warning_after_matching_page_marker(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Seite eins\n\n<!-- doctomd:page=2 -->\n\n| Wert | Ergebnis |\n| --- | --- |\n| A | B |\n"
        warning = ConversionWarning(
            "OCR_LOW_CONFIDENCE",
            "Die mittlere OCR-Wortkonfidenz liegt unter dem Grenzwert 70.",
            page=PageReference(2),
        )

        result = inject_cloud_review_warnings(content=content, warnings=(warning,))

        self.assertIn("<!-- doctomd:page=2 -->\n\n> [!warning] DocToMD-Prüfhinweis `OCR_LOW_CONFIDENCE`", result)
        self.assertIn("Bitte den betreffenden Inhalt am Original prüfen.", result)
        self.assertLess(result.index("# Seite eins"), result.index("DocToMD-Prüfhinweis"))
        self.assertLess(result.index("DocToMD-Prüfhinweis"), result.index("| Wert | Ergebnis |"))

    def test_ignores_global_and_info_warnings(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Titel\n"
        warnings = (
            ConversionWarning("GLOBAL", "Globaler Hinweis."),
            ConversionWarning("INFO", "Nur Information.", WarningSeverity.INFO, PageReference(1)),
        )

        self.assertEqual(inject_cloud_review_warnings(content=content, warnings=warnings), content)

    def test_keeps_technical_warning_only_in_manifest(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Titel\n"
        warning = ConversionWarning("MULTI_COLUMN_LAYOUT", "Technischer Analysebefund.", page=PageReference(1))

        self.assertEqual(inject_cloud_review_warnings(content=content, warnings=(warning,)), content)

    def test_omits_local_glyph_warning_when_cloud_page_is_clean(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Titel\n\nVollständig lesbarer Text.\n"
        warning = ConversionWarning("UNREADABLE_PDF_GLYPHS", "Nicht dekodierbare PDF-Zeichen wurden unverändert beibehalten.", page=PageReference(1))

        self.assertEqual(inject_cloud_review_warnings(content=content, warnings=(warning,)), content)

    def test_keeps_glyph_warning_when_cloud_page_still_contains_a_glyph(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Titel\n\n(cid:42)\n"
        warning = ConversionWarning("UNREADABLE_PDF_GLYPHS", "Nicht dekodierbare PDF-Zeichen wurden unverändert beibehalten.", page=PageReference(1))

        result = inject_cloud_review_warnings(content=content, warnings=(warning,))

        self.assertIn("DocToMD-Prüfhinweis `UNREADABLE_PDF_GLYPHS`", result)

    def test_inserts_verified_asset_after_matching_caption(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n*Abbildung 1: Herz.*\n"
        asset = Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.png"), PageReference(1), caption="Abbildung 1: Herz.", description_path=PurePosixPath("Quelle.assets/page-001-figure-01-description.md"))

        result = inject_cloud_assets(content=content, assets=(asset,))

        self.assertIn("![Abbildung 1: Herz.](Quelle.assets/page-001-figure-01.png)", result)
        self.assertLess(result.index("Abbildung 1: Herz."), result.index("![Abbildung 1: Herz.]"))

    def test_inserts_asset_after_a_normalized_figure_caption(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n**Figure 1:** Schematic of the proposed architecture.\n\nFollowing paragraph.\n"
        asset = Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.png"), PageReference(1), caption="Figure1:Schematicoftheproposedarchitecture.")

        result = inject_cloud_assets(content=content, assets=(asset,))

        self.assertIn("**Figure 1:** Schematic of the proposed architecture.\n\n<!-- doctomd:asset=page-001-figure-01", result)
        self.assertLess(result.index("![Figure1:"), result.index("Following paragraph."))

    def test_places_two_normalized_figure_assets_at_their_own_caption(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\nFigure 9: First chart.\n\nText.\n\n**Figure 10:** Second chart.\n"
        assets = (
            Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.png"), PageReference(1), caption="Figure10:Secondchart."),
            Asset("page-001-figure-02", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-02.png"), PageReference(1), caption="Figure9:Firstchart."),
        )

        result = inject_cloud_assets(content=content, assets=assets)

        self.assertIn("Figure 9: First chart.\n\n<!-- doctomd:asset=page-001-figure-02", result)
        self.assertIn("**Figure 10:** Second chart.\n\n<!-- doctomd:asset=page-001-figure-01", result)

    def test_keeps_full_page_scan_asset_out_of_cloud_derivative(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Rekonstruierter Befund\n"
        asset = Asset(
            "page-001-figure-01",
            AssetKind.IMAGE,
            PurePosixPath("Quelle.assets/page-001-figure-01.jpg"),
            PageReference(1),
        )

        result = inject_cloud_assets(
            content=content,
            assets=(asset,),
            skip_page_numbers=frozenset({1}),
        )

        self.assertEqual(result, content)

    def test_removes_generic_model_figure_warning_only_when_asset_is_verified(self) -> None:
        content = (
            "<!-- doctomd:page=1 -->\n\n> [!warning]\n> The page contains a diagram titled ‘Example’.\n\n# Seite eins\n\n"
            "<!-- doctomd:page=2 -->\n\n> [!warning]\n> A diagram titled ‘Keep’ is visible on this page.\n"
        )
        asset = Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.jpg"), PageReference(1))

        result = inject_cloud_assets(content=content, assets=(asset,))

        self.assertNotIn("Example", result)
        self.assertIn("Keep", result)
        self.assertIn("![Abbildung page-001-figure-01]", result)

    def test_removes_visible_on_page_model_warning_when_asset_is_verified(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n> [!warning]\n> A figure illustrating the system is visible on this page, showing hosts.\n"
        asset = Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.jpg"), PageReference(1))

        result = inject_cloud_assets(content=content, assets=(asset,))

        self.assertNotIn("illustrating the system", result)

    def test_injects_the_local_link_list_at_its_original_page(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Erste Seite\n\n<!-- doctomd:page=2 -->\n\n# Zweite Seite\n"
        links = (
            NativePdfLink("https://example.org/titel", PageReference(2), PdfAnnotationRect(1, 2, 3, 4), visible_title="Belegter Titel"),
            NativePdfLink("https://example.org/neutral", PageReference(2), PdfAnnotationRect(5, 6, 7, 8)),
        )

        result = inject_cloud_native_pdf_links(content=content, links=links)

        self.assertNotIn("native-pdf-links page=1", result)
        self.assertIn("<!-- doctomd:native-pdf-links page=2 -->", result)
        self.assertIn("[Belegter Titel](<https://example.org/titel>)", result)
        self.assertIn("[Externer Link auf Seite 2](<https://example.org/neutral>)", result)

    def test_injects_all_local_qr_targets_when_the_cloud_answer_has_no_links(self) -> None:
        content = "<!-- doctomd:page=1 -->\n\n# Rechengesetze\n"
        links = (
            NativePdfLink("https://example.org/potenz", PageReference(1), PdfAnnotationRect(1, 2, 3, 4), visible_title="Potenzgesetze"),
            NativePdfLink("https://example.org/wurzel", PageReference(1), PdfAnnotationRect(5, 6, 7, 8), visible_title="Wurzelgesetze"),
            NativePdfLink("https://example.org/logarithmus", PageReference(1), PdfAnnotationRect(9, 10, 11, 12), visible_title="Logarithmusgesetze, ab 1:02"),
            NativePdfLink("https://example.org/fakultaeten", PageReference(1), PdfAnnotationRect(13, 14, 15, 16), visible_title="Fakultäten kürzen"),
        )

        result = inject_cloud_native_pdf_links(content=content, links=links)

        self.assertEqual(result.count("doctomd:native-pdf-links"), 1)
        for title in ("Potenzgesetze", "Wurzelgesetze", "Logarithmusgesetze, ab 1:02", "Fakultäten kürzen"):
            self.assertIn(f"[{title}]", result)
        self.assertLess(result.index("# Rechengesetze"), result.index("native-pdf-links page=1"))

    def test_rejects_a_cloud_supplied_native_link_marker(self) -> None:
        content = "<!-- doctomd:page=1 -->\n<!-- doctomd:native-pdf-links page=1 -->\n"
        link = NativePdfLink("https://example.org/", PageReference(1), PdfAnnotationRect(1, 2, 3, 4))

        with self.assertRaisesRegex(ValueError, "Cloud-Antwort darf keine"):
            inject_cloud_native_pdf_links(content=content, links=(link,))


if __name__ == "__main__":
    unittest.main()
