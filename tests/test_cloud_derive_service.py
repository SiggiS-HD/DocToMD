"""Regressionen für die Cloud-Ableitung aus einer lokalen Basis."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.cloud_batch_execution import CloudBatchExecution
from app.cloud_derive_service import derive_cloud
from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_document_telemetry import CloudDocumentTelemetry
from app.cloud_document_prompt import CLOUD_DOCUMENT_PROMPT_VERSION
from app.cloud_markdown_validation import CloudMarkdownValidationError
from app.cloud_run_state import write_cloud_run_state
from app.manifest import build_manifest
from app.models import ConversionStatus
from app.openai_cloud_document import CloudDocumentResponse
from app.source_fingerprint import fingerprint_source


class CloudDeriveServiceTests(unittest.TestCase):
    def test_derives_from_local_context_without_local_pdf_pipeline(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF-1.7\nQuelle")
            markdown_path = root / "Quelle.md"
            markdown = "<!-- doctomd:page=1 -->\n# Lokale Basis\n"
            markdown_path.write_text(markdown, encoding="utf-8")
            source = fingerprint_source(source_path, media_type="application/pdf")
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            manifest = build_manifest(
                source=source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"),
                markdown_content=markdown, blocks=(), assets=(), tables=(), warnings=(),
                started_at=timestamp, completed_at=timestamp,
            )
            manifest_path = root / "Quelle.conversion.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            response = CloudDocumentResponse(
                {"id": "resp_test", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\n# Cloud\n"},
                CloudDocumentTelemetry("resp_test", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )
            events: list[tuple[str, str, str]] = []
            with patch("app.cloud_derive_service.request_document_response", return_value=response) as request:
                run = derive_cloud(
                    input_path=source_path, output_dir=root, on_conflict="error",
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    progress=lambda phase, status, message: events.append((phase, status, message)),
                )

            self.assertEqual(run.cloud_markdown_path, PurePosixPath("Quelle.cloud.md"))
            self.assertEqual(markdown_path.read_text(encoding="utf-8"), markdown)
            self.assertTrue((root / "Quelle.cloud.md").is_file())
            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["artifacts"]["cloud_markdown_path"], "Quelle.cloud.md")
            self.assertEqual(updated["conversion"]["cloud_document"]["response_id"], "resp_test")
            self.assertTrue(any(phase == "reuse" for phase, _, _ in events))
            request.assert_called_once()

    def test_resumes_matching_response_without_new_upload(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF-1.7\nQuelle")
            markdown = "<!-- doctomd:page=1 -->\n# Lokale Basis\n"
            (root / "Quelle.md").write_text(markdown, encoding="utf-8")
            source = fingerprint_source(source_path, media_type="application/pdf")
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            manifest = build_manifest(
                source=source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"),
                markdown_content=markdown, blocks=(), assets=(), tables=(), warnings=(),
                started_at=timestamp, completed_at=timestamp,
            )
            (root / "Quelle.conversion.json").write_text(json.dumps(manifest), encoding="utf-8")
            write_cloud_run_state(
                path=root / "Quelle.cloud-run.json",
                source=source,
                local_markdown_sha256=manifest["artifacts"]["local_reuse"]["markdown_sha256"],
                model_id="gpt-5.6-terra",
                prompt_version=CLOUD_DOCUMENT_PROMPT_VERSION,
                response_id="resp_pending",
            )
            response = CloudDocumentResponse(
                {"id": "resp_pending", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\n# Cloud\n"},
                CloudDocumentTelemetry("resp_pending", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )
            with patch("app.cloud_derive_service.request_document_response") as request, patch(
                "app.cloud_derive_service.retrieve_document_response", return_value=response
            ) as retrieve:
                derive_cloud(
                    input_path=source_path, output_dir=root, on_conflict="error",
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                )

            request.assert_not_called()
            retrieve.assert_called_once()
            self.assertFalse((root / "Quelle.cloud-run.json").exists())

    def test_does_not_publish_thin_cloud_derivative(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF-1.7\nQuelle")
            markdown = "<!-- doctomd:page=1 -->\n# Lokale Basis\n\nEin ausführlicher lokaler Absatz mit belegtem Inhalt.\n"
            (root / "Quelle.md").write_text(markdown, encoding="utf-8")
            source = fingerprint_source(source_path, media_type="application/pdf")
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            manifest = build_manifest(
                source=source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"),
                markdown_content=markdown, blocks=(), assets=(), tables=(), warnings=(),
                started_at=timestamp, completed_at=timestamp,
            )
            manifest_path = root / "Quelle.conversion.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            response = CloudDocumentResponse(
                {"id": "resp_test", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\n# Nur Überschrift\n"},
                CloudDocumentTelemetry("resp_test", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )
            with patch("app.cloud_derive_service.request_document_response", return_value=response):
                with self.assertRaisesRegex(CloudMarkdownValidationError, "zu dünn") as raised:
                    derive_cloud(
                        input_path=source_path, output_dir=root, on_conflict="error",
                        config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    )

            self.assertEqual(raised.exception.code, "CLOUD_MARKDOWN_CONTENT_INCOMPLETE")
            self.assertFalse((root / "Quelle.cloud.md").exists())
            self.assertNotIn("cloud_markdown_path", json.loads(manifest_path.read_text(encoding="utf-8"))["artifacts"])

    def test_uses_batch_executor_for_a_multi_batch_local_context(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF-1.7\nQuelle")
            markdown = "\n\n".join(
                f"<!-- doctomd:page={page} -->\nLokaler Inhalt {page}"
                for page in range(1, 8)
            )
            (root / "Quelle.md").write_text(markdown, encoding="utf-8")
            source = fingerprint_source(source_path, media_type="application/pdf")
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            manifest = build_manifest(
                source=source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"),
                markdown_content=markdown, blocks=(), assets=(), tables=(), warnings=(),
                started_at=timestamp, completed_at=timestamp,
            )
            (root / "Quelle.conversion.json").write_text(json.dumps(manifest), encoding="utf-8")
            execution = CloudBatchExecution(
                "\n\n".join(f"<!-- doctomd:page={page} -->\nCloud Inhalt {page}" for page in range(1, 8)),
                (),
            )
            with patch("app.cloud_derive_service.request_document_response") as request, patch(
                "app.cloud_derive_service.execute_cloud_batches", return_value=execution
            ) as batches:
                run = derive_cloud(
                    input_path=source_path, output_dir=root, on_conflict="error",
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                )

            request.assert_not_called()
            batches.assert_called_once()
            self.assertEqual(run.cloud_markdown_path, PurePosixPath("Quelle.cloud.md"))
            self.assertTrue((root / "Quelle.cloud.md").is_file())


if __name__ == "__main__":
    unittest.main()
