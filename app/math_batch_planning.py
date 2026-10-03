"""Deterministische, rein lokale Planung kleiner mathematischer Cloud-Batches."""

from __future__ import annotations

from dataclasses import dataclass
import re


BATCH_PLAN_SCHEMA_VERSION = "1.0"
MAX_BATCH_PAGES = 6
MAX_DENSE_PAGES_PER_BATCH = 1
_PAGE_MARKER = re.compile(r"<!-- doctomd:page=([1-9][0-9]*) -->")
_CHAPTER_HEADING = re.compile(r"^\s{0,3}#{1,2}\s+(.+?)\s*$")
_DISPLAY_FORMULA_DELIMITER = re.compile(r"(?<!\\)\$\$(?!\$)")
_GFM_TABLE_SEPARATOR = re.compile(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
_TABLE_MARKER = re.compile(r"<!-- doctomd:table=[^\s]+ page=[1-9][0-9]* -->")


class BatchPlanningError(ValueError):
    """Das lokale Markdown kann nicht sicher in fortlaufende Batches zerlegt werden."""


@dataclass(frozen=True, slots=True)
class CloudBatch:
    """Ein zusammenhängender, lokal geplanter Seitenbereich."""

    batch_id: str
    page_numbers: tuple[int, ...]
    chapter_start_page: int | None
    dense_page_numbers: tuple[int, ...]

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "page_numbers": list(self.page_numbers),
            "chapter_start_page": self.chapter_start_page,
            "dense_page_numbers": list(self.dense_page_numbers),
        }


@dataclass(frozen=True, slots=True)
class CloudBatchPlan:
    """Versionierter Plan ohne temporäre Dateien oder Cloud-Zustand."""

    batches: tuple[CloudBatch, ...]

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "schema_version": BATCH_PLAN_SCHEMA_VERSION,
            "max_pages_per_batch": MAX_BATCH_PAGES,
            "max_dense_pages_per_batch": MAX_DENSE_PAGES_PER_BATCH,
            "batches": [batch.to_contract_dict() for batch in self.batches],
        }


def plan_math_cloud_batches(*, markdown: str) -> CloudBatchPlan:
    """Plant Batches nach Kapitelgrenzen, Seitenlimit und mathematischer Dichte."""
    pages = _split_pages(markdown)
    batches: list[CloudBatch] = []
    current: list[_PageProfile] = []
    for page in pages:
        should_split = bool(current) and (
            len(current) >= MAX_BATCH_PAGES
            or page.chapter_start
            or (page.dense and any(item.dense for item in current))
        )
        if should_split:
            batches.append(_batch(len(batches) + 1, current))
            current = []
        current.append(page)
    if current:
        batches.append(_batch(len(batches) + 1, current))
    return CloudBatchPlan(tuple(batches))


@dataclass(frozen=True, slots=True)
class _PageProfile:
    page_number: int
    chapter_start: bool
    dense: bool


def _split_pages(markdown: str) -> tuple[_PageProfile, ...]:
    markers = tuple(_PAGE_MARKER.finditer(markdown))
    page_numbers = tuple(int(marker.group(1)) for marker in markers)
    if not markers or page_numbers != tuple(range(1, len(markers) + 1)):
        raise BatchPlanningError("Das Markdown benötigt lückenlose Seitenmarker ab Seite 1.")
    marker_lines = [line.strip() for line in markdown.splitlines() if "doctomd:page=" in line]
    if marker_lines != [f"<!-- doctomd:page={page_number} -->" for page_number in page_numbers]:
        raise BatchPlanningError("Die Seitenmarker müssen alleinstehend und exakt formatiert sein.")
    profiles: list[_PageProfile] = []
    for index, marker in enumerate(markers):
        content_end = markers[index + 1].start() if index + 1 < len(markers) else len(markdown)
        content = markdown[marker.end():content_end]
        formula_count = len(_DISPLAY_FORMULA_DELIMITER.findall(content)) // 2
        table_count = len(_TABLE_MARKER.findall(content)) + len(_GFM_TABLE_SEPARATOR.findall(content))
        profiles.append(_PageProfile(
            page_numbers[index],
            _has_chapter_heading(content, page_numbers[index]),
            formula_count >= 2 or table_count >= 1,
        ))
    return tuple(profiles)


def _has_chapter_heading(content: str, page_number: int) -> bool:
    """Ignoriert aus PDF-Layout abgeleitete Laufköpfe, TOC-Zeilen und Formelreste."""
    for line in content.splitlines():
        match = _CHAPTER_HEADING.match(line)
        if match is None:
            continue
        title = match.group(1).strip()
        letter_count = sum(character.isalpha() for character in title)
        if letter_count < 3 or "(cid:" in title or ". . ." in title:
            continue
        if title.startswith(f"{page_number} ") or re.search(rf"\b{page_number}$", title):
            continue
        return True
    return False


def _batch(index: int, pages: list[_PageProfile]) -> CloudBatch:
    page_numbers = tuple(page.page_number for page in pages)
    return CloudBatch(
        batch_id=f"batch-{index:03d}-pages-{page_numbers[0]:03d}-{page_numbers[-1]:03d}",
        page_numbers=page_numbers,
        chapter_start_page=next((page.page_number for page in pages if page.chapter_start), None),
        dense_page_numbers=tuple(page.page_number for page in pages if page.dense),
    )


__all__ = [
    "BATCH_PLAN_SCHEMA_VERSION",
    "MAX_BATCH_PAGES",
    "MAX_DENSE_PAGES_PER_BATCH",
    "BatchPlanningError",
    "CloudBatch",
    "CloudBatchPlan",
    "plan_math_cloud_batches",
]
