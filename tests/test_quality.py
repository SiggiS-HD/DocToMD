"""Unit-Tests für Manifest- und CLI-Qualitätsausgaben."""

from __future__ import annotations

import unittest

from app.cli_output import ExitCode, build_conversion_response
from app.models import ConversionWarning, PageReference, WarningSeverity
from app.quality import build_quality_section


class QualityTests(unittest.TestCase):
    """Prüft konsistente Qualitätsdarstellung in beiden Schnittstellen."""

    def test_empty_warning_list_has_ok_manifest_status(self) -> None:
        quality = build_quality_section(())

        self.assertEqual(quality, {"status": "ok", "warnings": [], "errors": []})

    def test_warning_is_serialized_with_page_reference(self) -> None:
        warning = ConversionWarning(
            code="READING_ORDER_UNCERTAIN",
            message="Die Lesereihenfolge könnte unklar sein.",
            page=PageReference(page_number=3, location="Spalte 2"),
        )

        quality = build_quality_section((warning,))

        self.assertEqual(quality["status"], "warning")
        self.assertEqual(
            quality["warnings"],
            [
                {
                    "code": "READING_ORDER_UNCERTAIN",
                    "message": "Die Lesereihenfolge könnte unklar sein.",
                    "severity": "warning",
                    "page": {"page_number": 3, "location": "Spalte 2"},
                }
            ],
        )
        self.assertEqual(quality["errors"], [])

    def test_error_severity_is_manifest_error_and_cli_error(self) -> None:
        warning = ConversionWarning(
            code="OCR_FAILED",
            message="OCR konnte nicht ausgeführt werden.",
            severity=WarningSeverity.ERROR,
            page=PageReference(page_number=2),
        )

        quality = build_quality_section((warning,))
        response = build_conversion_response(result={"id": "run-1"}, warnings=(warning,))

        self.assertEqual(quality["status"], "error")
        self.assertEqual(
            quality["errors"],
            [{"code": "OCR_FAILED", "message": "OCR konnte nicht ausgeführt werden.", "page": {"page_number": 2}}],
        )
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["exit_code"], ExitCode.ERROR)
        self.assertEqual(response["error"], quality["errors"][0])
        self.assertEqual(
            response["result"]["quality"],
            {
                "status": "error",
                "warning_count": 0,
                "warning_codes": {},
                "error_count": 1,
                "error_codes": {"OCR_FAILED": 1},
            },
        )

    def test_cli_uses_warning_exit_code_for_quality_warning(self) -> None:
        warning = ConversionWarning(code="TABLE_UNCERTAIN", message="Tabelle unsicher.")

        response = build_conversion_response(result=None, warnings=(warning,))

        self.assertEqual(response["status"], "warning")
        self.assertEqual(response["exit_code"], ExitCode.WARNING)
        self.assertEqual(response["warnings"], [])
        self.assertEqual(
            response["result"]["quality"],
            {
                "status": "warning",
                "warning_count": 1,
                "warning_codes": {"TABLE_UNCERTAIN": 1},
                "error_count": 0,
                "error_codes": {},
            },
        )

    def test_cli_compacts_repeated_warnings_by_code(self) -> None:
        warnings = (
            ConversionWarning(code="MULTI_COLUMN_LAYOUT", message="Mehrspaltig."),
            ConversionWarning(code="MULTI_COLUMN_LAYOUT", message="Mehrspaltig."),
            ConversionWarning(code="TABLE_UNCERTAIN", message="Tabelle unsicher."),
        )

        response = build_conversion_response(result={"id": "run-1"}, warnings=warnings)

        self.assertEqual(response["warnings"], [])
        self.assertEqual(response["result"]["quality"]["warning_count"], 3)
        self.assertEqual(
            response["result"]["quality"]["warning_codes"],
            {"MULTI_COLUMN_LAYOUT": 2, "TABLE_UNCERTAIN": 1},
        )


if __name__ == "__main__":
    unittest.main()
