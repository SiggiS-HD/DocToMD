"""Lokale Extraktion sicherer externer Ziele aus nativen PDF-Link-Annotationen."""

from __future__ import annotations

from dataclasses import dataclass, replace
import ipaddress
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from app.models import ConversionWarning, NativePdfLink, NativePdfLinkSource, PageReference, PdfAnnotationRect


class NativePdfLinkExtractionError(ValueError):
    """Die PDF konnte nicht sicher auf native Link-Annotationen geprüft werden."""


@dataclass(frozen=True, slots=True)
class NativePdfLinkExtractionOutcome:
    """Lokal akzeptierte Links und sichtbar bleibende Ablehnungswarnungen."""

    links: tuple[NativePdfLink, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()


@dataclass(frozen=True, slots=True)
class _VisibleLine:
    text: str
    left: float
    top: float
    right: float
    bottom: float


def extract_native_pdf_links(path: Path) -> NativePdfLinkExtractionOutcome:
    """Liest native Link-Annotationen, ohne ein extrahiertes Ziel aufzurufen."""
    source = path.expanduser().resolve(strict=False)
    links: list[NativePdfLink] = []
    warnings: list[ConversionWarning] = []
    try:
        with pdfplumber.open(source) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_reference = PageReference(page_number)
                page_links: list[NativePdfLink] = []
                rejected_counts: dict[str, int] = {}
                for annotation in _link_annotations(getattr(page, "annots", ())):
                    target_url = annotation.get("uri")
                    target_kind = _target_kind(target_url)
                    if target_kind is not None:
                        rejected_counts[target_kind] = rejected_counts.get(target_kind, 0) + 1
                        continue
                    try:
                        page_links.append(NativePdfLink(
                            target_url=target_url,
                            page=page_reference,
                            annotation_rect=PdfAnnotationRect(
                                left=float(annotation["x0"]),
                                bottom=float(annotation["y0"]),
                                right=float(annotation["x1"]),
                                top=float(annotation["y1"]),
                            ),
                        ))
                    except (KeyError, TypeError, ValueError):
                        rejected_counts["invalid_annotation"] = rejected_counts.get("invalid_annotation", 0) + 1
                if page_links:
                    visible_lines = _visible_lines(page)
                    links.extend(_with_visible_titles(page_links, float(page.height), visible_lines))
                warnings.extend(
                    _rejected_target_warning(target_kind, page_reference, count)
                    for target_kind, count in rejected_counts.items()
                )
    except (OSError, PDFSyntaxError, PdfminerException) as error:
        raise NativePdfLinkExtractionError(
            f"Native PDF-Link-Annotationen konnten nicht gelesen werden: {source}"
        ) from error
    return NativePdfLinkExtractionOutcome(tuple(links), tuple(warnings))


def link_display_label(link: NativePdfLink) -> str:
    """Gibt ausschließlich einen belegten Titel oder eine neutrale Seitenbezeichnung aus."""
    return link.visible_title or f"Externer Link auf Seite {link.page.page_number}"


def validate_native_pdf_links(links: Iterable[NativePdfLink]) -> tuple[NativePdfLink, ...]:
    """Prüft vor einer Übergabe nochmals Herkunft und Ziel ohne Netzverkehr."""
    link_list = tuple(links)
    for link in link_list:
        if link.source is not NativePdfLinkSource.NATIVE_PDF_LINK_ANNOTATION:
            raise ValueError("Native PDF-Links benötigen die Herkunft native_pdf_link_annotation.")
        if _target_kind(link.target_url) is not None:
            raise ValueError("Native PDF-Links benötigen ein sicheres externes HTTPS-Ziel.")
    return link_list


def _with_visible_titles(
    links: Iterable[NativePdfLink], page_height: float, lines: tuple[_VisibleLine, ...]
) -> tuple[NativePdfLink, ...]:
    return tuple(
        replace(link, visible_title=_visible_title(link.annotation_rect, page_height, lines))
        for link in links
    )


def _visible_title(
    rectangle: PdfAnnotationRect, page_height: float, lines: tuple[_VisibleLine, ...]
) -> str | None:
    annotation_top = page_height - rectangle.top
    annotation_bottom = page_height - rectangle.bottom
    below = [
        line for line in lines
        if rectangle.left - 3 <= line.left and line.right <= rectangle.right + 3
        and 0 <= line.top - annotation_bottom <= 18
    ]
    below_starts = [
        line for line in below
        if not any(
            other is not line and 0 <= line.top - other.bottom <= 6
            for other in below
        )
    ]
    if len(below_starts) == 1:
        return _join_title_lines(below_starts[0], lines, rectangle)

    above_right = [
        line for line in lines
        if 0 <= annotation_top - line.bottom <= 18
        and 0 <= line.left - rectangle.right <= 18
    ]
    if len(above_right) == 1:
        return above_right[0].text
    return None


def _join_title_lines(
    first_line: _VisibleLine, lines: tuple[_VisibleLine, ...], rectangle: PdfAnnotationRect
) -> str:
    title_lines = [first_line]
    while True:
        previous = title_lines[-1]
        continuation = [
            line for line in lines
            if rectangle.left - 3 <= line.left and line.right <= rectangle.right + 3
            and 0 <= line.top - previous.bottom <= 6
        ]
        if len(continuation) != 1:
            break
        title_lines.append(continuation[0])
    title = ""
    for line in title_lines:
        if title.endswith("-") and line.text[:1].islower():
            title = f"{title[:-1]}{line.text}"
        else:
            title = f"{title} {line.text}".strip()
    return title


def _visible_lines(page: Any) -> tuple[_VisibleLine, ...]:
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False, x_tolerance=1)
    ordered_words = sorted(
        (word for word in words if str(word.get("text", "")).strip()),
        key=lambda word: (float(word["top"]), float(word["x0"])),
    )
    row_groups: list[list[dict[str, Any]]] = []
    for word in ordered_words:
        if not row_groups or abs(float(word["top"]) - float(row_groups[-1][0]["top"])) > 3:
            row_groups.append([word])
        else:
            row_groups[-1].append(word)
    line_groups: list[list[dict[str, Any]]] = []
    for row in row_groups:
        row_segments: list[list[dict[str, Any]]] = []
        for word in sorted(row, key=lambda item: float(item["x0"])):
            if not row_segments or float(word["x0"]) - float(row_segments[-1][-1]["x1"]) > 18:
                row_segments.append([word])
            else:
                row_segments[-1].append(word)
        line_groups.extend(row_segments)
    return tuple(
        _VisibleLine(
            text=" ".join(str(word["text"]) for word in sorted(group, key=lambda item: float(item["x0"]))),
            left=min(float(word["x0"]) for word in group),
            top=min(float(word["top"]) for word in group),
            right=max(float(word["x1"]) for word in group),
            bottom=max(float(word["bottom"]) for word in group),
        )
        for group in line_groups
    )


