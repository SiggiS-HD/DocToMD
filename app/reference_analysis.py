"""Konservative Analyse zitierbarer Verweise mit Seitenbezug."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from app.models import Asset, AssetKind, ConversionWarning, DocumentBlock, DocumentReference, DocumentTable, PageReference, ReferenceKind


_CITATION = re.compile(r"\[(?P<numbers>\d+(?:\s*,\s*\d+)*)\]")
_BIBLIOGRAPHY_ENTRY = re.compile(r"^\[(?P<number>\d+)\]\s+.+")
_FOOTNOTE_MARKER = re.compile(r"\[\^(?P<number>\d+)\]")
_FOOTNOTE_DEFINITION = re.compile(r"^\[\^(?P<number>\d+)\]:\s+.+")
_FIGURE_REFERENCE = re.compile(r"\b(?:Figure|Fig\.)\s+(?P<number>\d+)\b", re.IGNORECASE)
_TABLE_REFERENCE = re.compile(r"\bTable\s+(?P<number>\d+)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ReferenceAnalysisOutcome:
    """Erkannte Verweise und sichtbare Hinweise für nicht belegte Ziele."""

    references: tuple[DocumentReference, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()


def analyze_references(
    *,
    blocks: Iterable[DocumentBlock],
    assets: Iterable[Asset],
    tables: Iterable[DocumentTable],
) -> ReferenceAnalysisOutcome:
    """Erfasst nur Referenzen, deren Marker im extrahierten Text sichtbar sind.

    Ziele werden ausschließlich über eine sichtbare Literatur- oder Fußnotendefinition
    beziehungsweise die stabile Reihenfolge exportierter Abbildungen und Tabellen
    bestimmt. Nicht auflösbare Marker bleiben unverändert und führen zu einer Warnung.
    """
    block_list = tuple(blocks)
    bibliography_pages = _definition_pages(block_list, _BIBLIOGRAPHY_ENTRY)
    footnote_pages = _definition_pages(block_list, _FOOTNOTE_DEFINITION)
    figure_targets = tuple(asset for asset in assets if asset.kind is AssetKind.IMAGE)
    table_targets = tuple(tables)
    references: list[DocumentReference] = []
    warnings: list[ConversionWarning] = []

    for block in block_list:
        text = block.text
        is_bibliography_entry = _BIBLIOGRAPHY_ENTRY.match(text) is not None
        is_footnote_definition = _FOOTNOTE_DEFINITION.match(text) is not None
        if not is_bibliography_entry:
            for match in _CITATION.finditer(text):
                for number in _numbers(match.group("numbers")):
                    references.append(_reference_or_warning(
                        kind=ReferenceKind.CITATION,
                        label=f"[{number}]",
                        source_page=block.page,
                        target_page=bibliography_pages.get(number),
                        target_id=None,
                        warnings=warnings,
                    ))
        if not is_footnote_definition:
            for match in _FOOTNOTE_MARKER.finditer(text):
                number = int(match.group("number"))
                references.append(_reference_or_warning(
                    kind=ReferenceKind.FOOTNOTE,
                    label=f"[^{number}]",
                    source_page=block.page,
                    target_page=footnote_pages.get(number),
                    target_id=None,
                    warnings=warnings,
                ))
        _add_numbered_references(ReferenceKind.FIGURE, _FIGURE_REFERENCE, text, block.page, figure_targets, references, warnings)
        _add_numbered_references(ReferenceKind.TABLE, _TABLE_REFERENCE, text, block.page, table_targets, references, warnings)

    return ReferenceAnalysisOutcome(tuple(references), tuple(warnings))


def _definition_pages(blocks: tuple[DocumentBlock, ...], pattern: re.Pattern[str]) -> dict[int, PageReference]:
    definitions: dict[int, PageReference] = {}
    for block in blocks:
        match = pattern.match(block.text)
        if match is not None:
            definitions.setdefault(int(match.group("number")), block.page)
    return definitions


def _numbers(value: str) -> tuple[int, ...]:
    return tuple(int(number.strip()) for number in value.split(","))


def _add_numbered_references(kind: ReferenceKind, pattern: re.Pattern[str], text: str, page: PageReference, targets: tuple[Asset | DocumentTable, ...], references: list[DocumentReference], warnings: list[ConversionWarning]) -> None:
    for match in pattern.finditer(text):
        number = int(match.group("number"))
        target = targets[number - 1] if 1 <= number <= len(targets) else None
        references.append(_reference_or_warning(
            kind=kind,
            label=match.group(0),
            source_page=page,
            target_page=target.page if target is not None else None,
            target_id=(target.asset_id if isinstance(target, Asset) else target.table_id) if target is not None else None,
            warnings=warnings,
        ))


def _reference_or_warning(*, kind: ReferenceKind, label: str, source_page: PageReference, target_page: PageReference | None, target_id: str | None, warnings: list[ConversionWarning]) -> DocumentReference:
    if target_page is None:
        warnings.append(ConversionWarning(
            code="UNRESOLVED_DOCUMENT_REFERENCE",
            message=f"{kind.value.capitalize()}-Verweis {label} konnte keinem sicheren Ziel zugeordnet werden.",
            page=source_page,
        ))
    return DocumentReference(kind, label, source_page, target_page, target_id)


__all__ = ["ReferenceAnalysisOutcome", "analyze_references"]
