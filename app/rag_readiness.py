"""Bewertet, ob ein Konvertierungslauf ohne weitere Rekonstruktion RAG-tauglich ist."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from app.models import ConversionWarning


_LOCAL_BLOCKERS = frozenset({
    "FORMULA_NOT_RECONSTRUCTED",
    "DISPLAY_FORMULA_LAYOUT_NOT_RECONSTRUCTED",
    "MULTI_COLUMN_LAYOUT",
    "MULTILINE_TABLE_CELLS",
    "OCR_LOW_CONFIDENCE",
    "OCR_LAYOUT_FALLBACK",
    "UNREADABLE_PDF_GLYPHS",
    "UNSUPPORTED_TABLE_STRUCTURE",
})
_CLOUD_CANDIDATE_REASONS = _LOCAL_BLOCKERS


def assess_rag_readiness(*, warnings: Iterable[ConversionWarning], rag_indexing: dict[str, Any]) -> dict[str, Any]:
    """Erstellt eine konservative, lokale Folgeempfehlung ohne Aktionen auszulösen.

    Die Befunde stammen aus der Analyse der Original-PDF und ihrer Derivate.
    Sie sind kein semantischer Vollständigkeitsnachweis und aktivieren niemals
    OCR, Vision oder einen Cloud-Transport.
    """
    warning_list = tuple(warnings)
    reasons = _reasons(warning_list)
    local_derivative_suitable = not any(item["code"] in _LOCAL_BLOCKERS for item in reasons)
    recommended_path = rag_indexing["recommended_markdown_path"]
    cloud_recommended = recommended_path.endswith(".cloud.md")

    if local_derivative_suitable:
        status = "ready"
        next_steps: list[dict[str, Any]] = []
    elif cloud_recommended:
        status = "review_required"
        next_steps = [{
            "kind": "review_recommended_derivative",
            "requires_explicit_opt_in": False,
            "reason_codes": [item["code"] for item in reasons],
        }]
    else:
        status = "local_not_suitable"
        blocker_codes = {item["code"] for item in reasons}
        next_steps = []
        if "UNREADABLE_PDF_GLYPHS" in blocker_codes:
            next_steps.append({
                "kind": "force_ocr",
                "requires_explicit_opt_in": True,
                "reason_codes": ["UNREADABLE_PDF_GLYPHS"],
            })
        if blocker_codes & _CLOUD_CANDIDATE_REASONS:
            next_steps.append({
                "kind": "cloud_document",
                "requires_explicit_opt_in": True,
                "reason_codes": [item["code"] for item in reasons if item["code"] in _CLOUD_CANDIDATE_REASONS],
            })

    return {
        "schema_version": "1.0",
        "status": status,
        "local_derivative_suitable": local_derivative_suitable,
        "recommended_derivative_path": recommended_path,
        "reasons": reasons,
        "suggested_next_steps": next_steps,
        "recommended_next_step": _recommended_next_step(status, next_steps),
    }


def _reasons(warnings: Iterable[ConversionWarning]) -> list[dict[str, Any]]:
    pages_by_code: dict[str, set[int]] = defaultdict(set)
    counts_by_code: dict[str, int] = defaultdict(int)
    for warning in warnings:
        if warning.code not in _CLOUD_CANDIDATE_REASONS:
            continue
        counts_by_code[warning.code] += 1
        if warning.page is not None:
            pages_by_code[warning.code].add(warning.page.page_number)
    return [
        {"code": code, "count": counts_by_code[code], "pages": sorted(pages_by_code[code])}
        for code in sorted(counts_by_code)
    ]


def _recommended_next_step(status: str, next_steps: list[dict[str, Any]]) -> dict[str, Any]:
    if status == "ready":
        return {
            "kind": "none",
            "requires_explicit_opt_in": False,
            "message": "Keine weitere Rekonstruktion erforderlich; das empfohlene Derivat kann vor der Indexierung regulär geprüft werden.",
        }
    for step in next_steps:
        if step["kind"] == "cloud_document":
            return {
                "kind": "cloud_document",
                "requires_explicit_opt_in": True,
                "message": "Das lokale Derivat ist nicht RAG-geeignet. Starte bei bewusster Freigabe einen Cloud-Dokumentlauf und prüfe danach das empfohlene Derivat.",
            }
    for step in next_steps:
        if step["kind"] == "force_ocr":
            return {
                "kind": "force_ocr",
                "requires_explicit_opt_in": True,
                "message": "Das lokale Derivat ist nicht RAG-geeignet. Führe bei bewusster Freigabe einen OCR-Forcelauf aus und prüfe das Ergebnis erneut.",
            }
    return {
        "kind": "review_recommended_derivative",
        "requires_explicit_opt_in": False,
        "message": "Prüfe das bereits empfohlene Derivat an den genannten Originalseiten, bevor es indexiert wird.",
    }


__all__ = ["assess_rag_readiness"]
