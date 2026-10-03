"""Ableitung und Serialisierung sichtbarer Konvertierungsqualität."""

from __future__ import annotations

from enum import Enum
from typing import Any, Iterable

from app.models import ConversionWarning, PageReference, WarningSeverity


class QualityStatus(str, Enum):
    """Zusammenfassender Qualitätszustand eines Konvertierungsergebnisses."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


def build_quality_section(
    warnings: Iterable[ConversionWarning],
) -> dict[str, Any]:
    """Erstellt den schema-konformen ``quality``-Abschnitt eines Manifests."""
    serialized_warnings: list[dict[str, Any]] = []
    serialized_errors: list[dict[str, Any]] = []
    highest_status = QualityStatus.OK

    for warning in warnings:
        if warning.severity is WarningSeverity.ERROR:
            highest_status = QualityStatus.ERROR
            serialized_errors.append(_serialize_error(warning))
        else:
            if warning.severity is WarningSeverity.WARNING and highest_status is QualityStatus.OK:
                highest_status = QualityStatus.WARNING
            serialized_warnings.append(serialize_warning(warning))

    return {
        "status": highest_status.value,
        "warnings": serialized_warnings,
        "errors": serialized_errors,
    }


def serialize_warning(warning: ConversionWarning) -> dict[str, Any]:
    """Serialisiert eine nicht-fehlerhafte Qualitätswarnung für JSON-Ausgaben."""
    serialized = {
        "code": warning.code,
        "message": warning.message,
        "severity": warning.severity.value,
    }
    if warning.page is not None:
        serialized["page"] = _serialize_page(warning.page)
    return serialized


def _serialize_error(warning: ConversionWarning) -> dict[str, Any]:
    serialized = {"code": warning.code, "message": warning.message}
    if warning.page is not None:
        serialized["page"] = _serialize_page(warning.page)
    return serialized


def _serialize_page(page: PageReference) -> dict[str, Any]:
    serialized = {"page_number": page.page_number}
    if page.location is not None:
        serialized["location"] = page.location
    return serialized


__all__ = ["QualityStatus", "build_quality_section", "serialize_warning"]
