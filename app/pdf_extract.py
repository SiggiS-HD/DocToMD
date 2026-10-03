"""Seitenweise, positionsgestützte Textextraktion aus digitalen PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from statistics import median
from typing import Any, Iterable

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException


class PdfExtractionError(ValueError):
    """Die PDF konnte nicht sicher seitenweise gelesen werden."""


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Unveränderter, lesereihengeordneter Text einer einsbasierten PDF-Seite."""

    page_number: int
    text: str
    word_count: int
    column_count: int
    layout_html: str | None = None
    heading_levels: tuple[tuple[str, int], ...] = ()
    bullet_lines: tuple[str, ...] = ()
    table_lines: tuple[str, ...] = ()
    display_formulas: tuple[tuple[str, str], ...] = ()
    formula_candidate_lines: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number muss mindestens 1 sein.")
        if self.word_count < 0:
            raise ValueError("word_count darf nicht negativ sein.")
        if self.column_count not in (1, 2):
            raise ValueError("column_count muss 1 oder 2 sein.")


@dataclass(frozen=True, slots=True)
class _Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    font_size: float | None = None


@dataclass(frozen=True, slots=True)
class _Line:
    words: tuple[_Word, ...]

    @property
    def top(self) -> float:
        return min(word.top for word in self.words)

    @property
    def bottom(self) -> float:
        return max(word.bottom for word in self.words)

    @property
    def x0(self) -> float:
        return min(word.x0 for word in self.words)

    @property
    def x1(self) -> float:
        return max(word.x1 for word in self.words)

    @property
    def font_size(self) -> float | None:
        sizes = [word.font_size for word in self.words if word.font_size is not None]
        return round(float(median(sizes)), 2) if sizes else None

    def as_text(self) -> str:
        return " ".join(word.text for word in sorted(self.words, key=lambda word: word.x0))


def extract_pdf_pages(path: Path) -> tuple[ExtractedPage, ...]:
    """Liest jede Seite einer digitalen PDF mit konservativer Spaltenreihenfolge."""
    source_path = path.expanduser().resolve(strict=False)
    if not source_path.is_file():
        raise PdfExtractionError(f"Die PDF-Quelldatei ist nicht lesbar: {source_path}")

    try:
        with pdfplumber.open(source_path) as pdf:
            return tuple(
                _extract_page(page, page_number)
                for page_number, page in enumerate(pdf.pages, start=1)
            )
    except (OSError, PDFSyntaxError, PdfminerException) as error:
        raise PdfExtractionError(f"Die PDF konnte nicht gelesen werden: {source_path}") from error


def _extract_page(page: Any, page_number: int) -> ExtractedPage:
    words = tuple(_to_word(word) for word in page.extract_words(
        keep_blank_chars=False,
        use_text_flow=False,
        extra_attrs=["size"],
    ))
    lines = _group_lines(words)
    table_bboxes = _table_bboxes(page)
    ordered_lines, column_count = _order_lines(lines, page.width, page.height, table_bboxes)
    return ExtractedPage(
        page_number=page_number,
        text=_render_ordered_lines(ordered_lines),
        word_count=len(words),
        column_count=column_count,
        heading_levels=_heading_levels(ordered_lines),
        bullet_lines=_bullet_lines(getattr(page, "curves", ()), ordered_lines),
        table_lines=_table_lines(ordered_lines, table_bboxes),
        display_formulas=_display_formulas(ordered_lines, page.width),
        formula_candidate_lines=_formula_candidate_lines(ordered_lines, page.width),
    )


def _render_ordered_lines(lines: tuple[_Line, ...]) -> str:
    """Erhält deutliche vertikale Lücken als Absatzgrenzen.

    Zeilen einer PDF sind nicht automatisch Absätze. Eine Lücke von mehr als
    dem Anderthalbfachen der mittleren Zeilenhöhe ist jedoch ein ausreichend
    konservatives Signal für eine sichtbare Absatzgrenze. Rücksprünge in der
    vertikalen Position entstehen bei Spaltenwechseln und werden nicht als
    Absatztrennung interpretiert.
    """
    if not lines:
        return ""
    line_heights = [line.bottom - line.top for line in lines]
    gap_threshold = median(line_heights) * 1.5
    rendered = [lines[0].as_text()]
    previous = lines[0]
    for line in lines[1:]:
        vertical_gap = line.top - previous.bottom
        if vertical_gap > gap_threshold:
            rendered.append("")
        rendered.append(line.as_text())
        previous = line
    return "\n".join(rendered)


