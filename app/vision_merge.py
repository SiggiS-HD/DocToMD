"""Explizite, konservative Übernahme validierter Vision-Vorschläge."""

from __future__ import annotations

from typing import Any, Iterable


def merge_validated_proposals(*, local_markdown: str, proposals: Iterable[dict[str, Any]]) -> str:
    """Erzeugt ein neues Derivat; nur exakt belegte Formeln werden ersetzt.

    Tabellen bleiben als klar markierte Ergänzung erhalten, weil ihre ursprüngliche
    Position ohne Koordinaten nicht sicher bestimmt werden kann.
    """
    merged = local_markdown
    supplements: list[str] = []
    for proposal in proposals:
        page_number = proposal["page"]["page_number"]
        for formula in proposal["formulas"]:
            source, latex = formula["source_text"], formula["latex"]
            if merged.count(source) == 1:
                merged = merged.replace(source, f"$$ {latex} $$", 1)
        for table in proposal["tables"]:
            title = table.get("title", "Vision-Tabelle")
            headers = "| " + " | ".join(table["headers"]) + " |"
            separator = "| " + " | ".join("---" for _ in table["headers"]) + " |"
            rows = "\n".join("| " + " | ".join(row) + " |" for row in table["rows"])
            supplements.append(f"<!-- doctomd:vision-table page={page_number} -->\n\n## {title} (Vision-Vorschlag, Seite {page_number})\n\n{headers}\n{separator}\n{rows}")
    if supplements:
        merged += "\n\n# Vision-Ergänzungen\n\n" + "\n\n".join(supplements)
    return merged


__all__ = ["merge_validated_proposals"]
