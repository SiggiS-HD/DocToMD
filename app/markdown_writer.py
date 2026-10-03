"""Markdown-Rendering mit stabilen Seitenmarkern."""

from __future__ import annotations

from collections.abc import Iterable

from app.models import Asset, AssetKind, BlockKind, DocumentBlock, DocumentTable, NativePdfLink, PageMarker, PageReference
from app.native_pdf_links import link_display_label
from app.pdf_extract import ExtractedPage


class MarkdownRenderingError(ValueError):
    """Die Seiten können nicht nachvollziehbar als Markdown gerendert werden."""


def format_page_marker(marker: PageMarker) -> str:
    """Formatiert einen unsichtbaren, stabilen Seitenmarker für Markdown."""
    return f"<!-- doctomd:page={marker.page.page_number} -->"


def render_pages(pages: Iterable[ExtractedPage]) -> str:
    """Rendert extrahierte Seiten mit streng aufsteigenden Originalseitenmarkern."""
    rendered_pages: list[str] = []
    previous_page_number = 0
    for page in pages:
        if page.page_number <= previous_page_number:
            raise MarkdownRenderingError(
                "Seiten müssen für Markdown strikt aufsteigend und eindeutig sein."
            )
        previous_page_number = page.page_number
        marker = format_page_marker(PageMarker(PageReference(page.page_number)))
        rendered_pages.append(f"{marker}\n{page.text}" if page.text else marker)
    return "\n\n".join(rendered_pages)


def render_blocks(blocks: Iterable[DocumentBlock]) -> str:
    """Rendert grundlegende Blöcke als Markdown ohne Seitenmarker zu verändern."""
    rendered, _, _ = _render_blocks(tuple(blocks))
    return rendered


def _render_blocks(
    blocks: Iterable[DocumentBlock],
    ordered_item_number: int = 0,
    previous_was_list_item: bool = False,
) -> tuple[str, int, bool]:
    """Rendert einen Blockabschnitt und erhält optional Listenstatus über Seiten."""
    rendered_blocks: list[str] = []
    for block in blocks:
        if block.kind is BlockKind.HEADING:
            rendered = f"{'#' * block.heading_level} {block.text}"
        elif block.kind is BlockKind.LIST_ITEM:
            if block.ordered:
                ordered_item_number = ordered_item_number + 1 if previous_was_list_item else 1
                prefix = f"{ordered_item_number}."
            else:
                prefix = "-"
                ordered_item_number = 0
            rendered = f"{prefix} {block.text}"
        else:
            rendered = block.text
        separator = "\n" if previous_was_list_item and block.kind is BlockKind.LIST_ITEM else "\n\n"
        rendered_blocks.append(f"{separator if rendered_blocks else ''}{rendered}")
        previous_was_list_item = block.kind is BlockKind.LIST_ITEM
    return "".join(rendered_blocks), ordered_item_number, previous_was_list_item


def render_asset(asset: Asset) -> str:
    """Rendert eine seitenbezogene Bildreferenz samt optionalem Beschreibungslink."""
    if asset.kind is not AssetKind.IMAGE:
        raise MarkdownRenderingError("Nur Bildassets können als Markdown-Abbildung gerendert werden.")
    label = asset.caption or f"Abbildung {asset.asset_id}"
    rendered = f"<!-- doctomd:asset={asset.asset_id} page={asset.page.page_number} -->\n![{label}]({asset.relative_path.as_posix()})"
    if asset.description_path is not None:
        rendered += f"\n\n[Bildbeschreibung bearbeiten]({asset.description_path.as_posix()})"
    return rendered


def render_table(table: DocumentTable) -> str:
    """Rendert eine bereits validierte einfache Tabelle als GitHub-Flavored Markdown."""
    header = "| " + " | ".join(table.headers) + " |"
    separator = "| " + " | ".join("---" for _ in table.headers) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in table.rows]
    return f"<!-- doctomd:table={table.table_id} page={table.page.page_number} -->\n" + "\n".join([header, separator, *rows])


def render_native_pdf_links(links: Iterable[NativePdfLink]) -> str:
    """Rendert ausschließlich lokal geprüfte native PDF-Ziele als kompakte Liste."""
    link_list = tuple(links)
    if not link_list:
        return ""
    page_number = link_list[0].page.page_number
    if any(link.page.page_number != page_number for link in link_list):
        raise MarkdownRenderingError("Eine native PDF-Linkliste darf nur eine Seite enthalten.")
    entries = [
        f"- [{_escape_link_label(link_display_label(link))}](<{link.target_url}>)"
        for link in link_list
    ]
    return (
        f"<!-- doctomd:native-pdf-links page={page_number} -->\n"
        "**Lokale PDF-Links**\n"
        + "\n".join(entries)
    )