def _to_word(word: dict[str, Any]) -> _Word:
    return _Word(
        text=word["text"],
        x0=float(word["x0"]),
        x1=float(word["x1"]),
        top=float(word["top"]),
        bottom=float(word["bottom"]),
        font_size=float(word["size"]) if word.get("size") is not None else None,
    )


def _heading_levels(lines: tuple[_Line, ...]) -> tuple[tuple[str, int], ...]:
    """Leitet Überschriften nur aus deutlich größerer Satzschrift ab.

    Schriftgrößen sind ein lokales, reproduzierbares Signal. Damit normaler
    Fließtext nicht zur Überschrift wird, muss eine Zeile mindestens zwanzig
    Prozent größer als die mittlere Satzschrift sein. Die größten Größen
    erhalten die oberste Markdown-Ebene; gleich große Größen bleiben auf einer
    Ebene.
    """
    known_sizes = [line.font_size for line in lines if line.font_size is not None]
    if not known_sizes:
        return ()
    body_size = median(known_sizes)
    candidate_lines = [
        line
        for line in lines
        if line.font_size is not None
        and line.font_size >= body_size * 1.2
        and len(line.as_text()) <= 160
        and "=" not in line.as_text()
    ]
    candidate_sizes = sorted({line.font_size for line in candidate_lines}, reverse=True)
    levels = {size: min(index + 1, 6) for index, size in enumerate(candidate_sizes)}
    return tuple((line.as_text(), levels[line.font_size]) for line in candidate_lines)


def _display_formulas(
    lines: tuple[_Line, ...], page_width: float
) -> tuple[tuple[str, str], ...]:
    """Rekonstruiert nur zentrierte Zustandsformeln mit belegten Scripts.

    Das PDF muss die drei Scripts jeweils als kleinere und vertikal versetzte
    Wörter enthalten. Die enge Grammatik vermeidet, dass mathematisch
    aussehender Fließtext oder komplexere Formeln als LaTeX erfunden werden.
    """
    formulas: list[tuple[str, str]] = []
    for line in lines:
        words = tuple(sorted(line.words, key=lambda word: word.x0))
        if len(words) != 8 or not _is_centered(line, page_width):
            continue
        first, future, separator, history, start, tail, end, closing = words
        first_match = re.fullmatch(r"(?P<name>[A-Za-z]+)\((?P<state>[A-Za-z]+)", first.text)
        tail_match = re.fullmatch(r",(?:…|\.\.\.),(?P<state>[A-Za-z]+)", tail.text)
        if (
            first_match is None
            or tail_match is None
            or separator.text not in {"|", "∣"}
            or closing.text != ")"
            or not re.fullmatch(r"[A-Za-z]+", history.text)
            or not all(re.fullmatch(r"[A-Za-z0-9+\-]+", word.text) for word in (future, start, end))
            or not _are_script_words((future, start, end), (first, separator, history, tail, closing))
        ):
            continue
        formulas.append((
            line.as_text(),
            f"{first_match.group('name')}({first_match.group('state')}^{{{future.text}}} "
            f"\\mid {history.text}_{{{start.text}}}, \\ldots, "
            f"{tail_match.group('state')}_{{{end.text}}})",
        ))
    return tuple(formulas)