def _link_annotations(annotations: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        data = annotation.get("data")
        subtype = data.get("Subtype") if isinstance(data, dict) else None
        if annotation.get("uri") is not None or str(subtype).casefold().rstrip("'").endswith("link"):
            yield annotation


def _target_kind(target_url: object) -> str | None:
    """Klassifiziert ohne Netzwerkzugriff ausschließlich syntaktisch."""
    if not isinstance(target_url, str) or not target_url or target_url != target_url.strip():
        return "invalid"
    if any(character.isspace() or ord(character) < 32 for character in target_url):
        return "invalid"
    try:
        parsed = urlsplit(target_url)
        _ = parsed.port
    except ValueError:
        return "invalid"
    if parsed.scheme.casefold() != "https" or not parsed.netloc or parsed.username or parsed.password:
        return "invalid"
    hostname = parsed.hostname
    if hostname is None:
        return "invalid"
    normalized_hostname = hostname.rstrip(".").casefold()
    if normalized_hostname == "localhost" or normalized_hostname.endswith(".localhost"):
        return "local"
    try:
        address = ipaddress.ip_address(normalized_hostname)
    except ValueError:
        return None
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
        or address.is_multicast
    ):
        return "local"
    return None


def _rejected_target_warning(target_kind: str, page: PageReference, count: int) -> ConversionWarning:
    prefix = f"{count} native PDF-Link-Annotation(en)"
    if target_kind == "invalid_annotation":
        return ConversionWarning(
            code="NATIVE_PDF_LINK_INVALID_ANNOTATION",
            message=f"{prefix} haben kein gültiges Rechteck und wurden nicht übernommen.",
            page=page,
        )
    if target_kind == "local":
        return ConversionWarning(
            code="NATIVE_PDF_LINK_LOCAL_TARGET",
            message=f"{prefix} verweisen auf ein lokales Ziel und wurden nicht übernommen.",
            page=page,
        )
    return ConversionWarning(
        code="NATIVE_PDF_LINK_UNSAFE_URL",
        message=f"{prefix} haben kein zulässiges externes HTTPS-Ziel und wurden nicht übernommen.",
        page=page,
    )


__all__ = [
    "NativePdfLinkExtractionError",
    "NativePdfLinkExtractionOutcome",
    "extract_native_pdf_links",
    "link_display_label",
    "validate_native_pdf_links",
]
