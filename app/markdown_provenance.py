"""Maschinenlesbare Herkunft für veröffentlichte Markdown-Derivate."""

from __future__ import annotations

import json
import re

from app.models import SourceDocument


_PROVENANCE_BLOCK = re.compile(r"\A---\n(?P<body>.*?)\n---\n(?:\n)?", re.DOTALL)


def add_provenance_block(*, content: str, source: SourceDocument, derivative_kind: str) -> str:
    """Stellt einen idempotenten DocToMD-Front-Matter-Block voran.

    Der absolute lokale Pfad bleibt ausschließlich im Manifest. Das Markdown
    enthält nur den portablen Dateinamen und den Quellhash.
    """
    if derivative_kind not in {"local", "cloud", "vision", "index"}:
        raise ValueError("Unbekannte DocToMD-Ableitungsart.")
    if source.sha256 is None:
        raise ValueError("Der Provenienzblock benötigt einen Quellhash.")
    remainder = strip_provenance_block(content)
    header = (
        "---\n"
        f"doctomd_source_document: {json.dumps(source.path.name, ensure_ascii=False)}\n"
        f"doctomd_source_sha256: {source.sha256}\n"
        f"doctomd_derivative_kind: {derivative_kind}\n"
        "---\n\n"
    )
    return header + remainder.lstrip("\n")


def strip_provenance_block(content: str) -> str:
    """Entfernt ausschließlich einen von DocToMD verwalteten Front-Matter-Block."""
    match = _PROVENANCE_BLOCK.match(content)
    if match is None or "doctomd_source_document:" not in match.group("body"):
        return content
    return content[match.end():]


__all__ = ["add_provenance_block", "strip_provenance_block"]
