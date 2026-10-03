"""Unit-Tests für stabile Namen abgeleiteter Artefakte."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.artifact_paths import ArtifactPlanningError, plan_artifact_paths


class ArtifactPathTests(unittest.TestCase):
    """Prüft die vorhersagbare und quellsichere Artefaktplanung."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source_path = self.root / "Bericht.final.pdf"
        self.source_path.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_plans_standard_artifact_names_in_output_directory(self) -> None:
        output_dir = self.root / "ergebnisse"

        paths = plan_artifact_paths(source_path=self.source_path, output_dir=output_dir)

        self.assertEqual(paths.markdown_path, output_dir.resolve() / "Bericht.final.md")
        self.assertEqual(paths.assets_dir, output_dir.resolve() / "Bericht.final.assets")
        self.assertFalse(hasattr(paths, "corrections_path"))
        self.assertEqual(
            paths.manifest_path,
            output_dir.resolve() / "Bericht.final.conversion.json",
        )
        self.assertEqual(paths.cloud_markdown_path, output_dir.resolve() / "Bericht.final.cloud.md")
        self.assertEqual(paths.cloud_run_state_path, output_dir.resolve() / "Bericht.final.cloud-run.json")

    def test_preserves_non_ascii_source_name(self) -> None:
        source_path = self.root / "Übersicht 2026.pdf"
        source_path.write_bytes(b"%PDF")

        paths = plan_artifact_paths(source_path=source_path, output_dir=self.root / "ausgabe")

        self.assertEqual(paths.markdown_path.name, "Übersicht 2026.md")
        self.assertEqual(paths.assets_dir.name, "Übersicht 2026.assets")
        self.assertEqual(paths.manifest_path.name, "Übersicht 2026.conversion.json")
        self.assertEqual(paths.cloud_markdown_path.name, "Übersicht 2026.cloud.md")
        self.assertEqual(paths.cloud_run_state_path.name, "Übersicht 2026.cloud-run.json")

    def test_rejects_a_derived_path_that_would_replace_source(self) -> None:
        markdown_source = self.root / "Quelle.md"
        markdown_source.write_text("Primärquelle", encoding="utf-8")

        with self.assertRaises(ArtifactPlanningError):
            plan_artifact_paths(source_path=markdown_source, output_dir=self.root)


if __name__ == "__main__":
    unittest.main()
