"""Unit-Tests für atomisches Schreiben abgeleiteter Artefakte."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.artifact_writer import ArtifactWriteError, write_cloud_markdown_derivative, write_conversion_documents, write_conversion_manifest


class ArtifactWriterTests(unittest.TestCase):
    """Prüft Veröffentlichungsreihenfolge, Inhalt und Konfliktschutz."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Quelle.pdf"
        self.source_path.write_bytes(b"%PDF")
        self.markdown_path = self.root / "ausgabe" / "Quelle.md"
        self.manifest_path = self.root / "ausgabe" / "Quelle.conversion.json"
        self.manifest = {"manifest_schema_version": "1.0", "source": {"path": "Quelle.pdf"}}

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_writes_markdown_and_manifest_as_utf8(self) -> None:
        write_conversion_documents(
            source_path=self.source_path,
            markdown_path=self.markdown_path,
            markdown_content="# Übersicht\n",
            manifest_path=self.manifest_path,
            manifest=self.manifest,
        )

        self.assertEqual(self.markdown_path.read_text(encoding="utf-8"), "# Übersicht\n")
        self.assertEqual(json.loads(self.manifest_path.read_text(encoding="utf-8")), self.manifest)
        self.assertEqual(list(self.markdown_path.parent.glob(".doctomd-*.tmp")), [])

    def test_refuses_existing_artifact_without_overwrite(self) -> None:
        self.markdown_path.parent.mkdir()
        self.markdown_path.write_text("bestehend", encoding="utf-8")

        with self.assertRaises(ArtifactWriteError):
            write_conversion_documents(
                source_path=self.source_path,
                markdown_path=self.markdown_path,
                markdown_content="neu",
                manifest_path=self.manifest_path,
                manifest=self.manifest,
            )

        self.assertEqual(self.markdown_path.read_text(encoding="utf-8"), "bestehend")
        self.assertFalse(self.manifest_path.exists())

    def test_overwrite_replaces_existing_derived_files(self) -> None:
        self.markdown_path.parent.mkdir()
        self.markdown_path.write_text("alt", encoding="utf-8")
        self.manifest_path.write_text("{}", encoding="utf-8")

        write_conversion_documents(
            source_path=self.source_path,
            markdown_path=self.markdown_path,
            markdown_content="neu",
            manifest_path=self.manifest_path,
            manifest=self.manifest,
            overwrite=True,
        )

        self.assertEqual(self.markdown_path.read_text(encoding="utf-8"), "neu")
        self.assertEqual(json.loads(self.manifest_path.read_text(encoding="utf-8")), self.manifest)

    def test_rejects_a_write_to_the_primary_source(self) -> None:
        with self.assertRaises(ArtifactWriteError):
            write_conversion_documents(
                source_path=self.source_path,
                markdown_path=self.source_path,
                markdown_content="unzulässig",
                manifest_path=self.manifest_path,
                manifest=self.manifest,
            )

        self.assertEqual(self.source_path.read_bytes(), b"%PDF")

    def test_writes_cloud_markdown_separately_and_requires_explicit_overwrite(self) -> None:
        cloud_markdown_path = self.root / "ausgabe" / "Quelle.cloud.md"
        write_cloud_markdown_derivative(
            source_path=self.source_path,
            cloud_markdown_path=cloud_markdown_path,
            content="# Cloud-Ergebnis\n",
        )

        self.assertEqual(cloud_markdown_path.read_text(encoding="utf-8"), "# Cloud-Ergebnis\n")
        self.assertEqual(self.source_path.read_bytes(), b"%PDF")
        with self.assertRaises(ArtifactWriteError):
            write_cloud_markdown_derivative(
                source_path=self.source_path,
                cloud_markdown_path=cloud_markdown_path,
                content="# Ersetzt\n",
            )

    def test_updates_only_manifest_without_rewriting_local_markdown(self) -> None:
        markdown_path = self.root / "ausgabe" / "Quelle.md"
        manifest_path = self.root / "ausgabe" / "Quelle.conversion.json"
        write_conversion_documents(
            source_path=self.source_path,
            markdown_path=markdown_path,
            markdown_content="# Lokale Basis\n",
            manifest_path=manifest_path,
            manifest=self.manifest,
        )

        updated_manifest = {**self.manifest, "cloud": {"status": "success"}}
        write_conversion_manifest(
            source_path=self.source_path,
            manifest_path=manifest_path,
            manifest=updated_manifest,
            overwrite=True,
        )

        self.assertEqual(markdown_path.read_text(encoding="utf-8"), "# Lokale Basis\n")
        self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8")), updated_manifest)


if __name__ == "__main__":
    unittest.main()
