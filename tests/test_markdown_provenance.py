"""Tests für den portablen Provenienzblock in Markdown-Derivaten."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.markdown_provenance import add_provenance_block, strip_provenance_block
from app.models import SourceDocument


class MarkdownProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.source = SourceDocument(
            Path(self.directory.name) / "Mathe1.pdf",
            "application/pdf",
            1,
            "a" * 64,
            datetime(2026, 10, 2, tzinfo=timezone.utc),
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_adds_portable_source_metadata_without_the_local_path(self) -> None:
        result = add_provenance_block(
            content="<!-- doctomd:page=1 -->\nInhalt\n",
            source=self.source,
            derivative_kind="cloud",
        )

        self.assertIn('doctomd_source_document: "Mathe1.pdf"', result)
        self.assertIn("doctomd_source_sha256: " + "a" * 64, result)
        self.assertIn("doctomd_derivative_kind: cloud", result)
        self.assertNotIn(self.directory.name, result)
        self.assertEqual(strip_provenance_block(result), "<!-- doctomd:page=1 -->\nInhalt\n")

    def test_replaces_its_own_block_without_duplication(self) -> None:
        initial = add_provenance_block(
            content="<!-- doctomd:page=1 -->\nInhalt\n",
            source=self.source,
            derivative_kind="local",
        )
        result = add_provenance_block(content=initial, source=self.source, derivative_kind="cloud")

        self.assertEqual(result.count("doctomd_source_document:"), 1)
        self.assertIn("doctomd_derivative_kind: cloud", result)


if __name__ == "__main__":
    unittest.main()
