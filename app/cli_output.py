"""Stabile, maschinenlesbare Ausgaben der DocToMD-CLI."""

from __future__ import annotations

from enum import IntEnum
import json
import sys
from typing import Any, Iterable

from app.models import ConversionWarning
from app.quality import QualityStatus, build_quality_section


JSON_SCHEMA_VERSION = "1.1"


class ExitCode(IntEnum):
    """Öffentliche Prozessstatus der DocToMD-CLI."""

    SUCCESS = 0
    WARNING = 1
    ERROR = 2


def build_response(
    *,
    status: str,
    exit_code: ExitCode,
    result: dict[str, Any] | None = None,
    warnings: list[dict[str, Any]] | None = None,
    error: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Erstellt den versionierten JSON-Envelope der CLI."""
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "status": status,
        "exit_code": int(exit_code),
        "result": result,
        "warnings": warnings or [],
        "error": error,
    }


def build_conversion_response(
    *,
    result: dict[str, Any] | None,
    warnings: Iterable[ConversionWarning],
) -> dict[str, Any]:
    """Erstellt eine kompakte CLI-Antwort; Details verbleiben im Manifest."""
    quality = build_quality_section(warnings)
    response_result = dict(result or {})
    response_result["quality"] = _build_cli_quality_summary(quality)

    if quality["status"] == QualityStatus.ERROR.value:
        return build_response(
            status="error",
            exit_code=ExitCode.ERROR,
            result=response_result,
            error=quality["errors"][0],
        )
    if quality["status"] == QualityStatus.WARNING.value:
        return build_response(
            status="warning",
            exit_code=ExitCode.WARNING,
            result=response_result,
        )
    return build_response(
        status="success",
        exit_code=ExitCode.SUCCESS,
        result=response_result,
    )


def _build_cli_quality_summary(quality: dict[str, Any]) -> dict[str, Any]:
    """Verdichtet Qualitätsdetails für die Konsolenschnittstelle."""
    warnings = quality["warnings"]
    errors = quality["errors"]
    return {
        "status": quality["status"],
        "warning_count": len(warnings),
        "warning_codes": _count_codes(warnings),
        "error_count": len(errors),
        "error_codes": _count_codes(errors),
    }


def _count_codes(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        code = item["code"]
        counts[code] = counts.get(code, 0) + 1
    return counts


def emit_error(*, code: str, message: str, json_output: bool) -> ExitCode:
    """Gibt einen Fehler als Text oder versionierten JSON-Envelope aus."""
    if json_output:
        response = build_response(
            status="error",
            exit_code=ExitCode.ERROR,
            error={"code": code, "message": message},
        )
        print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Fehler: {message}", file=sys.stderr)
    return ExitCode.ERROR
