"""Deterministische Rekonstruktion einer kleinen, überprüfbaren Formelgrammatik."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re

from app.models import BlockKind, ConversionWarning, DocumentBlock


_IDENTIFIER = r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)?"
_DISPLAY_SUM_FRACTION = re.compile(
    rf"^(?P<left>{_IDENTIFIER}\({_IDENTIFIER}\))\s*=\s*"
    rf"sum_(?P<index>[A-Za-z0-9]+)\s+"
    rf"(?P<numerator>{_IDENTIFIER}(?:\s*\*\s*{_IDENTIFIER})*)\s*/\s*"
    rf"(?P<denominator>{_IDENTIFIER})$"
)
_FORMULA_CANDIDATE = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]*(?:\([A-Za-z0-9_]+\))?\s*=\s*"
    r"[A-Za-z0-9_()[\]{}+\-*/^.,\\\s]+$"
)


@dataclass(frozen=True, slots=True)
class FormulaRenderingOutcome:
    """Gerenderte Blöcke und sichtbare Grenzen nicht rekonstruierter Formeln."""

    blocks: tuple[DocumentBlock, ...]
    warnings: tuple[ConversionWarning, ...] = ()


def parse_display_formula(text: str) -> str | None:
    """Gibt LaTeX nur für die vollständig unterstützte Summenbruch-Grammatik zurück."""
    match = _DISPLAY_SUM_FRACTION.fullmatch(text.strip())
    if match is None:
        return None
    numerator = " ".join(match.group("numerator").replace("*", " ").split())
    return (
        f"{match.group('left')} = \\frac{{\\sum_{match.group('index')} {numerator}}}"
        f"{{{match.group('denominator')}}}"
    )


def render_formula_blocks(blocks: tuple[DocumentBlock, ...]) -> tuple[DocumentBlock, ...]:
    """Ersetzt nur eigenständige, sicher geparste Formeln durch Display-LaTeX."""
    return render_formula_blocks_with_warnings(blocks).blocks


def render_formula_blocks_with_warnings(blocks: tuple[DocumentBlock, ...]) -> FormulaRenderingOutcome:
    """Rendert sichere Formeln und warnt konservativ bei nicht rekonstruierbaren Kandidaten."""
    rendered: list[DocumentBlock] = []
    warnings: list[ConversionWarning] = []
    for block in blocks:
        latex = parse_display_formula(block.text) if block.kind is BlockKind.PARAGRAPH else None
        if latex:
            rendered.append(replace(block, text=f"$${latex}$$"))
        else:
            rendered.append(block)
            if block.kind is BlockKind.PARAGRAPH and _is_formula_candidate(block.text):
                warnings.append(
                    ConversionWarning(
                        "FORMULA_NOT_RECONSTRUCTED",
                        "Die Formel konnte nicht zuverlässig als LaTeX rekonstruiert werden.",
                        page=block.page,
                    )
                )
    return FormulaRenderingOutcome(tuple(rendered), tuple(warnings))


def _is_formula_candidate(text: str) -> bool:
    """Erkennt nur kurze, eigenständige Gleichungsformen statt Fließtext mit Gleichheitszeichen."""
    return len(text.strip()) <= 160 and _FORMULA_CANDIDATE.fullmatch(text.strip()) is not None


__all__ = ["FormulaRenderingOutcome", "parse_display_formula", "render_formula_blocks", "render_formula_blocks_with_warnings"]
