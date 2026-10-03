"""Lokaler Tesseract-Fallback für PDF-Seiten ohne verwertbaren Textlayer."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path
import re
import subprocess

import pypdfium2 as pdfium

from app.pdf_extract import ExtractedPage
from app.models import ConversionWarning, PageReference
from app.ocr_config import resolve_ocr_pages, validate_min_word_confidence


class OcrExtractionError(ValueError):
    """Die lokale OCR konnte nicht sicher ausgeführt werden."""


_LANGUAGE_CODES = {
    "de": "deu",
    "en": "eng",
}


@dataclass(frozen=True, slots=True)
class OcrOutcome:
    pages: tuple[ExtractedPage, ...]
    warnings: tuple[ConversionWarning, ...] = ()
    page_metrics: tuple["OcrPageMetrics", ...] = ()


@dataclass(frozen=True, slots=True)
class OcrPageMetrics:
    page_number: int
    word_count: int
    average_word_confidence: float | None


def apply_ocr_fallback(
    *,
    source_path: Path,
    pages: tuple[ExtractedPage, ...],
    ocr_mode: str,
    ocr_language: str,
    ocr_pages: str = "all",
    min_word_confidence: int = 70,
) -> OcrOutcome:
    """Ersetzt Seiten nur bei erzwungener oder textloser PDF durch lokale OCR.

    Der automatische Modus betrachtet einen vorhandenen PDF-Textlayer als
    verwertbar, sobald mindestens eine Seite extrahierbare Wörter enthält.
    Damit bleibt ein digitales Dokument unverändert; ein reines Bild-PDF
    wird vollständig und nachvollziehbar seitenweise an Tesseract übergeben.
    """
    if ocr_mode not in {"auto", "off", "force"}:
        raise ValueError("ocr_mode muss auto, off oder force sein.")
    if ocr_mode == "off" or (ocr_mode == "auto" and any(page.word_count for page in pages)):
        return OcrOutcome(pages)

    language_code = _to_tesseract_language(ocr_language)
    _ensure_tesseract_ready(language_code)
    selected_pages = resolve_ocr_pages(ocr_pages, page_count=len(pages))
    threshold = validate_min_word_confidence(min_word_confidence)
    try:
        document = pdfium.PdfDocument(str(source_path))
    except Exception as error:
        raise OcrExtractionError(f"Die PDF konnte nicht für OCR gerendert werden: {source_path}") from error

    if len(document) != len(pages):
        raise OcrExtractionError("Die gerenderten OCR-Seiten stimmen nicht mit der PDF-Seitenzahl überein.")
    extracted: list[ExtractedPage] = []
    warnings: list[ConversionWarning] = []
    metrics: list[OcrPageMetrics] = []
    for existing in pages:
        if existing.page_number not in selected_pages:
            extracted.append(existing)
            continue
        page, confidences = _extract_ocr_page(document=document, page_number=existing.page_number, language_code=language_code)
        extracted.append(page)
        average = sum(confidences) / len(confidences) if confidences else None
        metrics.append(OcrPageMetrics(existing.page_number, page.word_count, average))
        if average is not None and average < threshold:
            warnings.append(ConversionWarning("OCR_LOW_CONFIDENCE", f"Die mittlere OCR-Wortkonfidenz liegt unter dem Grenzwert {threshold}.", page=PageReference(existing.page_number)))
    return OcrOutcome(tuple(extracted), tuple(warnings), tuple(metrics))


def _to_tesseract_language(language: str) -> str:
    normalized = language.strip().lower().replace("_", "-")
    primary_subtag = normalized.split("-", maxsplit=1)[0]
    try:
        return _LANGUAGE_CODES[primary_subtag]
    except KeyError as error:
        raise OcrExtractionError(
            f"Die OCR-Sprache {language!r} wird derzeit nicht unterstützt; verfügbar sind de und en."
        ) from error


def _extract_ocr_page(*, document: pdfium.PdfDocument, page_number: int, language_code: str) -> tuple[ExtractedPage, tuple[float, ...]]:
    page = document[page_number - 1]
    image = page.render(scale=300 / 72).to_pil()
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    text, confidences, layout_html = _run_tesseract(image_bytes.getvalue(), language_code)
    return ExtractedPage(
        page_number=page_number,
        text=text,
        word_count=len(re.findall(r"\S+", text)),
        column_count=1,
        layout_html=layout_html,
    ), confidences


def _run_tesseract(image: bytes, language_code: str) -> tuple[str, tuple[float, ...], str]:
    command = [
        "tesseract",
        "stdin",
        "stdout",
        "--oem",
        "1",
        "--psm",
        "3",
        "-l",
        language_code,
        "tsv",
    ]
    try:
        completed = subprocess.run(
            command,
            input=image,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except FileNotFoundError as error:
        raise OcrExtractionError("Tesseract ist nicht installiert oder nicht über PATH erreichbar.") from error
    except subprocess.TimeoutExpired as error:
        raise OcrExtractionError("Tesseract hat das OCR-Zeitlimit von 60 Sekunden überschritten.") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise OcrExtractionError(f"Tesseract konnte die Seite nicht erkennen: {detail or 'unbekannter Fehler'}")
    return _parse_tsv(completed.stdout.decode("utf-8", errors="replace"))


def _ensure_tesseract_ready(language_code: str) -> None:
    """Prüft Engine und Sprachdaten vor dem potenziell langen Seitenrendering."""
    try:
        version_check = subprocess.run(
            ["tesseract", "--version"], capture_output=True, check=False, timeout=10
        )
    except FileNotFoundError as error:
        raise OcrExtractionError(
            "Tesseract ist nicht installiert oder nicht über PATH erreichbar. "
            "Installieren Sie Tesseract 5 und nehmen Sie dessen Programmordner in PATH auf."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise OcrExtractionError("Tesseract reagiert nicht innerhalb von 10 Sekunden auf --version.") from error
    if version_check.returncode != 0:
        raise OcrExtractionError("Tesseract konnte nicht gestartet werden; prüfen Sie die lokale Installation.")
    try:
        languages = subprocess.run(
            ["tesseract", "--list-langs"], capture_output=True, check=False, timeout=10
        )
    except subprocess.TimeoutExpired as error:
        raise OcrExtractionError("Tesseract reagiert nicht innerhalb von 10 Sekunden auf --list-langs.") from error
    if languages.returncode != 0:
        raise OcrExtractionError("Die installierten Tesseract-Sprachdaten konnten nicht ermittelt werden.")
    installed = set(languages.stdout.decode("utf-8", errors="replace").splitlines()[1:])
    if language_code not in installed:
        raise OcrExtractionError(
            f"Die Tesseract-Sprachdaten {language_code!r} fehlen. "
            "Installieren Sie die passende .traineddata-Datei im tessdata-Ordner und versuchen Sie es erneut."
        )


def _parse_tsv(content: str) -> tuple[str, tuple[float, ...], str]:
    words: list[tuple[str, int, int, int, int]] = []
    confidences: list[float] = []
    for row in content.splitlines()[1:]:
        fields = row.split("\t", maxsplit=11)
        if len(fields) != 12 or fields[0] != "5" or not fields[11].strip():
            continue
        try:
            confidence = float(fields[10])
        except ValueError:
            continue
        try:
            left, top, width, height = int(fields[6]), int(fields[7]), int(fields[8]), int(fields[9])
        except ValueError:
            continue
        words.append((fields[11].strip(), left, width, top, height))
        confidences.append(confidence)
    lines = _group_words_by_vertical_position(words)
    compact_lines = [" ".join(word for word, _left, _width in line) for line in lines]
    return "\n".join(compact_lines), tuple(confidences), _render_positioned_html(lines)


def _group_words_by_vertical_position(words: list[tuple[str, int, int, int, int]]) -> list[list[tuple[str, int, int]]]:
    """Vereint getrennte OCR-Blöcke anhand der visuellen Grundlinie."""
    if not words:
        return []
    ordered = sorted(words, key=lambda item: (item[3], item[1]))
    heights = sorted(item[4] for item in ordered)
    tolerance = max(4, heights[len(heights) // 2] // 2)
    lines: list[list[tuple[str, int, int, int, int]]] = []
    for word in ordered:
        if not lines or abs(word[3] - lines[-1][0][3]) > tolerance:
            lines.append([word])
        else:
            lines[-1].append(word)
    return [[(word, left, width) for word, left, width, _top, _height in line] for line in lines]


def _render_positioned_html(lines: list[list[tuple[str, int, int]]]) -> str:
    """Erhält TSV-X-Positionen als editierbares, festbreites HTML im Markdown."""
    rendered: list[str] = []
    for words in lines:
        ordered = sorted(words, key=lambda item: item[1])
        char_widths = [width / max(len(word), 1) for word, _left, width in ordered]
        character_width = max(1.0, sum(char_widths) / len(char_widths))
        line = ""
        first_left = ordered[0][1]
        for word, left, _width in ordered:
            target = round((left - first_left) / character_width)
            line += " " * max(1 if line else 0, target - len(line)) + word
        rendered.append(escape(line))
    return "<pre class=\"doctomd-ocr-layout\">\n" + "\n".join(rendered) + "\n</pre>"


__all__ = ["OcrExtractionError", "OcrOutcome", "OcrPageMetrics", "apply_ocr_fallback"]
