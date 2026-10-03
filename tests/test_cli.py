"""Unit-Tests für den öffentlichen CLI-Vertrag."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.cli import create_parser, run
from app.cli_output import ExitCode
from app.openai_cloud_document import OpenAICloudDocumentError


class CliTests(unittest.TestCase):
    """Prüft Argumente und maschinenlesbare Fehlerantworten."""

    def setUp(self) -> None:
        self.parser = create_parser()

    def test_convert_uses_documented_defaults(self) -> None:
        arguments = self.parser.parse_args(
            ["convert", "Quelle.pdf", "--output-dir", "ergebnis"]
        )

        self.assertEqual(arguments.command, "convert")
        self.assertEqual(arguments.input_path, Path("Quelle.pdf"))
        self.assertEqual(arguments.output_dir, Path("ergebnis"))
        self.assertEqual(arguments.output_format, "markdown")
        self.assertEqual(arguments.on_conflict, "error")
        self.assertEqual(arguments.ocr_mode, "auto")
        self.assertEqual(arguments.ocr_language, "de")
        self.assertEqual(arguments.vision_provider, "none")
        self.assertEqual(arguments.vision_mode, "off")
        self.assertIsNone(arguments.vision_model)
        self.assertEqual(arguments.vision_render_dpi, 144)
        self.assertEqual(arguments.vision_timeout_seconds, 480)
        self.assertIsNone(arguments.lm_studio_endpoint)
        self.assertEqual(arguments.cloud_document_mode, "off")
        self.assertIsNone(arguments.cloud_document_model)
        self.assertEqual(arguments.cloud_document_timeout_seconds, 900)
        self.assertEqual(arguments.cloud_document_max_output_tokens, 32_768)
        self.assertFalse(arguments.json_output)
        self.assertEqual(arguments.progress, "human")

    def test_convert_accepts_all_explicit_options(self) -> None:
        arguments = self.parser.parse_args(
            [
                "convert",
                "Quelle.pdf",
                "--output-dir",
                "ergebnis",
                "--output-format",
                "markdown",
                "--on-conflict",
                "overwrite",
                "--ocr-mode",
                "force",
                "--ocr-language",
                "en",
                "--json",
            ]
        )

        self.assertEqual(arguments.on_conflict, "overwrite")
        self.assertEqual(arguments.ocr_mode, "force")
        self.assertEqual(arguments.ocr_language, "en")
        self.assertTrue(arguments.json_output)

    def test_convert_accepts_explicit_openai_vision_auto_configuration(self) -> None:
        arguments = self.parser.parse_args(
            [
                "convert",
                "Quelle.pdf",
                "--output-dir",
                "ergebnis",
                "--vision-provider",
                "openai",
                "--vision-mode",
                "auto",
                "--vision-model",
                "gpt-5.6-terra",
                "--vision-render-dpi",
                "192",
                "--vision-timeout-seconds",
                "300",
            ]
        )

        self.assertEqual(arguments.vision_provider, "openai")
        self.assertEqual(arguments.vision_mode, "auto")
        self.assertEqual(arguments.vision_model, "gpt-5.6-terra")
        self.assertEqual(arguments.vision_render_dpi, 192)
        self.assertEqual(arguments.vision_timeout_seconds, 300)

    def test_convert_accepts_explicit_cloud_document_configuration(self) -> None:
        arguments = self.parser.parse_args(
            [
                "convert",
                "Quelle.pdf",
                "--output-dir",
                "ergebnis",
                "--cloud-document-mode",
                "openai",
                "--cloud-document-model",
                "gpt-5.6-terra",
                "--cloud-document-timeout-seconds",
                "1200",
                "--cloud-document-max-output-tokens",
                "24000",
            ]
        )

        self.assertEqual(arguments.cloud_document_mode, "openai")
        self.assertEqual(arguments.cloud_document_model, "gpt-5.6-terra")
        self.assertEqual(arguments.cloud_document_timeout_seconds, 1200)
        self.assertEqual(arguments.cloud_document_max_output_tokens, 24000)

    def test_cloud_derive_has_an_explicit_minimal_contract(self) -> None:
        arguments = self.parser.parse_args(
            [
                "cloud-derive",
                "Quelle.pdf",
                "--output-dir",
                "ergebnis",
                "--on-conflict",
                "overwrite",
                "--cloud-document-model",
                "gpt-5.6-terra",
                "--cloud-document-timeout-seconds",
                "1200",
                "--cloud-document-max-output-tokens",
                "24000",
                "--json",
                "--progress",
                "jsonl",
            ]
        )

        self.assertEqual(arguments.command, "cloud-derive")
        self.assertEqual(arguments.input_path, Path("Quelle.pdf"))
        self.assertEqual(arguments.output_dir, Path("ergebnis"))
        self.assertEqual(arguments.on_conflict, "overwrite")
        self.assertEqual(arguments.cloud_document_model, "gpt-5.6-terra")
        self.assertEqual(arguments.cloud_document_timeout_seconds, 1200)
        self.assertEqual(arguments.cloud_document_max_output_tokens, 24000)
        self.assertTrue(arguments.json_output)
        self.assertEqual(arguments.progress, "jsonl")

    def test_cloud_evaluate_requires_a_positive_contiguous_page_range(self) -> None:
        arguments = self.parser.parse_args(
            ["cloud-evaluate", "Quelle.pdf", "--output-dir", "ergebnis", "--pages", "9-14"]
        )

        self.assertEqual(arguments.command, "cloud-evaluate")
        self.assertEqual(arguments.pages, (9, 10, 11, 12, 13, 14))
        self.assertEqual(arguments.cloud_document_model, "gpt-5.6-terra")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parser.parse_args(["cloud-evaluate", "Quelle.pdf", "--output-dir", "ergebnis", "--pages", "9,10"])

    def test_migrate_provenance_has_no_conversion_or_cloud_options(self) -> None:
        arguments = self.parser.parse_args(
            ["migrate-provenance", "Quelle.pdf", "--output-dir", "ergebnis", "--json"]
        )

        self.assertEqual(arguments.command, "migrate-provenance")
        self.assertEqual(arguments.input_path, Path("Quelle.pdf"))
        self.assertEqual(arguments.output_dir, Path("ergebnis"))
        self.assertTrue(arguments.json_output)

    def test_cloud_derive_rejects_missing_model_as_stable_json_error(self) -> None:
        arguments = self.parser.parse_args(
            ["cloud-derive", "Quelle.pdf", "--output-dir", "ergebnis", "--json"]
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = run(arguments, self.parser)

        response = json.loads(output.getvalue())
        self.assertEqual(exit_code, ExitCode.ERROR)
        self.assertEqual(response["error"]["code"], "CLOUD_DERIVE_CONFIGURATION_INVALID")

    def test_cloud_derive_does_not_start_a_conversion_without_a_local_context(self) -> None:
        arguments = self.parser.parse_args(
            [
                "cloud-derive", "Quelle.pdf", "--output-dir", "ergebnis",
                "--cloud-document-model", "gpt-5.6-terra", "--json",
            ]
        )

        output = io.StringIO()
        with redirect_stdout(output), patch("app.cli.convert_pdf") as convert_pdf:
            exit_code = run(arguments, self.parser)

        self.assertEqual(exit_code, ExitCode.ERROR)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "CLOUD_DERIVE_FAILED")
        convert_pdf.assert_not_called()

    @patch("app.cli.derive_cloud")
    @patch("app.cli.can_reuse_local_context", return_value=True)
    @patch("app.cli.convert_pdf")
    def test_convert_cloud_opt_in_redirects_when_local_context_is_valid(self, convert_pdf, _can_reuse, derive_cloud) -> None:
        arguments = self.parser.parse_args([
            "convert", "Quelle.pdf", "--output-dir", "ergebnis", "--cloud-document-mode", "openai",
            "--cloud-document-model", "gpt-5.6-terra", "--json", "--progress", "none",
        ])
        derive_cloud.return_value = type("Run", (), {
            "result": type("Result", (), {"warnings": (), "status": type("Status", (), {"value": "success"})(), "markdown_path": Path("Quelle.md"), "manifest_path": Path("Quelle.conversion.json")})(),
            "manifest": {}, "cloud_markdown_path": Path("Quelle.cloud.md"), "reused": False, "vision_pages": (),
        })()
        output = io.StringIO()
        with redirect_stdout(output):
            run(arguments, self.parser)

        convert_pdf.assert_not_called()
        derive_cloud.assert_called_once()

    def test_invalid_cloud_document_configuration_is_reported_as_json_error(self) -> None:
        arguments = self.parser.parse_args(
            [
                "convert",
                "Quelle.pdf",
                "--output-dir",
                "ergebnis",
                "--cloud-document-mode",
                "openai",
                "--json",
            ]
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = run(arguments, self.parser)

        response = json.loads(output.getvalue())
        self.assertEqual(exit_code, ExitCode.ERROR)
        self.assertEqual(response["error"]["code"], "CONVERSION_FAILED")

    def test_convert_requires_output_directory(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self.parser.parse_args(["convert", "Quelle.pdf"])

        self.assertEqual(raised.exception.code, 2)

    def test_missing_source_is_reported_as_json_error(self) -> None:
        arguments = self.parser.parse_args(
            ["convert", "nicht-vorhanden.pdf", "--output-dir", "ergebnis", "--json"]
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = run(arguments, self.parser)

        response = json.loads(output.getvalue())
        self.assertEqual(exit_code, ExitCode.ERROR)
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["exit_code"], 2)
        self.assertEqual(response["error"]["code"], "CONVERSION_FAILED")

    def test_json_error_response_is_indented(self) -> None:
        arguments = self.parser.parse_args(
            ["convert", "nicht-vorhanden.pdf", "--output-dir", "ergebnis", "--json"]
        )

        output = io.StringIO()
        with redirect_stdout(output):
            run(arguments, self.parser)

        self.assertTrue(output.getvalue().startswith("{\n"))
        self.assertIn('\n  "error": {', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["status"], "error")

    def test_json_progress_is_written_only_to_stderr(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "simple-digital.pdf"
        with TemporaryDirectory() as directory:
            arguments = self.parser.parse_args(
                ["convert", str(fixture), "--output-dir", str(Path(directory) / "output"), "--ocr-mode", "off", "--json", "--progress", "jsonl"]
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                run(arguments, self.parser)

        self.assertIn("\"event\": \"progress\"", stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["schema_version"], "1.1")

    def test_invalid_pdf_source_is_reported_as_json_error(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "Quelle.pdf"
            source_path.write_bytes(b"%PDF")
            arguments = self.parser.parse_args(
                ["convert", str(source_path), "--output-dir", "ergebnis", "--json"]
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = run(arguments, self.parser)

        response = json.loads(output.getvalue())
        self.assertEqual(exit_code, ExitCode.ERROR)
        self.assertEqual(response["error"]["code"], "CONVERSION_FAILED")

    @patch("app.cli.convert_pdf")
    def test_insufficient_cloud_credits_keep_the_specific_json_error_code(self, convert_pdf) -> None:
        convert_pdf.side_effect = OpenAICloudDocumentError(
            "OpenAI-Guthaben nicht ausreichend. Bitte Billing und Credit Balance prüfen.",
            code="CLOUD_INSUFFICIENT_CREDITS",
        )
        arguments = self.parser.parse_args(
            ["convert", "Quelle.pdf", "--output-dir", "ergebnis", "--json"]
        )
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = run(arguments, self.parser)

        response = json.loads(output.getvalue())
        self.assertEqual(exit_code, ExitCode.ERROR)
        self.assertEqual(response["error"]["code"], "CLOUD_INSUFFICIENT_CREDITS")
        self.assertEqual(
            response["error"]["message"],
            "OpenAI-Guthaben nicht ausreichend. Bitte Billing und Credit Balance prüfen.",
        )


if __name__ == "__main__":
    unittest.main()