def _formula_candidate_lines(lines: tuple[_Line, ...], page_width: float) -> tuple[str, ...]:
    """Markiert zentrierte mathematische Ausdrücke, die lokal nicht gerendert werden.

    Pfeil- und Mengenzeichen können in gewöhnlichem Fließtext vorkommen. Ein
    Befund entsteht deshalb nur für kurze, zentrierte Zeilen mit höchstens sechs
    Wortgruppen. Er ist eine Qualitätsgrenze, keine Formelinterpretation.
    """
    candidates: list[str] = []
    for line in lines:
        text = line.as_text()
        if (
            len(line.words) <= 6
            and len(text) <= 100
            and _is_centered(line, page_width)
            and ("→" in text or "∈" in text)
        ):
            candidates.append(text)
    return tuple(candidates)


def _is_centered(line: _Line, page_width: float) -> bool:
    return abs(((line.x0 + line.x1) / 2) - (page_width / 2)) <= page_width * 0.12


def _are_script_words(scripts: tuple[_Word, ...], bases: tuple[_Word, ...]) -> bool:
    base_sizes = [word.font_size for word in bases if word.font_size is not None]
    if not base_sizes or any(word.font_size is None for word in scripts):
        return False
    base_size = median(base_sizes)
    base_top = median(word.top for word in bases)
    return all(
        word.font_size <= base_size * 0.85 and word.top >= base_top + 1.0
        for word in scripts
    )


def _bullet_lines(curves: Iterable[dict[str, Any]], lines: tuple[_Line, ...]) -> tuple[str, ...]:
    """Ordnet kleine gefüllte Vektorformen links einer Textzeile als Bullet zu."""
    bullet_texts: list[str] = []
    for curve in curves:
        if not curve.get("fill"):
            continue
        width = float(curve["x1"]) - float(curve["x0"])
        height = float(curve["bottom"]) - float(curve["top"])
        if not 1.0 <= width <= 12.0 or not 1.0 <= height <= 12.0:
            continue
        vertical_center = (float(curve["top"]) + float(curve["bottom"])) / 2
        candidates = [
            line
            for line in lines
            if float(curve["x1"]) <= line.x0
            and abs(vertical_center - ((line.top + line.bottom) / 2)) <= max(4.0, (line.bottom - line.top) * 0.6)
        ]
        if candidates:
            text = min(candidates, key=lambda line: abs(vertical_center - ((line.top + line.bottom) / 2))).as_text()
            if text not in bullet_texts:
                bullet_texts.append(text)
    return tuple(bullet_texts)


def _table_bboxes(page: Any) -> tuple[tuple[float, float, float, float], ...]:
    """Liest nur die Geometrie erkannter Tabellen, ohne Tabelleninhalt zu deuten."""
    find_tables = getattr(page, "find_tables", None)
    if not callable(find_tables):
        return ()
    return tuple(tuple(float(value) for value in table.bbox) for table in find_tables())


def _table_lines(
    lines: tuple[_Line, ...], table_bboxes: tuple[tuple[float, float, float, float], ...]
) -> tuple[str, ...]:
    return tuple(line.as_text() for line in lines if _line_is_in_table(line, table_bboxes))


def _line_is_in_table(
    line: _Line, table_bboxes: tuple[tuple[float, float, float, float], ...]
) -> bool:
    vertical_center = (line.top + line.bottom) / 2
    horizontal_center = (line.x0 + line.x1) / 2
    return any(
        x0 <= horizontal_center <= x1 and top <= vertical_center <= bottom
        for x0, top, x1, bottom in table_bboxes
    )


def _group_lines(words: Iterable[_Word]) -> tuple[_Line, ...]:
    ordered_words = sorted(words, key=lambda word: (word.top, word.x0))
    if not ordered_words:
        return ()

    heights = [word.bottom - word.top for word in ordered_words]
    tolerance = max(1.0, median(heights) * 0.45)
    line_groups: list[list[_Word]] = []
    for word in ordered_words:
        if not line_groups or abs(word.top - line_groups[-1][0].top) > tolerance:
            line_groups.append([word])
        else:
            line_groups[-1].append(word)
    return tuple(_Line(tuple(group)) for group in line_groups)


