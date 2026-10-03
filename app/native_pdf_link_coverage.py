"""Vollständigkeitsprüfung für die lokale Native-PDF-Linkliste."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from app.markdown_writer import render_native_pdf_links
from app.models import NativePdfLink
from app.native_pdf_links import validate_native_pdf_links


class NativePdfLinkCoverageError(ValueError):
    """Ein Markdown-Derivat enthält die lokale Linkliste nicht unverändert."""


def verify_native_pdf_link_coverage(*, markdown: str, links: Iterable[NativePdfLink]) -> None:
    """Fordert jeden akzeptierten Link genau einmal in seiner Seitenliste.

    Der Vergleich verwendet den kanonischen lokalen Renderer. Dadurch werden
    Ziel, sichtbare oder neutrale Bezeichnung und Seitenmarker gemeinsam
    geprüft, ohne URLs abzurufen oder Markdown aus einem Modell auszuwerten.
    """
    links_by_page: dict[int, list[NativePdfLink]] = defaultdict(list)
    for link in validate_native_pdf_links(links):
        links_by_page[link.page.page_number].append(link)

    for page_number, page_links in links_by_page.items():
        expected = render_native_pdf_links(page_links)
        occurrences = markdown.count(expected)
        if occurrences != 1:
            raise NativePdfLinkCoverageError(
                "Die lokale Native-PDF-Linkliste für Seite "
                f"{page_number} ist im Markdown {occurrences}-mal statt genau einmal enthalten."
            )


__all__ = ["NativePdfLinkCoverageError", "verify_native_pdf_link_coverage"]
