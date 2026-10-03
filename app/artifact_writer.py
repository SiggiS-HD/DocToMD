"""Atomisches Schreiben abgeleiteter Markdown- und Manifest-Dateien."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from app.path_validation import PathValidationError, ensure_not_source_target


class ArtifactWriteError(OSError):
    """Ein abgeleitetes Artefakt konnte nicht sicher geschrieben werden."""


def write_conversion_documents(
    *,
    source_path: Path,
    markdown_path: Path,
    markdown_content: str,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    overwrite: bool = False,
) -> None:
    """Schreibt Markdown und Manifest atomisch, das Manifest stets zuletzt.

    Ohne ``overwrite`` wird ein vorhandenes Ziel nicht ersetzt. Der Aufrufer
    entscheidet die Konfliktstrategie; diese Funktion erzwingt nur einen
    sicheren, vollständigen Schreibvorgang pro Datei.
    """
    try:
        markdown_target = ensure_not_source_target(markdown_path, source_path)
        manifest_target = ensure_not_source_target(manifest_path, source_path)
    except PathValidationError as error:
        raise ArtifactWriteError(str(error)) from error

    _ensure_writable_target(markdown_target, overwrite=overwrite)
    _ensure_writable_target(manifest_target, overwrite=overwrite)

    try:
        _atomic_write_text(markdown_target, markdown_content, overwrite=overwrite)
        _atomic_write_text(
            manifest_target,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            overwrite=overwrite,
        )
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactWriteError(f"Artefakte konnten nicht geschrieben werden: {error}") from error


def write_conversion_manifest(
    *, source_path: Path, manifest_path: Path, manifest: Mapping[str, Any], overwrite: bool = False
) -> None:
    """Aktualisiert ausschließlich den atomaren Abschlussmarker einer Konvertierung."""
    try:
        target = ensure_not_source_target(manifest_path, source_path)
    except PathValidationError as error:
        raise ArtifactWriteError(str(error)) from error
    _ensure_writable_target(target, overwrite=overwrite)
    try:
        _atomic_write_text(
            target,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            overwrite=overwrite,
        )
    except (OSError, TypeError, ValueError) as error:
        raise ArtifactWriteError(f"Manifest konnte nicht geschrieben werden: {error}") from error


def write_text_artifact(*, source_path: Path, target_path: Path, content: str, overwrite: bool = False) -> None:
    """Schreibt ein zusätzliches abgeleitetes Textartefakt atomisch."""
    try:
        target = ensure_not_source_target(target_path, source_path)
    except PathValidationError as error:
        raise ArtifactWriteError(str(error)) from error
    _ensure_writable_target(target, overwrite=overwrite)
    _atomic_write_text(target, content, overwrite=overwrite)


def write_cloud_markdown_derivative(
    *, source_path: Path, cloud_markdown_path: Path, content: str, overwrite: bool = False
) -> None:
    """Schreibt ausschließlich das getrennte, konfliktgeschützte Cloud-Derivat."""
    write_text_artifact(
        source_path=source_path,
        target_path=cloud_markdown_path,
        content=content,
        overwrite=overwrite,
    )


def _ensure_writable_target(target: Path, *, overwrite: bool) -> None:
    if target.exists() and not target.is_file():
        raise ArtifactWriteError(f"Der Artefaktpfad ist keine Datei: {target}")
    if target.exists() and not overwrite:
        raise ArtifactWriteError(f"Das abgeleitete Artefakt existiert bereits: {target}")


def _atomic_write_text(target: Path, content: str, *, overwrite: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=".doctomd-",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if overwrite:
            os.replace(temporary_path, target)
        else:
            os.link(temporary_path, target)
            temporary_path.unlink()
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


__all__ = [
    "ArtifactWriteError",
    "write_cloud_markdown_derivative",
    "write_conversion_documents",
    "write_conversion_manifest",
    "write_text_artifact",
]
