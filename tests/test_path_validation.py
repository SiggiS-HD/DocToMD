"""Unit-Tests für Quell- und Ausgabewegvalidierung."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.path_validation import (
    PathValidationError,
    ensure_not_source_target,
    validate_conversion_paths,
)


class PathValidationTests(unittest.TestCase):
    """Prüft zulässige Pfade und den Schutz der Primärquelle."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_accepts_new_output_directory_below_existing_directory(self) -> None:
        output_dir = self.root / "ergebnis" / "neu"

        paths = validate_conversion_paths(self.source_path, output_dir)

        self.assertEqual(paths.source_path, self.source_path.resolve())
        self.assertEqual(paths.output_dir, output_dir.resolve())

    def test_rejects_missing_source_file(self) -> None:
        with self.assertRaises(PathValidationError):
            validate_conversion_paths(self.root / "fehlt.pdf", self.root / "ergebnis")

    def test_rejects_directory_as_source(self) -> None:
        with self.assertRaises(PathValidationError):
            validate_conversion_paths(self.root, self.root / "ergebnis")

    def test_rejects_existing_file_as_output_directory(self) -> None:
        output_file = self.root / "kein-ordner"
        output_file.write_text("kein Verzeichnis", encoding="utf-8")

        with self.assertRaises(PathValidationError):
            validate_conversion_paths(self.source_path, output_file)

    def test_rejects_write_target_equal_to_source(self) -> None:
        with self.assertRaises(PathValidationError):
            ensure_not_source_target(self.source_path, self.source_path)

    def test_allows_derived_target_beside_source(self) -> None:
        target_path = self.root / "Quelle.md"

        resolved_target = ensure_not_source_target(target_path, self.source_path)

        self.assertEqual(resolved_target, target_path.resolve())


if __name__ == "__main__":
    unittest.main()
