"""Konservative, rein geometrische Erkennung nicht exportierter Vektorgrafiken."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any, Iterable

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from app.models import ConversionWarning, PageReference


_CAPTION_PATTERN = re.compile(r"^(?:Figure|Fig\.)\s*\d+\s*:", re.IGNORECASE)
_MAX_CAPTION_GAP = 42.0
_COMPONENT_GAP = 14.0
_CAPTION_SEGMENT_GAP = 12.0


@dataclass(frozen=True, slots=True)
class VectorFigureCandidate:
    """Lokal belegter, noch nicht exportierter Vektorgrafikbereich."""

    page: PageReference
    caption: str
    bbox: tuple[float, float, float, float]
    primitive_count: int


@dataclass(frozen=True, slots=True)
class VectorFigureDetectionOutcome:
    """Kandidaten und sichtbare Grenzen der noch nicht exportierten Vektorgrafiken."""

    candidates: tuple[VectorFigureCandidate, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()
    unresolved_page_numbers: tuple[int, ...] = ()


def detect_vector_figures(*, source_path: Path, raster_asset_pages: Iterable[int]) -> VectorFigureDetectionOutcome:
    """Findet nur eindeutig unter einer Figure-Caption liegende Vektorbereiche.

    Die Funktion schreibt oder rendert nichts. Sie betrachtet ausschließlich
    Seiten ohne bereits exportiertes Rasterasset und bewertet eine Caption nur
    gemeinsam mit einem geometrisch zusammenhängenden Bereich signifikanter
    PDF-Vektorprimitiven.
    """
    raster_pages = frozenset(raster_asset_pages)
    candidates: list[VectorFigureCandidate] = []
    warnings: list[ConversionWarning] = []
    try:
        with pdfplumber.open(source_path.expanduser().resolve(strict=False)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                if page_number in raster_pages:
                    continue
                outcome = _detect_page(page, page_number)
                candidates.extend(outcome.candidates)
                warnings.extend(outcome.warnings)
    except (OSError, PDFSyntaxError, PdfminerException):
        # Die Text- und Rasterpipeline meldet Lesefehler bereits separat. Ein
        # zusätzlicher Kandidat darf daraus nicht geraten werden.
        return VectorFigureDetectionOutcome()
    return VectorFigureDetectionOutcome(tuple(candidates), tuple(warnings))


def _detect_page(page: Any, page_number: int) -> VectorFigureDetectionOutcome:
    captions = _captions(page)
    if not captions:
        return VectorFigureDetectionOutcome()
    reference = PageReference(page_number)
    components = _components(_primitive_boxes(page))
    words = tuple(page.extract_words(keep_blank_chars=False, use_text_flow=False))
    assignments = [
        (caption, [index for index, (box, count) in enumerate(components) if _is_eligible_component(
            box=box,
            primitive_count=count,
            caption_top=caption_top,
            caption_x0=caption_x0,
            caption_x1=caption_x1,
            page_width=float(page.width),
            page_height=float(page.height),
            words=words,
        )])
        for caption, caption_top, caption_x0, caption_x1 in captions
    ]
    selected_indices = [indices[0] for _, indices in assignments if len(indices) == 1]
    has_conflict = len(selected_indices) != len(set(selected_indices))
    has_uncertain_caption = any(len(indices) != 1 for _, indices in assignments) or has_conflict
    if has_uncertain_caption:
        candidates = tuple(
            VectorFigureCandidate(reference, caption, components[indices[0]][0], components[indices[0]][1])
            for caption, indices in assignments
            if len(indices) == 1 and selected_indices.count(indices[0]) == 1
        )
        return VectorFigureDetectionOutcome(
            candidates=candidates,
            warnings=(ConversionWarning(
                "VECTOR_FIGURE_NOT_EXPORTED",
                "Mindestens eine Figure-/Fig.-Caption konnte keinem eindeutigen signifikanten Vektorbereich zugeordnet werden.",
                page=reference,
            ),),
            unresolved_page_numbers=(page_number,),
        )
    candidates = tuple(
        VectorFigureCandidate(reference, caption, components[indices[0]][0], components[indices[0]][1])
        for caption, indices in assignments
    )
    return VectorFigureDetectionOutcome(
        candidates=candidates,
        warnings=(ConversionWarning(
            "VECTOR_FIGURE_NOT_EXPORTED",
            "Eine caption-gebundene Vektorgrafik wurde lokal erkannt, aber in diesem Schritt nicht exportiert.",
            page=reference,
        ),),
    )


def _captions(page: Any) -> list[tuple[str, float, float, float]]:
    lines: dict[float, list[dict[str, Any]]] = {}
    for word in page.extract_words(keep_blank_chars=False, use_text_flow=False):
        lines.setdefault(round(float(word["top"]), 1), []).append(word)
    captions: list[tuple[str, float, float, float]] = []
    for top, words in sorted(lines.items()):
        for segment in _caption_segments(words):
            text = " ".join(str(word["text"]) for word in segment)
            if _CAPTION_PATTERN.match(text):
                captions.append((text, top, float(segment[0]["x0"]), float(segment[-1]["x1"])))
    return captions


def _caption_segments(words: list[dict[str, Any]]) -> tuple[tuple[dict[str, Any], ...], ...]:
    """Trennt nebeneinander gesetzte Captions, aber keine normalen Wortabstände."""
    ordered = tuple(sorted(words, key=lambda item: float(item["x0"])))
    if not ordered:
        return ()
    segments: list[list[dict[str, Any]]] = [[ordered[0]]]
    for word in ordered[1:]:
        if float(word["x0"]) - float(segments[-1][-1]["x1"]) > _CAPTION_SEGMENT_GAP:
            segments.append([word])
        else:
            segments[-1].append(word)
    return tuple(tuple(segment) for segment in segments)


def _primitive_boxes(page: Any) -> tuple[tuple[float, float, float, float], ...]:
    boxes = []
    for primitive in (*getattr(page, "lines", ()), *getattr(page, "rects", ()), *getattr(page, "curves", ())):
        try:
            box = tuple(float(primitive[key]) for key in ("x0", "top", "x1", "bottom"))
        except (KeyError, TypeError, ValueError):
            continue
        if all(isfinite(value) for value in box) and box[0] <= box[2] and box[1] <= box[3]:
            # Linien haben in pdfplumber häufig eine Nullhöhe oder -breite.
            # Eine minimale Ausdehnung erhält ihre lokale Geometrie, ohne aus
            # einzelnen Punkten künstlich Fläche zu machen.
            x0, top, x1, bottom = box
            if x0 == x1:
                x1 += 0.1
            if top == bottom:
                bottom += 0.1
            boxes.append((x0, top, x1, bottom))
    return tuple(boxes)


def _components(boxes: tuple[tuple[float, float, float, float], ...]) -> tuple[tuple[tuple[float, float, float, float], int], ...]:
    components: list[list[tuple[float, float, float, float]]] = []
    for box in boxes:
        matching = [component for component in components if _touches(box, _union(component))]
        if not matching:
            components.append([box])
            continue
        merged = [box]
        for component in matching:
            merged.extend(component)
            components.remove(component)
        components.append(merged)
    return tuple((_union(component), len(component)) for component in components)


def _touches(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    return not (
        left[2] + _COMPONENT_GAP < right[0]
        or right[2] + _COMPONENT_GAP < left[0]
        or left[3] + _COMPONENT_GAP < right[1]
        or right[3] + _COMPONENT_GAP < left[1]
    )


def _union(boxes: Iterable[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    items = tuple(boxes)
    return min(box[0] for box in items), min(box[1] for box in items), max(box[2] for box in items), max(box[3] for box in items)


def _is_eligible_component(*, box: tuple[float, float, float, float], primitive_count: int, caption_top: float, caption_x0: float, caption_x1: float, page_width: float, page_height: float, words: tuple[dict[str, Any], ...]) -> bool:
    x0, top, x1, bottom = box
    width, height = x1 - x0, bottom - top
    if primitive_count < 3 or width < page_width * 0.20 or height < page_height * 0.10:
        return False
    if bottom > caption_top or caption_top - bottom > _MAX_CAPTION_GAP:
        return False
    horizontal_overlap = max(0.0, min(x1, caption_x1) - max(x0, caption_x0))
    if horizontal_overlap < min(12.0, (caption_x1 - caption_x0) * 0.25):
        return False
    if width >= page_width * 0.96 and height >= page_height * 0.96:
        return False
    text_area = sum(
        max(0.0, float(word["x1"]) - float(word["x0"])) * max(0.0, float(word["bottom"]) - float(word["top"]))
        for word in words
        if x0 <= (float(word["x0"]) + float(word["x1"])) / 2 <= x1
        and top <= (float(word["top"]) + float(word["bottom"])) / 2 <= bottom
    )
    return text_area / (width * height) <= 0.30


__all__ = ["VectorFigureCandidate", "VectorFigureDetectionOutcome", "detect_vector_figures"]
