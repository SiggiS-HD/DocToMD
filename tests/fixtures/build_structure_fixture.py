"""Erzeugt eine rechtlich unbedenkliche PDF-Fixture für Markdown-Strukturen."""

from __future__ import annotations

from pathlib import Path


FIXTURE_PATH = Path(__file__).with_name("structure-elements.pdf")


def _text(x: int, y: int, value: str, size: int = 10) -> str:
    escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET"


def _stream() -> bytes:
    commands = [
        _text(54, 748, "1 Overview", 14),
        _text(54, 720, "First paragraph line one."),
        _text(54, 706, "First paragraph line two."),
        _text(54, 672, "Second paragraph stays separate."),
        _text(54, 638, "- Bullet item"),
        _text(54, 620, "1. Ordered item"),
        _text(54, 586, "1.1 Details", 12),
        _text(54, 558, "print(42)", 9),
        "0.4 w 54 522 m 300 522 l 300 466 l 54 466 l h S",
        "0.4 w 170 522 m 170 466 l S",
        "0.4 w 54 503 m 300 503 l S",
        "0.4 w 54 484 m 300 484 l S",
        _text(62, 508, "Name", 9),
        _text(180, 508, "Value", 9),
        _text(62, 489, "Alpha", 9),
        _text(180, 489, "1", 9),
        _text(62, 470, "Beta", 9),
        _text(180, 470, "2", 9),
    ]
    return ("\n".join(commands) + "\n").encode("ascii")


def build_pdf(path: Path = FIXTURE_PATH) -> None:
    """Schreibt eine deterministische einseitige PDF ohne Drittbibliothek."""
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