def _order_lines(
    lines: tuple[_Line, ...], page_width: float, page_height: float,
    table_bboxes: tuple[tuple[float, float, float, float], ...] = (),
) -> tuple[tuple[_Line, ...], int]:
    """Liest zentrale Spalten vollständig links vor rechts.

    Die Heuristik wird nur aktiv, wenn beide Seiten mindestens drei Zeilen mit
    überlappender vertikaler Ausdehnung besitzen. Der obere und untere
    zwölfprozentige Seitenrand bleibt davon ausgenommen: Kopf- und Fußzeilen
    werden dort in ihrer geometrischen Reihenfolge erhalten. Uneindeutige
    Layouts bleiben in der geometrischen Standardreihenfolge, damit keine
    erfundene Struktur entsteht.
    """
    margin_height = page_height * 0.12
    header_lines = [line for line in lines if line.top < margin_height]
    footer_lines = [line for line in lines if line.bottom > page_height - margin_height]
    table_lines = [line for line in lines if _line_is_in_table(line, table_bboxes)]
    body_lines = [
        line
        for line in lines
        if line not in header_lines and line not in footer_lines and line not in table_lines
    ]
    midpoint = page_width / 2
    left_lines: list[_Line] = []
    right_lines: list[_Line] = []
    spanning_lines: list[_Line] = []
    for line in body_lines:
        split_columns = _split_line_at_column_gutter(line, midpoint, page_width)
        if split_columns is not None:
            left_lines.append(split_columns[0])
            right_lines.append(split_columns[1])
        elif line.x1 <= midpoint:
            left_lines.append(line)
        elif line.x0 >= midpoint:
            right_lines.append(line)
        else:
            spanning_lines.append(line)

    has_overlapping_columns = (
        left_lines
        and right_lines
        and max(line.top for line in left_lines) >= min(line.top for line in right_lines)
        and max(line.top for line in right_lines) >= min(line.top for line in left_lines)
    )
    if len(left_lines) < 3 or len(right_lines) < 3 or not has_overlapping_columns:
        return tuple(sorted(lines, key=lambda line: line.top)), 1

    first_column_top = min(left_lines[0].top, right_lines[0].top)
    body_prefix = [line for line in (*spanning_lines, *table_lines) if line.top < first_column_top]
    body_trailing = [line for line in (*spanning_lines, *table_lines) if line.top >= first_column_top]
    return (
        tuple(sorted(header_lines, key=lambda line: line.top))
        + tuple(sorted(body_prefix, key=lambda line: line.top))
        + tuple(sorted(left_lines, key=lambda line: line.top))
        + tuple(sorted(right_lines, key=lambda line: line.top))
        + tuple(sorted(body_trailing, key=lambda line: line.top))
        + tuple(sorted(footer_lines, key=lambda line: line.top)),
        2,
    )


def _split_line_at_column_gutter(
    line: _Line, midpoint: float, page_width: float
) -> tuple[_Line, _Line] | None:
    """Teilt nur durch eine sichtbare Mittelgasse getrennte Zeilenpaare.

    Einspaltiger Fließtext kann Wörter auf beiden Seiten der Seitenmitte
    enthalten. Die bloße Seitenmitte ist daher kein Spaltenkriterium. Ein
    echter Zeilenpaar-Kandidat benötigt stattdessen eine breite Lücke, die die
    Seitenmitte einschließt. Die Grenze von acht Prozent der Seitenbreite ist
    deutlich größer als ein normaler Wortabstand und kleiner als die Gasse der
    versionierten wissenschaftlichen Zwei-Spalten-Fixture.
    """
    ordered_words = tuple(sorted(line.words, key=lambda word: word.x0))
    minimum_gutter_width = page_width * 0.08
    for index, left_word in enumerate(ordered_words[:-1]):
        right_word = ordered_words[index + 1]
        if (
            left_word.x1 <= midpoint <= right_word.x0
            and right_word.x0 - left_word.x1 >= minimum_gutter_width
        ):
            return _Line(ordered_words[: index + 1]), _Line(ordered_words[index + 1 :])
    return None


__all__ = ["ExtractedPage", "PdfExtractionError", "extract_pdf_pages"]
