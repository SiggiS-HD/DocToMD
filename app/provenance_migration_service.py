"""Rüstet die Herkunft vorhandener Markdown-Derivate lokal nach."""

from __future__ import annotations

import json
from pathlib import Path
from pathlib import PurePosixPath

from app.artifact_writer import write_conversion_documents, write_text_artifact
from app.local_reuse_context import build_local_reuse_metadata, rehydrate_local_reuse_context
from app.markdown_provenance import add_provenance_block
from app.models import SourceDocument
from app.source_fingerprint import fingerprint_source


def migrate_markdown_provenance(*, input_path: Path, output_dir: Path) -> tuple[Path, ...]:
    """Ergänzt lokale und vorhandene Cloud-Derivate ohne PDF- oder Cloud-Lauf."""
    source = fingerprint_source(input_path, media_type="application/pdf")
    output_root = output_dir.expanduser().resolve(strict=False)
    manifest_path = output_root / f"{source.path.stem}.conversion.json"
    manifest = _load_manifest(manifest_path)
    _validate_source(manifest, source)
    artifacts = _artifacts(manifest)
    markdown_path = _artifact_path(output_root, artifacts.get("markdown_path"), "Lokales Markdown")
    cloud_path = _artifact_path(output_root, artifacts.get("cloud_markdown_path"), "Cloud-Markdown", required=False)
    if cloud_path is None:
        legacy_cloud_path = output_root / f"{source.path.stem}.cloud.md"
        if legacy_cloud_path.is_file():
            cloud_path = legacy_cloud_path
    if isinstance(artifacts.get("local_reuse"), dict):
        context = rehydrate_local_reuse_context(source_path=input_path, manifest_path=manifest_path)
        source, manifest, markdown_path = context.source, context.manifest, context.markdown_path
        local_content = context.markdown
    else:
        local_content = _read_markdown(markdown_path, "Lokales Markdown")
    local_markdown = add_provenance_block(
        content=local_content,
        source=source,
        derivative_kind="local",
    )
    manifest["artifacts"]["local_reuse"] = build_local_reuse_metadata(markdown=local_markdown)
    write_conversion_documents(
        source_path=source.path,
        markdown_path=markdown_path,
        markdown_content=local_markdown,
        manifest_path=manifest_path,
        manifest=manifest,
        overwrite=True,
    )
    changed = [markdown_path]
    if cloud_path is not None and cloud_path.is_file():
        cloud_markdown = _read_markdown(cloud_path, "Cloud-Markdown")
        write_text_artifact(
            source_path=source.path,
            target_path=cloud_path,
            content=add_provenance_block(
                content=cloud_markdown,
                source=source,
                derivative_kind="cloud",
            ),
            overwrite=True,
        )
        changed.append(cloud_path)
    return tuple(changed)


def _load_manifest(path: Path) -> dict:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Das Konvertierungsmanifest ist nicht lesbar: {path}") from error
    if not isinstance(content, dict) or content.get("manifest_schema_version") != "1.0":
        raise ValueError("Das Konvertierungsmanifest hat keine unterstützte Schema-Version.")
    return content


def _validate_source(manifest: dict, source: SourceDocument) -> None:
    stored = manifest.get("source")
    if not isinstance(stored, dict):
        raise ValueError("Das Konvertierungsmanifest enthält keine gültige Primärquelle.")
    try:
        stored_path = Path(stored["path"]).expanduser().resolve(strict=False)
        valid = (
            stored_path == source.path
            and stored["media_type"] == source.media_type
            and stored["size_bytes"] == source.size_bytes
            and stored["sha256"] == source.sha256
            and stored["modified_at"] == source.modified_at.isoformat()
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Die PDF-Primärquelle stimmt nicht mit dem Konvertierungsmanifest überein.")


def _artifacts(manifest: dict) -> dict:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("Das Konvertierungsmanifest enthält keine gültigen Artefakte.")
    return artifacts


def _artifact_path(root: Path, value: object, name: str, *, required: bool = True) -> Path | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Das Konvertierungsmanifest enthält keinen gültigen Pfad für {name}.")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or Path(value).is_absolute() or len(relative.parts) == 0:
        raise ValueError(f"Der Artefaktpfad für {name} ist nicht sicher.")
    target = (root / Path(*relative.parts)).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Der Artefaktpfad für {name} verlässt den Ausgabeordner.") from error
    return target


def _read_markdown(path: Path | None, name: str) -> str:
    if path is None or not path.is_file():
        raise ValueError(f"{name} fehlt: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"{name} ist nicht als UTF-8 lesbar.") from error
    if not content.strip():
        raise ValueError(f"{name} ist leer.")
    return content


__all__ = ["migrate_markdown_provenance"]
