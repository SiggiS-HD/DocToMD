"""Mock-Regressionen für die getrennte Cloud-Seitenbereichsevaluation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_document_telemetry import CloudDocumentTelemetry
from app.cloud_evaluate_service import CloudEvaluateError, evaluate_cloud_pages, parse_page_range
from app.manifest import build_manifest
from app.models import ConversionStatus
from app.openai_cloud_document import CloudDocumentResponse
from app.source_fingerprint import fingerprint_source


class CloudEvaluateServiceTests(unittest.TestCase):
    def test_page_range_only_accepts_positive_contiguous_ranges(self) -> None:
        self.assertEqual(parse_page_range("10"), (10,))
        self.assertEqual(parse_page_range("9-14"), (9, 10, 11, 12, 13, 14))
        for invalid in ("0", "14-9", "9,10", " 9-14", "09"):
            with self.assertRaises(ValueError):
                parse_page_range(invalid)

    def test_writes_separate_subset_artifacts_without_mutating_regular_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, manifest_path, regular_cloud_path = _local_context(root)
            before_manifest = manifest_path.read_bytes()
            before_cloud = regular_cloud_path.read_bytes()
            before_source = source_path.read_bytes()
            timestamp = datetime(2026, 9, 25, tzinfo=timezone.utc)
            response = CloudDocumentResponse(
                {"id": "resp_evaluate", "model": "gpt-5.6-terra", "status": "completed", "output_text": "<!-- doctomd:page=2 -->\nCloud-Inhalt zwei mit ausreichend Text.\n<!-- doctomd:page=3 -->\nCloud-Inhalt drei mit ausreichend Text."},
                CloudDocumentTelemetry("resp_evaluate", "gpt-5.6-terra", 1, 2, 3, timestamp, timestamp, 1),
            )
            subset_page_counts: list[int] = []
            def respond(**kwargs):
                subset_page_counts.append(len(PdfReader(kwargs["source_path"]).pages))
                return response

            with patch("app.cloud_evaluate_service.request_document_response", side_effect=respond) as request:
                result = evaluate_cloud_pages(
                    input_path=source_path, output_dir=root, page_numbers=(2, 3),
                    config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                )

            self.assertEqual(result["pages"], [2, 3])
            self.assertTrue((root / "Quelle.pages-002-003.local.md").is_file())
            self.assertTrue((root / "Quelle.pages-002-003.cloud.md").is_file())
            record = json.loads((root / "Quelle.pages-002-003.evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(record["pages"], [2, 3])
            self.assertEqual(record["prompt_version"], "1.5")
            self.assertEqual(manifest_path.read_bytes(), before_manifest)
            self.assertEqual(regular_cloud_path.read_bytes(), before_cloud)
            self.assertEqual(source_path.read_bytes(), before_source)
            self.assertFalse((root / "Quelle.cloud-run.json").exists())
            self.assertEqual(subset_page_counts, [2])
            instructions = request.call_args.kwargs["instructions"]
            self.assertIn("original PDF pages 2, 3", instructions)
            self.assertIn("doctomd:page=2", instructions)

    def test_rejects_existing_evaluation_artifact_before_request(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, _, _ = _local_context(root)
            (root / "Quelle.pages-002.local.md").write_text("bereits vorhanden", encoding="utf-8")
            with patch("app.cloud_evaluate_service.request_document_response") as request:
                with self.assertRaises(CloudEvaluateError):
                    evaluate_cloud_pages(
                        input_path=source_path, output_dir=root, page_numbers=(2,),
                        config=CloudDocumentConfig(mode=CloudDocumentMode.OPENAI, model_id="gpt-5.6-terra"),
                    )
            request.assert_not_called()


def _local_context(root: Path) -> tuple[Path, Path, Path]:
    source_path = root / "Quelle.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    with source_path.open("wb") as file:
        writer.write(file)
    markdown = "\n\n".join(
        f"<!-- doctomd:page={page} -->\nLokaler Inhalt Seite {page} mit ausreichend überprüfbarem Text."
        for page in range(1, 4)
    ) + "\n"
    (root / "Quelle.md").write_text(markdown, encoding="utf-8")
    source = fingerprint_source(source_path, media_type="application/pdf")
    timestamp = datetime(2026, 9, 25, tzinfo=timezone.utc)
    manifest = build_manifest(
        source=source, status=ConversionStatus.SUCCESS, markdown_path=PurePosixPath("Quelle.md"), markdown_content=markdown,
        blocks=(), assets=(), tables=(), warnings=(), started_at=timestamp, completed_at=timestamp,
    )
    manifest_path = root / "Quelle.conversion.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    regular_cloud_path = root / "Quelle.cloud.md"
    regular_cloud_path.write_text("unverändert", encoding="utf-8")
    return source_path, manifest_path, regular_cloud_path


if __name__ == "__main__":
    unittest.main()
