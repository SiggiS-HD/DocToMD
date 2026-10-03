"""Technische Mindestvalidierung für vollständiges Cloud-Dokument-Markdown."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


PAGE_MARKER = re.compile(r"<!-- doctomd:page=([1-9][0-9]*) -->")
FORBIDDEN_OUTPUT = re.compile(
    r"file://|<\s*/?\s*(?:html|head|body|script|iframe|meta)\b|<!doctype|<\?",
    re.IGNORECASE,
)


class CloudMarkdownValidationError(ValueError):
    """Die Cloud-Antwort erfüllt den Markdown-Minimalvertrag nicht."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ValidatedCloudMarkdown:
    """Lokal geprüfter Markdown-Inhalt mit nachvollziehbaren Seitenmarkern."""

    content: str
    page_numbers: tuple[int, ...]


def validate_cloud_markdown_response(
    *, response: dict[str, Any], expected_page_count: int | None = None, expected_page_numbers: tuple[int, ...] | None = None
) -> ValidatedCloudMarkdown:
    """Prüft Response-Status, Text und Seitenmarker ohne Textlayer-Vergleich."""
    if response.get("status") != "completed":
        _raise_response_status_error(response)
    if response.get("incomplete_details") is not None:
        _raise("CLOUD_RESPONSE_INCOMPLETE", "Die Cloud-Antwort ist als unvollständig markiert.")
    content = _extract_output_text(response)
    if not content.strip():
        _raise("CLOUD_MARKDOWN_EMPTY", "Die Cloud-Antwort enthält kein Markdown.")
    if FORBIDDEN_OUTPUT.search(content):
        _raise("CLOUD_MARKDOWN_FORBIDDEN_OUTPUT", "Die Cloud-Antwort enthält unzulässige Ausgabeformen oder Befehle.")
    if expected_page_count is not None and expected_page_numbers is not None:
        raise ValueError("expected_page_count und expected_page_numbers schließen sich aus.")
    expected: tuple[int, ...] | None = None
    if expected_page_count is not None:
        if expected_page_count < 1:
            raise ValueError("expected_page_count muss mindestens 1 sein.")
        expected = tuple(range(1, expected_page_count + 1))
    if expected_page_numbers is not None:
        if not expected_page_numbers or any(not isinstance(page, int) or page < 1 for page in expected_page_numbers):
            raise ValueError("expected_page_numbers muss positive Seitennummern enthalten.")
        expected = expected_page_numbers
    page_numbers = _validate_page_markers(content, expected_page_numbers=expected)
    if expected is not None and page_numbers != expected:
        if expected_page_numbers is not None:
            _raise("CLOUD_MARKDOWN_PAGE_COUNT", "Die Cloud-Antwort enthält nicht die erwarteten Originalseitenmarker.")
        _raise("CLOUD_MARKDOWN_PAGE_COUNT", "Die Cloud-Antwort enthält nicht alle erwarteten Seitenmarker.")
    return ValidatedCloudMarkdown(content=content, page_numbers=page_numbers)


def _raise_response_status_error(response: dict[str, Any]) -> None:
    status = response.get("status")
    if status == "incomplete":
        _raise("CLOUD_RESPONSE_TRUNCATED", "Die Cloud-Antwort wurde unvollständig beendet.")
    _raise("CLOUD_RESPONSE_NOT_COMPLETED", "Die Cloud-Antwort wurde nicht erfolgreich abgeschlossen.")


def _extract_output_text(response: dict[str, Any]) -> str:
    direct_text = response.get("output_text")
    if isinstance(direct_text, str):
        return direct_text
    parts: list[str] = []
    output = response.get("output")
    if not isinstance(output, list):
        _raise("CLOUD_MARKDOWN_MISSING", "Die Cloud-Antwort enthält keinen Textausgabebereich.")
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if not parts:
        _raise("CLOUD_MARKDOWN_MISSING", "Die Cloud-Antwort enthält keinen Textausgabebereich.")
    return "".join(parts)


def _validate_page_markers(content: str, *, expected_page_numbers: tuple[int, ...] | None = None) -> tuple[int, ...]:
    lines = content.splitlines()
    first_nonempty = next((line.strip() for line in lines if line.strip()), None)
    expected_first_page = expected_page_numbers[0] if expected_page_numbers is not None else 1
    if first_nonempty != f"<!-- doctomd:page={expected_first_page} -->":
        _raise("CLOUD_MARKDOWN_FIRST_PAGE", f"Das Cloud-Markdown muss mit dem Marker der Seite {expected_first_page} beginnen.")
    page_numbers = tuple(int(match.group(1)) for match in PAGE_MARKER.finditer(content))
    if not page_numbers:
        _raise("CLOUD_MARKDOWN_PAGE_MARKERS", "Das Cloud-Markdown enthält keine Seitenmarker.")
    expected = tuple(range(1, len(page_numbers) + 1))
    if expected_page_numbers is None and page_numbers != expected:
        _raise("CLOUD_MARKDOWN_PAGE_MARKERS", "Die Seitenmarker müssen lückenlos und aufsteigend sein.")
    marker_lines = [line.strip() for line in lines if "doctomd:page=" in line]
    if marker_lines != [f"<!-- doctomd:page={page} -->" for page in page_numbers]:
        _raise("CLOUD_MARKDOWN_PAGE_MARKERS", "Die Seitenmarker müssen alleinstehend und exakt formatiert sein.")
    return page_numbers


def _raise(code: str, message: str) -> None:
    raise CloudMarkdownValidationError(code, message)


__all__ = [
    "CloudMarkdownValidationError",
    "ValidatedCloudMarkdown",
    "validate_cloud_markdown_response",
]
