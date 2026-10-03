"""Erzeugt die rechtlich unbedenkliche wissenschaftliche PDF-Testfixture."""

from __future__ import annotations

from pathlib import Path


FIXTURE_PATH = Path(__file__).with_name("scientific-two-column.pdf")


def _text(x: int, y: int, value: str, size: int = 9) -> str:
    escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET"


def _stream() -> bytes:
    commands = [
        "0.7 w 54 752 m 558 752 l S",
        _text(54, 766, "Synthetic Methods Note", 10),
        _text(500, 766, "Page 1", 9),
        _text(54, 728, "A Small Reproducible Study", 15),
        _text(54, 710, "Author One; Author Two", 9),
        "0.4 w 54 696 m 558 696 l S",
        _text(54, 678, "Abstract", 10),
        _text(54, 664, "This synthetic paper provides a legal fixture."),
        _text(54, 646, "1 Introduction", 10),
        _text(54, 632, "The left column contains short prose with a displayed equation."),
        _text(54, 614, "The fixture deliberately uses only ASCII text and vector rules."),
        _text(54, 580, "p(x) = sum_i w_i * x_i / n", 11),
        _text(54, 552, "2 Method", 10),
        _text(54, 524, "A header, two columns, a formula,"),
        _text(54, 510, "and a table form the evaluation set."),
        _text(315, 678, "3 Results", 10),
        _text(315, 664, "The right column starts independently."),
        _text(315, 646, "Table 1 reports deliberately simple reference values."),
        "0.4 w 315 626 m 558 626 l 558 570 l 315 570 l h S",
        "0.4 w 405 626 m 405 570 l S",
        "0.4 w 315 608 m 558 608 l S",
        "0.4 w 315 589 m 558 589 l S",
        _text(323, 614, "Metric", 8),
        _text(420, 614, "Value", 8),
        _text(323, 596, "precision", 8),
        _text(420, 596, "0.80", 8),
        _text(323, 577, "recall", 8),
        _text(420, 577, "0.75", 8),
        _text(315, 548, "4 Discussion", 10),
        _text(315, 534, "The footer is intentionally outside both content columns."),
        "0.7 w 54 42 m 558 42 l S",
        _text(54, 28, "Synthetic fixture - not a published work", 8),
    ]
    return ("\n".join(commands) + "\n").encode("ascii")


def build_pdf(path: Path = FIXTURE_PATH) -> None:
    """Schreibt eine einzelne, deterministische PDF-Seite ohne Drittbibliothek."""
    stream = _stream()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    content = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, object_body in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{number} 0 obj\n".encode("ascii"))
        content.extend(object_body)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    content.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:]))
    content.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    path.write_bytes(content)


if __name__ == "__main__":
    build_pdf()
