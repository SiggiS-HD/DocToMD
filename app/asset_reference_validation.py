"""Prüft Markdown-Bildreferenzen gegen die lokale autoritative Assetliste."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
from typing import Iterable

from app.models import Asset


_MARKDOWN_IMAGE = re.compile(r"!\[[^\]\n]*\]\((?:<(?P<angled>[^>\n]+)>|(?P<plain>[^)\n]+))\)")
_HTML_IMAGE = re.compile(r"(?is)<img\b[^>]*\bsrc\s*=\s*['\"](?P<src>[^'\"]+)['\"][^>]*>")


class AssetReferenceValidationError(ValueError):
    """Eine Bildreferenz ist nicht durch ein lokales Asset autorisiert."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_cloud_model_has_no_image_references(*, markdown: str) -> None:
    """Verwirft Bildpfade aus einer rohen Cloud-Antwort.

    Bildassets werden ausschließlich nach der Cloud-Validierung aus der
    lokalen, autoritativen Assetliste eingefügt. Das Modell darf deshalb
    keinen Pfad – auch keinen zufällig passenden – ausgeben.
    """
    if _image_references(markdown):
        raise AssetReferenceValidationError(
            "CLOUD_UNAUTHORIZED_IMAGE_REFERENCE",
            "Die Cloud-Antwort enthält eine Bildreferenz. DocToMD fügt geprüfte lokale Bilder selbst ein. Bitte starten Sie die Cloud-Ableitung erneut; der betroffene Batch wird dann mit dem aktuellen Prompt neu angefragt.",
        )


def validate_markdown_image_references(*, markdown: str, assets: Iterable[Asset], output_dir: Path, error_code: str) -> None:
    """Akzeptiert ausschließlich vorhandene, sichere Pfade aus ``assets``.

    Die Prüfung erfolgt vor jeder Veröffentlichung. Sie akzeptiert weder
    externe URLs noch absolute, aufsteigende oder nur im Modelltext erfundene
    Pfade.
    """
    root = output_dir.expanduser().resolve(strict=False)
    asset_list = tuple(assets)
    authorized = {asset.relative_path.as_posix() for asset in asset_list}
    for asset in asset_list:
        _require_existing_asset(root=root, path=asset.relative_path, error_code=error_code)
    for reference in _image_references(markdown):
        if reference not in authorized:
            raise AssetReferenceValidationError(error_code, "Die Bildreferenz ist kein autorisiertes lokales Asset.")
        _require_existing_asset(root=root, path=PurePosixPath(reference), error_code=error_code)


def _image_references(markdown: str) -> tuple[str, ...]:
    references = [match.group("angled") or match.group("plain") for match in _MARKDOWN_IMAGE.finditer(markdown)]
    references.extend(match.group("src") for match in _HTML_IMAGE.finditer(markdown))
    return tuple(references)


def _require_existing_asset(*, root: Path, path: PurePosixPath, error_code: str) -> None:
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise AssetReferenceValidationError(error_code, "Der Assetpfad ist nicht sicher relativ.")
    target = (root / Path(*path.parts)).resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise AssetReferenceValidationError(error_code, "Der Assetpfad verlässt den Ausgabeordner.") from error
    if not target.is_file():
        raise AssetReferenceValidationError(error_code, "Das autoritative Bildasset fehlt im Ausgabeordner.")


__all__ = ["AssetReferenceValidationError", "validate_cloud_model_has_no_image_references", "validate_markdown_image_references"]
