"""Lokale Auswahl risikobehafteter PDF-Seiten für einen späteren Vision-Schritt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models import ConversionWarning
from app.pdf_extract import ExtractedPage
from app.vision_config import VisionConfig, VisionMode, VisionProvider


RISK_WARNING_CODES = frozenset(
    {
        "FORMULA_NOT_RECONSTRUCTED",
        "MULTI_COLUMN_LAYOUT",
        "POSSIBLE_HYPHENATION_PRESERVED",
        "UNREADABLE_PDF_GLYPHS",
        "MULTILINE_TABLE_CELLS",
        "UNSUPPORTED_EMBEDDED_IMAGE",
        "UNSUPPORTED_TABLE_STRUCTURE",
    }
)


@dataclass(frozen=True, slots=True)
class VisionPagePlan:
    """Deterministische, seitenbezogene Auswahl ohne Rendern oder Netzwerkzugriff."""

    page_numbers: tuple[int, ...] = ()


def plan_vision_pages(
    *,
    config: VisionConfig,
    pages: Iterable[ExtractedPage],
    warnings: Iterable[ConversionWarning],
) -> VisionPagePlan:
    """Wählt nur im expliziten Modus ``auto`` oder ``force`` geeignete Seiten.

    ``auto`` nutzt ausschließlich bereits lokale, seitenbezogene Qualitätswarnungen.
    Dadurch kann ein späterer Cloud-Provider niemals eine unauffällige Seite als
    Nebenwirkung der normalen Konvertierung erhalten.
    """
    page_numbers = tuple(page.page_number for page in pages)
    if config.provider is VisionProvider.NONE or config.mode is VisionMode.OFF:
        return VisionPagePlan()
    if config.mode is VisionMode.FORCE:
        return VisionPagePlan(page_numbers)

    risky_pages = {
        warning.page.page_number
        for warning in warnings
        if warning.code in RISK_WARNING_CODES and warning.page is not None
    }
    return VisionPagePlan(tuple(page_number for page_number in page_numbers if page_number in risky_pages))


__all__ = ["RISK_WARNING_CODES", "VisionPagePlan", "plan_vision_pages"]
