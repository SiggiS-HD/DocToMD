"""Ermittlung stabiler Fingerabdrücke für lokale Primärquellen."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path

from app.models import SourceDocument


_HASH_BLOCK_SIZE = 1024 * 1024


class SourceFingerprintError(ValueError):
    """Der Fingerabdruck einer Primärquelle konnte nicht verlässlich ermittelt werden."""


def fingerprint_source(path: Path, *, media_type: str) -> SourceDocument:
    """Erstellt einen SHA-256-basierten Fingerabdruck einer unveränderten Datei.

    Der Zeitpunkt und die Größe werden vor und nach dem Lesen verglichen, damit
    ein während des Hashens verändertes Dokument nicht stillschweigend als
    konsistente Quelle protokolliert wird.
    """
    source_path = path.expanduser().resolve(strict=False)
    if not source_path.is_file():
        raise SourceFingerprintError(f"Die Quelldatei ist nicht lesbar: {source_path}")

    before = source_path.stat()
    digest = hashlib.sha256()
    try:
        with source_path.open("rb") as source_file:
            while block := source_file.read(_HASH_BLOCK_SIZE):
                digest.update(block)
    except OSError as error:
        raise SourceFingerprintError(
            f"Der Quellfingerabdruck konnte nicht gelesen werden: {source_path}"
        ) from error

    after = source_path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise SourceFingerprintError(
            f"Die Quelldatei wurde während der Fingerabdruckerstellung verändert: {source_path}"
        )

    return SourceDocument(
        path=source_path,
        media_type=media_type,
        size_bytes=before.st_size,
        sha256=digest.hexdigest(),
        modified_at=datetime.fromtimestamp(before.st_mtime, tz=timezone.utc),
    )


__all__ = ["SourceFingerprintError", "fingerprint_source"]
