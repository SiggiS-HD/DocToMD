"""Tests für autoritative lokale Markdown-Bildreferenzen."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest

from app.asset_reference_validation import AssetReferenceValidationError, validate_cloud_model_has_no_image_references, validate_markdown_image_references
from app.models import Asset, AssetKind, PageReference


class AssetReferenceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.relative = PurePosixPath("Quelle.assets/page-001-figure-01.png")
        target = self.root / Path(*self.relative.parts)
        target.parent.mkdir()
        target.write_bytes(b"png")
        self.asset = Asset("page-001-figure-01", AssetKind.IMAGE, self.relative, PageReference(1))

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_accepts_an_existing_authoritative_asset_path(self) -> None:
        validate_markdown_image_references(
            markdown="![Figure](Quelle.assets/page-001-figure-01.png)",
            assets=(self.asset,), output_dir=self.root, error_code="TEST",
        )

    def test_rejects_an_invented_cloud_image_path(self) -> None:
        with self.assertRaises(AssetReferenceValidationError) as raised:
            validate_markdown_image_references(
                markdown="![Figure](figure-2.png)",
                assets=(self.asset,), output_dir=self.root, error_code="CLOUD_UNAUTHORIZED_IMAGE_REFERENCE",
            )

        self.assertEqual(raised.exception.code, "CLOUD_UNAUTHORIZED_IMAGE_REFERENCE")

    def test_rejects_an_external_html_image(self) -> None:
        with self.assertRaises(AssetReferenceValidationError):
            validate_markdown_image_references(
                markdown='<img src="https://example.org/figure.png">',
                assets=(self.asset,), output_dir=self.root, error_code="CLOUD_UNAUTHORIZED_IMAGE_REFERENCE",
            )

    def test_rejects_any_image_reference_from_the_raw_cloud_response(self) -> None:
        with self.assertRaises(AssetReferenceValidationError) as raised:
            validate_cloud_model_has_no_image_references(markdown="![Figure](figure-2.png)")

        self.assertEqual(raised.exception.code, "CLOUD_UNAUTHORIZED_IMAGE_REFERENCE")
        self.assertIn("Bitte starten Sie die Cloud-Ableitung erneut", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
