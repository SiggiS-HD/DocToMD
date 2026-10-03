"""Unit-Tests für Konflikt- und Wiederholungsentscheidungen."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.artifact_paths import plan_artifact_paths
from app.conflict_policy import (
    ArtifactConflictError,
    ConflictAction,
    resolve_conflict,
)
from app.source_fingerprint import fingerprint_source


class ConflictPolicyTests(unittest.TestCase):
    """Prüft sichere Entscheidungen ohne Schreibnebenwirkungen."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF-1.7")
        self.output_dir = self.root / "ausgabe"
        self.paths = plan_artifact_paths(source_path=self.source_path, output_dir=self.output_dir)
        self.source = fingerprint_source(self.source_path, media_type="application/pdf")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_creates_when_no_derived_artifacts_exist(self) -> None:
        resolution = resolve_conflict(
            mode="update",
            source=self.source,
            artifact_paths=self.paths,
        )

        self.assertEqual(resolution.action, ConflictAction.CREATE)
        self.assertFalse(resolution.overwrite)

    def test_error_mode_rejects_any_existing_derived_artifact(self) -> None:
        self.paths.markdown_path.parent.mkdir()
        self.paths.markdown_path.write_text("# Bestehend", encoding="utf-8")

        with self.assertRaises(ArtifactConflictError):
            resolve_conflict(mode="error", source=self.source, artifact_paths=self.paths)

    def test_error_mode_rejects_existing_cloud_derivative(self) -> None:
        self.paths.cloud_markdown_path.parent.mkdir()
        self.paths.cloud_markdown_path.write_text("# Cloud", encoding="utf-8")

        with self.assertRaises(ArtifactConflictError):
            resolve_conflict(mode="error", source=self.source, artifact_paths=self.paths)

    def test_overwrite_mode_allows_explicit_replacement(self) -> None:
        self.paths.markdown_path.parent.mkdir()
        self.paths.markdown_path.write_text("# Bestehend", encoding="utf-8")

        resolution = resolve_conflict(
            mode="overwrite",
            source=self.source,
            artifact_paths=self.paths,
        )

        self.assertEqual(resolution.action, ConflictAction.REPLACE)
        self.assertTrue(resolution.overwrite)

    def test_update_reuses_complete_derivative_for_unchanged_source(self) -> None:
        self._write_complete_derivative()

        resolution = resolve_conflict(
            mode="update",
            source=self.source,
            artifact_paths=self.paths,
        )

        self.assertEqual(resolution.action, ConflictAction.REUSE)

    def test_update_replaces_complete_derivative_for_changed_source(self) -> None:
        self._write_complete_derivative()
        self.source_path.write_bytes(b"%PDF-2.0 geaendert")
        changed_source = fingerprint_source(self.source_path, media_type="application/pdf")

        resolution = resolve_conflict(
            mode="update",
            source=changed_source,
            artifact_paths=self.paths,
        )

        self.assertEqual(resolution.action, ConflictAction.REPLACE)

    def test_update_rejects_incomplete_derivative(self) -> None:
        self.paths.markdown_path.parent.mkdir()
        self.paths.markdown_path.write_text("# Unvollständig", encoding="utf-8")

        with self.assertRaises(ArtifactConflictError):
            resolve_conflict(mode="update", source=self.source, artifact_paths=self.paths)

    def test_update_rejects_invalid_manifest(self) -> None:
        self.paths.markdown_path.parent.mkdir()
        self.paths.markdown_path.write_text("# Bestehend", encoding="utf-8")
        self.paths.manifest_path.write_text("kein JSON", encoding="utf-8")

        with self.assertRaises(ArtifactConflictError):
            resolve_conflict(mode="update", source=self.source, artifact_paths=self.paths)

    def _write_complete_derivative(self) -> None:
        self.paths.markdown_path.parent.mkdir()
        self.paths.markdown_path.write_text("# Ergebnis", encoding="utf-8")
        self.paths.manifest_path.write_text(
            json.dumps(
                {
                    "source": {
                        "path": str(self.source.path),
                        "size_bytes": self.source.size_bytes,
                        "sha256": self.source.sha256,
                        "modified_at": self.source.modified_at.isoformat(),
                    }
                }
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
