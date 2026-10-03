"""Domänenmodelle für nachvollziehbare DocToMD-Konvertierungen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite
from pathlib import Path, PurePosixPath


class AssetKind(str, Enum):
    """Arten abgeleiteter Assets."""

    IMAGE = "image"
    TABLE = "table"


class ReferenceKind(str, Enum):
    """Konservativ erkannte Verweise innerhalb eines Dokuments."""

    CITATION = "citation"
    FOOTNOTE = "footnote"
    FIGURE = "figure"
    TABLE = "table"


class NativePdfLinkSource(str, Enum):
    """Lokal belegbare Herkunft eines externen PDF-Ziels."""

    NATIVE_PDF_LINK_ANNOTATION = "native_pdf_link_annotation"


class ConversionStatus(str, Enum):
    """Abschlussstatus einer Konvertierung."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


class WarningSeverity(str, Enum):
    """Schweregrade sichtbarer Qualitätswarnungen."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class BlockKind(str, Enum):
    """Grundlegende strukturelle Markdown-Blöcke."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"


@dataclass(frozen=True, slots=True)
class PageReference:
    """Referenz auf eine einsbasierte Seite der Primärquelle."""

    page_number: int
    location: str | None = None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number muss mindestens 1 sein.")


NATIVE_PDF_LINK_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class PdfAnnotationRect:
    """PDF-Annotationsrechteck im PDF-User-Space mit Ursprung links unten."""

    left: float
    bottom: float
    right: float
    top: float

    def __post_init__(self) -> None:
        if not all(isfinite(value) for value in (self.left, self.bottom, self.right, self.top)):
            raise ValueError("annotation_rect muss ausschließlich endliche Koordinaten enthalten.")
        if self.left >= self.right or self.bottom >= self.top:
            raise ValueError("annotation_rect muss eine positive Breite und Höhe haben.")


@dataclass(frozen=True, slots=True)
class NativePdfLink:
    """Lokal belegter externer Link aus einer nativen PDF-Link-Annotation."""

    target_url: str
    page: PageReference
    annotation_rect: PdfAnnotationRect
    source: NativePdfLinkSource = NativePdfLinkSource.NATIVE_PDF_LINK_ANNOTATION
    visible_title: str | None = None

    def __post_init__(self) -> None:
        if not self.target_url.strip():
            raise ValueError("target_url darf nicht leer sein.")
        if self.visible_title is not None and not self.visible_title.strip():
            raise ValueError("visible_title darf nicht leer sein, wenn er gesetzt ist.")

    def to_contract_dict(self) -> dict[str, object]:
        """Serialisiert den stabilen Vertrag; URL- und Titelprüfung folgen separat."""

        result: dict[str, object] = {
            "target_url": self.target_url,
            "page": {"page_number": self.page.page_number},
            "annotation_rect": {
                "left": self.annotation_rect.left,
                "bottom": self.annotation_rect.bottom,
                "right": self.annotation_rect.right,
                "top": self.annotation_rect.top,
            },
            "source": self.source.value,
        }
        if self.visible_title is not None:
            result["visible_title"] = self.visible_title
        return result


@dataclass(frozen=True, slots=True)
class PageMarker:
    """Strukturmodell eines unsichtbaren Markdown-Seitenmarkers."""

    page: PageReference


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    """Strukturierter Textblock mit Herkunftsseite."""

    kind: BlockKind
    text: str
    page: PageReference
    heading_level: int | None = None
    ordered: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text darf nicht leer sein.")
        if self.kind is BlockKind.HEADING:
            if self.heading_level is None or not 1 <= self.heading_level <= 6:
                raise ValueError("Überschriften benötigen eine Ebene von 1 bis 6.")
        elif self.heading_level is not None:
            raise ValueError("Nur Überschriften dürfen eine Ebene haben.")
        if self.kind is not BlockKind.LIST_ITEM and self.ordered:
            raise ValueError("ordered ist nur für Listenelemente zulässig.")


