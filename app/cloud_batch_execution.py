"""Temporäre PDF-Batches, lokale Einzelvalidierung und deterministische Zusammenführung."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import re

from pypdf import PdfReader, PdfWriter

from app.artifact_writer import write_text_artifact
from app.asset_reference_validation import AssetReferenceValidationError, validate_cloud_model_has_no_image_references
from app.cloud_document_config import CloudDocumentConfig
from app.cloud_document_prompt import build_batch_cloud_markdown_instructions
from app.cloud_document_telemetry import CloudCostEvidence, CloudDocumentTelemetry, serialize_cloud_document_telemetry
from app.cloud_content_completeness import CloudContentCompletenessError, verify_cloud_content_completeness
from app.cloud_markdown_validation import CloudMarkdownValidationError, ValidatedCloudMarkdown, validate_cloud_markdown_response
from app.math_batch_planning import CloudBatch, CloudBatchPlan
from app.openai_cloud_document import request_document_response, retrieve_document_response
from app.cloud_run_state import CloudBatchRunEntry, load_matching_cloud_batch_run_state, write_cloud_batch_run_state
from app.models import SourceDocument
from app.progress import ProgressCallback


_PAGE_MARKER = re.compile(r"(?m)^<!-- doctomd:page=([1-9][0-9]*) -->$")


class CloudBatchExecutionError(ValueError):
    """Ein temporärer Batch stimmt nicht sicher mit der Primärquelle überein."""


@dataclass(frozen=True, slots=True)
class CloudBatchExecution:
    """Nur im laufenden Prozess verfügbare Ergebnisse vollständig geprüfter Batches."""

    markdown: str
    telemetry: tuple[CloudDocumentTelemetry, ...]


def execute_cloud_batches(*, source_path: Path, source: SourceDocument, state_path: Path, local_markdown_sha256: str, prompt_version: str, plan: CloudBatchPlan, config: CloudDocumentConfig, local_markdown: str | None = None, progress: ProgressCallback | None = None) -> CloudBatchExecution:
    """Erzeugt kurzlebige Teil-PDFs und vereinigt ausschließlich gültige Antworten."""
    source_file = source_path.expanduser().resolve(strict=True)
    reader = PdfReader(source_file)
    expected_pages = tuple(page for batch in plan.batches for page in batch.page_numbers)
    if expected_pages != tuple(range(1, len(reader.pages) + 1)):
        raise CloudBatchExecutionError("Der Batchplan deckt nicht exakt alle Seiten der Primärquelle ab.")
    plan_contract = tuple((batch.batch_id, batch.page_numbers) for batch in plan.batches)
    state = load_matching_cloud_batch_run_state(
        path=state_path,
        source=source,
        local_markdown_sha256=local_markdown_sha256,
        model_id=config.model_id or "",
        prompt_version=prompt_version,
        plan=plan_contract,
    )
    entries = list(state.entries) if state is not None else [
        CloudBatchRunEntry(batch.batch_id, batch.page_numbers) for batch in plan.batches
    ]
    _write_state(
        path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
        model_id=config.model_id or "", prompt_version=prompt_version,
        plan=plan_contract, entries=entries,
    )
    results: list[tuple[CloudBatch, ValidatedCloudMarkdown]] = []
    telemetry: list[CloudDocumentTelemetry] = []
    with tempfile.TemporaryDirectory(prefix="doctomd-cloud-batches-") as directory:
        temporary_root = Path(directory)
        for index, batch in enumerate(plan.batches):
            entry = entries[index]
            if entry.markdown is not None:
                validated = validate_cloud_markdown_response(
                    response={"status": "completed", "output_text": entry.markdown},
                    expected_page_numbers=batch.page_numbers,
                )
                try:
                    validate_cloud_model_has_no_image_references(markdown=validated.content)
                except AssetReferenceValidationError:
                    entries[index] = replace(entry, response_id=None, markdown=None, telemetry=None)
                    _write_state(
                        path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
                        model_id=config.model_id or "", prompt_version=prompt_version,
                        plan=plan_contract, entries=entries,
                    )
                    _progress(progress, "cloud", "batch_image_reference_retry", f"Cloud-Batch {batch.batch_id} wird wegen einer nicht autorisierten Bildreferenz erneut angefragt.")
                    entry = entries[index]
                else:
                    if local_markdown is None:
                        results.append((batch, validated))
                        telemetry.append(_telemetry_from_state(entry.telemetry))
                        _progress(progress, "cloud", "batch_reused", f"Cloud-Batch {batch.batch_id} wird lokal wiederverwendet.")
                        continue
                    try:
                        _verify_batch_content(local_markdown=local_markdown, batch=batch, cloud_markdown=validated.content)
                    except CloudContentCompletenessError:
                        entries[index] = replace(entry, response_id=None, markdown=None, telemetry=None)
                        _write_state(
                            path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
                            model_id=config.model_id or "", prompt_version=prompt_version,
                            plan=plan_contract, entries=entries,
                        )
                        _progress(progress, "cloud", "batch_content_retry", f"Cloud-Batch {batch.batch_id} wird wegen unvollständigem Inhalt erneut angefragt.")
                        entry = entries[index]
                    else:
                        results.append((batch, validated))
                        telemetry.append(_telemetry_from_state(entry.telemetry))
                        _progress(progress, "cloud", "batch_reused", f"Cloud-Batch {batch.batch_id} wird lokal wiederverwendet.")
                        continue
            if entry.response_id is not None:
                _progress(progress, "cloud", "batch_resuming", f"Cloud-Batch {batch.batch_id} wird ohne Neu-Upload fortgesetzt.")
                response = retrieve_document_response(
                    response_id=entry.response_id,
                    timeout_seconds=config.timeout_seconds,
                    on_status=lambda status, batch_id=batch.batch_id: _progress(progress, "cloud", status, f"Cloud-Batch {batch_id}: {status}."),
                )
            else:
                batch_path = temporary_root / f"{batch.batch_id}.pdf"
                _write_batch_pdf(reader=reader, batch=batch, target_path=batch_path)
                _progress(progress, "cloud", "batch_starting", f"Cloud-Batch {batch.batch_id} wird gestartet.")
                response = request_document_response(
                    source_path=batch_path,
                    model_id=config.model_id or "",
                    timeout_seconds=config.timeout_seconds,
                    max_output_tokens=config.max_output_tokens,
                    instructions=build_batch_cloud_markdown_instructions(page_numbers=batch.page_numbers),
                    on_response_started=lambda response_id, index=index: _record_pending_response(
                        entries=entries, index=index, response_id=response_id, path=state_path, source=source,
                        local_markdown_sha256=local_markdown_sha256, model_id=config.model_id or "",
                        prompt_version=prompt_version, plan=plan_contract,
                    ),
                    on_status=lambda status, batch_id=batch.batch_id: _progress(progress, "cloud", status, f"Cloud-Batch {batch_id}: {status}."),
                )
            try:
                validated = validate_cloud_markdown_response(
                    response=response.payload,
                    expected_page_numbers=batch.page_numbers,
                )
            except CloudMarkdownValidationError as error:
                # Eine abgeschlossene, aber vertragswidrige Antwort darf beim
                # nächsten ausdrücklich gestarteten Lauf nicht erneut blockieren.
                if error.code in {"CLOUD_MARKDOWN_FIRST_PAGE", "CLOUD_MARKDOWN_PAGE_COUNT", "CLOUD_MARKDOWN_PAGE_MARKERS"}:
                    entries[index] = replace(entries[index], response_id=None)
                    _write_state(
                        path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
                        model_id=config.model_id or "", prompt_version=prompt_version,
                        plan=plan_contract, entries=entries,
                    )
                raise
            try:
                validate_cloud_model_has_no_image_references(markdown=validated.content)
            except AssetReferenceValidationError as error:
                entries[index] = replace(entries[index], response_id=None, markdown=None, telemetry=None)
                _write_state(
                    path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
                    model_id=config.model_id or "", prompt_version=prompt_version,
                    plan=plan_contract, entries=entries,
                )
                raise CloudMarkdownValidationError(error.code, f"Cloud-Batch {batch.batch_id}: {error}") from error
            if local_markdown is not None:
                try:
                    _verify_batch_content(local_markdown=local_markdown, batch=batch, cloud_markdown=validated.content)
                except CloudContentCompletenessError as error:
                    _write_rejected_batch_artifacts(
                        state_path=state_path, source=source, batch=batch,
                        cloud_markdown=validated.content, error=error, telemetry=response.telemetry,
                    )
                    entries[index] = replace(entries[index], response_id=None, markdown=None, telemetry=None)
                    _write_state(
                        path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
                        model_id=config.model_id or "", prompt_version=prompt_version,
                        plan=plan_contract, entries=entries,
                    )
                    raise CloudMarkdownValidationError(
                        "CLOUD_MARKDOWN_CONTENT_INCOMPLETE",
                        f"Cloud-Batch {batch.batch_id} ist im Vergleich zur lokalen Basis zu dünn: {error}",
                    ) from error
            entries[index] = replace(
                entries[index], response_id=response.telemetry.response_id,
                markdown=validated.content,
                telemetry=serialize_cloud_document_telemetry(response.telemetry),
            )
            _write_state(
                path=state_path, source=source, local_markdown_sha256=local_markdown_sha256,
                model_id=config.model_id or "", prompt_version=prompt_version,
                plan=plan_contract, entries=entries,
            )
            results.append((batch, validated))
            telemetry.append(response.telemetry)
    return CloudBatchExecution(_merge_batches(plan=plan, results=results), tuple(telemetry))


def _write_batch_pdf(*, reader: PdfReader, batch: CloudBatch, target_path: Path) -> None:
    writer = PdfWriter()
    for page_number in batch.page_numbers:
        writer.add_page(reader.pages[page_number - 1])
    with target_path.open("wb") as file:
        writer.write(file)
    if len(PdfReader(target_path).pages) != len(batch.page_numbers):
        raise CloudBatchExecutionError(f"Temporärer Batch {batch.batch_id} enthält nicht die erwartete Seitenzahl.")


def _merge_batches(*, plan: CloudBatchPlan, results: list[tuple[CloudBatch, ValidatedCloudMarkdown]]) -> str:
    if tuple(batch.batch_id for batch, _ in results) != tuple(batch.batch_id for batch in plan.batches):
        raise CloudBatchExecutionError("Cloud-Batches können nicht deterministisch zusammengeführt werden.")
    return "\n\n".join(markdown.content.strip() for _, markdown in results) + "\n"


def _verify_batch_content(*, local_markdown: str, batch: CloudBatch, cloud_markdown: str) -> None:
    verify_cloud_content_completeness(
        local_markdown=_select_pages(markdown=local_markdown, page_numbers=batch.page_numbers),
        cloud_markdown=cloud_markdown,
    )


def _select_pages(*, markdown: str, page_numbers: tuple[int, ...]) -> str:
    markers = tuple(_PAGE_MARKER.finditer(markdown))
    pages: list[str] = []
    for index, marker in enumerate(markers):
        if int(marker.group(1)) in page_numbers:
            end = markers[index + 1].start() if index + 1 < len(markers) else len(markdown)
            pages.append(markdown[marker.start():end].strip())
    if len(pages) != len(page_numbers):
        raise CloudBatchExecutionError("Die lokale Basis enthält nicht alle Seiten eines Cloud-Batches.")
    return "\n\n".join(pages) + "\n"


def _write_rejected_batch_artifacts(*, state_path: Path, source: SourceDocument, batch: CloudBatch, cloud_markdown: str, error: CloudContentCompletenessError, telemetry: CloudDocumentTelemetry) -> None:
    """Bewahrt eine verworfene, marker-gültige Antwort nur für die Diagnose."""
    base_name = state_path.name.removesuffix(".cloud-run.json")
    response_digest = hashlib.sha256(telemetry.response_id.encode("utf-8")).hexdigest()[:12]
    prefix = state_path.parent / f"{base_name}.{batch.batch_id}.rejected-{response_digest}"
    write_text_artifact(source_path=source.path, target_path=Path(f"{prefix}.md"), content=cloud_markdown, overwrite=True)
    record = {
        "schema_version": "1.0",
        "kind": "cloud_batch_content_rejection",
        "batch_id": batch.batch_id,
        "page_numbers": list(batch.page_numbers),
        "reason_code": "CLOUD_MARKDOWN_CONTENT_INCOMPLETE",
        "reason": str(error),
        "response_id": telemetry.response_id,
        "telemetry": serialize_cloud_document_telemetry(telemetry),
    }
    write_text_artifact(
        source_path=source.path,
        target_path=Path(f"{prefix}.json"),
        content=json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        overwrite=True,
    )


def _record_pending_response(*, entries: list[CloudBatchRunEntry], index: int, response_id: str, path: Path, source: SourceDocument, local_markdown_sha256: str, model_id: str, prompt_version: str, plan: tuple[tuple[str, tuple[int, ...]], ...]) -> None:
    entries[index] = replace(entries[index], response_id=response_id)
    _write_state(path=path, source=source, local_markdown_sha256=local_markdown_sha256, model_id=model_id, prompt_version=prompt_version, plan=plan, entries=entries)


def _write_state(*, path: Path, source: SourceDocument, local_markdown_sha256: str, model_id: str, prompt_version: str, plan: tuple[tuple[str, tuple[int, ...]], ...], entries: list[CloudBatchRunEntry]) -> None:
    write_cloud_batch_run_state(
        path=path, source=source, local_markdown_sha256=local_markdown_sha256,
        model_id=model_id, prompt_version=prompt_version, plan=plan, entries=tuple(entries),
    )


def _telemetry_from_state(value: dict[str, object] | None) -> CloudDocumentTelemetry:
    if value is None:
        raise CloudBatchExecutionError("Ein gespeicherter erfolgreicher Batch enthält keine Telemetrie.")
    try:
        cost_payload = value.get("cost")
        cost = None if cost_payload is None else CloudCostEvidence(
            Decimal(cost_payload["amount_usd"]), cost_payload["source_url"], datetime.fromisoformat(cost_payload["retrieved_at"]),
        )
        return CloudDocumentTelemetry(
            response_id=value["response_id"], model_id=value["model_id"],
            input_tokens=value["input_tokens"], output_tokens=value["output_tokens"], total_tokens=value["total_tokens"],
            started_at=datetime.fromisoformat(value["started_at"]), completed_at=datetime.fromisoformat(value["completed_at"]),
            duration_ms=value["duration_ms"], cost=cost,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CloudBatchExecutionError("Die gespeicherte Batch-Telemetrie ist ungültig.") from error


def _progress(callback: ProgressCallback | None, phase: str, status: str, message: str) -> None:
    if callback is not None:
        callback(phase, status, message)


__all__ = ["CloudBatchExecution", "CloudBatchExecutionError", "execute_cloud_batches"]
