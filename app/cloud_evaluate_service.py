"""Getrennte Cloud-Evaluation eines kleinen, geprüften Originalseitenbereichs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import tempfile
from typing import Any

from pypdf import PdfReader, PdfWriter

from app.artifact_paths import plan_artifact_paths
from app.asset_reference_validation import AssetReferenceValidationError, validate_cloud_model_has_no_image_references, validate_markdown_image_references
from app.artifact_writer import write_text_artifact
from app.cloud_content_completeness import CloudContentCompletenessError, verify_cloud_content_completeness
from app.cloud_document_config import CloudDocumentConfig
from app.cloud_document_prompt import CLOUD_DOCUMENT_PROMPT_VERSION, build_batch_cloud_markdown_instructions
from app.cloud_document_telemetry import serialize_cloud_document_telemetry
from app.cloud_markdown_validation import CloudMarkdownValidationError, validate_cloud_markdown_response
from app.cloud_review import inject_cloud_assets, inject_cloud_native_pdf_links, inject_cloud_review_warnings
from app.local_reuse_context import LocalReuseContext, rehydrate_local_reuse_context
from app.native_pdf_link_coverage import NativePdfLinkCoverageError, verify_native_pdf_link_coverage
from app.openai_cloud_document import request_document_response
from app.progress import ProgressCallback


_PAGE_MARKER = re.compile(r"(?m)^<!-- doctomd:page=([1-9][0-9]*) -->$")


class CloudEvaluateError(ValueError):
    """Ein separater Cloud-Seitenbereichstest kann nicht sicher ausgeführt werden."""


def parse_page_range(value: str) -> tuple[int, ...]:
    """Akzeptiert nur eine positive Seite oder einen zusammenhängenden Bereich."""
    match = re.fullmatch(r"([1-9][0-9]*)(?:-([1-9][0-9]*))?", value)
    if match is None:
        raise ValueError("--pages akzeptiert nur eine positive Seite oder einen Bereich wie 9-14.")
    first = int(match.group(1))
    last = int(match.group(2) or first)
    if last < first:
        raise ValueError("--pages muss aufsteigend und zusammenhängend sein.")
    return tuple(range(first, last + 1))


@dataclass(frozen=True, slots=True)
class CloudPageEvaluation:
    """Pfade und Seiten einer erfolgreich geschriebenen Bereichsevaluation."""

    page_numbers: tuple[int, ...]
    local_markdown_path: Path
    cloud_markdown_path: Path
    evaluation_path: Path

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "pages": list(self.page_numbers),
            "local_markdown_path": str(self.local_markdown_path),
            "cloud_markdown_path": str(self.cloud_markdown_path),
            "evaluation_path": str(self.evaluation_path),
        }


def evaluate_cloud_pages(*, input_path: Path, output_dir: Path, page_numbers: tuple[int, ...], config: CloudDocumentConfig, progress: ProgressCallback | None = None) -> dict[str, object]:
    """Evaluiert einen Bereich ohne reguläre Cloud-Artefakte oder Batchzustand anzufassen."""
    _validate_page_numbers(page_numbers)
    paths = plan_artifact_paths(source_path=input_path, output_dir=output_dir)
    context = rehydrate_local_reuse_context(source_path=input_path, manifest_path=paths.manifest_path)
    if page_numbers[-1] > len(context.page_numbers):
        raise CloudEvaluateError("Der angeforderte Seitenbereich liegt außerhalb der geprüften lokalen Basis.")
    names = _evaluation_paths(input_path=input_path, output_dir=output_dir, page_numbers=page_numbers)
    for target in (names.local_markdown_path, names.cloud_markdown_path, names.evaluation_path):
        if target.exists():
            raise CloudEvaluateError(f"Das Evaluierungsartefakt existiert bereits: {target}")

    local_markdown = _select_pages(context.markdown, page_numbers)
    _progress(progress, "reuse", "completed", "Geprüfter lokaler Wiederverwendungskontext wird für den Seitenbereich verwendet.")
    _progress(progress, "cloud", "starting", "Kurzlebige Teil-PDF wird für die Cloud-Evaluation erzeugt.")
    response = _request_subset(context=context, page_numbers=page_numbers, config=config, progress=progress)
    validated = validate_cloud_markdown_response(response=response.payload, expected_page_numbers=page_numbers).content
    try:
        validate_cloud_model_has_no_image_references(markdown=validated)
    except AssetReferenceValidationError as error:
        raise CloudMarkdownValidationError(error.code, str(error)) from error
    try:
        verify_cloud_content_completeness(local_markdown=local_markdown, cloud_markdown=validated)
    except CloudContentCompletenessError as error:
        raise CloudMarkdownValidationError("CLOUD_MARKDOWN_CONTENT_INCOMPLETE", "Die Cloud-Evaluation ist im Vergleich zur lokalen Seitenbasis zu dünn: " + str(error)) from error

    assets = tuple(asset for asset in context.assets if asset.page.page_number in page_numbers)
    warnings = tuple(warning for warning in context.warnings if warning.page is not None and warning.page.page_number in page_numbers)
    links = tuple(link for link in context.native_pdf_links if link.page.page_number in page_numbers)
    cloud_markdown = inject_cloud_assets(content=validated, assets=assets)
    cloud_markdown = inject_cloud_native_pdf_links(content=cloud_markdown, links=links)
    cloud_markdown = inject_cloud_review_warnings(content=cloud_markdown, warnings=warnings)
    try:
        validate_markdown_image_references(
            markdown=cloud_markdown,
            assets=assets,
            output_dir=output_dir,
            error_code="CLOUD_UNAUTHORIZED_IMAGE_REFERENCE",
        )
    except ValueError as error:
        raise CloudMarkdownValidationError("CLOUD_UNAUTHORIZED_IMAGE_REFERENCE", str(error)) from error
    try:
        verify_native_pdf_link_coverage(markdown=cloud_markdown, links=links)
    except NativePdfLinkCoverageError as error:
        raise CloudMarkdownValidationError("CLOUD_NATIVE_LINK_COVERAGE", "Die Cloud-Evaluation enthält die lokalen Native-PDF-Links nicht vollständig.") from error

    write_text_artifact(source_path=context.source.path, target_path=names.local_markdown_path, content=local_markdown)
    write_text_artifact(source_path=context.source.path, target_path=names.cloud_markdown_path, content=cloud_markdown)
    record = _evaluation_record(context=context, evaluation=names, config=config, telemetry=response.telemetry, assets=assets, warnings=warnings, links=links)
    write_text_artifact(source_path=context.source.path, target_path=names.evaluation_path, content=json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _progress(progress, "complete", "completed", "Getrennte Cloud-Seitenbereichsevaluation wurde geschrieben.")
    return names.to_contract_dict()


def _request_subset(*, context: LocalReuseContext, page_numbers: tuple[int, ...], config: CloudDocumentConfig, progress: ProgressCallback | None):
    with tempfile.TemporaryDirectory(prefix="doctomd-cloud-evaluate-") as directory:
        subset_path = Path(directory) / "evaluation.pdf"
        _write_subset_pdf(source_path=context.source.path, page_numbers=page_numbers, target_path=subset_path)
        return request_document_response(
            source_path=subset_path,
            model_id=config.model_id or "",
            timeout_seconds=config.timeout_seconds,
            max_output_tokens=config.max_output_tokens,
            instructions=build_batch_cloud_markdown_instructions(page_numbers=page_numbers),
            on_response_started=lambda _response_id: None,
            on_status=lambda status: _progress(progress, "cloud", status, f"Cloud-Evaluation: {status}."),
        )


def _write_subset_pdf(*, source_path: Path, page_numbers: tuple[int, ...], target_path: Path) -> None:
    reader = PdfReader(source_path.expanduser().resolve(strict=True))
    if page_numbers[-1] > len(reader.pages):
        raise CloudEvaluateError("Der angeforderte Seitenbereich liegt außerhalb der PDF-Primärquelle.")
    writer = PdfWriter()
    for page_number in page_numbers:
        writer.add_page(reader.pages[page_number - 1])
    with target_path.open("wb") as file:
        writer.write(file)
    if len(PdfReader(target_path).pages) != len(page_numbers):
        raise CloudEvaluateError("Die kurzlebige Teil-PDF enthält nicht die angeforderten Originalseiten.")


def _evaluation_paths(*, input_path: Path, output_dir: Path, page_numbers: tuple[int, ...]) -> CloudPageEvaluation:
    root = output_dir.expanduser().resolve(strict=False)
    label = f"{page_numbers[0]:03d}" if len(page_numbers) == 1 else f"{page_numbers[0]:03d}-{page_numbers[-1]:03d}"
    base = input_path.expanduser().resolve(strict=False).stem + f".pages-{label}"
    return CloudPageEvaluation(page_numbers, root / f"{base}.local.md", root / f"{base}.cloud.md", root / f"{base}.evaluation.json")


def _select_pages(markdown: str, page_numbers: tuple[int, ...]) -> str:
    markers = tuple(_PAGE_MARKER.finditer(markdown))
    parts: list[str] = []
    for index, marker in enumerate(markers):
        if int(marker.group(1)) in page_numbers:
            end = markers[index + 1].start() if index + 1 < len(markers) else len(markdown)
            parts.append(markdown[marker.start():end].strip())
    selected = "\n\n".join(parts) + "\n"
    if not parts:
        raise CloudEvaluateError("Der angeforderte Seitenbereich enthält keine lokalen Seitenmarker.")
    return selected


def _evaluation_record(*, context: LocalReuseContext, evaluation: CloudPageEvaluation, config: CloudDocumentConfig, telemetry: object, assets: tuple, warnings: tuple, links: tuple) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "cloud_page_evaluation",
        "prompt_version": CLOUD_DOCUMENT_PROMPT_VERSION,
        "source": {
            "path": str(context.source.path), "sha256": context.source.sha256,
            "size_bytes": context.source.size_bytes, "modified_at": context.source.modified_at.isoformat() if context.source.modified_at else None,
        },
        "local_reuse": {"manifest_path": str(context.manifest_path), "markdown_sha256": context.manifest["artifacts"]["local_reuse"]["markdown_sha256"]},
        "pages": list(evaluation.page_numbers),
        "artifacts": evaluation.to_contract_dict(),
        "cloud_document": {"options": config.public_options(), "telemetry": serialize_cloud_document_telemetry(telemetry)},
        "authoritative_local_additions": {"asset_ids": [asset.asset_id for asset in assets], "warning_codes": [warning.code for warning in warnings], "native_pdf_link_count": len(links)},
    }


def _validate_page_numbers(page_numbers: tuple[int, ...]) -> None:
    if not page_numbers or any(not isinstance(page, int) or isinstance(page, bool) or page < 1 for page in page_numbers):
        raise CloudEvaluateError("Der Seitenbereich muss positive ganze Seiten enthalten.")
    if page_numbers != tuple(range(page_numbers[0], page_numbers[-1] + 1)):
        raise CloudEvaluateError("Der Seitenbereich muss zusammenhängend und aufsteigend sein.")


def _progress(callback: ProgressCallback | None, phase: str, status: str, message: str) -> None:
    if callback is not None:
        callback(phase, status, message)


__all__ = ["CloudEvaluateError", "CloudPageEvaluation", "evaluate_cloud_pages", "parse_page_range"]
