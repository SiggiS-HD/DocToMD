"""Ermittelt eine nachvollziehbare Empfehlung für die RAG-Indexierung."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any


_PAGE_MARKER = re.compile(r"<!-- doctomd:page=\d+ -->")
_HEADING = re.compile(r"(?m)^#{1,6}\s")
_TABLE_MARKER = re.compile(r"<!-- doctomd:table=[^\s]+ page=\d+ -->")
_GFM_TABLE = re.compile(r"(?m)^\|[^\n]*\|\r?\n\|(?:\s*:?-{3,}:?\s*\|)+\s*$")
_DISPLAY_FORMULA = re.compile(r"(?m)^\$\$")
_UNREADABLE_GLYPH = re.compile(r"\(cid:")


def recommend_markdown_for_rag(*, markdown_path: PurePosixPath, markdown: str, cloud_markdown_path: PurePosixPath | None = None, cloud_markdown: str | None = None) -> dict[str, Any]:
    """Wählt zwischen lokalem und bereits technisch validiertem Cloud-Markdown.

    Ein Cloud-Derivat wird ausschließlich empfohlen, wenn es mindestens ein
    zusätzliches lokal messbares Strukturelement enthält. Die Kennzahlen sind
    Diagnosewerte, keine Behauptung vollständiger inhaltlicher Korrektheit.
    """
    local = _candidate("local", markdown_path, markdown)
    candidates = [local]
    if cloud_markdown_path is None or cloud_markdown is None:
        return {
            "schema_version": "1.0",
            "recommended_markdown_path": markdown_path.as_posix(),
            "selection_reason": "cloud_derivative_not_available",
            "candidates": candidates,
        }

    cloud = _candidate("cloud", cloud_markdown_path, cloud_markdown)
    candidates.append(cloud)
    if cloud["structure_score"] > local["structure_score"]:
        return {
            "schema_version": "1.0",
            "recommended_markdown_path": cloud_markdown_path.as_posix(),
            "selection_reason": "validated_cloud_has_more_structure",
            "candidates": candidates,
        }
    return {
        "schema_version": "1.0",
        "recommended_markdown_path": markdown_path.as_posix(),
        "selection_reason": "local_structure_is_equal_or_better",
        "candidates": candidates,
    }


def _candidate(kind: str, path: PurePosixPath, content: str) -> dict[str, Any]:
    metrics = {
        "page_marker_count": len(_PAGE_MARKER.findall(content)),
        "heading_count": len(_HEADING.findall(content)),
        "table_count": _count_tables(content),
        "display_formula_count": len(_DISPLAY_FORMULA.findall(content)),
        "unreadable_glyph_count": len(_UNREADABLE_GLYPH.findall(content)),
    }
    structure_score = (
        metrics["heading_count"]
        + 3 * metrics["table_count"]
        + 2 * metrics["display_formula_count"]
        - metrics["unreadable_glyph_count"]
    )
    return {
        "kind": kind,
        "path": path.as_posix(),
        **metrics,
        "structure_score": structure_score,
    }


def _count_tables(content: str) -> int:
    """Zählt Tabellenmarker und GFM-Tabellen ohne doppelte Markerzählung."""
    marker_matches = tuple(_TABLE_MARKER.finditer(content))
    gfm_matches = tuple(_GFM_TABLE.finditer(content))
    paired_markers: set[int] = set()
    for table in gfm_matches:
        for index, marker in reversed(tuple(enumerate(marker_matches))):
            if marker.end() > table.start():
                continue
            if not content[marker.end():table.start()].strip():
                paired_markers.add(index)
            break
    return len(marker_matches) + len(gfm_matches) - len(paired_markers)


__all__ = ["recommend_markdown_for_rag"]
