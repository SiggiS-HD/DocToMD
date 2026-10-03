"""Zusammenhängende, vollständig lokale Regressionen für den Cloud-Vertrag."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.artifact_paths import plan_artifact_paths
from app.artifact_writer import write_cloud_markdown_derivative
from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_document_prompt import build_cloud_markdown_instructions
from app.cloud_markdown_validation import CloudMarkdownValidationError, validate_cloud_markdown_response
from app.conflict_policy import ArtifactConflictError, resolve_conflict
from app.manifest import build_manifest
from app.models import ConversionStatus
from app.openai_cloud_document import request_document_response
from app.source_fingerprint import fingerprint_source


class _Response:
    """Kontextmanager-kompatible, lokale Ersatzantwort für ``urlopen``."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class CloudDocumentRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @patch("app.openai_cloud_document.urlopen")
    def test_mocked_cloud_flow_keeps_source_and_local_markdown_separate(self, urlopen) -> None:
        urlopen.side_effect = [
            _Response({"id": "file_test"}),
            _Response(
                {
                    "id": "resp_test",
                    "model": "gpt-5.6-terra",
                    "status": "completed",
                    "output_text": "<!-- doctomd:page=1 -->\n\n# Titel\n\nText.",
                    "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
                }
            ),
            _Response({"id": "file_test", "deleted": True}),
        ]
        config = CloudDocumentConfig(
            mode=CloudDocumentMode.OPENAI,
            model_id="gpt-5.6-terra",
            timeout_seconds=120,
            max_output_tokens=20_000,
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            original_bytes = "%PDF-1.7\nPrimärquelle".encode("utf-8")
            source_path.write_bytes(original_bytes)
            paths = plan_artifact_paths(source_path=source_path, output_dir=root / "ausgabe")
            paths.markdown_path.parent.mkdir(parents=True)
            paths.markdown_path.write_text("# Lokaler Export\n", encoding="utf-8")

            cloud_response = request_document_response(
                source_path=source_path,
                model_id=config.model_id or "",
                timeout_seconds=config.timeout_seconds,
                max_output_tokens=config.max_output_tokens,
                instructions=build_cloud_markdown_instructions(),
            )
            markdown = validate_cloud_markdown_response(
                response=cloud_response.payload,
                expected_page_count=1,
            )
            write_cloud_markdown_derivative(
                source_path=source_path,
                cloud_markdown_path=paths.cloud_markdown_path,
                content=markdown.content,
            )
            source = fingerprint_source(source_path, media_type="application/pdf")
            manifest = build_manifest(
                source=source,
                status=ConversionStatus.SUCCESS,
                markdown_path=PurePosixPath(paths.markdown_path.name),
                cloud_markdown_path=PurePosixPath(paths.cloud_markdown_path.name),
                cloud_document_telemetry=cloud_response.telemetry,
                blocks=(),
                assets=(),
                tables=(),
                warnings=(),
                started_at=cloud_response.telemetry.started_at,
                completed_at=cloud_response.telemetry.completed_at,
                ocr_mode="off",
                ocr_language="de",
            )

            self.assertEqual(config.public_options()["mode"], "openai")
            self.assertEqual(paths.cloud_markdown_path.read_text(encoding="utf-8"), markdown.content)
            self.assertEqual(paths.markdown_path.read_text(encoding="utf-8"), "# Lokaler Export\n")
            self.assertEqual(source_path.read_bytes(), original_bytes)
            self.assertEqual(manifest["artifacts"]["cloud_markdown_path"], "Quelle.cloud.md")
            self.assertEqual(manifest["conversion"]["cloud_document"]["response_id"], "resp_test")

        self.assertEqual(urlopen.call_count, 3)
        response_payload = json.loads(urlopen.call_args_list[1].args[0].data.decode("utf-8"))
        self.assertEqual(response_payload["model"], "gpt-5.6-terra")
        self.assertFalse(response_payload["store"])
        self.assertEqual(response_payload["max_output_tokens"], 20_000)

    @patch("app.openai_cloud_document.urlopen")
    def test_incomplete_mocked_response_creates_no_cloud_derivative(self, urlopen) -> None:
        urlopen.side_effect = [
            _Response({"id": "file_test"}),
            _Response({"id": "resp_test", "model": "gpt-5.6-terra", "status": "incomplete"}),
            _Response({"id": "file_test", "deleted": True}),
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            original_bytes = "%PDF-1.7\nPrimärquelle".encode("utf-8")
            source_path.write_bytes(original_bytes)
            paths = plan_artifact_paths(source_path=source_path, output_dir=root / "ausgabe")
            paths.markdown_path.parent.mkdir(parents=True)
            paths.markdown_path.write_text("# Lokaler Export\n", encoding="utf-8")

            cloud_response = request_document_response(
                source_path=source_path,
                model_id="gpt-5.6-terra",
                timeout_seconds=120,
                max_output_tokens=20_000,
                instructions="Test",
            )
            with self.assertRaisesRegex(CloudMarkdownValidationError, "unvollständig"):
                validate_cloud_markdown_response(response=cloud_response.payload)

            self.assertFalse(paths.cloud_markdown_path.exists())
            self.assertEqual(paths.markdown_path.read_text(encoding="utf-8"), "# Lokaler Export\n")
            self.assertEqual(source_path.read_bytes(), original_bytes)

        self.assertEqual(urlopen.call_count, 3)

    def test_existing_cloud_derivative_is_a_conflict_without_explicit_overwrite(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            original_bytes = "%PDF-1.7\nPrimärquelle".encode("utf-8")
            source_path.write_bytes(original_bytes)
            paths = plan_artifact_paths(source_path=source_path, output_dir=root / "ausgabe")
            paths.cloud_markdown_path.parent.mkdir(parents=True)
            paths.cloud_markdown_path.write_text("# Bestehendes Cloud-Derivat\n", encoding="utf-8")
            source = fingerprint_source(source_path, media_type="application/pdf")

            with self.assertRaises(ArtifactConflictError):
                resolve_conflict(mode="error", source=source, artifact_paths=paths)

            self.assertEqual(paths.cloud_markdown_path.read_text(encoding="utf-8"), "# Bestehendes Cloud-Derivat\n")
            self.assertEqual(source_path.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
