"""Erzeugt kleine, rechtlich unbedenkliche Vektor-PDF-Fixtures."""

from __future__ import annotations

from pathlib import Path


FIXTURE_PATH = Path(__file__).with_name("vector-figure.pdf")


def _text(x: int, y: int, value: str, size: int = 10) -> str:
    escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET"


def build_pdf(path: Path = FIXTURE_PATH, *, ambiguous: bool = False, compact_caption: bool = False, paired_figures: bool = False) -> None:
    """Schreibt eine Seite mit eindeutigem Vektordiagramm und Figure-Caption."""
    commands = [
        "0.8 w 72 250 m 72 500 l 430 500 l S",
        "0.6 w 72 440 m 430 440 l S",
        "0.6 w 72 380 m 430 380 l S",
        "0.6 w 72 320 m 430 320 l S",
        "1.5 w 82 475 m 160 430 l 245 360 l 335 300 l 420 275 l S",
        _text(72, 220, "Figure1: Synthetic vector trend." if compact_caption else "Figure 1: Synthetic vector trend."),
    ]
    if ambiguous:
        commands.append(_text(72, 200, "Fig. 2: Another synthetic caption."))
    if paired_figures:
        commands = [
            "0.8 w 72 250 m 72 500 l 270 500 l S",
            "0.6 w 72 440 m 270 440 l S",
            "0.6 w 72 380 m 270 380 l S",
            "1.5 w 82 475 m 145 420 l 210 350 l 260 290 l S",
            "0.8 w 340 250 m 340 500 l 540 500 l S",
            "0.6 w 340 440 m 540 440 l S",
            "0.6 w 340 380 m 540 380 l S",
            "1.5 w 350 285 m 410 340 l 475 420 l 530 470 l S",
            _text(72, 220, "Figure 1: Left synthetic trend."),
            _text(340, 220, "Figure 2: Right synthetic trend."),
        ]
    stream = ("\n".join(commands) + "\n").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
    ]
    content = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, object_body in enumerate(objects, start=1):
        offsets.append(len(content)); content.extend(f"{number} 0 obj\n".encode("ascii")); content.extend(object_body); content.extend(b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii")); content.extend(b"0000000000 65535 f \n")
    content.extend(b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets))
    content.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(content)


if __name__ == "__main__":
    build_pdf()
