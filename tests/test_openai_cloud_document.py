"""Mock-Tests für die einmalige, rückstandsarme PDF-Übergabe an OpenAI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from app.cloud_document_prompt import build_cloud_markdown_instructions
from app.openai_cloud_document import OpenAICloudDocumentError, request_document_response


class _Response:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class OpenAICloudDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @patch("app.openai_cloud_document.urlopen")
    def test_uploads_pdf_once_uses_input_file_and_deletes_remote_file(self, urlopen) -> None:
        urlopen.side_effect = [
            _Response({"id": "file_test"}),
            _Response({"id": "resp_test", "status": "queued"}),
            _Response({"id": "resp_test", "status": "completed", "model": "gpt-5.6-terra", "usage": {"input_tokens": 123, "output_tokens": 456, "total_tokens": 579}}),
            _Response({"id": "file_test", "deleted": True}),
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "Quelle.pdf"
            source.write_bytes(b"%PDF-1.7\n")

            response = request_document_response(
                source_path=source,
                model_id="gpt-5.6-terra",
                timeout_seconds=120,
                max_output_tokens=20_000,
                instructions=build_cloud_markdown_instructions(),
            )

        self.assertEqual(response.payload["id"], "resp_test")
        self.assertEqual(response.telemetry.model_id, "gpt-5.6-terra")
        self.assertEqual(response.telemetry.input_tokens, 123)
        self.assertEqual(response.telemetry.output_tokens, 456)
        self.assertEqual(response.telemetry.total_tokens, 579)
        self.assertGreaterEqual(response.telemetry.duration_ms, 0)
        self.assertEqual(urlopen.call_count, 4)
        upload_request = urlopen.call_args_list[0].args[0]
        response_request = urlopen.call_args_list[1].args[0]
        poll_request = urlopen.call_args_list[2].args[0]
        delete_request = urlopen.call_args_list[3].args[0]
        self.assertEqual(upload_request.full_url, "https://api.openai.com/v1/files")
        self.assertIn(b"%PDF-1.7", upload_request.data)
        self.assertIn(b'name="purpose"', upload_request.data)
        self.assertIn(b"user_data", upload_request.data)
        response_payload = json.loads(response_request.data.decode("utf-8"))
        self.assertFalse(response_payload["store"])
        self.assertTrue(response_payload["background"])
        self.assertEqual(response_payload["max_output_tokens"], 20_000)
        self.assertEqual(response_payload["instructions"], build_cloud_markdown_instructions())
        self.assertEqual(
            response_payload["input"][0]["content"],
            [{"type": "input_file", "file_id": "file_test"}],
        )
        self.assertEqual(delete_request.get_method(), "DELETE")
        self.assertEqual(delete_request.full_url, "https://api.openai.com/v1/files/file_test")
        self.assertEqual(poll_request.get_method(), "GET")
        self.assertEqual(poll_request.full_url, "https://api.openai.com/v1/responses/resp_test")

    def test_requires_environment_key_without_exposing_it(self) -> None:
        with patch.dict(os.environ, {}, clear=True), TemporaryDirectory() as directory:
            source = Path(directory) / "Quelle.pdf"
            source.write_bytes(b"%PDF")
            with self.assertRaisesRegex(OpenAICloudDocumentError, "OPENAI_API_KEY"):
                request_document_response(
                    source_path=source,
                    model_id="gpt-5.6-terra",
                    timeout_seconds=120,
                    max_output_tokens=20_000,
                    instructions="Test",
                )

    @patch("app.openai_cloud_document.urlopen")
    def test_deletes_uploaded_file_when_response_fails(self, urlopen) -> None:
        urlopen.side_effect = [_Response({"id": "file_test"}), TimeoutError(), _Response({"id": "file_test", "deleted": True})]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "Quelle.pdf"
            source.write_bytes(b"%PDF")
            with self.assertRaises(OpenAICloudDocumentError):
                request_document_response(
                    source_path=source,
                    model_id="gpt-5.6-terra",
                    timeout_seconds=120,
                    max_output_tokens=20_000,
                    instructions="Test",
                )

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(urlopen.call_args_list[2].args[0].get_method(), "DELETE")

    @patch("app.openai_cloud_document.urlopen")
    def test_reports_sanitized_structured_http_error_and_deletes_uploaded_file(self, urlopen) -> None:
        error_payload = {
            "error": {
                "code": "unsupported_parameter",
                "message": "Unsupported parameter for file-file_test: sk-test-secret",
            }
        }
        urlopen.side_effect = [
            _Response({"id": "file_test"}),
            HTTPError(
                url="https://api.openai.com/v1/responses",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=BytesIO(json.dumps(error_payload).encode("utf-8")),
            ),
            _Response({"id": "file_test", "deleted": True}),
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "Quelle.pdf"
            source.write_bytes(b"%PDF")
            with self.assertRaisesRegex(OpenAICloudDocumentError, "unsupported_parameter") as context:
                request_document_response(
                    source_path=source,
                    model_id="gpt-5.6-terra",
                    timeout_seconds=120,
                    max_output_tokens=20_000,
                    instructions="Test",
                )

        message = str(context.exception)
        self.assertIn("Unsupported parameter", message)
        self.assertNotIn("file_test", message)
        self.assertNotIn("sk-test-secret", message)
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(urlopen.call_args_list[2].args[0].get_method(), "DELETE")

    @patch("app.openai_cloud_document.urlopen")
    def test_reports_insufficient_credits_without_provider_error_detail(self, urlopen) -> None:
        error_payload = {
            "error": {
                "code": "insufficient_quota",
                "message": "You exceeded your current quota; sk-test-secret",
            }
        }
        urlopen.side_effect = [
            _Response({"id": "file_test"}),
            HTTPError(
                url="https://api.openai.com/v1/responses",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=BytesIO(json.dumps(error_payload).encode("utf-8")),
            ),
            _Response({"id": "file_test", "deleted": True}),
        ]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "Quelle.pdf"
            source.write_bytes(b"%PDF")
            with self.assertRaises(OpenAICloudDocumentError) as context:
                request_document_response(
                    source_path=source,
                    model_id="gpt-5.6-terra",
                    timeout_seconds=120,
                    max_output_tokens=20_000,
                    instructions="Test",
                )

        self.assertEqual(context.exception.code, "CLOUD_INSUFFICIENT_CREDITS")
        self.assertEqual(
            str(context.exception),
            "OpenAI-Guthaben nicht ausreichend. Bitte Billing und Credit Balance prüfen.",
        )
        self.assertEqual(urlopen.call_count, 3)

    @patch("app.openai_cloud_document.urlopen")
    def test_reports_response_id_before_polling(self, urlopen) -> None:
        urlopen.side_effect = [
            _Response({"id": "file_test"}),
            _Response({"id": "resp_test", "status": "queued"}),
            _Response({"id": "resp_test", "status": "completed", "model": "gpt-5.6-terra"}),
            _Response({"id": "file_test", "deleted": True}),
        ]
        started: list[str] = []
        with TemporaryDirectory() as directory:
            source = Path(directory) / "Quelle.pdf"
            source.write_bytes(b"%PDF")
            request_document_response(
                source_path=source, model_id="gpt-5.6-terra", timeout_seconds=120,
                max_output_tokens=20_000, instructions="Test", on_response_started=started.append,
            )

        self.assertEqual(started, ["resp_test"])


if __name__ == "__main__":
    unittest.main()
