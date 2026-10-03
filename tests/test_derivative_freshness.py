"""Ablauf-Tests für die Aktualität vorhandener Konvertierungsderivate."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.artifact_paths import plan_artifact_paths
from app.conflict_policy import ConflictAction, resolve_conflict
from app.source_fingerprint import SourceFingerprintError, fingerprint_source


class DerivativeFreshnessTests(unittest.TestCase):
    """Verbindet Quellprüfung, Fingerabdruck und Update-Entscheidung."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF-1.7\nAusgangsinhalt")
        self.paths = plan_artifact_paths(
            source_path=self.source_path,
            output_dir=self.root / "ausgabe",
        )
        self.source = fingerprint_source(self.source_path, media_type="application/pdf")
        self._write_derivative_for(self.source)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_unchanged_source_reuses_existing_derivative(self) -> None:
        current_source = fingerprint_source(self.source_path, media_type="application/pdf")

        resolution = resolve_conflict(
            mode="update",
            source=current_source,
            artifact_paths=self.paths,
        )

        self.assertEqual(resolution.action, ConflictAction.REUSE)

    def test_changed_source_marks_existing_derivative_for_replacement(self) -> None:
        self.source_path.write_bytes(b"%PDF-1.7\nAktualisierter Inhalt")
        current_source = fingerprint_source(self.source_path, media_type="application/pdf")

        resolution = resolve_conflict(
            mode="update",
            source=current_source,
            artifact_paths=self.paths,
        )

        self.assertEqual(resolution.action, ConflictAction.REPLACE)

    def test_missing_source_stops_before_derivative_reuse(self) -> None:
        self.source_path.unlink()

        with self.assertRaises(SourceFingerprintError):
            fingerprint_source(self.source_path, media_type="application/pdf")

        self.assertTrue(self.paths.markdown_path.is_file())
        self.assertTrue(self.paths.manifest_path.is_file())

    def _write_derivative_for(self, source) -> None:
        self.paths.markdown_path.parent.mkdir()
        self.paths.markdown_path.write_text("# Vorhandenes Ergebnis", encoding="utf-8")
        self.paths.manifest_path.write_text(
            json.dumps(
                {
                    "source": {
                        "path": str(source.path),
                        "size_bytes": source.size_bytes,
                        "sha256": source.sha256,
                        "modified_at": source.modified_at.isoformat(),
                    }
                }
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
