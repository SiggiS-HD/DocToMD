"""Tests für den versionsgebundenen lokalen Wiederverwendungskontext."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest

from app.local_reuse_context import LocalReuseContextError, build_local_reuse_metadata, rehydrate_local_reuse_context
from app.manifest import build_manifest
from app.models import Asset, AssetKind, ConversionStatus, ConversionWarning, NativePdfLink, PageReference, PdfAnnotationRect
from app.source_fingerprint import fingerprint_source


class LocalReuseContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF-1.7\nTest")
        self.markdown_path = self.root / "Quelle.md"
        self.markdown = (
            "<!-- doctomd:page=1 -->\n\n# Titel\n\n"
            "<!-- doctomd:page=2 -->\n\nText\n\n"
            "<!-- doctomd:native-pdf-links page=2 -->\n**Lokale PDF-Links**\n"
            "- [Lokaler Titel](<https://example.org/regel>)\n"
        )
        self.markdown_path.write_text(self.markdown, encoding="utf-8")
        assets = self.root / "Quelle.assets"
        assets.mkdir()
        (assets / "figure.png").write_bytes(b"PNG")
        (assets / "figure-description.md").write_text("Beschreibung", encoding="utf-8")
        self.asset = Asset(
            "page-001-figure-01", AssetKind.IMAGE, PurePosixPath("Quelle.assets/figure.png"),
            PageReference(1), description_path=PurePosixPath("Quelle.assets/figure-description.md"),
        )
        self.link = NativePdfLink(
            "https://example.org/regel", PageReference(2), PdfAnnotationRect(1, 2, 3, 4),
            visible_title="Lokaler Titel",
        )
        self.manifest_path = self.root / "Quelle.conversion.json"
        self._write_manifest()

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _write_manifest(self) -> None:
        source = fingerprint_source(self.source_path, media_type="application/pdf")
        timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
        manifest = build_manifest(
            source=source, status=ConversionStatus.PARTIAL, markdown_path=PurePosixPath("Quelle.md"),
            markdown_content=self.markdown, blocks=(), assets=(self.asset,), tables=(),
            native_pdf_links=(self.link,),
            warnings=(ConversionWarning("OCR_LOW_CONFIDENCE", "OCR unsicher.", page=PageReference(2)),),
            started_at=timestamp, completed_at=timestamp,
        )
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_rehydrates_only_verified_local_basis(self) -> None:
        context = rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)

        self.assertEqual(context.page_numbers, (1, 2))
        self.assertEqual(context.assets, (self.asset,))
        self.assertEqual(context.native_pdf_links, (self.link,))
        self.assertEqual(context.warnings[0].code, "OCR_LOW_CONFIDENCE")

    def test_rejects_changed_source_or_markdown(self) -> None:
        self.source_path.write_bytes("%PDF-1.7\nGeändert".encode("utf-8"))
        with self.assertRaisesRegex(LocalReuseContextError, "Primärquelle"):
            rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)

        self.source_path.write_bytes(b"%PDF-1.7\nTest")
        self._write_manifest()
        self.markdown_path.write_text(self.markdown + "\nManuelle Änderung\n", encoding="utf-8")
        with self.assertRaisesRegex(LocalReuseContextError, "Markdown wurde"):
            rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)

    def test_rejects_unsafe_or_missing_artifacts_and_bad_page_markers(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["assets"][0]["path"] = "../fremd.png"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(LocalReuseContextError, "sicherer relativer Pfad"):
            rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)

        self._write_manifest()
        self.markdown_path.write_text("<!-- doctomd:page=2 -->\n", encoding="utf-8")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["local_reuse"] = {
            "schema_version": "1.0",
            "markdown_sha256": hashlib.sha256(self.markdown_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            "page_numbers": [2],
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(LocalReuseContextError, "lückenlosen Seitenmarker"):
            rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)

    def test_rejects_inconsistent_quality_and_native_link_coverage(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["quality"]["status"] = "ok"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(LocalReuseContextError, "Qualitätsstatus"):
            rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)

        self._write_manifest()
        self.markdown_path.write_text(
            self.markdown.replace("- [Lokaler Titel](<https://example.org/regel>)\n", ""),
            encoding="utf-8",
        )
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["artifacts"]["local_reuse"] = build_local_reuse_metadata(
            markdown=self.markdown_path.read_text(encoding="utf-8")
        )
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(LocalReuseContextError, "Native-PDF-Linkliste"):
            rehydrate_local_reuse_context(source_path=self.source_path, manifest_path=self.manifest_path)


if __name__ == "__main__":
    unittest.main()
