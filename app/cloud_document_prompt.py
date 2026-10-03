"""Versionierter Prompt-Vertrag für vollständiges Cloud-Dokument-Markdown."""

from __future__ import annotations


CLOUD_DOCUMENT_PROMPT_VERSION = "1.5"


def build_cloud_markdown_instructions() -> str:
    """Liefert den vollständigen, providerunabhängig prüfbaren Ausgabevertrag."""
    return """You convert the attached PDF into a complete, faithful Markdown derivative.

Return only UTF-8 Markdown. Do not add an introduction, explanation, YAML front matter, HTML document wrapper, file command, or shell command. Preserve source code as ordinary Markdown fenced code blocks when it is visible in the PDF; do not wrap the complete response in a code fence.

Preserve every PDF page in strictly ascending, one-based order. Begin the content for every source page with exactly `<!-- doctomd:page=N -->`, replacing N with that page number. Keep a page marker even if a page has no recoverable text.

Preserve the document's heading hierarchy using Markdown headings, paragraphs, lists, citations, footnotes, figure captions, and tables where they are visible. Render inline mathematics as `$...$` and standalone mathematics as `$$...$$`. Keep mathematical symbols and table cells faithful to the source; do not invent text, rows, columns, formula terms, citations, or references.

Produce an editable, visually structured document rather than a page transcription. Prefer normal Markdown for headings and prose, GitHub-Flavored Markdown tables for tabular findings, and small HTML tables only when they are necessary for a compact two-column header or aligned address block. Do not use ASCII-art spacing or preformatted text to imitate a table. Do not reproduce source-page images, screenshots, or PDF pages. Preserve visible figure captions, but do not emit Markdown or HTML image references (`![...](...)` or `<img ...>`), invent local image paths, or add a warning merely because a figure is not embedded; DocToMD adds verified local figure assets after validation.

When content is unreadable or structurally uncertain, retain its page marker and write a visible Markdown warning beginning with `> [!warning]` that describes the uncertainty. Never claim that the reconstruction is lossless or complete.

This is DocToMD cloud-document Markdown contract version 1.5."""


def build_batch_cloud_markdown_instructions(*, page_numbers: tuple[int, ...]) -> str:
    """Ergänzt den Cloud-Vertrag um die Originalseiten eines temporären Batches."""
    if not page_numbers or any(page < 1 for page in page_numbers):
        raise ValueError("Ein Cloud-Batch benötigt mindestens eine positive Originalseite.")
    pages = ", ".join(str(page) for page in page_numbers)
    return (
        build_cloud_markdown_instructions()
        + "\n\nThis input contains only the original PDF pages "
        + pages
        + ". Emit exactly these original page numbers in the page markers, not renumbered batch pages."
        + f" The first non-empty output line MUST be exactly `<!-- doctomd:page={page_numbers[0]} -->`, even when the attached subset itself has physical page 1."
        + " Do not emit prose, a title, or a batch-page marker before it."
    )


__all__ = ["CLOUD_DOCUMENT_PROMPT_VERSION", "build_batch_cloud_markdown_instructions", "build_cloud_markdown_instructions"]
