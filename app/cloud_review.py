"""Fügt lokale Qualitätsbefunde in ein lesbares Cloud-Markdown ein."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from app.markdown_writer import render_native_pdf_links
from app.models import Asset, ConversionWarning, NativePdfLink, WarningSeverity
from app.native_pdf_links import validate_native_pdf_links


_PAGE_MARKER = re.compile(r"(?m)^<!-- doctomd:page=([1-9][0-9]*) -->$")
_NATIVE_LINK_MARKER = re.compile(r"(?m)^<!-- doctomd:native-pdf-links page=[1-9][0-9]* -->$")
_FIGURE_CAPTION = re.compile(r"(?:figure|fig\.?|abbildung)\s*(?P<number>[1-9][0-9]*)\s*:", re.IGNORECASE)
_REDUNDANT_MODEL_FIGURE_WARNING = re.compile(
    r"(?im)^> \[!warning\]\n> (?:The page contains|(?:A|An) [^\n]*\bis visible on this page[.,])[^\n]*\n(?:\n)?"
)
_END_USER_WARNING_CODES = frozenset({
    "OCR_LOW_CONFIDENCE",
    "UNREADABLE_PDF_GLYPHS",
    "FORMULA_NOT_RECONSTRUCTED",
    "VISION_BACKEND_UNREACHABLE",
    "VISION_INVALID_JSON",
    "VISION_LOW_CONFIDENCE",
    "VISION_TIMEOUT",
    "VISION_UNVERIFIABLE_CONTENT",
})


def inject_cloud_review_warnings(
    *, content: str, warnings: Iterable[ConversionWarning]
) -> str:
    """Platziert seitenbezogene lokale Prüfhinweise direkt nach dem Marker.

    Nur explizit endbenutzerrelevante Warnungen und Fehler mit konkreter Seite
    werden aufgenommen. Technische Analysebefunde bleiben im Manifest, damit
    sie das bearbeitbare Dokument nicht mit wiederholten Callouts überlagern.
    """
    unreadable_glyph_pages = _unreadable_glyph_pages(content)
    warnings_by_page: dict[int, list[ConversionWarning]] = defaultdict(list)
    for warning in warnings:
        if (
            warning.page is not None
            and warning.severity in {WarningSeverity.WARNING, WarningSeverity.ERROR}
            and warning.code in _END_USER_WARNING_CODES
            and not (
                warning.code == "UNREADABLE_PDF_GLYPHS"
                and warning.page.page_number not in unreadable_glyph_pages
            )
        ):
            warnings_by_page[warning.page.page_number].append(warning)
    if not warnings_by_page:
        return content

    def add_after_marker(match: re.Match[str]) -> str:
        page_number = int(match.group(1))
        page_warnings = warnings_by_page.get(page_number, ())
        if not page_warnings:
            return match.group(0)
        return match.group(0) + "\n\n" + _render_callouts(page_warnings)

    return _PAGE_MARKER.sub(add_after_marker, content)


def _unreadable_glyph_pages(content: str) -> frozenset[int]:
    markers = tuple(_PAGE_MARKER.finditer(content))
    pages: set[int] = set()
    for index, marker in enumerate(markers):
        page_end = markers[index + 1].start() if index + 1 < len(markers) else len(content)
        if "(cid:" in content[marker.end():page_end]:
            pages.add(int(marker.group(1)))
    return frozenset(pages)


def inject_cloud_assets(
    *,
    content: str,
    assets: Iterable[Asset],
    skip_page_numbers: frozenset[int] = frozenset(),
) -> str:
    """Ergänzt lokal exportierte Abbildungen im Cloud-Derivat.

    Ein Asset wird direkt hinter seiner sichtbaren Caption eingefügt, wenn die
    Cloud sie unverändert erhalten hat. Ohne sicher auffindbare Caption wird es
    am Ende der jeweiligen Seite ergänzt. Vollseitige Scan-Raster werden vom
    Aufrufer seitenbezogen ausgelassen; ihre Dateien bleiben als prüfbare lokale
    Assets und im Manifest erhalten.
    """
    assets_by_page: dict[int, list[Asset]] = defaultdict(list)
    for asset in assets:
        if asset.page.page_number in skip_page_numbers:
            continue
        assets_by_page[asset.page.page_number].append(asset)
    if not assets_by_page:
        return content

    markers = list(_PAGE_MARKER.finditer(content))
    parts: list[str] = []
    cursor = 0
    for index, marker in enumerate(markers):
        parts.append(content[cursor:marker.start()])
        next_start = markers[index + 1].start() if index + 1 < len(markers) else len(content)
        page_number = int(marker.group(1))
        page_content = content[marker.start():next_start]
        page_assets = assets_by_page.get(page_number, ())
        if page_assets:
            page_content = _REDUNDANT_MODEL_FIGURE_WARNING.sub("", page_content)
        parts.append(_insert_assets_into_page(page_content, page_assets))
        cursor = next_start
    parts.append(content[cursor:])
    return "".join(parts)


def inject_cloud_native_pdf_links(*, content: str, links: Iterable[NativePdfLink]) -> str:
    """Fügt ausschließlich die lokale, unveränderte Linkliste in das Cloud-Derivat ein."""
    link_list = validate_native_pdf_links(links)
    if not link_list:
        return content
    if _NATIVE_LINK_MARKER.search(content):
        raise ValueError("Die Cloud-Antwort darf keine DocToMD-Native-Linkliste enthalten.")
    links_by_page: dict[int, list[NativePdfLink]] = defaultdict(list)
    for link in link_list:
        links_by_page[link.page.page_number].append(link)

    markers = list(_PAGE_MARKER.finditer(content))
    parts: list[str] = []
    cursor = 0
    for index, marker in enumerate(markers):
        parts.append(content[cursor:marker.start()])
        next_start = markers[index + 1].start() if index + 1 < len(markers) else len(content)
        page_number = int(marker.group(1))
        page_content = content[marker.start():next_start]
        page_links = links_by_page.pop(page_number, ())
        if page_links:
            page_content = page_content.rstrip() + "\n\n" + render_native_pdf_links(page_links) + "\n"
        parts.append(page_content)
        cursor = next_start
    parts.append(content[cursor:])
    if links_by_page:
        raise ValueError("Ein nativer PDF-Link verweist auf eine im Cloud-Markdown fehlende Seite.")
    return "".join(parts)


def _insert_assets_into_page(content: str, assets: Iterable[Asset]) -> str:
    result = content
    deferred: list[str] = []
    for asset in assets:
        rendered = _render_asset(asset)
        caption = asset.caption
        caption_end = _find_caption_line_end(content=result, caption=caption)
        if caption_end is not None:
            result = result[:caption_end] + "\n\n" + rendered + result[caption_end:]
            continue
        deferred.append(rendered)
    if deferred:
        result = result.rstrip() + "\n\n" + "\n\n".join(deferred) + "\n"
    return result


def _find_caption_line_end(*, content: str, caption: str | None) -> int | None:
    """Findet eine eindeutige sichtbare Caption-Zeile ohne Modelltext zu raten."""
    if not caption:
        return None
    figure_match = _FIGURE_CAPTION.search(caption)
    if figure_match is not None:
        number = figure_match.group("number")
        candidates = [
            line.end()
            for line in re.finditer(r"(?m)^.*$", content)
            if _visible_figure_caption_number(line.group(0)) == number
        ]
        if len(candidates) == 1:
            return candidates[0]
        return None
    exact = tuple(re.finditer(re.escape(caption), content))
    if len(exact) != 1:
        return None
    return content.find("\n", exact[0].start()) if "\n" in content[exact[0].start():] else len(content)


def _visible_figure_caption_number(line: str) -> str | None:
    """Liest nur einen am Zeilenanfang sichtbaren Figure-/Fig.-Captionkopf."""
    candidate = line.lstrip()
    candidate = re.sub(r"^(?:>\s*|#{1,6}\s+|[-+]\s+|[0-9]+[.)]\s+)", "", candidate)
    candidate = candidate.lstrip("*_` ")
    match = _FIGURE_CAPTION.match(candidate)
    return None if match is None else match.group("number")


def _render_asset(asset: Asset) -> str:
    label = asset.caption or f"Abbildung {asset.asset_id}"
    parts = [
        f"<!-- doctomd:asset={asset.asset_id} page={asset.page.page_number} -->",
        f"![{label}]({asset.relative_path.as_posix()})",
    ]
    if asset.description_path is not None:
        parts.append(f"[Bildbeschreibung bearbeiten]({asset.description_path.as_posix()})")
    return "\n\n".join(parts)


def _render_callouts(warnings: Iterable[ConversionWarning]) -> str:
    callouts: list[str] = []
    for warning in warnings:
        callouts.append(
            f"> [!warning] DocToMD-Prüfhinweis `{warning.code}`\n"
            f"> {warning.message} Bitte den betreffenden Inhalt am Original prüfen."
        )
    return "\n\n".join(callouts)


__all__ = [
    "inject_cloud_assets",
    "inject_cloud_native_pdf_links",
    "inject_cloud_review_warnings",
]
