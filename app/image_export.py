"""Export eingebetteter Rasterbilder aus digitalen PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any

import pdfplumber
from PIL import Image
from pdfminer.pdftypes import resolve1
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from app.models import Asset, AssetKind, ConversionWarning, PageReference


_CAPTION_PATTERN = re.compile(r"^(?:Figure|Fig\.|Abbildung)\s+\d+\b.+", re.IGNORECASE)
_MIN_CONTENT_IMAGE_PIXELS = 50_000
IMAGE_DESCRIPTION_TEMPLATE = """<!-- doctomd:image-description-template -->
# Bildbeschreibung

## Kurzbeschreibung

<!-- Was ist auf dem Bild zu sehen? -->

## Fachliche Einordnung

<!-- Welche Aussage, welcher Ablauf oder welche Entscheidung ist für die Suche relevant? -->

## Sichtbare Details

<!-- Beschrifte Achsen, Legende, Abkürzungen, Werte oder relevante Bildelemente nur, wenn sie klar erkennbar sind. -->

## Unsicherheiten

<!-- Fehlende, unlesbare oder nicht sicher interpretierbare Informationen festhalten. -->
"""


@dataclass(frozen=True, slots=True)
class ImageExportOutcome:
    """Erzeugte native Bildassets und sichtbare, nicht exportierte Sonderfälle."""

    assets: tuple[Asset, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()


def export_embedded_images(*, source_path: Path, asset_directory: Path) -> ImageExportOutcome:
    """Exportiert direkte JPEGs und sichere 8-Bit-Flate-Rasterbilder."""
    source = source_path.expanduser().resolve(strict=False)
    exports: list[tuple[int, int, bytes, str, str | None]] = []
    warnings: list[ConversionWarning] = []
    try:
        with pdfplumber.open(source) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                for figure_number, image in enumerate(page.images, start=1):
                    if _is_decorative_image(image):
                        continue
                    exported = _export_image(image)
                    if exported is None:
                        warnings.append(ConversionWarning(
                            code="UNSUPPORTED_EMBEDDED_IMAGE",
                            message="Ein eingebettetes Bild konnte nicht sicher als JPEG oder PNG exportiert werden.",
                            page=PageReference(page_number),
                        ))
                    else:
                        image_data, extension = exported
                        exports.append((page_number, figure_number, image_data, extension, _find_caption(page, image)))
    except (OSError, PDFSyntaxError, PdfminerException) as error:
        raise ValueError(f"Eingebettete Bilder konnten nicht gelesen werden: {source}") from error

    if not exports:
        return ImageExportOutcome(warnings=tuple(warnings))

    asset_directory.mkdir(parents=True, exist_ok=True)
    assets: list[Asset] = []
    for page_number, figure_number, image_data, extension, caption in exports:
        filename = f"page-{page_number:03d}-figure-{figure_number:02d}.{extension}"
        description_filename = f"page-{page_number:03d}-figure-{figure_number:02d}-description.md"
        asset_path = asset_directory / filename
        description_path = asset_directory / description_filename
        if not asset_path.exists():
            _write_new_binary_file(asset_path, image_data)
        if not description_path.exists():
            _write_new_text_file(description_path, IMAGE_DESCRIPTION_TEMPLATE)
        assets.append(Asset(
            asset_id=f"page-{page_number:03d}-figure-{figure_number:02d}",
            kind=AssetKind.IMAGE,
            relative_path=PurePosixPath(asset_directory.name, filename),
            page=PageReference(page_number),
            caption=caption,
            description_path=PurePosixPath(asset_directory.name, description_filename),
        ))
    return ImageExportOutcome(tuple(assets), tuple(warnings))


def _export_image(image: dict[str, Any]) -> tuple[bytes, str] | None:
    stream = image["stream"]
    raw_data = stream.get_rawdata()
    if isinstance(raw_data, bytes) and raw_data.startswith(b"\xff\xd8\xff"):
        return raw_data, "jpg"
    try:
        decoded_data = stream.get_data()
    except (TypeError, ValueError):
        decoded_data = None
    if isinstance(decoded_data, bytes) and decoded_data.startswith(b"\xff\xd8\xff"):
        return decoded_data, "jpg"
    if "FlateDecode" not in str(getattr(stream, "attrs", {}).get("Filter", "")):
        return None
    return _flate_stream_as_png(stream)


def _is_decorative_image(image: dict[str, Any]) -> bool:
    """Lässt wiederholte, sehr kleine Kopf- und Fußgrafiken bewusst aus."""
    attrs = getattr(image.get("stream"), "attrs", {})
    try:
        return int(attrs["Width"]) * int(attrs["Height"]) < _MIN_CONTENT_IMAGE_PIXELS
    except (KeyError, TypeError, ValueError):
        return False


def _flate_stream_as_png(stream: Any) -> tuple[bytes, str] | None:
    """Kodiert einfache, bereits dekodierte 8-Bit-RGB/Gray-Flate-Daten als PNG."""
    attrs = getattr(stream, "attrs", {})
    color_space = attrs.get("ColorSpace", "")
    mode = {"/'DeviceRGB'": "RGB", "/'DeviceGray'": "L"}.get(str(color_space))
    indexed_palette = _indexed_rgb_palette(color_space)
    if (mode is None and indexed_palette is None) or attrs.get("BitsPerComponent") != 8:
        return None
    try:
        width = int(attrs["Width"])
        height = int(attrs["Height"])
        decoded = stream.get_data()
    except (KeyError, TypeError, ValueError):
        return None
    expected_length = width * height * (3 if mode == "RGB" else 1)
    if len(decoded) != expected_length:
        return None
    try:
        image = Image.frombytes("P" if indexed_palette is not None else mode, (width, height), decoded)
        if indexed_palette is not None:
            image.putpalette(indexed_palette, rawmode="RGB")
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
    except (ValueError, OSError):
        return None
    return buffer.getvalue(), "png"


def _indexed_rgb_palette(color_space: Any) -> bytes | None:
    """Löst ausschließlich einfache 8-Bit-Indexed/DeviceRGB-Paletten auf."""
    if not isinstance(color_space, list) or len(color_space) != 4:
        return None
    if "Indexed" not in str(color_space[0]) or "DeviceRGB" not in str(color_space[1]):
        return None
    try:
        maximum_index = int(color_space[2])
        palette_stream = resolve1(color_space[3])
        palette = palette_stream.get_data()
    except (TypeError, ValueError, AttributeError):
        return None
    required_length = (maximum_index + 1) * 3
    if not isinstance(palette, bytes) or len(palette) < required_length or required_length > 768:
        return None
    return palette[:required_length].ljust(768, b"\x00")


def _write_new_binary_file(path: Path, content: bytes) -> None:
    """Publiziert ein neues Asset atomisch, ohne ein vorhandenes zu ersetzen."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_new_text_file(path: Path, content: str) -> None:
    """Legt eine editierbare Beschreibungsdatei ohne Ersetzen an."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _find_caption(page: Any, image: dict[str, Any]) -> str | None:
    """Erkennt nur unmittelbar unter dem Bild stehende, eindeutig benannte Captions."""
    image_bottom = image.get("bottom")
    if image_bottom is None or not hasattr(page, "extract_words"):
        return None
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    nearby_words = [word for word in words if float(image_bottom) <= float(word["top"]) <= float(image_bottom) + 36]
    lines: dict[float, list[dict[str, Any]]] = {}
    for word in nearby_words:
        lines.setdefault(round(float(word["top"]), 1), []).append(word)
    for line_words in lines.values():
        text = " ".join(word["text"] for word in sorted(line_words, key=lambda word: float(word["x0"])))
        if _CAPTION_PATTERN.match(text):
            return text
    return None


__all__ = ["IMAGE_DESCRIPTION_TEMPLATE", "ImageExportOutcome", "export_embedded_images"]
