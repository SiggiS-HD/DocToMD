"""Sichere Rehydrierung einer geprüften lokalen Konvertierungsbasis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from app.models import Asset, AssetKind, ConversionWarning, NativePdfLink, NativePdfLinkSource, PageReference, PdfAnnotationRect, SourceDocument, WarningSeverity
from app.markdown_provenance import strip_provenance_block
from app.asset_reference_validation import AssetReferenceValidationError, validate_markdown_image_references
from app.native_pdf_link_coverage import verify_native_pdf_link_coverage
from app.native_pdf_links import validate_native_pdf_links
from app.quality import build_quality_section
from app.source_fingerprint import fingerprint_source


LOCAL_REUSE_CONTEXT_SCHEMA_VERSION = "1.0"
_PAGE_MARKER = re.compile(r"<!-- doctomd:page=([1-9][0-9]*) -->")


class LocalReuseContextError(ValueError):
    """Ein lokales Derivat erfüllt den Wiederverwendungsvertrag nicht."""


@dataclass(frozen=True, slots=True)
class LocalReuseContext:
    """Erneut geprüfte, ausschließlich lokale Basis für eine spätere Ableitung."""

    source: SourceDocument
    manifest_path: Path
    markdown_path: Path
    markdown: str
    page_numbers: tuple[int, ...]
    assets: tuple[Asset, ...]
    warnings: tuple[ConversionWarning, ...]
    native_pdf_links: tuple[NativePdfLink, ...]
    manifest: dict[str, Any]


def build_local_reuse_metadata(*, markdown: str) -> dict[str, object]:
    """Erzeugt den versionsgebundenen Nachweis für unverändertes lokales Markdown."""
    return {
        "schema_version": LOCAL_REUSE_CONTEXT_SCHEMA_VERSION,
        "markdown_sha256": _sha256_text(markdown),
        "page_numbers": list(_page_numbers(markdown)),
    }


def rehydrate_local_reuse_context(*, source_path: Path, manifest_path: Path) -> LocalReuseContext:
    """Lädt nur einen vollständig verifizierten lokalen Kontext, ohne PDF-Analyse."""
    source = fingerprint_source(source_path, media_type="application/pdf")
    if source.path.suffix.casefold() != ".pdf":
        raise LocalReuseContextError("Der Wiederverwendungskontext benötigt eine PDF-Primärquelle.")
    manifest_file = manifest_path.expanduser().resolve(strict=False)
    payload = _load_manifest(manifest_file)
    _validate_source(payload, source)
    artifacts = _mapping(payload.get("artifacts"), "artifacts")
    root = manifest_file.parent.resolve(strict=False)
    markdown_relative = _relative_path(artifacts.get("markdown_path"), "markdown_path")
    markdown_file = _resolve_artifact(root, markdown_relative, "Markdown")
    markdown = _read_text(markdown_file, "Markdown")
    reuse = _mapping(artifacts.get("local_reuse"), "artifacts.local_reuse")
    _validate_reuse_metadata(reuse, markdown)
    page_numbers = _page_numbers(markdown)
    assets = _parse_assets(artifacts.get("assets"), root, page_numbers)
    try:
        validate_markdown_image_references(
            markdown=markdown,
            assets=assets,
            output_dir=root,
            error_code="LOCAL_UNAUTHORIZED_IMAGE_REFERENCE",
        )
    except AssetReferenceValidationError as error:
        raise LocalReuseContextError("Das lokale Markdown enthält keine autorisierte Bildreferenz.") from error
    _validate_content_references(artifacts.get("content_references"), assets, page_numbers)
    warnings = _parse_quality(payload.get("quality"), page_numbers)
    links = _parse_native_pdf_links(artifacts.get("native_pdf_links"), page_numbers)
    try:
        verify_native_pdf_link_coverage(markdown=markdown, links=links)
    except ValueError as error:
        raise LocalReuseContextError("Die Native-PDF-Linkliste im lokalen Markdown ist nicht vollständig gültig.") from error
    return LocalReuseContext(source, manifest_file, markdown_file, markdown, page_numbers, assets, warnings, links, payload)


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LocalReuseContextError(f"Das lokale Manifest fehlt: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LocalReuseContextError("Das lokale Manifest ist nicht als UTF-8-JSON lesbar.") from error
    if not isinstance(payload, dict) or payload.get("manifest_schema_version") != "1.0":
        raise LocalReuseContextError("Das lokale Manifest hat keine unterstützte Schema-Version.")
    return payload


def _validate_source(payload: dict[str, Any], source: SourceDocument) -> None:
    stored = _mapping(payload.get("source"), "source")
    try:
        stored_path = Path(_string(stored.get("path"), "source.path")).expanduser().resolve(strict=False)
        stored_size = stored["size_bytes"]
        stored_hash = stored["sha256"]
        stored_modified = datetime.fromisoformat(_string(stored.get("modified_at"), "source.modified_at"))
    except (KeyError, TypeError, ValueError) as error:
        raise LocalReuseContextError("Der Quellfingerabdruck im Manifest ist ungültig.") from error
    if not isinstance(stored_size, int) or isinstance(stored_size, bool) or not isinstance(stored_hash, str):
        raise LocalReuseContextError("Der Quellfingerabdruck im Manifest ist ungültig.")
    if stored.get("media_type") != "application/pdf" or stored_path != source.path:
        raise LocalReuseContextError("Das Manifest gehört nicht zu dieser PDF-Primärquelle.")
    if (stored_size, stored_hash, stored_modified) != (source.size_bytes, source.sha256, source.modified_at):
        raise LocalReuseContextError("Die PDF-Primärquelle stimmt nicht mehr mit dem Manifestfingerabdruck überein.")


def _validate_reuse_metadata(metadata: dict[str, Any], markdown: str) -> None:
    if metadata.get("schema_version") != LOCAL_REUSE_CONTEXT_SCHEMA_VERSION:
        raise LocalReuseContextError("Der lokale Wiederverwendungskontext hat keine unterstützte Version.")
    expected_hash = metadata.get("markdown_sha256")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise LocalReuseContextError("Der lokale Wiederverwendungskontext enthält keinen gültigen Markdown-Fingerabdruck.")
    if expected_hash != _sha256_text(markdown):
        raise LocalReuseContextError("Das lokale Markdown wurde seit der geprüften Konvertierung verändert.")
    stored_pages = metadata.get("page_numbers")
    if not isinstance(stored_pages, list) or tuple(stored_pages) != _page_numbers(markdown):
        raise LocalReuseContextError("Die Seitenmarker stimmen nicht mit dem lokalen Wiederverwendungskontext überein.")


def _parse_assets(value: object, root: Path, pages: tuple[int, ...]) -> tuple[Asset, ...]:
    if not isinstance(value, list):
        raise LocalReuseContextError("Das Manifest enthält keine gültige Assetliste.")
    assets: list[Asset] = []
    asset_ids: set[str] = set()
    for item in value:
        entry = _mapping(item, "asset")
        asset_id = _string(entry.get("asset_id"), "asset.asset_id")
        if asset_id in asset_ids:
            raise LocalReuseContextError("Das Manifest enthält doppelte Asset-IDs.")
        asset_ids.add(asset_id)
        relative_path = _relative_path(entry.get("path"), "asset.path")
        _require_file(root, relative_path, "Asset")
        description_value = entry.get("description_path")
        description_path = _relative_path(description_value, "asset.description_path") if description_value is not None else None
        if description_path is not None:
            _require_file(root, description_path, "Asset-Beschreibung")
        try:
            page = _page_reference(entry.get("page"), pages, "asset.page")
            asset = Asset(asset_id, AssetKind(_string(entry.get("kind"), "asset.kind")), relative_path, page, entry.get("caption"), entry.get("description"), description_path)
        except (TypeError, ValueError) as error:
            raise LocalReuseContextError("Ein Asset im Manifest ist ungültig.") from error
        assets.append(asset)
    return tuple(assets)


def _validate_content_references(value: object, assets: tuple[Asset, ...], pages: tuple[int, ...]) -> None:
    if not isinstance(value, list):
        raise LocalReuseContextError("Das Manifest enthält keine gültigen Inhaltsreferenzen.")
    asset_ids = {asset.asset_id for asset in assets}
    for item in value:
        entry = _mapping(item, "content_reference")
        if entry.get("kind") not in {"text", "table", "asset"}:
            raise LocalReuseContextError("Das Manifest enthält eine ungültige Inhaltsreferenz.")
        _page_reference(entry.get("page"), pages, "content_reference.page")
        if entry.get("kind") == "asset" and entry.get("asset_id") not in asset_ids:
            raise LocalReuseContextError("Eine Inhaltsreferenz verweist auf ein unbekanntes Asset.")


def _parse_quality(value: object, pages: tuple[int, ...]) -> tuple[ConversionWarning, ...]:
    quality = _mapping(value, "quality")
    warnings = _warning_list(quality.get("warnings"), pages, WarningSeverity.WARNING)
    errors = _warning_list(quality.get("errors"), pages, WarningSeverity.ERROR)
    combined = (*warnings, *errors)
    if quality.get("status") != build_quality_section(combined)["status"]:
        raise LocalReuseContextError("Der Qualitätsstatus im Manifest stimmt nicht mit den Qualitätsbefunden überein.")
    return combined


def _warning_list(value: object, pages: tuple[int, ...], fallback: WarningSeverity) -> tuple[ConversionWarning, ...]:
    if not isinstance(value, list):
        raise LocalReuseContextError("Die Qualitätsbefunde im Manifest sind ungültig.")
    result: list[ConversionWarning] = []
    for item in value:
        entry = _mapping(item, "quality entry")
        try:
            severity = WarningSeverity(entry.get("severity", fallback.value))
            if fallback is WarningSeverity.ERROR and severity is not WarningSeverity.ERROR:
                raise ValueError
            page = _page_reference(entry["page"], pages, "quality.page") if "page" in entry else None
            result.append(ConversionWarning(_string(entry.get("code"), "quality.code"), _string(entry.get("message"), "quality.message"), severity, page))
        except (KeyError, ValueError) as error:
            raise LocalReuseContextError("Ein Qualitätsbefund im Manifest ist ungültig.") from error
    return tuple(result)


def _parse_native_pdf_links(value: object, pages: tuple[int, ...]) -> tuple[NativePdfLink, ...]:
    if value is None:
        return ()
    container = _mapping(value, "artifacts.native_pdf_links")
    if container.get("schema_version") != "1.0" or not isinstance(container.get("items"), list):
        raise LocalReuseContextError("Die Native-PDF-Linkliste im Manifest hat keine unterstützte Version.")
    links: list[NativePdfLink] = []
    for item in container["items"]:
        entry = _mapping(item, "native_pdf_link")
        try:
            page = _page_reference(entry.get("page"), pages, "native_pdf_link.page")
            rectangle = _mapping(entry.get("annotation_rect"), "native_pdf_link.annotation_rect")
            link = NativePdfLink(_string(entry.get("target_url"), "native_pdf_link.target_url"), page, PdfAnnotationRect(float(rectangle["left"]), float(rectangle["bottom"]), float(rectangle["right"]), float(rectangle["top"])), NativePdfLinkSource(_string(entry.get("source"), "native_pdf_link.source")), entry.get("visible_title"))
            expected_status = "geometrically_verified" if link.visible_title is not None else "neutral_page_label"
            if entry.get("title_assignment_status") != expected_status:
                raise ValueError
            links.append(link)
        except (KeyError, TypeError, ValueError) as error:
            raise LocalReuseContextError("Ein nativer PDF-Link im Manifest ist ungültig.") from error
    try:
        return validate_native_pdf_links(links)
    except ValueError as error:
        raise LocalReuseContextError("Ein nativer PDF-Link im Manifest ist nicht sicher.") from error


def _page_numbers(markdown: str) -> tuple[int, ...]:
    content = strip_provenance_block(markdown)
    lines = content.splitlines()
    first = next((line.strip() for line in lines if line.strip()), None)
    pages = tuple(int(match.group(1)) for match in _PAGE_MARKER.finditer(content))
    if first != "<!-- doctomd:page=1 -->" or not pages or pages != tuple(range(1, len(pages) + 1)):
        raise LocalReuseContextError("Das lokale Markdown enthält keine lückenlosen Seitenmarker ab Seite 1.")
    marker_lines = [line.strip() for line in lines if "doctomd:page=" in line]
    if marker_lines != [f"<!-- doctomd:page={page} -->" for page in pages]:
        raise LocalReuseContextError("Die Seitenmarker im lokalen Markdown sind nicht exakt formatiert.")
    return pages


def _relative_path(value: object, name: str) -> PurePosixPath:
    raw = _string(value, name)
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or Path(raw).is_absolute() or re.match(r"^[A-Za-z]:", raw):
        raise LocalReuseContextError(f"{name} muss ein sicherer relativer Pfad sein.")
    return path


def _resolve_artifact(root: Path, relative: PurePosixPath, name: str) -> Path:
    target = (root / Path(*relative.parts)).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise LocalReuseContextError(f"{name}-Pfad verlässt den Ausgabeordner.") from error
    return target


def _require_file(root: Path, relative: PurePosixPath, name: str) -> None:
    target = _resolve_artifact(root, relative, name)
    if not target.is_file():
        raise LocalReuseContextError(f"{name} fehlt oder ist keine reguläre Datei: {relative.as_posix()}")


def _read_text(path: Path, name: str) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise LocalReuseContextError(f"{name} ist nicht als UTF-8 lesbar.") from error
    if not content.strip():
        raise LocalReuseContextError(f"{name} ist leer.")
    return content


def _page_reference(value: object, pages: tuple[int, ...], name: str) -> PageReference:
    entry = _mapping(value, name)
    number = entry.get("page_number")
    if not isinstance(number, int) or isinstance(number, bool) or number not in pages:
        raise LocalReuseContextError(f"{name} verweist auf keine Seite des lokalen Markdown.")
    location = entry.get("location")
    if location is not None and (not isinstance(location, str) or not location.strip()):
        raise LocalReuseContextError(f"{name}.location ist ungültig.")
    return PageReference(number, location)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LocalReuseContextError(f"{name} muss ein Objekt sein.")
    return value


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise LocalReuseContextError(f"{name} muss ein nichtleerer Text sein.")
    return value


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


__all__ = ["LOCAL_REUSE_CONTEXT_SCHEMA_VERSION", "LocalReuseContext", "LocalReuseContextError", "build_local_reuse_metadata", "rehydrate_local_reuse_context"]
