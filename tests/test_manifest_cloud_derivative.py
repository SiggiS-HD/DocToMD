"""Tests für die Manifest-Referenz des getrennten Cloud-Markdowns."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath
import unittest

from app.manifest import build_manifest
from app.cloud_document_telemetry import CloudCostEvidence, CloudDocumentTelemetry
from app.models import ConversionStatus, SourceDocument


class ManifestCloudDerivativeTests(unittest.TestCase):
    def test_records_relative_cloud_path_and_telemetry_without_unproven_cost(self) -> None:
        source = SourceDocument(
            path=Path("C:/sources/Quelle.pdf"),
            media_type="application/pdf",
            size_bytes=10,
            sha256="a" * 64,
            modified_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )
        manifest = build_manifest(
            source=source,
            status=ConversionStatus.SUCCESS,
            markdown_path=PurePosixPath("Quelle.md"),
            cloud_markdown_path=PurePosixPath("Quelle.cloud.md"),
            cloud_document_telemetry=CloudDocumentTelemetry(
                response_id="resp_123",
                model_id="gpt-5.6-terra",
                input_tokens=123,
                output_tokens=None,
                total_tokens=None,
                started_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
                completed_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
                duration_ms=456,
            ),
            blocks=(),
            assets=(),
            tables=(),
            warnings=(),
            started_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            completed_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            ocr_mode="off",
            ocr_language="de",
        )

        self.assertEqual(manifest["artifacts"]["markdown_path"], "Quelle.md")
        self.assertEqual(manifest["artifacts"]["cloud_markdown_path"], "Quelle.cloud.md")
        telemetry = manifest["conversion"]["cloud_document"]
        self.assertEqual(telemetry["response_id"], "resp_123")
        self.assertEqual(telemetry["input_tokens"], 123)
        self.assertIsNone(telemetry["output_tokens"])
        self.assertNotIn("cost", telemetry)

    def test_records_cost_only_with_explicit_evidence(self) -> None:
        telemetry = CloudDocumentTelemetry(
            response_id="resp_123",
            model_id="gpt-5.6-terra",
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            started_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            completed_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            duration_ms=4,
            cost=CloudCostEvidence(
                amount_usd=Decimal("0.0123"),
                source_url="https://developers.openai.com/pricing",
                retrieved_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            ),
        )

        from app.cloud_document_telemetry import serialize_cloud_document_telemetry

        serialized = serialize_cloud_document_telemetry(telemetry)
        self.assertEqual(serialized["cost"]["amount_usd"], "0.0123")
        self.assertEqual(serialized["cost"]["source_url"], "https://developers.openai.com/pricing")


if __name__ == "__main__":
    unittest.main()
