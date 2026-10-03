"""Unit-Tests für Quellfingerabdrücke."""

from __future__ import annotations

from datetime import timezone
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.source_fingerprint import SourceFingerprintError, fingerprint_source


class SourceFingerprintTests(unittest.TestCase):
    """Prüft Inhalt, Metadaten und Fehlerfälle des Quellfingerabdrucks."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"
        self.content = b"%PDF-1.7\\nBeispielinhalt"
        self.source_path.write_bytes(self.content)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_fingerprint_contains_path_hash_size_and_modified_time(self) -> None:
        fingerprint = fingerprint_source(self.source_path, media_type="application/pdf")

        self.assertEqual(fingerprint.path, self.source_path.resolve())
        self.assertEqual(fingerprint.media_type, "application/pdf")
        self.assertEqual(fingerprint.size_bytes, len(self.content))
        self.assertEqual(fingerprint.sha256, hashlib.sha256(self.content).hexdigest())
        self.assertIsNotNone(fingerprint.modified_at)
        self.assertEqual(fingerprint.modified_at.tzinfo, timezone.utc)

    def test_changed_content_has_a_different_fingerprint(self) -> None:
        first = fingerprint_source(self.source_path, media_type="application/pdf")
        self.source_path.write_bytes(b"%PDF-1.7\\nGeaenderter Inhalt")

        second = fingerprint_source(self.source_path, media_type="application/pdf")

        self.assertNotEqual(first.sha256, second.sha256)
        self.assertNotEqual(first.size_bytes, second.size_bytes)

    def test_missing_source_is_rejected(self) -> None:
        missing_path = self.root / "fehlt.pdf"

        with self.assertRaises(SourceFingerprintError):
            fingerprint_source(missing_path, media_type="application/pdf")


if __name__ == "__main__":
    unittest.main()