@dataclass(frozen=True, slots=True)
class DocumentTable:
    """Einfache rechteckige Tabelle mit Herkunftsseite."""

    table_id: str
    page: PageReference
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if not self.table_id:
            raise ValueError("table_id darf nicht leer sein.")
        if len(self.headers) < 2 or any(not cell.strip() for cell in self.headers):
            raise ValueError("Tabellen benötigen mindestens zwei nichtleere Kopfzellen.")
        if not self.rows or any(len(row) != len(self.headers) or any(not cell.strip() for cell in row) for row in self.rows):
            raise ValueError("Tabellenzeilen müssen vollständig zur Kopfzeile passen.")


@dataclass(frozen=True, slots=True)
class DocumentReference:
    """Belegbarer Verweis mit Quell- und optionaler Zielseite."""

    kind: ReferenceKind
    label: str
    page: PageReference
    target_page: PageReference | None = None
    target_id: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("label darf nicht leer sein.")
        if self.target_id is not None and not self.target_id.strip():
            raise ValueError("target_id darf nicht leer sein.")


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """Lokale Primärquelle mit optionalen Fingerabdruckdaten."""

    path: Path
    media_type: str
    size_bytes: int | None = None
    sha256: str | None = None
    modified_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.media_type:
            raise ValueError("media_type darf nicht leer sein.")
        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError("size_bytes darf nicht negativ sein.")


@dataclass(frozen=True, slots=True)
class Asset:
    """Abgeleitetes Asset mit Herkunftsseite und optionaler Semantik."""

    asset_id: str
    kind: AssetKind
    relative_path: PurePosixPath
    page: PageReference
    caption: str | None = None
    description: str | None = None
    description_path: PurePosixPath | None = None

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("asset_id darf nicht leer sein.")
        if self.relative_path.is_absolute() or ".." in self.relative_path.parts:
            raise ValueError("relative_path muss ein sicherer relativer Pfad sein.")
        if self.description_path is not None and (
            self.description_path.is_absolute() or ".." in self.description_path.parts
        ):
            raise ValueError("description_path muss ein sicherer relativer Pfad sein.")


@dataclass(frozen=True, slots=True)
class ConversionWarning:
    """Sichtbare Qualitätswarnung mit optionalem Seitenbezug."""

    code: str
    message: str
    severity: WarningSeverity = WarningSeverity.WARNING
    page: PageReference | None = None

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code darf nicht leer sein.")
        if not self.message:
            raise ValueError("message darf nicht leer sein.")


@dataclass(frozen=True, slots=True)
class ConversionResult:
    """Nachvollziehbares Ergebnis einer vollständigen oder teilweisen Konvertierung."""

    source: SourceDocument
    status: ConversionStatus
    output_format: str
    markdown_path: PurePosixPath | None = None
    manifest_path: PurePosixPath | None = None
    assets: tuple[Asset, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()

    def __post_init__(self) -> None:
        if not self.output_format:
            raise ValueError("output_format darf nicht leer sein.")
        for path_name, path in (("markdown_path", self.markdown_path), ("manifest_path", self.manifest_path)):
            if path is not None and (path.is_absolute() or ".." in path.parts):
                raise ValueError(f"{path_name} muss ein sicherer relativer Pfad sein.")


__all__ = [
    "Asset",
    "AssetKind",
    "BlockKind",
    "ConversionResult",
    "ConversionStatus",
    "ConversionWarning",
    "DocumentBlock",
    "DocumentReference",
    "DocumentTable",
    "NativePdfLink",
    "NativePdfLinkSource",
    "NATIVE_PDF_LINK_SCHEMA_VERSION",
    "PageMarker",
    "PageReference",
    "PdfAnnotationRect",
    "ReferenceKind",
    "SourceDocument",
    "WarningSeverity",
]
