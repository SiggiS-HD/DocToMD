"""Orchestrierung der textbasierten PDF-zu-Markdown-Konvertierung."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath

from app.artifact_paths import plan_artifact_paths
from app.asset_reference_validation import AssetReferenceValidationError, validate_cloud_model_has_no_image_references, validate_markdown_image_references
from app.artifact_writer import write_cloud_markdown_derivative, write_conversion_documents, write_conversion_manifest, write_text_artifact
from app.block_builder import build_page_blocks
from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_run_state import write_cloud_run_state
from app.cloud_document_prompt import CLOUD_DOCUMENT_PROMPT_VERSION, build_cloud_markdown_instructions
from app.cloud_content_completeness import CloudContentCompletenessError, verify_cloud_content_completeness
from app.cloud_markdown_validation import CloudMarkdownValidationError, validate_cloud_markdown_response
from app.cloud_review import inject_cloud_assets, inject_cloud_native_pdf_links, inject_cloud_review_warnings
from app.conversion_review_service import write_conversion_review
from app.conflict_policy import ConflictAction, resolve_conflict
from app.formula_parser import render_formula_blocks_with_warnings
from app.image_export import export_embedded_images
from app.vector_figure_detection import detect_vector_figures
from app.vector_figure_export import export_vector_figures
from app.manifest import build_manifest
from app.markdown_writer import render_document
from app.markdown_provenance import add_provenance_block
from app.native_pdf_links import extract_native_pdf_links
from app.native_pdf_link_coverage import NativePdfLinkCoverageError, verify_native_pdf_link_coverage
from app.models import BlockKind, ConversionResult, ConversionStatus, ConversionWarning, PageReference
from app.path_validation import validate_conversion_paths
from app.pdf_extract import extract_pdf_pages
from app.ocr_extract import apply_ocr_fallback
from app.reference_analysis import analyze_references
from app.rag_indexing import recommend_markdown_for_rag
from app.rag_readiness import assess_rag_readiness
from app.openai_cloud_document import request_document_response
from app.progress import ProgressCallback
from app.source_fingerprint import fingerprint_source
from app.text_normalization import normalize_blocks
from app.table_extract import extract_simple_tables
from app.vision_config import VisionConfig
from app.vision_planner import plan_vision_pages
from app.vision_service import execute_vision_proposals
from app.vision_merge import merge_validated_proposals
from app.vision_review import render_vision_review


@dataclass(frozen=True, slots=True)
class ConversionRun:
    result: ConversionResult
    manifest: dict
    reused: bool
    vision_pages: tuple[int, ...] = ()
    cloud_markdown_path: PurePosixPath | None = None


def convert_pdf(*, input_path: Path, output_dir: Path, on_conflict: str, ocr_mode: str, ocr_language: str, ocr_pages: str = "all", ocr_min_word_confidence: int = 70, vision_config: VisionConfig = VisionConfig(), cloud_document_config: CloudDocumentConfig = CloudDocumentConfig(), progress: ProgressCallback | None = None) -> ConversionRun:
    """Konvertiert lokal und erzeugt bei explizitem Opt-in ein Cloud-Derivat."""
    _progress(progress, "prepare", "started", "Konvertierung wird vorbereitet.")
    paths = validate_conversion_paths(input_path, output_dir)
    source = fingerprint_source(paths.source_path, media_type="application/pdf")
    targets = plan_artifact_paths(source_path=source.path, output_dir=paths.output_dir)
    resolution = resolve_conflict(mode=on_conflict, source=source, artifact_paths=targets)
    markdown_relative = PurePosixPath(targets.markdown_path.relative_to(paths.output_dir).as_posix())
    manifest_relative = PurePosixPath(targets.manifest_path.relative_to(paths.output_dir).as_posix())
    if resolution.action is ConflictAction.REUSE:
        with targets.manifest_path.open(encoding="utf-8") as file:
            manifest = json.load(file)
        cloud_path = manifest.get("artifacts", {}).get("cloud_markdown_path")
        cloud_relative = PurePosixPath(cloud_path) if isinstance(cloud_path, str) else None
        return ConversionRun(ConversionResult(source, ConversionStatus.SUCCESS, "markdown", markdown_relative, manifest_relative), manifest, True, cloud_markdown_path=cloud_relative)
    started_at = datetime.now(timezone.utc)
    _progress(progress, "extract", "started", "PDF-Text wird extrahiert.")
    pages = extract_pdf_pages(source.path)
    _progress(progress, "extract", "completed", "PDF-Text wurde extrahiert.")
    _progress(progress, "ocr", "started", "OCR-Bedarf wird geprüft.")
    ocr_outcome = apply_ocr_fallback(
        source_path=source.path,
        pages=pages,
        ocr_mode=ocr_mode,
        ocr_language=ocr_language,
        ocr_pages=ocr_pages,
        min_word_confidence=ocr_min_word_confidence,
    )
    pages = ocr_outcome.pages
    _progress(progress, "ocr", "completed", "OCR-Prüfung wurde abgeschlossen.")
    _progress(progress, "assets", "started", "Eingebettete Bilder und Tabellen werden analysiert.")
    native_link_extraction = extract_native_pdf_links(source.path)
    image_export = export_embedded_images(source_path=source.path, asset_directory=targets.assets_dir)
    vector_figures = detect_vector_figures(
        source_path=source.path,
        raster_asset_pages=(asset.page.page_number for asset in image_export.assets),
    )
    vector_assets, vector_export_warnings = export_vector_figures(
        source_path=source.path,
        asset_directory=targets.assets_dir,
        candidates=vector_figures.candidates,
        existing_assets=image_export.assets,
    )
    assets = (*image_export.assets, *vector_assets)
    table_extraction = extract_simple_tables(source.path)
    _progress(progress, "assets", "completed", "Bilder und Tabellen wurden analysiert.")
    _progress(progress, "structure", "started", "Markdown-Struktur und Qualitätsbefunde werden erstellt.")
    blocks = tuple(block for page in pages for block in build_page_blocks(page))
    normalized_blocks, normalization_warnings = normalize_blocks(blocks)
    formula_rendering = render_formula_blocks_with_warnings(normalized_blocks)
    rendered_blocks = formula_rendering.blocks
    reference_analysis = analyze_references(
        blocks=rendered_blocks,
        assets=assets,
        tables=table_extraction.tables,
    )
    warnings = (
        *native_link_extraction.warnings,
        *ocr_outcome.warnings,
        *normalization_warnings,
        *_extractability_warnings(pages),
        *_ocr_layout_warnings(pages, rendered_blocks, table_extraction.tables),
        *formula_rendering.warnings,
        *image_export.warnings,
        *(warning for warning in vector_figures.warnings if warning.page is None or warning.page.page_number not in {asset.page.page_number for asset in vector_assets} or warning.page.page_number in vector_figures.unresolved_page_numbers),
        *vector_export_warnings,
        *table_extraction.warnings,
        *reference_analysis.warnings,
    )
    vision_plan = plan_vision_pages(config=vision_config, pages=pages, warnings=warnings)
    schema_path = Path(__file__).parent.parent / "schemas" / "vision-proposal-1.0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    proposal_paths, vision_warnings = execute_vision_proposals(source_path=source.path, pages=pages, page_numbers=vision_plan.page_numbers, config=vision_config, proposal_dir=targets.vision_proposals_dir, schema=schema)
    warnings = (*warnings, *vision_warnings)
    markdown = render_document(
        pages,
        rendered_blocks,
        assets,
        table_extraction.tables,
        native_link_extraction.links,
    )
    markdown = add_provenance_block(content=markdown, source=source, derivative_kind="local")
    validate_markdown_image_references(
        markdown=markdown,
        assets=assets,
        output_dir=paths.output_dir,
        error_code="LOCAL_UNAUTHORIZED_IMAGE_REFERENCE",
    )
    verify_native_pdf_link_coverage(
        markdown=markdown,
        links=native_link_extraction.links,
    )
    proposals = tuple(json.loads(path.read_text(encoding="utf-8")) for path in proposal_paths)
    vision_markdown = merge_validated_proposals(local_markdown=markdown, proposals=proposals) if proposals else None
    vision_review = render_vision_review(selected_pages=vision_plan.page_numbers, proposal_paths=tuple(PurePosixPath(path.relative_to(paths.output_dir).as_posix()) for path in proposal_paths), warnings=vision_warnings) if vision_plan.page_numbers else None
    _progress(progress, "structure", "completed", "Markdown-Struktur wurde erstellt.")
    status = ConversionStatus.PARTIAL if warnings else ConversionStatus.SUCCESS
    local_completed_at = datetime.now(timezone.utc)
    local_rag_indexing = recommend_markdown_for_rag(markdown_path=markdown_relative, markdown=markdown)
    local_rag_readiness = assess_rag_readiness(warnings=warnings, rag_indexing=local_rag_indexing)
    base_manifest = build_manifest(source=source, status=status, markdown_path=markdown_relative, markdown_content=markdown, blocks=rendered_blocks, assets=assets, tables=table_extraction.tables, native_pdf_links=native_link_extraction.links, references=reference_analysis.references, vision_proposals=tuple(PurePosixPath(path.relative_to(paths.output_dir).as_posix()) for path in proposal_paths), vision_markdown_path=PurePosixPath(targets.vision_markdown_path.relative_to(paths.output_dir).as_posix()) if vision_markdown is not None else None, vision_review_path=PurePosixPath(targets.vision_review_path.relative_to(paths.output_dir).as_posix()) if vision_review is not None else None, rag_indexing=local_rag_indexing, rag_readiness=local_rag_readiness, ocr_outcome=ocr_outcome, ocr_pages=ocr_pages, ocr_min_word_confidence=ocr_min_word_confidence, warnings=warnings, started_at=started_at, completed_at=local_completed_at, ocr_mode=ocr_mode, ocr_language=ocr_language)
    if vision_markdown is not None:
        vision_markdown = add_provenance_block(content=vision_markdown, source=source, derivative_kind="vision")
        write_text_artifact(source_path=source.path, target_path=targets.vision_markdown_path, content=vision_markdown, overwrite=resolution.overwrite)
    if vision_review is not None:
        write_text_artifact(source_path=source.path, target_path=targets.vision_review_path, content=vision_review, overwrite=resolution.overwrite)
    _progress(progress, "write", "started", "Lokales Markdown und Basismanifest werden veröffentlicht.")
    write_conversion_documents(source_path=source.path, markdown_path=targets.markdown_path, markdown_content=markdown, manifest_path=targets.manifest_path, manifest=base_manifest, overwrite=resolution.overwrite)
    write_conversion_review(input_path=source.path, output_dir=paths.output_dir, overwrite=True)
    _progress(progress, "write", "completed", "Lokales Markdown und Basismanifest wurden veröffentlicht.")
    cloud_markdown = None
    cloud_telemetry = None
    cloud_relative = None
    manifest = base_manifest
    if cloud_document_config.mode is CloudDocumentMode.OPENAI:
        _progress(progress, "cloud", "starting", "Cloud-Dokumentanfrage wird gestartet.")
        cloud_response = request_document_response(
            source_path=source.path,
            model_id=cloud_document_config.model_id or "",
            timeout_seconds=cloud_document_config.timeout_seconds,
            max_output_tokens=cloud_document_config.max_output_tokens,
            instructions=build_cloud_markdown_instructions(),
            on_response_started=lambda response_id: write_cloud_run_state(
                path=targets.cloud_run_state_path,
                source=source,
                local_markdown_sha256=base_manifest["artifacts"]["local_reuse"]["markdown_sha256"],
                model_id=cloud_document_config.model_id or "",
                prompt_version=CLOUD_DOCUMENT_PROMPT_VERSION,
                response_id=response_id,
            ),
            on_status=lambda status: _progress(progress, "cloud", status, _cloud_message(status)),
        )
        validated_cloud_markdown = validate_cloud_markdown_response(
            response=cloud_response.payload,
            expected_page_count=len(pages),
        )
        try:
            validate_cloud_model_has_no_image_references(markdown=validated_cloud_markdown.content)
        except AssetReferenceValidationError as error:
            raise CloudMarkdownValidationError(error.code, str(error)) from error
        try:
            verify_cloud_content_completeness(
                local_markdown=markdown,
                cloud_markdown=validated_cloud_markdown.content,
            )
        except CloudContentCompletenessError as error:
            raise CloudMarkdownValidationError(
                "CLOUD_MARKDOWN_CONTENT_INCOMPLETE",
                "Das Cloud-Derivat ist im Vergleich zur lokalen Seitenbasis zu dünn: " + str(error),
            ) from error
        cloud_markdown = inject_cloud_assets(
            content=validated_cloud_markdown.content,
            assets=assets,
            skip_page_numbers=frozenset(
                page.page_number for page in pages if page.layout_html is not None
            ),
        )
        cloud_markdown = inject_cloud_native_pdf_links(
            content=cloud_markdown,
            links=native_link_extraction.links,
        )
        cloud_markdown = inject_cloud_review_warnings(
            content=cloud_markdown,
            warnings=warnings,
        )
        cloud_markdown = add_provenance_block(content=cloud_markdown, source=source, derivative_kind="cloud")
        try:
            validate_markdown_image_references(
                markdown=cloud_markdown,
                assets=assets,
                output_dir=paths.output_dir,
                error_code="CLOUD_UNAUTHORIZED_IMAGE_REFERENCE",
            )
        except ValueError as error:
            raise CloudMarkdownValidationError("CLOUD_UNAUTHORIZED_IMAGE_REFERENCE", str(error)) from error
        try:
            verify_native_pdf_link_coverage(
                markdown=cloud_markdown,
                links=native_link_extraction.links,
            )
        except NativePdfLinkCoverageError as error:
            raise CloudMarkdownValidationError(
                "CLOUD_NATIVE_LINK_COVERAGE",
                "Das Cloud-Derivat enthält die lokal geprüften nativen PDF-Links nicht vollständig.",
            ) from error
        cloud_telemetry = cloud_response.telemetry
        cloud_relative = PurePosixPath(targets.cloud_markdown_path.relative_to(paths.output_dir).as_posix())
        rag_indexing = recommend_markdown_for_rag(markdown_path=markdown_relative, markdown=markdown, cloud_markdown_path=cloud_relative, cloud_markdown=cloud_markdown)
        rag_readiness = assess_rag_readiness(warnings=warnings, rag_indexing=rag_indexing)
        manifest = build_manifest(source=source, status=status, markdown_path=markdown_relative, markdown_content=markdown, blocks=rendered_blocks, assets=assets, tables=table_extraction.tables, native_pdf_links=native_link_extraction.links, references=reference_analysis.references, vision_proposals=tuple(PurePosixPath(path.relative_to(paths.output_dir).as_posix()) for path in proposal_paths), vision_markdown_path=PurePosixPath(targets.vision_markdown_path.relative_to(paths.output_dir).as_posix()) if vision_markdown is not None else None, vision_review_path=PurePosixPath(targets.vision_review_path.relative_to(paths.output_dir).as_posix()) if vision_review is not None else None, cloud_markdown_path=cloud_relative, cloud_document_telemetry=cloud_telemetry, rag_indexing=rag_indexing, rag_readiness=rag_readiness, ocr_outcome=ocr_outcome, ocr_pages=ocr_pages, ocr_min_word_confidence=ocr_min_word_confidence, warnings=warnings, started_at=started_at, completed_at=datetime.now(timezone.utc), ocr_mode=ocr_mode, ocr_language=ocr_language)
        write_cloud_markdown_derivative(source_path=source.path, cloud_markdown_path=targets.cloud_markdown_path, content=cloud_markdown, overwrite=resolution.overwrite)
        write_conversion_manifest(source_path=source.path, manifest_path=targets.manifest_path, manifest=manifest, overwrite=True)
        write_conversion_review(input_path=source.path, output_dir=paths.output_dir, overwrite=True)
        targets.cloud_run_state_path.unlink(missing_ok=True)
    _progress(progress, "complete", "completed", "Konvertierung wurde abgeschlossen.")
    return ConversionRun(ConversionResult(source, status, "markdown", markdown_relative, manifest_relative, assets=assets, warnings=warnings), manifest, False, vision_plan.page_numbers, cloud_relative)


def serialize_run(run: ConversionRun) -> dict:
    result = {"conversion_status": run.result.status.value, "markdown_path": run.result.markdown_path.as_posix() if run.result.markdown_path else None, "manifest_path": run.result.manifest_path.as_posix() if run.result.manifest_path else None, "cloud_markdown_path": run.cloud_markdown_path.as_posix() if run.cloud_markdown_path else None, "reused": run.reused, "vision_pages": list(run.vision_pages)}
    cloud_document = run.manifest.get("conversion", {}).get("cloud_document")
    if isinstance(cloud_document, dict):
        result["cloud_document"] = cloud_document
    rag_indexing = run.manifest.get("rag_indexing")
    if isinstance(rag_indexing, dict):
        result["rag_indexing"] = rag_indexing
    rag_readiness = run.manifest.get("rag_readiness")
    if isinstance(rag_readiness, dict):
        result["rag_readiness"] = rag_readiness
    return result


def _extractability_warnings(pages: tuple) -> tuple[ConversionWarning, ...]:
    """Kennzeichnet Layout- und Zeichenkodierungsgrenzen der digitalen Extraktion."""
    warnings: list[ConversionWarning] = []
    for page in pages:
        reference = PageReference(page.page_number)
        if page.column_count > 1:
            warnings.append(ConversionWarning(
                code="MULTI_COLUMN_LAYOUT",
                message="Mehrspaltiges Layout kann Lesereihenfolge und Absatzgrenzen beeinträchtigen.",
                page=reference,
            ))
        if "(cid:" in page.text:
            warnings.append(ConversionWarning(
                code="UNREADABLE_PDF_GLYPHS",
                message="Nicht dekodierbare PDF-Zeichen wurden unverändert beibehalten.",
                page=reference,
            ))
        if page.formula_candidate_lines:
            warnings.append(ConversionWarning(
                code="DISPLAY_FORMULA_LAYOUT_NOT_RECONSTRUCTED",
                message=(
                    f"{len(page.formula_candidate_lines)} zentrierte mathematische Ausdrücke "
                    "wurden nicht zuverlässig als LaTeX rekonstruiert."
                ),
                page=reference,
            ))
    return tuple(warnings)


def _ocr_layout_warnings(
    pages: tuple,
    blocks: tuple,
    tables: tuple,
) -> tuple[ConversionWarning, ...]:
    """Kennzeichnet OCR-Layoutblöcke ohne nutzbare semantische Struktur.

    Der festbreite Fallback bewahrt OCR-Zeilen und deren relative Ausrichtung,
    ist aber für Überschriften- und Tabellen-orientiertes Chunking ungeeignet.
    Eine Warnung wird nur gesetzt, wenn die jeweilige Seite weder eine
    semantische Überschrift noch eine überprüfbar übertragene Tabelle enthält.
    """
    heading_pages = {
        block.page.page_number
        for block in blocks
        if block.kind is BlockKind.HEADING
    }
    table_pages = {table.page.page_number for table in tables}
    return tuple(
        ConversionWarning(
            code="OCR_LAYOUT_FALLBACK",
            message=(
                "Die OCR-Seite konnte nur als positionierter Layoutblock ohne "
                "strukturierte Überschrift oder Tabelle übertragen werden."
            ),
            page=PageReference(page.page_number),
        )
        for page in pages
        if page.layout_html is not None
        and page.page_number not in heading_pages
        and page.page_number not in table_pages
    )


def _progress(callback: ProgressCallback | None, phase: str, status: str, message: str) -> None:
    if callback is not None:
        callback(phase, status, message)


def _cloud_message(status: str) -> str:
    return {
        "queued": "Cloud-Dokumentanfrage wartet in der Warteschlange.",
        "in_progress": "Cloud-Dokument wird von OpenAI verarbeitet.",
        "completed": "Cloud-Antwort wurde empfangen und wird geprüft.",
    }.get(status, f"Cloud-Dokumentanfrage: {status}.")


__all__ = ["ConversionRun", "convert_pdf", "serialize_run"]
