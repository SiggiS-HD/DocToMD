"""Tests für die rein lokale Konvertierungsbewertung."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pypdf import PdfWriter

from app.conversion_review_service import write_conversion_review
from app.source_fingerprint import fingerprint_source


class ConversionReviewServiceTests(unittest.TestCase):
    def test_writes_manifest_based_review_without_changing_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as stream:
                writer.write(stream)
            source = fingerprint_source(source_path, media_type="application/pdf")
            manifest_path = root / "Quelle.conversion.json"
            manifest = {
                "source": {"sha256": source.sha256, "path": str(source.path)},
                "conversion": {"status": "success", "started_at": "2026-09-25T10:00:00+00:00", "completed_at": "2026-09-25T10:01:02.500+00:00", "cloud_document": {"mode": "batched", "batches": [{"duration_ms": 1_250}, {"duration_ms": 2_500}]}},
                "artifacts": {"markdown_path": "Quelle.md", "assets": [], "native_pdf_links": {"items": []}, "cloud_markdown_path": "Quelle.cloud.md", "local_reuse": {"page_numbers": [1]}},
                "quality": {"status": "warning", "warnings": [{"code": "UNREADABLE_PDF_GLYPHS", "page": {"page_number": 1}}]},
                "rag_readiness": {"status": "review_required"},
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            before = manifest_path.read_bytes()

            review_path = write_conversion_review(input_path=source_path, output_dir=root, overwrite=False)

            content = review_path.read_text(encoding="utf-8")
            self.assertEqual(manifest_path.read_bytes(), before)
            self.assertIn("# Konvertierungsbewertung", content)
            self.assertIn("Validierte Batches: 2", content)
            self.assertIn("Seiten: 1", content)
            self.assertIn("`UNREADABLE_PDF_GLYPHS`", content)
            self.assertIn("Lokale Verarbeitung: 1 min 2,500 s", content)
            self.assertIn("Cloud-API-Laufzeit (Summe): 3,750 s", content)

    def test_rejects_manifest_for_a_different_source(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as stream:
                writer.write(stream)
            (root / "Quelle.conversion.json").write_text(json.dumps({"source": {"sha256": "wrong"}}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unveränderten Primärquelle"):
                write_conversion_review(input_path=source_path, output_dir=root, overwrite=False)


if __name__ == "__main__":
    unittest.main()
