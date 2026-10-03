"""Verlustarme und nachvollziehbare Textnormalisierung."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
import unicodedata

from app.models import ConversionWarning, DocumentBlock, PageReference


_POSSIBLE_HYPHENATION = re.compile(r"\w-\s+(?=\w)")


@dataclass(frozen=True, slots=True)
class TextNormalizationResult:
    """Normalisierter Text mit dokumentierten Umformungen und Warnungen."""

    text: str
    transformations: tuple[str, ...]
    warnings: tuple[ConversionWarning, ...]


def normalize_text(text: str, *, page: PageReference | None = None) -> TextNormalizationResult:
    """Vereinheitlicht nur sichere Darstellungen und bewahrt unsicheren Inhalt."""
    transformations: list[str] = []
    normalized = text
    if "\r" in normalized:
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        transformations.append("line_endings_to_lf")

    nfc_text = unicodedata.normalize("NFC", normalized)
    if nfc_text != normalized:
        normalized = nfc_text
        transformations.append("unicode_nfc")

    warnings: list[ConversionWarning] = []
    if "\ufffd" in normalized:
        warnings.append(
            ConversionWarning(
                code="TEXT_REPLACEMENT_CHARACTER",
                message="Der extrahierte Text enthält ein nicht auflösbares Ersatzzeichen.",
                page=page,
            )
        )
    if "\u00ad" in normalized:
        warnings.append(
            ConversionWarning(
                code="SOFT_HYPHEN_PRESERVED",
                message="Ein weicher Trennstrich wurde unverändert beibehalten.",
                page=page,
            )
        )
    if _POSSIBLE_HYPHENATION.search(normalized):
        warnings.append(
            ConversionWarning(
                code="POSSIBLE_HYPHENATION_PRESERVED",
                message="Eine mögliche Zeilentrennung wurde nicht automatisch zusammengeführt.",
                page=page,
            )
        )

    return TextNormalizationResult(
        text=normalized,
        transformations=tuple(transformations),
        warnings=tuple(warnings),
    )


def normalize_blocks(
    blocks: tuple[DocumentBlock, ...],
) -> tuple[tuple[DocumentBlock, ...], tuple[ConversionWarning, ...]]:
    """Normalisiert Blocktext und erhält alle Struktur- und Seitenmetadaten."""
    normalized_blocks: list[DocumentBlock] = []
    warnings: list[ConversionWarning] = []
    for block in blocks:
        result = normalize_text(block.text, page=block.page)
        normalized_blocks.append(replace(block, text=result.text))
        warnings.extend(result.warnings)
    return tuple(normalized_blocks), tuple(warnings)


__all__ = ["TextNormalizationResult", "normalize_blocks", "normalize_text"]
