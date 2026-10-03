"""Tests für die explizite lokale OCR-Auswahl."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from app.ocr_extract import OcrExtractionError, _ensure_tesseract_ready, _run_tesseract, apply_ocr_fallback
from app.pdf_extract import ExtractedPage


class OcrExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_path = Path("Quelle.pdf")

    @patch("app.ocr_extract.pdfium.PdfDocument")
    def test_auto_keeps_a_document_with_textlayer(self, pdf_document) -> None:
        pages = (ExtractedPage(1, "Digitaler Text", 2, 1),)

        result = apply_ocr_fallback(
            source_path=self.source_path,
            pages=pages,
            ocr_mode="auto",
            ocr_language="de",
        )

        self.assertEqual(result.pages, pages)
        pdf_document.assert_not_called()

    @patch("app.ocr_extract._extract_ocr_page")
    @patch("app.ocr_extract.pdfium.PdfDocument")
    def test_auto_uses_ocr_for_a_textless_pdf(self, pdf_document, extract_page) -> None:
        pages = (ExtractedPage(1, "", 0, 1), ExtractedPage(2, "", 0, 1))
        document = MagicMock()
        document.__len__.return_value = 2
        pdf_document.return_value = document
        extract_page.side_effect = (
            (ExtractedPage(1, "Erkannter Text", 2, 1), (90.0,)),
            (ExtractedPage(2, "Zweite Seite", 2, 1), (90.0,)),
        )

        result = apply_ocr_fallback(
            source_path=self.source_path,
            pages=pages,
            ocr_mode="auto",
            ocr_language="de-DE",
        )

        self.assertEqual([page.text for page in result.pages], ["Erkannter Text", "Zweite Seite"])
        pdf_document.assert_called_once_with(str(self.source_path))
        self.assertEqual(
            [call.kwargs for call in extract_page.call_args_list],
            [
                {"document": document, "page_number": 1, "language_code": "deu"},
                {"document": document, "page_number": 2, "language_code": "deu"},
            ],
        )

    @patch("app.ocr_extract._extract_ocr_page")
    @patch("app.ocr_extract.pdfium.PdfDocument")
    def test_force_uses_ocr_despite_existing_textlayer(self, pdf_document, extract_page) -> None:
        document = MagicMock()
        document.__len__.return_value = 1
        pdf_document.return_value = document
        extract_page.return_value = (ExtractedPage(1, "OCR", 1, 1), (90.0,))

        result = apply_ocr_fallback(
            source_path=self.source_path,
            pages=(ExtractedPage(1, "Digitaler Text", 2, 1),),
            ocr_mode="force",
            ocr_language="en",
        )

        self.assertEqual(result.pages[0].text, "OCR")
        self.assertEqual(extract_page.call_args.kwargs["language_code"], "eng")

    def test_rejects_unsupported_language_before_rendering(self) -> None:
        with self.assertRaisesRegex(OcrExtractionError, "nicht unterstützt"):
            apply_ocr_fallback(
                source_path=self.source_path,
                pages=(ExtractedPage(1, "", 0, 1),),
                ocr_mode="force",
                ocr_language="fr",
            )

    @patch("app.ocr_extract._extract_ocr_page")
    @patch("app.ocr_extract.pdfium.PdfDocument")
    def test_force_limits_ocr_to_selected_pages_and_warns_for_low_confidence(self, pdf_document, extract_page) -> None:
        document = MagicMock(); document.__len__.return_value = 2; pdf_document.return_value = document
        extract_page.return_value = (ExtractedPage(2, "Unsicher", 1, 1), (40.0,))

        result = apply_ocr_fallback(source_path=self.source_path, pages=(ExtractedPage(1, "Erste", 1, 1), ExtractedPage(2, "Zweite", 1, 1)), ocr_mode="force", ocr_language="de", ocr_pages="2", min_word_confidence=70)

        self.assertEqual([page.text for page in result.pages], ["Erste", "Unsicher"])
        self.assertEqual([(warning.code, warning.page.page_number) for warning in result.warnings], [("OCR_LOW_CONFIDENCE", 2)])

    @patch("app.ocr_extract.subprocess.run")
    def test_runs_tesseract_with_lstm_and_automatic_segmentation(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, stdout=b"level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t0\t0\t1\t1\t95\tErkannter\n5\t1\t1\t1\t1\t2\t0\t0\t1\t1\t92\tText\n", stderr=b"")

        text, confidences, layout = _run_tesseract(b"png", "deu")

        self.assertEqual(text, "Erkannter Text")
        self.assertEqual(confidences, (95.0, 92.0))
        self.assertIn('<pre class="doctomd-ocr-layout">', layout)
        self.assertEqual(
            run.call_args.args[0],
            ["tesseract", "stdin", "stdout", "--oem", "1", "--psm", "3", "-l", "deu", "tsv"],
        )
        self.assertEqual(run.call_args.kwargs["input"], b"png")

    @patch("app.ocr_extract.subprocess.run", side_effect=FileNotFoundError())
    def test_reports_missing_tesseract(self, _run) -> None:
        with self.assertRaisesRegex(OcrExtractionError, "nicht installiert"):
            _run_tesseract(b"png", "deu")

    @patch("app.ocr_extract.subprocess.run")
    def test_reports_missing_language_data_before_ocr(self, run) -> None:
        run.side_effect = (
            subprocess.CompletedProcess([], 0, stdout=b"tesseract 5\n", stderr=b""),
            subprocess.CompletedProcess([], 0, stdout=b"List of available languages\neng\nosd\n", stderr=b""),
        )

        with self.assertRaisesRegex(OcrExtractionError, "Sprachdaten 'deu' fehlen"):
            _ensure_tesseract_ready("deu")

    @patch("app.ocr_extract.subprocess.run", side_effect=FileNotFoundError())
    def test_reports_installation_guidance_before_ocr(self, _run) -> None:
        with self.assertRaisesRegex(OcrExtractionError, "Installieren Sie Tesseract 5"):
            _ensure_tesseract_ready("deu")


if __name__ == "__main__":
    unittest.main()
