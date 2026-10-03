"""Menschenlesbare Prüfung nicht automatisch übernommener Vision-Ergebnisse."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable

from app.models import ConversionWarning


def render_vision_review(*, selected_pages: Iterable[int], proposal_paths: Iterable[PurePosixPath], warnings: Iterable[ConversionWarning]) -> str:
    """Listet Auswahl, akzeptierte Vorschläge und verworfene Seiten nachvollziehbar auf."""
    accepted = {path.stem.removeprefix("page-").removesuffix(".proposal") for path in proposal_paths}
    lines = ["# Vision-Review", "", "Dieses Artefakt ändert weder Quelle noch lokales Markdown.", "", "## Ausgewählte Seiten", ""]
    for page in selected_pages:
        key = f"{page:03d}"
        status = "akzeptierter Vorschlag vorhanden" if key in accepted else "kein automatisch übernehmbarer Vorschlag"
        lines.append(f"- Seite {page}: {status}")
    relevant = [warning for warning in warnings if warning.code.startswith("VISION_")]
    if relevant:
        lines.extend(["", "## Verworfene oder fehlgeschlagene Vorschläge", ""])
        lines.extend(f"- Seite {warning.page.page_number if warning.page else '?'}: `{warning.code}` – {warning.message}" for warning in relevant)
    return "\n".join(lines) + "\n"


__all__ = ["render_vision_review"]
