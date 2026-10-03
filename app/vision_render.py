"""Lokales Rendern einzelner PDF-Seiten für den expliziten Vision-Schritt."""

from __future__ import annotations

from pathlib import Path
import subprocess


class VisionRenderError(OSError):
    """Eine ausgewählte PDF-Seite konnte nicht als PNG erzeugt werden."""


def render_page(*, source_path: Path, page_number: int, output_path: Path, dpi: int) -> Path:
    """Rendert genau eine einsbasierte Seite mit Poppler, ohne die Quelle zu ändern."""
    if page_number < 1:
        raise ValueError("page_number muss mindestens 1 sein.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = output_path.with_suffix("")
    try:
        completed = subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_number), "-l", str(page_number), "-singlefile", str(source_path), str(prefix)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise VisionRenderError("Poppler pdftoppm ist für den Vision-Schritt nicht verfügbar.") from error
    if completed.returncode != 0 or not output_path.is_file():
        raise VisionRenderError(f"Die PDF-Seite {page_number} konnte nicht gerendert werden.")
    return output_path


__all__ = ["VisionRenderError", "render_page"]