def _escape_link_label(label: str) -> str:
    return label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def render_document(pages: Iterable[ExtractedPage], blocks: Iterable[DocumentBlock], assets: Iterable[Asset] = (), tables: Iterable[DocumentTable] = (), native_pdf_links: Iterable[NativePdfLink] = ()) -> str:
    """Rendert Seitenmarker und die zugehörigen strukturierten Blöcke zusammen."""
    blocks_by_page: dict[int, list[DocumentBlock]] = {}
    for block in blocks:
        blocks_by_page.setdefault(block.page.page_number, []).append(block)
    assets_by_page: dict[int, list[Asset]] = {}
    for asset in assets:
        assets_by_page.setdefault(asset.page.page_number, []).append(asset)
    tables_by_page: dict[int, list[DocumentTable]] = {}
    for table in tables:
        tables_by_page.setdefault(table.page.page_number, []).append(table)
    links_by_page: dict[int, list[NativePdfLink]] = {}
    for link in native_pdf_links:
        links_by_page.setdefault(link.page.page_number, []).append(link)

    rendered_pages: list[str] = []
    page_continues_previous_list: list[bool] = []
    previous_page_number = 0
    ordered_item_number = 0
    previous_was_list_item = False
    for page in pages:
        if page.page_number <= previous_page_number:
            raise MarkdownRenderingError(
                "Seiten müssen für Markdown strikt aufsteigend und eindeutig sein."
            )
        previous_page_number = page.page_number
        marker = format_page_marker(PageMarker(PageReference(page.page_number)))
        page_blocks = blocks_by_page.pop(page.page_number, ())
        continues_list_item = (
            page.layout_html is None
            and previous_was_list_item
            and bool(page_blocks)
            and page_blocks[0].kind is BlockKind.PARAGRAPH
        )
        if continues_list_item:
            continuation = page_blocks[0]
            rendered_rest, ordered_item_number, previous_was_list_item = _render_blocks(
                page_blocks[1:], ordered_item_number, previous_was_list_item
            )
            rendered_blocks = f"  {marker}\n  {continuation.text}"
            if rendered_rest:
                rendered_blocks += f"\n{rendered_rest}"
            page_marker_is_embedded = True
        elif page.layout_html is None:
            rendered_blocks, ordered_item_number, previous_was_list_item = _render_blocks(
                page_blocks, ordered_item_number, previous_was_list_item
            )
            page_marker_is_embedded = False
        else:
            rendered_blocks = page.layout_html
            ordered_item_number = 0
            previous_was_list_item = False
            page_marker_is_embedded = False
        rendered_parts = [rendered_blocks]
        rendered_parts.append(render_native_pdf_links(links_by_page.pop(page.page_number, ())))
        if page.layout_html is not None:
            previous_was_list_item = False
        rendered_parts.extend(render_asset(asset) for asset in assets_by_page.pop(page.page_number, ()))
        rendered_parts.extend(render_table(table) for table in tables_by_page.pop(page.page_number, ()))
        page_markdown = "\n\n".join(part for part in rendered_parts if part)
        if page_marker_is_embedded:
            rendered_pages.append(page_markdown)
        else:
            rendered_pages.append(f"{marker}\n{page_markdown}" if page_markdown else marker)
        page_continues_previous_list.append(continues_list_item)
    if blocks_by_page:
        raise MarkdownRenderingError("Ein Block verweist auf eine nicht extrahierte Seite.")
    if assets_by_page:
        raise MarkdownRenderingError("Ein Asset verweist auf eine nicht extrahierte Seite.")
    if tables_by_page:
        raise MarkdownRenderingError("Eine Tabelle verweist auf eine nicht extrahierte Seite.")
    if links_by_page:
        raise MarkdownRenderingError("Ein nativer PDF-Link verweist auf eine nicht extrahierte Seite.")
    if not rendered_pages:
        return ""
    document = rendered_pages[0]
    for page_markdown, continues_list_item in zip(rendered_pages[1:], page_continues_previous_list[1:]):
        document += ("\n" if continues_list_item else "\n\n") + page_markdown
    return document


__all__ = [
    "MarkdownRenderingError",
    "format_page_marker",
    "render_blocks",
    "render_document",
    "render_asset",
    "render_native_pdf_links",
    "render_table",
    "render_pages",
]
