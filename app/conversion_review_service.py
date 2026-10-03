"""Deterministische, rein lokale Zusammenfassung eines Konvertierungsmanifests."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

from app.artifact_paths import plan_artifact_paths
from app.artifact_writer import write_text_artifact
from app.source_fingerprint import fingerprint_source


def write_conversion_review(*, input_path: Path, output_dir: Path, overwrite: bool) -> Path:
    """Prüft den lokalen Kontext und schreibt ausschließlich die Review-Note."""
    paths = plan_artifact_paths(source_path=input_path, output_dir=output_dir)
    source = fingerprint_source(input_path, media_type="application/pdf")
    try:
        manifest = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Das Konvertierungsmanifest ist nicht lesbar: {paths.manifest_path}") from error
    if manifest.get("source", {}).get("sha256") != source.sha256:
        raise ValueError("Das Konvertierungsmanifest gehört nicht zur unveränderten Primärquelle.")
    content = render_conversion_review(manifest=manifest)
    write_text_artifact(
        source_path=source.path,
        target_path=paths.conversion_review_path,
        content=content,
        overwrite=overwrite,
    )
    return paths.conversion_review_path


def render_conversion_review(*, manifest: dict) -> str:
    """Rendert ausschließlich belegbare Daten aus einem gültigen Manifest."""
    source = manifest["source"]
    conversion = manifest["conversion"]
    artifacts = manifest["artifacts"]
    local_reuse = artifacts.get("local_reuse", {})
    warnings = manifest.get("quality", {}).get("warnings", [])
    warning_counts = Counter(item.get("code", "UNKNOWN") for item in warnings if isinstance(item, dict))
    warning_pages: dict[str, set[int]] = defaultdict(set)
    for item in warnings:
        if isinstance(item, dict) and isinstance(item.get("code"), str) and isinstance(item.get("page"), dict):
            page = item["page"].get("page_number")
            if isinstance(page, int):
                warning_pages[item["code"]].add(page)
    lines = [
        "# Konvertierungsbewertung",
        "",
        "Diese Note wird deterministisch aus dem Konvertierungsmanifest erzeugt. Sie führt keine PDF-Analyse, Netzwerkanfrage oder inhaltliche Neubewertung aus.",
        "",
        "## Ergebnis",
        "",
        f"- Status: `{conversion.get('status', 'unknown')}`",
        f"- Quelle: `{source.get('path', 'unknown')}`",
        f"- Quellhash (SHA-256): `{source.get('sha256', 'unknown')}`",
        f"- Lokales Markdown: `{artifacts.get('markdown_path', 'unknown')}`",
        f"- Seiten: {len(local_reuse.get('page_numbers', []))}",
        f"- Assets: {len(artifacts.get('assets', []))}",
        f"- Native PDF-Links: {len(artifacts.get('native_pdf_links', {}).get('items', []))}",
    ]
    local_duration = _duration_between(conversion.get("started_at"), conversion.get("completed_at"))
    if local_duration is not None:
        lines.extend(["", "## Laufzeiten", "", f"- Lokale Verarbeitung: {_format_duration_ms(local_duration)}"])
    cloud_path = artifacts.get("cloud_markdown_path")
    if isinstance(cloud_path, str):
        lines.extend(["", "## Cloud-Derivat", "", f"- Datei: `{cloud_path}`"])
        cloud = conversion.get("cloud_document")
        if isinstance(cloud, dict):
            lines.append(f"- Modus: `{cloud.get('mode', 'single')}`")
            cloud_runs = cloud.get("batches") if isinstance(cloud.get("batches"), list) else [cloud]
            if isinstance(cloud.get("batches"), list):
                lines.append(f"- Validierte Batches: {len(cloud_runs)}")
            durations = [item["duration_ms"] for item in cloud_runs if isinstance(item, dict) and isinstance(item.get("duration_ms"), int)]
            if durations:
                if "## Laufzeiten" not in lines:
                    lines.extend(["", "## Laufzeiten", ""])
                lines.append(f"- Cloud-API-Laufzeit (Summe): {_format_duration_ms(sum(durations))}")
                if len(durations) > 1:
                    lines.append(f"- Cloud-Batchlaufzeit: {_format_duration_ms(min(durations))} bis {_format_duration_ms(max(durations))}")
    lines.extend(["", "## Qualitätsbefunde", "", f"- Qualitätsstatus: `{manifest.get('quality', {}).get('status', 'unknown')}`", f"- Warnungen: {len(warnings)}"])
    if warning_counts:
        lines.extend(["", "| Warncode | Anzahl | Betroffene Seiten |", "| --- | ---: | --- |"])
        for code, count in sorted(warning_counts.items()):
            pages = ", ".join(str(page) for page in sorted(warning_pages[code])) or "–"
            lines.append(f"| `{code}` | {count} | {pages} |")
    readiness = manifest.get("rag_readiness")
    if isinstance(readiness, dict):
        lines.extend(["", "## RAG-Empfehlung", ""])
        for key in ("status", "recommendation", "reason"):
            value = readiness.get(key)
            if value is not None:
                lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def _duration_between(started_at: object, completed_at: object) -> int | None:
    if not isinstance(started_at, str) or not isinstance(completed_at, str):
        return None
    try:
        return max(0, round((datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)).total_seconds() * 1000))
    except ValueError:
        return None


def _format_duration_ms(value: int) -> str:
    seconds, milliseconds = divmod(value, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} h")
    if minutes or hours:
        parts.append(f"{minutes} min")
    parts.append(f"{seconds},{milliseconds:03d} s")
    return " ".join(parts)


__all__ = ["render_conversion_review", "write_conversion_review"]
