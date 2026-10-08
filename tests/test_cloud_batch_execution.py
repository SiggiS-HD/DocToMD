"""Tests für temporäre PDF-Batches ohne echte Cloud-Anfrage."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import ANY, patch

from pypdf import PdfWriter

from app.cloud_batch_execution import execute_cloud_batches
from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_document_telemetry import CloudDocumentTelemetry, serialize_cloud_document_telemetry
from app.cloud_markdown_validation import CloudMarkdownValidationError
from app.cloud_run_state import CloudBatchRunEntry, load_matching_cloud_batch_run_state, write_cloud_batch_run_state
from app.math_batch_planning import plan_math_cloud_batches
from app.openai_cloud_document import CloudDocumentResponse, OpenAICloudDocumentError
from app.source_fingerprint import fingerprint_source


class CloudBatchExecutionTests(unittest.TestCase):
    def test_accepts_indented_page_markers_from_a_continued_local_list(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(2):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            markdown = "<!-- doctomd:page=1 -->\n- Ein Listenelement\n  <!-- doctomd:page=2 -->\n  wird auf Seite zwei fortgesetzt.\n"
            plan = plan_math_cloud_batches(markdown=markdown)
            source = fingerprint_source(source_path, media_type="application/pdf")
            timestamp = datetime(2026, 10, 8, tzinfo=timezone.utc)
            response = CloudDocumentResponse(
                {"id": "resp_indented", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\nCloud eins\n\n<!-- doctomd:page=2 -->\nCloud zwei"},
                CloudDocumentTelemetry("resp_indented", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )

            with patch("app.cloud_batch_execution.request_document_response", return_value=response):
                execution = execute_cloud_batches(
                    source_path=source_path,
                    source=source,
                    state_path=root / "Quelle.cloud-run.json",
                    local_markdown_sha256="local-markdown-sha256",
                    prompt_version="1.5",
                    plan=plan,
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    local_markdown=markdown,
                )

            self.assertEqual(execution.markdown.count("<!-- doctomd:page="), 2)

    def test_writes_validated_temporary_batches_and_merges_in_page_order(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            original_bytes = source_path.read_bytes()
            markdown = "\n\n".join(f"<!-- doctomd:page={page} -->\nText {page}" for page in range(1, 8))
            plan = plan_math_cloud_batches(markdown=markdown)
            source = fingerprint_source(source_path, media_type="application/pdf")
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            temporary_paths: list[Path] = []

            def request(**kwargs):
                path = kwargs["source_path"]
                temporary_paths.append(path)
                page_numbers = (1, 2, 3, 4, 5, 6) if path.name.startswith("batch-001") else (7,)
                output = "\n\n".join(f"<!-- doctomd:page={page} -->\nCloud {page}" for page in page_numbers)
                return CloudDocumentResponse(
                    {"id": f"resp_{page_numbers[0]}", "model": "gpt-5.6-terra", "status": "completed", "output_text": output},
                    CloudDocumentTelemetry(f"resp_{page_numbers[0]}", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
                )

            with patch("app.cloud_batch_execution.request_document_response", side_effect=request):
                execution = execute_cloud_batches(
                    source_path=source_path,
                    source=source,
                    state_path=Path(directory) / "Quelle.cloud-run.json",
                    local_markdown_sha256="local-markdown-sha256",
                    prompt_version="1.3",
                    plan=plan,
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                )

            self.assertEqual(source_path.read_bytes(), original_bytes)
            self.assertEqual(len(temporary_paths), 2)
            self.assertTrue(all(not path.exists() for path in temporary_paths))
            self.assertEqual(execution.markdown.count("<!-- doctomd:page="), 7)
            self.assertLess(execution.markdown.index("page=6"), execution.markdown.index("page=7"))
            self.assertEqual([item.response_id for item in execution.telemetry], ["resp_1", "resp_7"])

    def test_reuses_completed_batches_and_resumes_open_response_without_upload(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            markdown = "\n\n".join(f"<!-- doctomd:page={page} -->\nText {page}" for page in range(1, 8))
            plan = plan_math_cloud_batches(markdown=markdown)
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)

            def response(page_numbers: tuple[int, ...], response_id: str) -> CloudDocumentResponse:
                return CloudDocumentResponse(
                    {"id": response_id, "model": "gpt-5.6-terra", "status": "completed", "output_text": "\n\n".join(f"<!-- doctomd:page={page} -->\nCloud {page}" for page in page_numbers)},
                    CloudDocumentTelemetry(response_id, "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
                )

            def interrupted_request(**kwargs):
                if kwargs["source_path"].name.startswith("batch-001"):
                    return response((1, 2, 3, 4, 5, 6), "resp_1")
                kwargs["on_response_started"]("resp_7")
                raise TimeoutError("zeitüberschritten")

            arguments = {
                "source_path": source_path,
                "source": source,
                "state_path": state_path,
                "local_markdown_sha256": "local-markdown-sha256",
                "prompt_version": "1.3",
                "plan": plan,
                "config": CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
            }
            with patch("app.cloud_batch_execution.request_document_response", side_effect=interrupted_request):
                with self.assertRaises(TimeoutError):
                    execute_cloud_batches(**arguments)

            with patch("app.cloud_batch_execution.request_document_response") as request, patch(
                "app.cloud_batch_execution.retrieve_document_response", return_value=response((7,), "resp_7")
            ) as retrieve:
                execution = execute_cloud_batches(**arguments)

            request.assert_not_called()
            retrieve.assert_called_once_with(response_id="resp_7", timeout_seconds=900, on_status=ANY)
            self.assertEqual([item.response_id for item in execution.telemetry], ["resp_1", "resp_7"])
            self.assertIn("<!-- doctomd:page=7 -->", execution.markdown)

    def test_budget_failure_keeps_completed_batch_and_leaves_missing_batch_unstarted(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            markdown = "\n\n".join(f"<!-- doctomd:page={page} -->\nText {page}" for page in range(1, 8))
            plan = plan_math_cloud_batches(markdown=markdown)
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)

            def request(**kwargs):
                if kwargs["source_path"].name.startswith("batch-001"):
                    return CloudDocumentResponse(
                        {"id": "resp_1", "model": "gpt-5.6-terra", "status": "completed", "output_text": "\n\n".join(f"<!-- doctomd:page={page} -->\nCloud {page}" for page in range(1, 7))},
                        CloudDocumentTelemetry("resp_1", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
                    )
                raise OpenAICloudDocumentError("Guthaben nicht ausreichend.", code="CLOUD_INSUFFICIENT_CREDITS")

            with patch("app.cloud_batch_execution.request_document_response", side_effect=request):
                with self.assertRaises(OpenAICloudDocumentError) as raised:
                    execute_cloud_batches(
                        source_path=source_path, source=source, state_path=state_path,
                        local_markdown_sha256="context-a", prompt_version="1.3", plan=plan,
                        config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    )

            state = load_matching_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a",
                model_id="gpt-5.6-terra", prompt_version="1.3",
                plan=tuple((batch.batch_id, batch.page_numbers) for batch in plan.batches),
            )
            self.assertEqual(raised.exception.code, "CLOUD_INSUFFICIENT_CREDITS")
            self.assertIsNotNone(state)
            self.assertIsNotNone(state.entries[0].markdown)
            self.assertIsNone(state.entries[1].response_id)

    def test_incomplete_batch_response_is_not_merged_or_marked_successful(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            markdown = "\n\n".join(f"<!-- doctomd:page={page} -->\nText {page}" for page in range(1, 8))
            plan = plan_math_cloud_batches(markdown=markdown)
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"

            def incomplete(**kwargs):
                kwargs["on_response_started"]("resp_incomplete")
                return CloudDocumentResponse(
                    {"id": "resp_incomplete", "model": "gpt-5.6-terra", "status": "incomplete"},
                    CloudDocumentTelemetry("resp_incomplete", "gpt-5.6-terra", 1, 2, 3, datetime(2026, 9, 24, tzinfo=timezone.utc), datetime(2026, 9, 24, tzinfo=timezone.utc), 1),
                )

            with patch("app.cloud_batch_execution.request_document_response", side_effect=incomplete):
                with self.assertRaises(CloudMarkdownValidationError) as raised:
                    execute_cloud_batches(
                        source_path=source_path, source=source, state_path=state_path,
                        local_markdown_sha256="context-a", prompt_version="1.3", plan=plan,
                        config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    )

            state = load_matching_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a",
                model_id="gpt-5.6-terra", prompt_version="1.3",
                plan=tuple((batch.batch_id, batch.page_numbers) for batch in plan.batches),
            )
            self.assertEqual(raised.exception.code, "CLOUD_RESPONSE_TRUNCATED")
            self.assertIsNotNone(state)
            self.assertEqual(state.entries[0].response_id, "resp_incomplete")
            self.assertIsNone(state.entries[0].markdown)

    def test_image_reference_in_a_fresh_batch_is_reset_with_a_retry_instruction(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            source = fingerprint_source(source_path, media_type="application/pdf")
            markdown = "\n\n".join(f"<!-- doctomd:page={page} -->\nText {page}" for page in range(1, 8))
            plan = plan_math_cloud_batches(markdown=markdown)
            state_path = root / "Quelle.cloud-run.json"
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            output = "\n\n".join(
                f"<!-- doctomd:page={page} -->\n" + ("![Figure](figure-2.png)" if page == 1 else f"Cloud {page}")
                for page in range(1, 7)
            )
            response = CloudDocumentResponse(
                {"id": "resp_image", "model": "gpt-5.6-terra", "status": "completed", "output_text": output},
                CloudDocumentTelemetry("resp_image", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )

            with patch("app.cloud_batch_execution.request_document_response", return_value=response):
                with self.assertRaises(CloudMarkdownValidationError) as raised:
                    execute_cloud_batches(
                        source_path=source_path, source=source, state_path=state_path,
                        local_markdown_sha256="context-a", prompt_version="1.5", plan=plan,
                        config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    )

            state = load_matching_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a",
                model_id="gpt-5.6-terra", prompt_version="1.5",
                plan=tuple((batch.batch_id, batch.page_numbers) for batch in plan.batches),
            )
            self.assertEqual(raised.exception.code, "CLOUD_UNAUTHORIZED_IMAGE_REFERENCE")
            self.assertIn("Bitte starten Sie die Cloud-Ableitung erneut", str(raised.exception))
            self.assertIsNotNone(state)
            self.assertIsNone(state.entries[0].response_id)
            self.assertIsNone(state.entries[0].markdown)

    def test_retries_a_stored_batch_with_an_unauthorized_image_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            source = fingerprint_source(source_path, media_type="application/pdf")
            markdown = "\n\n".join(f"<!-- doctomd:page={page} -->\nText {page}" for page in range(1, 8))
            plan = plan_math_cloud_batches(markdown=markdown)
            state_path = root / "Quelle.cloud-run.json"
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)

            def telemetry(response_id: str) -> dict[str, object]:
                return serialize_cloud_document_telemetry(
                    CloudDocumentTelemetry(response_id, "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1)
                )

            first, second = plan.batches
            write_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a", model_id="gpt-5.6-terra", prompt_version="1.5",
                plan=tuple((batch.batch_id, batch.page_numbers) for batch in plan.batches),
                entries=(
                    CloudBatchRunEntry(first.batch_id, first.page_numbers, "old_image", "\n\n".join(f"<!-- doctomd:page={page} -->\n" + ("![Figure](figure-2.png)" if page == 1 else f"Cloud {page}") for page in first.page_numbers), telemetry("old_image")),
                    CloudBatchRunEntry(second.batch_id, second.page_numbers, "old_good", f"<!-- doctomd:page=7 -->\nCloud 7", telemetry("old_good")),
                ),
            )
            replacement = CloudDocumentResponse(
                {"id": "new_good", "model": "gpt-5.6-terra", "status": "completed", "output_text": "\n\n".join(f"<!-- doctomd:page={page} -->\nCloud {page}" for page in first.page_numbers)},
                CloudDocumentTelemetry("new_good", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )
            events: list[str] = []

            with patch("app.cloud_batch_execution.request_document_response", return_value=replacement) as request:
                execution = execute_cloud_batches(
                    source_path=source_path, source=source, state_path=state_path,
                    local_markdown_sha256="context-a", prompt_version="1.5", plan=plan,
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    progress=lambda _phase, status, _message: events.append(status),
                )

            request.assert_called_once()
            self.assertIn("batch_image_reference_retry", events)
            self.assertEqual([item.response_id for item in execution.telemetry], ["new_good", "old_good"])

    def test_retries_only_a_stored_batch_with_missing_local_table_structure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            for _ in range(7):
                writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            markdown = "\n\n".join([
                "<!-- doctomd:page=1 -->\n<!-- doctomd:table=table-1 page=1 -->\nLokale Tabelle\n\n| A | B |\n| --- | --- |\n| 1 | 2 |",
                *[f"<!-- doctomd:page={page} -->\nText {page}" for page in range(2, 8)],
            ])
            plan = plan_math_cloud_batches(markdown=markdown)
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)

            def response(page_numbers: tuple[int, ...], response_id: str, *, table: bool = False) -> CloudDocumentResponse:
                parts = []
                for page in page_numbers:
                    content = "Cloud-Tabelle\n\n| A | B |\n| --- | --- |\n| 1 | 2 |" if table and page == 1 else f"Cloud Text {page}"
                    parts.append(f"<!-- doctomd:page={page} -->\n{content}")
                return CloudDocumentResponse(
                    {"id": response_id, "model": "gpt-5.6-terra", "status": "completed", "output_text": "\n\n".join(parts)},
                    CloudDocumentTelemetry(response_id, "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
                )

            def initial(**kwargs):
                pages = (1, 2, 3, 4, 5, 6) if kwargs["source_path"].name.startswith("batch-001") else (7,)
                return response(pages, f"old_{pages[0]}")

            arguments = {
                "source_path": source_path, "source": source, "state_path": state_path,
                "local_markdown_sha256": "context-a", "prompt_version": "1.4", "plan": plan,
                "config": CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
            }
            with patch("app.cloud_batch_execution.request_document_response", side_effect=initial):
                execute_cloud_batches(**arguments)

            def replacement(**kwargs):
                pages = (1, 2, 3, 4, 5, 6) if kwargs["source_path"].name.startswith("batch-001") else (7,)
                return response(pages, f"new_{pages[0]}", table=True)

            events: list[str] = []
            with patch("app.cloud_batch_execution.request_document_response", side_effect=replacement) as request:
                execution = execute_cloud_batches(
                    **arguments, local_markdown=markdown,
                    progress=lambda _phase, status, _message: events.append(status),
                )

            self.assertEqual(request.call_count, 1)
            self.assertIn("batch_content_retry", events)
            self.assertEqual([item.response_id for item in execution.telemetry], ["new_1", "old_7"])

    def test_preserves_a_rejected_fresh_batch_response_as_diagnostic_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with source_path.open("wb") as file:
                writer.write(file)
            source = fingerprint_source(source_path, media_type="application/pdf")
            markdown = "<!-- doctomd:page=1 -->\n" + " ".join(["lokal"] * 20)
            plan = plan_math_cloud_batches(markdown=markdown)
            timestamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
            response = CloudDocumentResponse(
                {"id": "resp_rejected", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=1 -->\nkurz"},
                CloudDocumentTelemetry("resp_rejected", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )

            with patch("app.cloud_batch_execution.request_document_response", return_value=response):
                with self.assertRaisesRegex(CloudMarkdownValidationError, "zu dünn"):
                    execute_cloud_batches(
                        source_path=source_path, source=source, state_path=root / "Quelle.cloud-run.json",
                        local_markdown_sha256="context-a", prompt_version="1.4", plan=plan,
                        config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                        local_markdown=markdown,
                    )

            rejected_markdown = list(root.glob("Quelle.batch-001-pages-001-001.rejected-*.md"))
            rejected_record = list(root.glob("Quelle.batch-001-pages-001-001.rejected-*.json"))
            self.assertEqual(len(rejected_markdown), 1)
            self.assertEqual(rejected_markdown[0].read_text(encoding="utf-8"), "<!-- doctomd:page=1 -->\nkurz")
            self.assertEqual(json.loads(rejected_record[0].read_text(encoding="utf-8"))["reason_code"], "CLOUD_MARKDOWN_CONTENT_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
