"""Erzeugung des versionierten DocToMD-Konvertierungsmanifests."""

from __future__ import annotations

from datetime import datetime
from importlib.metadata import version
from pathlib import PurePosixPath
from typing import Any, Iterable

from app.models import Asset, ConversionStatus, ConversionWarning, DocumentBlock, DocumentReference, DocumentTable, NATIVE_PDF_LINK_SCHEMA_VERSION, NativePdfLink, SourceDocument
from app.cloud_document_telemetry import CloudDocumentTelemetry, serialize_cloud_document_telemetry
from app.native_pdf_links import validate_native_pdf_links
from app.quality import build_quality_section
from app.ocr_extract import OcrOutcome
from app.local_reuse_context import build_local_reuse_metadata


def build_manifest(*, source: SourceDocument, status: ConversionStatus, markdown_path: PurePosixPath, markdown_content: str | None = None, blocks: Iterable[DocumentBlock], assets: Iterable[Asset], tables: Iterable[DocumentTable], native_pdf_links: Iterable[NativePdfLink] = (), references: Iterable[DocumentReference] = (), vision_proposals: Iterable[PurePosixPath] = (), vision_markdown_path: PurePosixPath | None = None, vision_review_path: PurePosixPath | None = None, cloud_markdown_path: PurePosixPath | None = None, cloud_document_telemetry: CloudDocumentTelemetry | None = None, rag_indexing: dict[str, Any] | None = None, rag_readiness: dict[str, Any] | None = None, ocr_outcome: OcrOutcome | None = None, ocr_pages: str = "all", ocr_min_word_confidence: int = 70, warnings: Iterable[ConversionWarning] = (), started_at: datetime | None = None, completed_at: datetime | None = None, ocr_mode: str = "off", ocr_language: str = "de") -> dict[str, Any]:
    if source.size_bytes is None or source.sha256 is None or source.modified_at is None:
        raise ValueError("Das Manifest benötigt einen vollständigen Quellfingerabdruck.")
    if markdown_path.is_absolute() or ".." in markdown_path.parts:
        raise ValueError("Der Markdown-Pfad im Manifest muss sicher relativ sein.")
    link_list = validate_native_pdf_links(native_pdf_links)
    if link_list and (source.media_type != "application/pdf" or source.path.suffix.casefold() != ".pdf"):
        raise ValueError("Native PDF-Links dürfen nur für eine PDF-Primärquelle gespeichert werden.")
    block_list, asset_list, table_list, reference_list, proposal_list, warning_list = tuple(blocks), tuple(assets), tuple(tables), tuple(references), tuple(vision_proposals), tuple(warnings)
    serialized_assets = [{"asset_id": asset.asset_id, "kind": asset.kind.value, "path": asset.relative_path.as_posix(), "page": {"page_number": asset.page.page_number}, **({"caption": asset.caption} if asset.caption else {}), **({"description": asset.description} if asset.description else {}), **({"description_path": asset.description_path.as_posix()} if asset.description_path else {})} for asset in asset_list]
    content_references = [{"kind": "text", "page": {"page_number": block.page.page_number}} for block in block_list]
    content_references.extend({"kind": "asset", "asset_id": asset.asset_id, "page": {"page_number": asset.page.page_number}} for asset in asset_list)
    content_references.extend({"kind": "table", "page": {"page_number": table.page.page_number}} for table in table_list)
    serialized_references = [
        {
            "kind": reference.kind.value,
            "label": reference.label,
            "page": {"page_number": reference.page.page_number},
            **({"target_page": {"page_number": reference.target_page.page_number}} if reference.target_page else {}),
            **({"target_id": reference.target_id} if reference.target_id else {}),
        }
        for reference in reference_list
    ]
    artifacts = {"markdown_path": markdown_path.as_posix(), "assets": serialized_assets, "content_references": content_references, "references": serialized_references, "vision_proposals": [path.as_posix() for path in proposal_list]}
    if markdown_content is not None:
        artifacts["local_reuse"] = build_local_reuse_metadata(markdown=markdown_content)
    if link_list:
        artifacts["native_pdf_links"] = {
            "schema_version": NATIVE_PDF_LINK_SCHEMA_VERSION,
            "items": [
                {
                    **link.to_contract_dict(),
                    "title_assignment_status": (
                        "geometrically_verified" if link.visible_title is not None else "neutral_page_label"
                    ),
                }
                for link in link_list
            ],
        }
    if vision_markdown_path is not None:
        artifacts["vision_markdown_path"] = vision_markdown_path.as_posix()
    if vision_review_path is not None:
        artifacts["vision_review_path"] = vision_review_path.as_posix()
    if cloud_markdown_path is not None:
        artifacts["cloud_markdown_path"] = cloud_markdown_path.as_posix()
    if started_at is None or completed_at is None:
        raise ValueError("Das Manifest benötigt Start- und Endzeit.")
    conversion = {"status": status.value, "output_format": "markdown", "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(), "components": {"engine": {"name": "doctomd", "version": "0.1.0"}, "extractor": {"name": "pdfplumber", "version": version("pdfplumber")}}, "options": {"ocr_mode": ocr_mode, "ocr_language": ocr_language, "page_range": ocr_pages}}
    if ocr_outcome is not None:
        conversion["ocr"] = {"min_word_confidence": ocr_min_word_confidence, "pages": [{"page_number": item.page_number, "word_count": item.word_count, "average_word_confidence": item.average_word_confidence} for item in ocr_outcome.page_metrics]}
    if cloud_document_telemetry is not None:
        conversion["cloud_document"] = serialize_cloud_document_telemetry(cloud_document_telemetry)
    manifest = {"manifest_schema_version": "1.0", "created_at": completed_at.isoformat(), "source": {"path": str(source.path), "media_type": source.media_type, "size_bytes": source.size_bytes, "sha256": source.sha256, "modified_at": source.modified_at.isoformat()}, "conversion": conversion, "artifacts": artifacts, "quality": build_quality_section(warning_list)}
    if rag_indexing is not None:
        manifest["rag_indexing"] = rag_indexing
    if rag_readiness is not None:
        manifest["rag_readiness"] = rag_readiness
    return manifest


__all__ = ["build_manifest"]
