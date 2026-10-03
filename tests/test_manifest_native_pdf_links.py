"""Tests für den Manifestvertrag lokaler nativer PDF-Links."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import unittest

from app.manifest import build_manifest
from app.models import ConversionStatus, NativePdfLink, PageReference, PdfAnnotationRect, SourceDocument


class ManifestNativePdfLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SourceDocument(
            path=Path("C:/sources/Quelle.pdf"), media_type="application/pdf", size_bytes=10,
            sha256="a" * 64, modified_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
        )
        self.timestamp = datetime(2026, 9, 23, tzinfo=timezone.utc)

    def test_records_versioned_links_with_title_assignment_status(self) -> None:
        manifest = build_manifest(
            source=self.source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"),
            blocks=(), assets=(), tables=(),
            native_pdf_links=(
                NativePdfLink("https://example.org/titel", PageReference(10), PdfAnnotationRect(1, 2, 3, 4), visible_title="Belegter Titel"),
                NativePdfLink("https://example.org/neutral", PageReference(11), PdfAnnotationRect(5, 6, 7, 8)),
            ),
            warnings=(), started_at=self.timestamp, completed_at=self.timestamp,
        )

        self.assertEqual(
            manifest["artifacts"]["native_pdf_links"],
            {
                "schema_version": "1.0",
                "items": [
                    {
                        "target_url": "https://example.org/titel", "page": {"page_number": 10},
                        "annotation_rect": {"left": 1, "bottom": 2, "right": 3, "top": 4},
                        "source": "native_pdf_link_annotation", "visible_title": "Belegter Titel",
                        "title_assignment_status": "geometrically_verified",
                    },
                    {
                        "target_url": "https://example.org/neutral", "page": {"page_number": 11},
                        "annotation_rect": {"left": 5, "bottom": 6, "right": 7, "top": 8},
                        "source": "native_pdf_link_annotation", "title_assignment_status": "neutral_page_label",
                    },
                ],
            },
        )

    def test_rejects_unsafe_url_non_pdf_source_and_unsafe_markdown_path(self) -> None:
        link = NativePdfLink("http://example.org/", PageReference(1), PdfAnnotationRect(1, 2, 3, 4))
        with self.assertRaisesRegex(ValueError, "sicheres externes HTTPS-Ziel"):
            build_manifest(source=self.source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"), blocks=(), assets=(), tables=(), native_pdf_links=(link,), started_at=self.timestamp, completed_at=self.timestamp)
        with self.assertRaisesRegex(ValueError, "PDF-Primärquelle"):
            build_manifest(source=SourceDocument(Path("C:/sources/Quelle.txt"), "text/plain", 10, "a" * 64, self.timestamp), status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"), blocks=(), assets=(), tables=(), native_pdf_links=(NativePdfLink("https://example.org/", PageReference(1), PdfAnnotationRect(1, 2, 3, 4)),), started_at=self.timestamp, completed_at=self.timestamp)
        with self.assertRaisesRegex(ValueError, "sicher relativ"):
            build_manifest(source=self.source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("../Quelle.md"), blocks=(), assets=(), tables=(), started_at=self.timestamp, completed_at=self.timestamp)


if __name__ == "__main__":
    unittest.main()
