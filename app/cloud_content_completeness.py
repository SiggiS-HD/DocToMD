"""Lokale Mindestprüfung der Cloud-Inhaltsdichte je Originalseite."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re


_PAGE_MARKER = re.compile(r"<!-- doctomd:page=([1-9][0-9]*) -->")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_NATIVE_LINK_SECTION = re.compile(
    r"<!-- doctomd:native-pdf-links page=[1-9][0-9]* -->\s*"
    r"\*\*Lokale PDF-Links\*\*(?:\s*\n- \[[^\n]+\]\(<[^\n]+>\))*",
    re.MULTILINE,
)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
_WARNING = re.compile(r"^\s*>\s*(?:\[!warning\])?", re.IGNORECASE)
_IMAGE = re.compile(r"^\s*!\[[^\]]*\]\([^\n]*\)\s*$")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_GFM_TABLE_SEPARATOR = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
_FORMULA = re.compile(r"\$\$|(?<!\\)\$(?!\$).+?(?<!\\)\$(?!\$)", re.DOTALL)


class CloudContentCompletenessError(ValueError):
    """Das Cloud-Markdown enthält zu wenig prüfbaren Seiteninhalt."""


@dataclass(frozen=True, slots=True)
class _PageContent:
    word_count: int
    has_table: bool
    has_formula: bool


def verify_cloud_content_completeness(*, local_markdown: str, cloud_markdown: str) -> None:
    """Lehnt dünne Cloud-Seiten gegen die geprüfte lokale Basis ab.

    Die Prüfung ist absichtlich keine semantische Gleichheitsbehauptung. Sie
    verlangt aber für jede lokal gehaltvolle Seite eine nicht nur aus
    Überschriften oder Warn-Callouts bestehende Cloud-Seite mit mindestens
    einem Fünftel der lokalen Wortdichte (mindestens ein bis drei Wörter).
    Lokal sichtbare Tabellen und Formeln benötigen außerdem ihren jeweiligen
    Markdown-Strukturträger im Cloud-Derivat.
    """
    local_pages = _pages(local_markdown)
    cloud_pages = _pages(cloud_markdown)
    if tuple(local_pages) != tuple(cloud_pages):
        raise CloudContentCompletenessError("Die Cloud-Seiten stimmen nicht mit der lokalen Basis überein.")
    incomplete: list[str] = []
    for page_number, local_content in local_pages.items():
        local = _profile(local_content)
        cloud = _profile(cloud_pages[page_number])
        required_words = min(local.word_count, max(1, math.ceil(local.word_count / 5)))
        if local.word_count and cloud.word_count < required_words:
            incomplete.append(f"Seite {page_number}: zu wenig Fließ- oder Listeninhalt")
        if local.has_table and not cloud.has_table:
            incomplete.append(f"Seite {page_number}: lokale Tabelle fehlt")
        if local.has_formula and not cloud.has_formula:
            incomplete.append(f"Seite {page_number}: lokale Formelstruktur fehlt")
    if incomplete:
        raise CloudContentCompletenessError("; ".join(incomplete))


def _pages(markdown: str) -> dict[int, str]:
    markers = tuple(_PAGE_MARKER.finditer(markdown))
    return {
        int(marker.group(1)): markdown[marker.end():markers[index + 1].start() if index + 1 < len(markers) else len(markdown)]
        for index, marker in enumerate(markers)
    }


def _profile(page_content: str) -> _PageContent:
    cleaned = _NATIVE_LINK_SECTION.sub("", page_content)
    cleaned = _HTML_COMMENT.sub("", cleaned)
    body_lines: list[str] = []
    has_table = False
    for line in cleaned.splitlines():
        if _HEADING.match(line) or _WARNING.match(line) or _IMAGE.match(line):
            continue
        if _GFM_TABLE_SEPARATOR.match(line):
            has_table = True
            continue
        body_lines.append(line)
    body = "\n".join(body_lines)
    return _PageContent(
        word_count=len(_WORD.findall(body)),
        has_table=has_table,
        has_formula=bool(_FORMULA.search(body)),
    )


__all__ = ["CloudContentCompletenessError", "verify_cloud_content_completeness"]
