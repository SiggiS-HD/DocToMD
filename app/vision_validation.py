"""Konservative lokale Validierung unverbindlicher Vision-Vorschläge."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from app.models import ConversionWarning, PageReference


MIN_CONFIDENCE = 0.85
_ROOT_KEYS = frozenset({"schema_version", "page", "paragraphs", "formulas", "tables", "captions"})
_FORBIDDEN_LATEX = ("$$", "\\[", "\\]", "\\begin", "\\end", "\\input", "\\include", "\\write")


@dataclass(frozen=True, slots=True)
class VisionValidationOutcome:
    """Entweder vollständig lokal geprüfter Vorschlag oder sichtbare Warnungen."""

    proposal: dict[str, Any] | None
    warnings: tuple[ConversionWarning, ...] = ()


def backend_failure_warning(*, failure: str, page_number: int) -> ConversionWarning:
    """Ordnet Adapterfehler einer stabilen, seitenbezogenen Warnung zu."""
    messages = {
        "unreachable": ("VISION_BACKEND_UNREACHABLE", "Das Vision-Backend ist nicht erreichbar."),
        "timeout": ("VISION_TIMEOUT", "Die Vision-Anfrage hat das konfigurierte Timeout überschritten."),
    }
    try:
        code, message = messages[failure]
    except KeyError as error:
        raise ValueError("Unbekannter Vision-Backendfehler.") from error
    return ConversionWarning(code, message, page=PageReference(page_number))


def validate_vision_proposal(
    *,
    response_text: str,
    requested_page: int,
    local_page_text: str,
    min_confidence: float = MIN_CONFIDENCE,
) -> VisionValidationOutcome:
    """Akzeptiert nur eine vollständig prüfbare Antwort für die angefragte Seite."""
    page = PageReference(requested_page)
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence muss zwischen 0 und 1 liegen.")
    try:
        proposal = json.loads(response_text)
    except (TypeError, json.JSONDecodeError):
        return _invalid_json(page)
    if not isinstance(proposal, dict) or set(proposal) != _ROOT_KEYS:
        return _invalid_json(page)
    if proposal.get("schema_version") != "1.0" or not _is_page(proposal.get("page"), requested_page):
        return _invalid_json(page)

    try:
        _validate_items(proposal, requested_page, local_page_text, min_confidence)
    except _LowConfidence:
        return VisionValidationOutcome(None, (ConversionWarning("VISION_LOW_CONFIDENCE", "Der Vision-Vorschlag unterschreitet die lokale Konfidenzschwelle.", page=page),))
    except _Unverifiable:
        return VisionValidationOutcome(None, (ConversionWarning("VISION_UNVERIFIABLE_CONTENT", "Der Vision-Vorschlag kann lokal nicht sicher geprüft werden.", page=page),))
    except _InvalidShape:
        return _invalid_json(page)
    return VisionValidationOutcome(proposal)


def _validate_items(proposal: dict[str, Any], requested_page: int, local_page_text: str, min_confidence: float) -> None:
    for key, allowed_keys, required_keys in (
        ("paragraphs", {"text", "page", "confidence"}, {"text", "page", "confidence"}),
        ("formulas", {"source_text", "latex", "page", "confidence"}, {"source_text", "latex", "page", "confidence"}),
        ("tables", {"title", "headers", "rows", "page", "confidence"}, {"headers", "rows", "page", "confidence"}),
        ("captions", {"text", "target_hint", "page", "confidence"}, {"text", "page", "confidence"}),
    ):
        items = proposal.get(key)
        if not isinstance(items, list):
            raise _InvalidShape
        for item in items:
            if not isinstance(item, dict) or not required_keys.issubset(item) or not set(item).issubset(allowed_keys):
                raise _InvalidShape
            _validate_common(item, requested_page, min_confidence)
            if key in {"paragraphs", "captions"} and not _nonempty_text(item.get("text")):
                raise _InvalidShape
            if key == "formulas":
                _validate_formula(item, local_page_text)
            if key == "tables":
                _validate_table(item)


def _validate_common(item: dict[str, Any], requested_page: int, min_confidence: float) -> None:
    if not _is_page(item.get("page"), requested_page):
        raise _Unverifiable
    confidence = item.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise _InvalidShape
    if confidence < min_confidence:
        raise _LowConfidence


def _validate_formula(item: dict[str, Any], local_page_text: str) -> None:
    source_text, latex = item.get("source_text"), item.get("latex")
    if not _nonempty_text(source_text) or not _nonempty_text(latex):
        raise _InvalidShape
    if _normalize(source_text) not in _normalize(local_page_text):
        raise _Unverifiable
    if any(token in latex for token in _FORBIDDEN_LATEX):
        raise _Unverifiable


def _validate_table(item: dict[str, Any]) -> None:
    headers, rows = item.get("headers"), item.get("rows")
    if not isinstance(headers, list) or len(headers) < 2 or not all(_nonempty_text(cell) for cell in headers):
        raise _InvalidShape
    if not isinstance(rows, list) or not rows:
        raise _InvalidShape
    if any(not isinstance(row, list) or len(row) != len(headers) or not all(_nonempty_text(cell) for cell in row) for row in rows):
        raise _Unverifiable
    if "title" in item and not _nonempty_text(item["title"]):
        raise _InvalidShape


def _is_page(value: object, requested_page: int) -> bool:
    return isinstance(value, dict) and set(value) == {"page_number"} and value.get("page_number") == requested_page


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _invalid_json(page: PageReference) -> VisionValidationOutcome:
    return VisionValidationOutcome(None, (ConversionWarning("VISION_INVALID_JSON", "Die Vision-Antwort ist kein gültiges JSON gemäß dem Vision-Vorschlagsvertrag.", page=page),))


class _InvalidShape(Exception):
    pass


class _LowConfidence(Exception):
    pass


class _Unverifiable(Exception):
    pass


__all__ = ["MIN_CONFIDENCE", "VisionValidationOutcome", "backend_failure_warning", "validate_vision_proposal"]
