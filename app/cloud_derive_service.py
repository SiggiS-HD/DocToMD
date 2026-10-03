"""Explizite Cloud-Ableitung aus einer bereits geprüften lokalen Basis."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.artifact_paths import plan_artifact_paths
from app.asset_reference_validation import AssetReferenceValidationError, validate_cloud_model_has_no_image_references, validate_markdown_image_references
from app.artifact_writer import write_cloud_markdown_derivative, write_conversion_manifest
from app.cloud_document_config import CloudDocumentConfig
from app.cloud_document_telemetry import serialize_cloud_document_telemetry
from app.cloud_document_prompt import build_cloud_markdown_instructions
from app.cloud_document_prompt import CLOUD_DOCUMENT_PROMPT_VERSION
from app.cloud_batch_execution import execute_cloud_batches
from app.cloud_content_completeness import CloudContentCompletenessError, verify_cloud_content_completeness
from app.cloud_run_state import load_matching_cloud_run_state, write_cloud_run_state
from app.cloud_markdown_validation import CloudMarkdownValidationError, validate_cloud_markdown_response
from app.cloud_review import inject_cloud_assets, inject_cloud_native_pdf_links, inject_cloud_review_warnings
from app.conversion_review_service import write_conversion_review
from app.local_reuse_context import LocalReuseContext, rehydrate_local_reuse_context
from app.math_batch_planning import plan_math_cloud_batches
from app.markdown_provenance import add_provenance_block
from app.models import ConversionResult, ConversionStatus
from app.native_pdf_link_coverage import NativePdfLinkCoverageError, verify_native_pdf_link_coverage
from app.openai_cloud_document import request_document_response, retrieve_document_response
from app.progress import ProgressCallback
from app.rag_indexing import recommend_markdown_for_rag
from app.rag_readiness import assess_rag_readiness


@dataclass(frozen=True, slots=True)
class CloudDeriveRun:
    result: ConversionResult
    manifest: dict
    cloud_markdown_path: PurePosixPath
    reused: bool = False
    vision_pages: tuple[int, ...] = ()
    reused_local_context: bool = True


def can_reuse_local_context(*, input_path: Path, output_dir: Path) -> bool:
    """Prüft nur lesend, ob der automatische Wechsel sicher möglich ist."""
    paths = plan_artifact_paths(source_path=input_path, output_dir=output_dir)
    try:
        rehydrate_local_reuse_context(source_path=input_path, manifest_path=paths.manifest_path)
    except (OSError, ValueError):
        return False
    return True


def derive_cloud(*, input_path: Path, output_dir: Path, on_conflict: str, config: CloudDocumentConfig, progress: ProgressCallback | None = None) -> CloudDeriveRun:
    """Erzeugt ein Cloud-Derivat ohne erneute lokale PDF-Analyse."""
    if on_conflict not in {"error", "overwrite"}:
        raise ValueError("cloud-derive unterstützt nur on-conflict error oder overwrite.")
    resolved_output_dir = output_dir.expanduser().resolve(strict=False)
    paths = plan_artifact_paths(source_path=input_path, output_dir=output_dir)
    context = rehydrate_local_reuse_context(source_path=input_path, manifest_path=paths.manifest_path)
    if paths.cloud_markdown_path.exists() and on_conflict != "overwrite":
        raise ValueError(f"Das Cloud-Derivat existiert bereits: {paths.cloud_markdown_path}")
    _progress(progress, "reuse", "completed", "Geprüfter lokaler Wiederverwendungskontext wird verwendet.")
    context_hash = context.manifest["artifacts"]["local_reuse"]["markdown_sha256"]
    model_id = config.model_id or ""
    batch_plan = plan_math_cloud_batches(markdown=context.markdown)
    cloud_telemetry = None
    if len(batch_plan.batches) > 1:
        _progress(progress, "cloud", "batching", f"{len(batch_plan.batches)} lokale Cloud-Batches werden verarbeitet.")
        execution = execute_cloud_batches(
            source_path=context.source.path,
            source=context.source,
            state_path=paths.cloud_run_state_path,
            local_markdown_sha256=context_hash,
            prompt_version=CLOUD_DOCUMENT_PROMPT_VERSION,
            plan=batch_plan,
            config=config,
            local_markdown=context.markdown,
            progress=progress,
        )
        validated_content = execution.markdown
        cloud_telemetry = execution.telemetry
    else:
        pending = load_matching_cloud_run_state(path=paths.cloud_run_state_path, source=context.source, local_markdown_sha256=context_hash, model_id=model_id, prompt_version=CLOUD_DOCUMENT_PROMPT_VERSION)
        if pending is not None:
            _progress(progress, "cloud", "resuming", "Bestehende Cloud-Anfrage wird ohne Neu-Upload fortgesetzt.")
            response = retrieve_document_response(response_id=pending.response_id, timeout_seconds=config.timeout_seconds, on_status=lambda status: _progress(progress, "cloud", status, f"Cloud-Status: {status}."))
        else:
            _progress(progress, "cloud", "starting", "Cloud-Dokumentanfrage wird aus der lokalen Basis gestartet.")
            response = request_document_response(
                source_path=context.source.path,
                model_id=model_id,
                timeout_seconds=config.timeout_seconds,
                max_output_tokens=config.max_output_tokens,
                instructions=build_cloud_markdown_instructions(),
                on_response_started=lambda response_id: write_cloud_run_state(path=paths.cloud_run_state_path, source=context.source, local_markdown_sha256=context_hash, model_id=model_id, prompt_version=CLOUD_DOCUMENT_PROMPT_VERSION, response_id=response_id),
                on_status=lambda status: _progress(progress, "cloud", status, f"Cloud-Status: {status}."),
            )
        validated_content = validate_cloud_markdown_response(response=response.payload, expected_page_count=len(context.page_numbers)).content
        cloud_telemetry = response.telemetry
    try:
        validate_cloud_model_has_no_image_references(markdown=validated_content)
    except AssetReferenceValidationError as error:
        # Die Response darf bei einem erneut gestarteten Lauf nicht wieder
        # aufgenommen werden, weil sie denselben Bildpfad erneut liefern würde.
        paths.cloud_run_state_path.unlink(missing_ok=True)
        raise CloudMarkdownValidationError(error.code, str(error)) from error
    try:
        verify_cloud_content_completeness(
            local_markdown=context.markdown,
            cloud_markdown=validated_content,
        )
    except CloudContentCompletenessError as error:
        raise CloudMarkdownValidationError(
            "CLOUD_MARKDOWN_CONTENT_INCOMPLETE",
            "Das Cloud-Derivat ist im Vergleich zur lokalen Seitenbasis zu dünn: " + str(error),
        ) from error
    cloud_markdown = inject_cloud_assets(content=validated_content, assets=context.assets)
    cloud_markdown = inject_cloud_native_pdf_links(content=cloud_markdown, links=context.native_pdf_links)
    cloud_markdown = inject_cloud_review_warnings(content=cloud_markdown, warnings=context.warnings)
    cloud_markdown = add_provenance_block(content=cloud_markdown, source=context.source, derivative_kind="cloud")
    try:
        validate_markdown_image_references(
            markdown=cloud_markdown,
            assets=context.assets,
            output_dir=resolved_output_dir,
            error_code="CLOUD_UNAUTHORIZED_IMAGE_REFERENCE",
        )
    except ValueError as error:
        raise CloudMarkdownValidationError("CLOUD_UNAUTHORIZED_IMAGE_REFERENCE", str(error)) from error
    try:
        verify_native_pdf_link_coverage(markdown=cloud_markdown, links=context.native_pdf_links)
    except NativePdfLinkCoverageError as error:
        raise CloudMarkdownValidationError("CLOUD_NATIVE_LINK_COVERAGE", "Das Cloud-Derivat enthält die lokal geprüften nativen PDF-Links nicht vollständig.") from error
    cloud_relative = PurePosixPath(paths.cloud_markdown_path.relative_to(resolved_output_dir).as_posix())
    manifest = _cloud_manifest(context, cloud_relative, cloud_markdown, cloud_telemetry)
    write_cloud_markdown_derivative(source_path=context.source.path, cloud_markdown_path=paths.cloud_markdown_path, content=cloud_markdown, overwrite=on_conflict == "overwrite")
    write_conversion_manifest(source_path=context.source.path, manifest_path=paths.manifest_path, manifest=manifest, overwrite=True)
    write_conversion_review(input_path=context.source.path, output_dir=resolved_output_dir, overwrite=True)
    paths.cloud_run_state_path.unlink(missing_ok=True)
    _progress(progress, "complete", "completed", "Cloud-Derivat wurde aus der lokalen Basis erstellt.")
    return CloudDeriveRun(
        ConversionResult(context.source, ConversionStatus(context.manifest["conversion"]["status"]), "markdown", PurePosixPath(context.manifest["artifacts"]["markdown_path"]), PurePosixPath(paths.manifest_path.relative_to(resolved_output_dir).as_posix()), context.assets, context.warnings),
        manifest, cloud_relative,
    )


def _cloud_manifest(context: LocalReuseContext, cloud_path: PurePosixPath, cloud_markdown: str, telemetry: object | None) -> dict:
    manifest = deepcopy(context.manifest)
    artifacts = manifest["artifacts"]
    artifacts["cloud_markdown_path"] = cloud_path.as_posix()
    if telemetry is not None:
        if isinstance(telemetry, tuple):
            manifest["conversion"]["cloud_document"] = {
                "schema_version": "1.0",
                "mode": "batched",
                "batches": [serialize_cloud_document_telemetry(item) for item in telemetry],
            }
        else:
            manifest["conversion"]["cloud_document"] = serialize_cloud_document_telemetry(telemetry)
    else:
        manifest["conversion"].pop("cloud_document", None)
    local_path = PurePosixPath(artifacts["markdown_path"])
    rag_indexing = recommend_markdown_for_rag(markdown_path=local_path, markdown=context.markdown, cloud_markdown_path=cloud_path, cloud_markdown=cloud_markdown)
    manifest["rag_indexing"] = rag_indexing
    manifest["rag_readiness"] = assess_rag_readiness(warnings=context.warnings, rag_indexing=rag_indexing)
    return manifest


def _progress(callback: ProgressCallback | None, phase: str, status: str, message: str) -> None:
    if callback is not None:
        callback(phase, status, message)


__all__ = ["CloudDeriveRun", "can_reuse_local_context", "derive_cloud"]
