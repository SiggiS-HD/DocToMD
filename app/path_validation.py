"""Validierung von Quell- und Ausgabewegen für sichere Konvertierungen."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PathValidationError(ValueError):
    """Ein Quell-, Ausgabe- oder Schreibpfad verletzt den CLI-Vertrag."""


@dataclass(frozen=True, slots=True)
class ConversionPaths:
    """Kanonische Pfade einer zulässigen Konvertierungsanfrage."""

    source_path: Path
    output_dir: Path


def validate_conversion_paths(input_path: Path, output_dir: Path) -> ConversionPaths:
    """Prüft die Primärquelle und einen künftig beschreibbaren Ausgabeordner."""
    source_path = input_path.expanduser().resolve(strict=False)
    if not source_path.exists():
        raise PathValidationError(f"Die Quelldatei existiert nicht: {source_path}")
    if not source_path.is_file():
        raise PathValidationError(f"Der Eingabepfad ist keine Datei: {source_path}")

    resolved_output_dir = output_dir.expanduser().resolve(strict=False)
    if resolved_output_dir.exists() and not resolved_output_dir.is_dir():
        raise PathValidationError(
            f"Der Ausgabeordner verweist auf eine Datei: {resolved_output_dir}"
        )

    existing_parent = resolved_output_dir
    while not existing_parent.exists():
        existing_parent = existing_parent.parent
    if not existing_parent.is_dir():
        raise PathValidationError(
            f"Der Ausgabeordner besitzt keinen vorhandenen Verzeichnisvorfahren: {resolved_output_dir}"
        )

    return ConversionPaths(source_path=source_path, output_dir=resolved_output_dir)


def ensure_not_source_target(target_path: Path, source_path: Path) -> Path:
    """Verhindert, dass ein abgeleiteter Schreibvorgang die Primärquelle trifft."""
    resolved_target = target_path.expanduser().resolve(strict=False)
    resolved_source = source_path.expanduser().resolve(strict=False)
    if resolved_target == resolved_source:
        raise PathValidationError(
            f"Die Primärquelle darf nicht überschrieben werden: {resolved_source}"
        )
    return resolved_target
