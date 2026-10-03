"""Entscheidung über Konflikte und Wiederholungsläufe von Konvertierungen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any

from app.artifact_paths import ArtifactPaths
from app.models import SourceDocument


class ConflictMode(str, Enum):
    """Öffentliche Konfliktmodi der CLI."""

    ERROR = "error"
    UPDATE = "update"
    OVERWRITE = "overwrite"


class ConflictAction(str, Enum):
    """Schreibentscheidung für eine geplante Konvertierung."""

    CREATE = "create"
    REUSE = "reuse"
    REPLACE = "replace"


class ArtifactConflictError(ValueError):
    """Vorhandene Artefakte erlauben keine sichere Konvertierung."""


@dataclass(frozen=True, slots=True)
class ConflictResolution:
    """Konfliktentscheidung ohne Dateien zu verändern."""

    action: ConflictAction
    existing_paths: tuple[Path, ...]

    @property
    def overwrite(self) -> bool:
        """Gibt an, ob der atomische Schreiber vorhandene Dateien ersetzen darf."""
        return self.action is ConflictAction.REPLACE


def resolve_conflict(
    *,
    mode: ConflictMode | str,
    source: SourceDocument,
    artifact_paths: ArtifactPaths,
) -> ConflictResolution:
    """Entscheidet sicher über neue, unveränderte und veraltete Derivate."""
    try:
        conflict_mode = ConflictMode(mode)
    except ValueError as error:
        raise ArtifactConflictError(f"Unbekannter Konfliktmodus: {mode}") from error

    existing_paths = _existing_paths(artifact_paths)
    if not existing_paths:
        return ConflictResolution(ConflictAction.CREATE, existing_paths)

    if conflict_mode is ConflictMode.ERROR:
        raise ArtifactConflictError(
            "Abgeleitete Artefakte existieren bereits; "
            "verwenden Sie --on-conflict update oder --on-conflict overwrite."
        )
    if conflict_mode is ConflictMode.OVERWRITE:
        return ConflictResolution(ConflictAction.REPLACE, existing_paths)

    _validate_update_state(artifact_paths)
    manifest = _load_manifest(artifact_paths.manifest_path)
    if _matches_source_fingerprint(manifest, source):
        return ConflictResolution(ConflictAction.REUSE, existing_paths)
    return ConflictResolution(ConflictAction.REPLACE, existing_paths)


def _existing_paths(artifact_paths: ArtifactPaths) -> tuple[Path, ...]:
    return tuple(
        path
        for path in (
            artifact_paths.markdown_path,
            artifact_paths.assets_dir,
            artifact_paths.manifest_path,
            artifact_paths.vision_proposals_dir,
            artifact_paths.vision_markdown_path,
            artifact_paths.vision_review_path,
            artifact_paths.cloud_markdown_path,
        )
        if path.exists()
    )


def _validate_update_state(artifact_paths: ArtifactPaths) -> None:
    if not artifact_paths.markdown_path.is_file() or not artifact_paths.manifest_path.is_file():
        raise ArtifactConflictError(
            "Update erfordert ein vollständiges Markdown- und Manifest-Paar; "
            "verwenden Sie für unvollständige Derivate --on-conflict overwrite."
        )
    if artifact_paths.assets_dir.exists() and not artifact_paths.assets_dir.is_dir():
        raise ArtifactConflictError(
            f"Der Asset-Pfad ist kein Verzeichnis: {artifact_paths.assets_dir}"
        )


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        with manifest_path.open(encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ArtifactConflictError(
            f"Das vorhandene Manifest ist nicht lesbar: {manifest_path}"
        ) from error
    if not isinstance(manifest, dict):
        raise ArtifactConflictError(f"Das vorhandene Manifest ist kein JSON-Objekt: {manifest_path}")
    return manifest


def _matches_source_fingerprint(manifest: dict[str, Any], source: SourceDocument) -> bool:
    stored_source = manifest.get("source")
    if not isinstance(stored_source, dict) or source.modified_at is None:
        return False

    try:
        stored_modified_at = _parse_timestamp(stored_source["modified_at"])
        return (
            stored_source["path"] == str(source.path)
            and stored_source["size_bytes"] == source.size_bytes
            and stored_source["sha256"] == source.sha256
            and stored_modified_at == source.modified_at
        )
    except (KeyError, TypeError, ValueError):
        return False


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Zeitstempel muss ein String sein.")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Zeitstempel muss eine Zeitzone enthalten.")
    return timestamp


__all__ = [
    "ArtifactConflictError",
    "ConflictAction",
    "ConflictMode",
    "ConflictResolution",
    "resolve_conflict",
]
