"""Erzeugt die rechtlich unbedenkliche digitale PDF-Basisfixture."""

from __future__ import annotations

from pathlib import Path


FIXTURE_PATH = Path(__file__).with_name("simple-digital.pdf")


def build_pdf(path: Path = FIXTURE_PATH) -> None:
    """Schreibt eine deterministische zweitseitige PDF ohne Drittbibliothek."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length 74 >>\nstream\nBT /F1 18 Tf 72 720 Td (Fixture Titel) Tj 0 -36 Td (Erster Absatz.) Tj ET\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Length 71 >>\nstream\nBT /F1 18 Tf 72 720 Td (2 Details) Tj 0 -36 Td (Zweiter Absatz.) Tj ET\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
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
