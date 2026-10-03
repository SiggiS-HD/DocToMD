"""Unit-Tests für die textbasierte Konvertierungsorchestrierung."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import ANY, patch
from app.conversion_service import convert_pdf, serialize_run
from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_document_prompt import build_cloud_markdown_instructions
from app.cloud_document_telemetry import CloudDocumentTelemetry
from app.cloud_markdown_validation import CloudMarkdownValidationError
from app.image_export import ImageExportOutcome
from app.vector_figure_detection import VectorFigureDetectionOutcome
from app.native_pdf_links import NativePdfLinkExtractionOutcome
from app.table_extract import TableExtractionOutcome
from app.models import Asset, AssetKind, ConversionStatus, ConversionWarning, DocumentTable, NativePdfLink, PageReference, PdfAnnotationRect
from app.pdf_extract import ExtractedPage
from app.ocr_extract import OcrOutcome, OcrPageMetrics
from app.openai_cloud_document import CloudDocumentResponse
from app.openai_cloud_document import OpenAICloudDocumentError
from app.vision_config import VisionConfig, VisionMode, VisionProvider


class ConversionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory(); self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"; self.source_path.write_bytes(b"%PDF-1.7")
        self.output_dir = self.root / "ausgabe"
        self.extract_native_links = patch(
            "app.conversion_service.extract_native_pdf_links",
            return_value=NativePdfLinkExtractionOutcome(),
        )
        self.extract_native_links_mock = self.extract_native_links.start()
    def tearDown(self) -> None:
        self.extract_native_links.stop()
        self.directory.cleanup()

    @patch("app.conversion_service.detect_vector_figures")
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_surfaces_non_exported_vector_figure_as_a_page_warning(self, extract_pages, _export_images, _extract_tables, detect_vectors) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 2, 1),)
        detect_vectors.return_value = VectorFigureDetectionOutcome(warnings=(ConversionWarning(
            "VECTOR_FIGURE_NOT_EXPORTED", "Vektorbereich wird nicht exportiert.", page=PageReference(1),
        ),))

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertEqual(run.result.assets, ())
        self.assertEqual(
            [(item["code"], item["page"]["page_number"]) for item in run.manifest["quality"]["warnings"]],
            [("VECTOR_FIGURE_NOT_EXPORTED", 1)],
        )

    @patch("app.conversion_service.apply_ocr_fallback")
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_passes_textlayer_pages_to_explicit_ocr_fallback(self, extract_pages, _export_images, _extract_tables, ocr_fallback) -> None:
        pages = (ExtractedPage(1, "Lokaler Text", 2, 1),)
        extract_pages.return_value = pages
        ocr_fallback.return_value = OcrOutcome(pages)

        convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="auto", ocr_language="de")

        ocr_fallback.assert_called_once_with(
            source_path=self.source_path.resolve(),
            pages=pages,
            ocr_mode="auto",
            ocr_language="de",
            ocr_pages="all",
            min_word_confidence=70,
        )

    @patch("app.conversion_service.apply_ocr_fallback")
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_mocked_scan_ocr_writes_text_metrics_and_quality_warning(self, extract_pages, _export_images, _extract_tables, ocr_fallback) -> None:
        extract_pages.return_value = (ExtractedPage(1, "", 0, 1), ExtractedPage(2, "", 0, 1))
        warning = ConversionWarning("OCR_LOW_CONFIDENCE", "OCR unsicher.", page=PageReference(2))
        ocr_fallback.return_value = OcrOutcome(
            pages=(ExtractedPage(1, "Erkannte erste Seite", 3, 1), ExtractedPage(2, "Erkannte zweite Seite", 3, 1)),
            warnings=(warning,),
            page_metrics=(OcrPageMetrics(1, 3, 93.5), OcrPageMetrics(2, 3, 52.0)),
        )

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="auto", ocr_language="de", ocr_pages="all", ocr_min_word_confidence=70)

        markdown = (self.output_dir / "Quelle.md").read_text(encoding="utf-8")
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertIn("Erkannte erste Seite", markdown)
        self.assertIn("Erkannte zweite Seite", markdown)
        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertEqual(manifest["conversion"]["ocr"]["pages"], [{"page_number": 1, "word_count": 3, "average_word_confidence": 93.5}, {"page_number": 2, "word_count": 3, "average_word_confidence": 52.0}])
        self.assertEqual(manifest["quality"]["warnings"][0]["code"], "OCR_LOW_CONFIDENCE")
        self.assertFalse((self.output_dir / "Quelle.corrections.md").exists())

    @patch("app.conversion_service.request_document_response")
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_default_conversion_never_calls_cloud_adapter(self, extract_pages, _export_images, _extract_tables, request_cloud) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 1, 1),)

        convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        request_cloud.assert_not_called()

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    @patch("app.conversion_service.request_document_response")
    def test_rejects_cloud_invented_image_reference_before_publication(self, request_cloud, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 1, 1),)
        timestamp = datetime(2026, 10, 1, tzinfo=timezone.utc)
        request_cloud.return_value = CloudDocumentResponse(
            {"id": "resp_test", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\n\nLokaler Text\n\n![Erfundene Abbildung](figure-2.png)\n"},
            CloudDocumentTelemetry("resp_test", "gpt-5.6-terra", 10, 20, 30, timestamp, timestamp, 1),
        )

        with self.assertRaises(CloudMarkdownValidationError) as raised:
            convert_pdf(
                input_path=self.source_path,
                output_dir=self.output_dir,
                on_conflict="error",
                ocr_mode="off",
                ocr_language="de",
                cloud_document_config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
            )

        self.assertEqual(raised.exception.code, "CLOUD_UNAUTHORIZED_IMAGE_REFERENCE")
        self.assertFalse((self.output_dir / "Quelle.cloud.md").exists())
        self.assertTrue((self.output_dir / "Quelle.md").is_file())

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    @patch("app.conversion_service.request_document_response")
    def test_cloud_request_failure_keeps_published_local_basis(self, request_cloud, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 1, 1),)
        request_cloud.side_effect = OpenAICloudDocumentError("Cloud nicht erreichbar.")

        with self.assertRaisesRegex(OpenAICloudDocumentError, "Cloud nicht erreichbar"):
            convert_pdf(
                input_path=self.source_path,
                output_dir=self.output_dir,
                on_conflict="error",
                ocr_mode="off",
                ocr_language="de",
                cloud_document_config=CloudDocumentConfig(
                    mode=CloudDocumentMode.OPENAI,
                    model_id="gpt-5.6-terra",
                ),
            )

        markdown = self.output_dir / "Quelle.md"
        manifest_path = self.output_dir / "Quelle.conversion.json"
        self.assertTrue(markdown.is_file())
        self.assertTrue(manifest_path.is_file())
        local_content = markdown.read_text(encoding="utf-8")
        self.assertIn('doctomd_source_document: "Quelle.pdf"', local_content)
        self.assertIn("doctomd_derivative_kind: local", local_content)
        self.assertTrue(local_content.endswith("<!-- doctomd:page=1 -->\nLokaler Text"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertNotIn("cloud_markdown_path", manifest["artifacts"])
        self.assertNotIn("cloud_document", manifest["conversion"])
        self.assertFalse((self.output_dir / "Quelle.cloud.md").exists())

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_writes_locally_validated_native_links_to_manifest(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 2, 1),)
        self.extract_native_links_mock.return_value = NativePdfLinkExtractionOutcome(
            links=(NativePdfLink(
                "https://example.org/", PageReference(1), PdfAnnotationRect(1, 2, 3, 4),
                visible_title="Belegter Titel",
            ),),
        )

        convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["artifacts"]["native_pdf_links"]["schema_version"], "1.0")
        self.assertEqual(manifest["artifacts"]["native_pdf_links"]["items"][0]["title_assignment_status"], "geometrically_verified")

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    @patch("app.conversion_service.request_document_response")
    def test_explicit_cloud_mode_writes_validated_derivative_and_manifest(self, request_cloud, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 1, 1),)
        self.extract_native_links_mock.return_value = NativePdfLinkExtractionOutcome(
            links=(NativePdfLink(
                "https://example.org/lokal", PageReference(1), PdfAnnotationRect(1, 2, 3, 4),
                visible_title="Lokaler Titel",
            ),),
        )
        timestamp = datetime(2026, 9, 17, tzinfo=timezone.utc)
        request_cloud.return_value = CloudDocumentResponse(
            {
                "id": "resp_test",
                "model": "gpt-5.6-terra",
                "status": "completed",
                "output_text": "<!-- doctomd:page=1 -->\n\n# Cloud-Titel\n\nLokaler Text\n",
            },
            CloudDocumentTelemetry(
                response_id="resp_test",
                model_id="gpt-5.6-terra",
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                started_at=timestamp,
                completed_at=timestamp,
                duration_ms=1,
            ),
        )
        config = CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra")

        run = convert_pdf(
            input_path=self.source_path,
            output_dir=self.output_dir,
            on_conflict="error",
            ocr_mode="off",
            ocr_language="de",
            cloud_document_config=config,
        )

        cloud_path = self.output_dir / "Quelle.cloud.md"
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        cloud_content = cloud_path.read_text(encoding="utf-8")
        self.assertIn('doctomd_source_document: "Quelle.pdf"', cloud_content)
        self.assertIn("doctomd_derivative_kind: cloud", cloud_content)
        self.assertTrue(cloud_content.endswith(
            "<!-- doctomd:page=1 -->\n\n# Cloud-Titel\n\nLokaler Text\n\n"
            "<!-- doctomd:native-pdf-links page=1 -->\n**Lokale PDF-Links**\n"
            "- [Lokaler Titel](<https://example.org/lokal>)\n"
        ))
        self.assertIn("doctomd_derivative_kind: local", (self.output_dir / "Quelle.md").read_text(encoding="utf-8"))
        self.assertEqual(run.cloud_markdown_path, PurePosixPath("Quelle.cloud.md"))
        self.assertEqual(serialize_run(run)["cloud_markdown_path"], "Quelle.cloud.md")
        self.assertEqual(serialize_run(run)["cloud_document"]["total_tokens"], 30)
        self.assertEqual(manifest["artifacts"]["cloud_markdown_path"], "Quelle.cloud.md")
        self.assertEqual(manifest["conversion"]["cloud_document"]["response_id"], "resp_test")
        self.assertEqual(manifest["rag_indexing"]["recommended_markdown_path"], "Quelle.cloud.md")
        self.assertEqual(serialize_run(run)["rag_indexing"]["selection_reason"], "validated_cloud_has_more_structure")
        request_cloud.assert_called_once_with(
            source_path=self.source_path.resolve(),
            model_id="gpt-5.6-terra",
            timeout_seconds=900,
            max_output_tokens=32_768,
            instructions=build_cloud_markdown_instructions(),
            on_response_started=ANY,
            on_status=ANY,
        )

    @patch("app.conversion_service.inject_cloud_native_pdf_links")
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    @patch("app.conversion_service.request_document_response")
    def test_rejects_cloud_derivative_when_native_link_coverage_is_missing(
        self,
        request_cloud,
        extract_pages,
        _export_images,
        _extract_tables,
        inject_native_links,
    ) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Lokaler Text", 1, 1),)
        self.extract_native_links_mock.return_value = NativePdfLinkExtractionOutcome(
            links=(NativePdfLink(
                "https://example.org/lokal", PageReference(1), PdfAnnotationRect(1, 2, 3, 4),
                visible_title="Lokaler Titel",
            ),),
        )
        timestamp = datetime(2026, 9, 17, tzinfo=timezone.utc)
        request_cloud.return_value = CloudDocumentResponse(
            {
                "id": "resp_test",
                "model": "gpt-5.6-terra",
                "status": "completed",
                "output_text": "<!-- doctomd:page=1 -->\n\n# Cloud-Titel\n\nLokaler Text\n",
            },
            CloudDocumentTelemetry("resp_test", "gpt-5.6-terra", 10, 20, 30, timestamp, timestamp, 1),
        )
        inject_native_links.return_value = "<!-- doctomd:page=1 -->\n\n# Cloud-Titel\n\nLokaler Text\n"

        with self.assertRaisesRegex(CloudMarkdownValidationError, "lokal geprüften") as raised:
            convert_pdf(
                input_path=self.source_path,
                output_dir=self.output_dir,
                on_conflict="error",
                ocr_mode="off",
                ocr_language="de",
                cloud_document_config=CloudDocumentConfig(
                    mode=CloudDocumentMode.OPENAI,
                    model_id="gpt-5.6-terra",
                ),
            )

        self.assertEqual(raised.exception.code, "CLOUD_NATIVE_LINK_COVERAGE")
        self.assertFalse((self.output_dir / "Quelle.cloud.md").exists())
        self.assertTrue((self.output_dir / "Quelle.conversion.json").is_file())
        base_manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertNotIn("cloud_markdown_path", base_manifest["artifacts"])

    @patch("app.conversion_service.apply_ocr_fallback")
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    @patch("app.conversion_service.request_document_response")
    def test_cloud_derivative_includes_local_page_quality_warning(self, request_cloud, extract_pages, _export_images, _extract_tables, ocr_fallback) -> None:
        extract_pages.return_value = (ExtractedPage(1, "", 0, 1),)
        warning = ConversionWarning("OCR_LOW_CONFIDENCE", "OCR unsicher.", page=PageReference(1))
        ocr_fallback.return_value = OcrOutcome(
            pages=(ExtractedPage(1, "Lokaler OCR-Text", 3, 1),),
            warnings=(warning,),
        )
        timestamp = datetime(2026, 9, 17, tzinfo=timezone.utc)
        request_cloud.return_value = CloudDocumentResponse(
            {"id": "resp_test", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\n\n# Cloud-Titel\n\nLokaler OCR-Text\n"},
            CloudDocumentTelemetry("resp_test", "gpt-5.6-terra", 10, 20, 30, timestamp, timestamp, 1),
        )

        convert_pdf(
            input_path=self.source_path,
            output_dir=self.output_dir,
            on_conflict="error",
            ocr_mode="auto",
            ocr_language="de",
            cloud_document_config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
        )

        cloud_markdown = (self.output_dir / "Quelle.cloud.md").read_text(encoding="utf-8")
        self.assertIn("> [!warning] DocToMD-Prüfhinweis `OCR_LOW_CONFIDENCE`", cloud_markdown)
        self.assertLess(cloud_markdown.index("DocToMD-Prüfhinweis"), cloud_markdown.index("# Cloud-Titel"))
    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_writes_page_marked_markdown_manifest_and_warnings(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Abstract\nText mit \ufffd", 4, 1), ExtractedPage(2, "2 Details\nWeiterer Text", 3, 1))
        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")
        markdown = (self.output_dir / "Quelle.md").read_text(encoding="utf-8")
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertIn("<!-- doctomd:page=1 -->", markdown); self.assertIn("# Abstract", markdown); self.assertIn("<!-- doctomd:page=2 -->", markdown)
        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertEqual(manifest["artifacts"]["markdown_path"], "Quelle.md")
        self.assertEqual(manifest["quality"]["status"], "warning")

    def test_converts_versioned_digital_pdf_fixture(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "simple-digital.pdf"
        run = convert_pdf(input_path=fixture, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")
        markdown = (self.output_dir / "simple-digital.md").read_text(encoding="utf-8")
        manifest = json.loads((self.output_dir / "simple-digital.conversion.json").read_text(encoding="utf-8"))
        self.assertEqual(run.result.status, ConversionStatus.SUCCESS)
        self.assertIn("<!-- doctomd:page=1 -->", markdown)
        self.assertIn("Fixture Titel", markdown)
        self.assertIn("<!-- doctomd:page=2 -->", markdown)
        self.assertIn("# 2 Details", markdown)
        self.assertEqual(
            {item["page"]["page_number"] for item in manifest["artifacts"]["content_references"]},
            {1, 2},
        )
        self.assertEqual(manifest["quality"]["status"], "ok")
        self.assertEqual(manifest["rag_indexing"]["recommended_markdown_path"], "simple-digital.md")
        self.assertEqual(manifest["rag_indexing"]["selection_reason"], "cloud_derivative_not_available")
        self.assertEqual(manifest["rag_readiness"]["status"], "ready")
        self.assertTrue(serialize_run(run)["rag_readiness"]["local_derivative_suitable"])

    def test_converts_scientific_fixture_formula_to_latex(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "scientific-two-column.pdf"

        run = convert_pdf(input_path=fixture, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")
        markdown = (self.output_dir / "scientific-two-column.md").read_text(encoding="utf-8")

        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertIn(r"$$p(x) = \frac{\sum_i w_i x_i}{n}$$", markdown)
        self.assertNotIn("p(x) = sum_i w_i * x_i / n", markdown)

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_preserves_unreconstructed_formula_and_reports_page_warning(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "A = [a_ij]", 3, 1),)

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")
        markdown = (self.output_dir / "Quelle.md").read_text(encoding="utf-8")
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))

        self.assertIn("A = [a_ij]", markdown)
        self.assertNotIn("$$A", markdown)
        self.assertEqual([(warning.code, warning.page.page_number) for warning in run.result.warnings], [("FORMULA_NOT_RECONSTRUCTED", 1)])
        self.assertEqual(manifest["quality"]["warnings"][0]["code"], "FORMULA_NOT_RECONSTRUCTED")

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_auto_vision_plan_selects_an_unreconstructed_formula_page(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "A = [a_ij]", 3, 1), ExtractedPage(2, "Text", 1, 1))
        config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.AUTO, model_id="gpt-5.6-terra")

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de", vision_config=config)

        self.assertEqual(run.vision_pages, (1,))

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_reports_layout_and_encoding_warnings(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (
            ExtractedPage(1, "Zweispaltiger Text", 2, 2),
            ExtractedPage(2, "(cid:42) nicht dekodierbar", 2, 1),
        )

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertEqual(
            {(warning.code, warning.page.page_number) for warning in run.result.warnings},
            {("MULTI_COLUMN_LAYOUT", 1), ("UNREADABLE_PDF_GLYPHS", 2)},
        )

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_reports_unreconstructed_display_math_as_a_cloud_relevant_limit(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (
            ExtractedPage(1, "Text → Vektor", 3, 1, formula_candidate_lines=("Text → Vektor",)),
        )

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        self.assertEqual([(warning.code, warning.page.page_number) for warning in run.result.warnings], [
            ("DISPLAY_FORMULA_LAYOUT_NOT_RECONSTRUCTED", 1),
        ])
        self.assertEqual(run.manifest["rag_readiness"]["recommended_next_step"]["kind"], "cloud_document")

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_reports_unstructured_ocr_layout_fallback_as_a_cloud_relevant_limit(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (
            ExtractedPage(1, "OCR-Zeile ohne Struktur", 4, 1, layout_html="<pre>OCR-Zeile ohne Struktur</pre>"),
        )

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        self.assertEqual([(warning.code, warning.page.page_number) for warning in run.result.warnings], [
            ("OCR_LAYOUT_FALLBACK", 1),
        ])
        self.assertEqual(run.manifest["rag_readiness"]["recommended_next_step"]["kind"], "cloud_document")

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_does_not_flag_an_ocr_layout_page_with_a_structured_heading(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (
            ExtractedPage(1, "1 Überschrift\nOCR-Text", 3, 1, layout_html="<pre>OCR-Text</pre>"),
        )

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")

        self.assertEqual(run.result.warnings, ())

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_auto_vision_plan_selects_only_pages_with_local_risks(self, extract_pages, _export_images, _extract_tables) -> None:
        extract_pages.return_value = (
            ExtractedPage(1, "Mehrspaltig", 1, 2),
            ExtractedPage(2, "Unauffällig", 1, 1),
        )
        config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.AUTO, model_id="gpt-5.6-terra")

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de", vision_config=config)

        self.assertEqual(run.vision_pages, (1,))
        self.assertEqual(serialize_run(run)["vision_pages"], [1])

    @patch("app.conversion_service.extract_simple_tables", return_value=TableExtractionOutcome())
    @patch("app.conversion_service.export_embedded_images")
    @patch("app.conversion_service.extract_pdf_pages")
    def test_writes_image_reference_and_manifest_asset(self, extract_pages, export_images, _extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Bildseite", 1, 1),)
        asset = Asset("page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/page-001-figure-01.jpg"), PageReference(1), description_path=PurePosixPath("Quelle.assets/page-001-figure-01-description.md"))
        export_images.return_value = ImageExportOutcome(assets=(asset,))
        asset_directory = self.output_dir / "Quelle.assets"
        asset_directory.mkdir(parents=True)
        (asset_directory / "page-001-figure-01.jpg").write_bytes(b"jpeg")
        (asset_directory / "page-001-figure-01-description.md").write_text("Beschreibung", encoding="utf-8")
        convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="overwrite", ocr_mode="off", ocr_language="de")
        markdown = (self.output_dir / "Quelle.md").read_text(encoding="utf-8")
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertIn("![Abbildung page-001-figure-01](Quelle.assets/page-001-figure-01.jpg)", markdown)
        self.assertIn("[Bildbeschreibung bearbeiten](Quelle.assets/page-001-figure-01-description.md)", markdown)
        self.assertEqual(manifest["artifacts"]["assets"][0]["page"]["page_number"], 1)
        self.assertEqual(manifest["artifacts"]["assets"][0]["description_path"], "Quelle.assets/page-001-figure-01-description.md")
        self.assertEqual(manifest["artifacts"]["content_references"][-1]["asset_id"], "page-001-figure-01")

    @patch("app.conversion_service.extract_simple_tables")
    @patch("app.conversion_service.export_embedded_images", return_value=ImageExportOutcome())
    @patch("app.conversion_service.extract_pdf_pages")
    def test_writes_simple_table_and_manifest_reference(self, extract_pages, _export_images, extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Siehe Table 1.", 1, 1),)
        extract_tables.return_value = TableExtractionOutcome(tables=(DocumentTable("page-001-table-01", PageReference(1), ("Name", "Wert"), (("Alpha", "1"),)),))
        convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")
        markdown = (self.output_dir / "Quelle.md").read_text(encoding="utf-8")
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertIn("| Name | Wert |", markdown)
        self.assertEqual(manifest["artifacts"]["content_references"][-1], {"kind": "table", "page": {"page_number": 1}})
        self.assertEqual(manifest["artifacts"]["references"], [{"kind": "table", "label": "Table 1", "page": {"page_number": 1}, "target_page": {"page_number": 1}, "target_id": "page-001-table-01"}])

    @patch("app.conversion_service.extract_simple_tables")
    @patch("app.conversion_service.export_embedded_images")
    @patch("app.conversion_service.extract_pdf_pages")
    def test_propagates_image_and_table_warnings_to_manifest(self, extract_pages, export_images, extract_tables) -> None:
        extract_pages.return_value = (ExtractedPage(1, "Inhalt", 1, 1), ExtractedPage(2, "Tabelle", 1, 1))
        export_images.return_value = ImageExportOutcome(warnings=(
            ConversionWarning("UNSUPPORTED_EMBEDDED_IMAGE", "Bild konnte nicht sicher exportiert werden.", page=PageReference(1)),
        ))
        extract_tables.return_value = TableExtractionOutcome(warnings=(
            ConversionWarning("UNSUPPORTED_TABLE_STRUCTURE", "Tabelle konnte nicht sicher übertragen werden.", page=PageReference(2)),
        ))

        run = convert_pdf(input_path=self.source_path, output_dir=self.output_dir, on_conflict="error", ocr_mode="off", ocr_language="de")
        manifest = json.loads((self.output_dir / "Quelle.conversion.json").read_text(encoding="utf-8"))

        self.assertEqual(run.result.status, ConversionStatus.PARTIAL)
        self.assertEqual(
            {(warning.code, warning.page.page_number) for warning in run.result.warnings},
            {("UNSUPPORTED_EMBEDDED_IMAGE", 1), ("UNSUPPORTED_TABLE_STRUCTURE", 2)},
        )
        self.assertEqual(manifest["quality"]["status"], "warning")
        self.assertEqual(
            {(warning["code"], warning["page"]["page_number"]) for warning in manifest["quality"]["warnings"]},
            {("UNSUPPORTED_EMBEDDED_IMAGE", 1), ("UNSUPPORTED_TABLE_STRUCTURE", 2)},
        )


if __name__ == "__main__": unittest.main()
