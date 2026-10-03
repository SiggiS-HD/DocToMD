"""Regressionen für die lokale Nachrüstung alter Markdown-Derivate."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.provenance_migration_service import migrate_markdown_provenance
from app.source_fingerprint import fingerprint_source


class ProvenanceMigrationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source = self.root / "Quelle.pdf"
        self.source.write_bytes(b"%PDF-1.4\n")
        self.output = self.root / "Ausgabe"
        self.output.mkdir()
        fingerprint = fingerprint_source(self.source, media_type="application/pdf")
        manifest = {
            "manifest_schema_version": "1.0",
            "source": {
                "path": str(fingerprint.path),
                "media_type": fingerprint.media_type,
                "size_bytes": fingerprint.size_bytes,
                "sha256": fingerprint.sha256,
                "modified_at": fingerprint.modified_at.isoformat(),
            },
            "artifacts": {
                "markdown_path": "Quelle.md",
                "cloud_markdown_path": "Quelle.cloud.md",
            },
        }
        (self.output / "Quelle.md").write_text("<!-- doctomd:page=1 -->\nLokal\n", encoding="utf-8")
        (self.output / "Quelle.cloud.md").write_text("<!-- doctomd:page=1 -->\nCloud\n", encoding="utf-8")
        (self.output / "Quelle.conversion.json").write_text(json.dumps(manifest), encoding="utf-8")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_migrates_a_legacy_manifest_without_local_reuse(self) -> None:
        changed = migrate_markdown_provenance(input_path=self.source, output_dir=self.output)

        self.assertEqual([path.name for path in changed], ["Quelle.md", "Quelle.cloud.md"])
        self.assertIn('doctomd_source_document: "Quelle.pdf"', (self.output / "Quelle.md").read_text(encoding="utf-8"))
        self.assertIn("doctomd_derivative_kind: cloud", (self.output / "Quelle.cloud.md").read_text(encoding="utf-8"))
        manifest = json.loads((self.output / "Quelle.conversion.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["artifacts"]["local_reuse"]["page_numbers"], [1])

    def test_migrates_a_canonical_legacy_cloud_file_not_yet_in_the_manifest(self) -> None:
        manifest_path = self.output / "Quelle.conversion.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        del manifest["artifacts"]["cloud_markdown_path"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        changed = migrate_markdown_provenance(input_path=self.source, output_dir=self.output)

        self.assertEqual([path.name for path in changed], ["Quelle.md", "Quelle.cloud.md"])
        self.assertIn("doctomd_derivative_kind: cloud", (self.output / "Quelle.cloud.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
