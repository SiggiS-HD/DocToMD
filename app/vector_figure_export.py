"""Lokaler Export eindeutig belegter Vektorgrafikbereiche als PNG-Assets."""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from math import ceil, floor
from pathlib import Path, PurePosixPath
from typing import Iterable

import pypdfium2 as pdfium

from app.image_export import IMAGE_DESCRIPTION_TEMPLATE, _write_new_binary_file, _write_new_text_file
from app.models import Asset, AssetKind, ConversionWarning
from app.vector_figure_detection import VectorFigureCandidate


VECTOR_FIGURE_RENDER_DPI = 144


def export_vector_figures(*, source_path: Path, asset_directory: Path, candidates: Iterable[VectorFigureCandidate], existing_assets: Iterable[Asset] = ()) -> tuple[tuple[Asset, ...], tuple[ConversionWarning, ...]]:
    """Rendert ausschließlich bestätigte Vektor-Bounding-Boxen als neue PNG-Assets."""
    candidate_list = tuple(sorted(candidates, key=lambda item: (item.page.page_number, item.bbox[1], item.bbox[0])))
    if not candidate_list:
        return (), ()
    figure_numbers = defaultdict(int)
    for asset in existing_assets:
        figure_numbers[asset.page.page_number] += 1
    rendered: list[tuple[VectorFigureCandidate, int, bytes]] = []
    warnings: list[ConversionWarning] = []
    for candidate in candidate_list:
        figure_numbers[candidate.page.page_number] += 1
        try:
            png = render_vector_crop(source_path=source_path, page_number=candidate.page.page_number, bbox=candidate.bbox, dpi=VECTOR_FIGURE_RENDER_DPI)
        except (OSError, ValueError) as error:
            warnings.append(ConversionWarning("VECTOR_FIGURE_NOT_EXPORTED", f"Der lokal belegte Vektorbereich konnte nicht als PNG gerendert werden: {error}", page=candidate.page))
            continue
        rendered.append((candidate, figure_numbers[candidate.page.page_number], png))
    if not rendered:
        return (), tuple(warnings)
    asset_directory.mkdir(parents=True, exist_ok=True)
    assets: list[Asset] = []
    for candidate, figure_number, png in rendered:
        stem = f"page-{candidate.page.page_number:03d}-figure-{figure_number:02d}"
        asset_path = asset_directory / f"{stem}.png"
        description_path = asset_directory / f"{stem}-description.md"
        if not asset_path.exists():
            _write_new_binary_file(asset_path, png)
        if not description_path.exists():
            _write_new_text_file(description_path, IMAGE_DESCRIPTION_TEMPLATE)
        assets.append(Asset(stem, AssetKind.IMAGE, PurePosixPath(asset_directory.name, f"{stem}.png"), candidate.page, caption=candidate.caption, description_path=PurePosixPath(asset_directory.name, f"{stem}-description.md")))
    return tuple(assets), tuple(warnings)


def render_vector_crop(*, source_path: Path, page_number: int, bbox: tuple[float, float, float, float], dpi: int) -> bytes:
    """Rendert eine PDF-Seite lokal und gibt ausschließlich den validierten Crop zurück."""
    if page_number < 1 or dpi <= 0:
        raise ValueError("page_number und dpi müssen positiv sein.")
    x0, top, x1, bottom = bbox
    if not (x0 < x1 and top < bottom):
        raise ValueError("Die Vektor-Bounding-Box muss positive Breite und Höhe haben.")
    document = None
    page = None
    try:
        document = pdfium.PdfDocument(str(source_path))
        if page_number > len(document):
            raise ValueError("Die Vektorgrafik verweist auf eine nicht vorhandene PDF-Seite.")
        page = document[page_number - 1]
        image = page.render(scale=dpi / 72).to_pil().copy()
    except ValueError:
        raise
    except Exception as error:
        raise OSError("Die PDF konnte nicht mit dem lokalen Renderer verarbeitet werden.") from error
    finally:
        if page is not None:
            page.close()
        if document is not None:
            document.close()
    scale = dpi / 72
    crop_box = (floor(x0 * scale), floor(top * scale), ceil(x1 * scale), ceil(bottom * scale))
    if crop_box[0] < 0 or crop_box[1] < 0 or crop_box[2] > image.width or crop_box[3] > image.height:
        raise ValueError("Die Vektor-Bounding-Box liegt nicht vollständig auf der gerenderten PDF-Seite.")
    cropped = image.crop(crop_box)
    if cropped.width >= image.width and cropped.height >= image.height:
        raise ValueError("Ein Vektorasset darf keine vollständige Seite enthalten.")
    output = BytesIO()
    cropped.save(output, format="PNG")
    return output.getvalue()


__all__ = ["VECTOR_FIGURE_RENDER_DPI", "export_vector_figures", "render_vector_crop"]
