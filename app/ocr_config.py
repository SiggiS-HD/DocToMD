"""Validierung der konfigurierbaren OCR-Seitenauswahl."""

from __future__ import annotations


def resolve_ocr_pages(specification: str, *, page_count: int) -> frozenset[int]:
    """Löst `all` oder eine Liste wie `1-3,5` in einsbasierte Seiten auf."""
    if page_count < 1:
        return frozenset()
    normalized = specification.strip().lower()
    if normalized == "all":
        return frozenset(range(1, page_count + 1))
    selected: set[int] = set()
    for part in normalized.split(","):
        bounds = part.strip().split("-", maxsplit=1)
        try:
            first = int(bounds[0])
            last = int(bounds[-1])
        except ValueError as error:
            raise ValueError("--ocr-pages erwartet all oder Seiten wie 1-3,5.") from error
        if first < 1 or last < first or last > page_count:
            raise ValueError(f"--ocr-pages muss Seiten von 1 bis {page_count} enthalten.")
        selected.update(range(first, last + 1))
    if not selected:
        raise ValueError("--ocr-pages darf nicht leer sein.")
    return frozenset(selected)


def validate_min_word_confidence(value: int) -> int:
    if not 0 <= value <= 100:
        raise ValueError("--ocr-min-word-confidence muss zwischen 0 und 100 liegen.")
    return value


__all__ = ["resolve_ocr_pages", "validate_min_word_confidence"]
