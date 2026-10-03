"""Kurzlebiger lokaler Wiederaufnahmezustand für OpenAI-Hintergrundläufe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from app.artifact_writer import write_text_artifact
from app.models import SourceDocument


CLOUD_RUN_STATE_SCHEMA_VERSION = "1.0"
CLOUD_BATCH_RUN_STATE_SCHEMA_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class CloudRunState:
    response_id: str
    source_sha256: str
    local_markdown_sha256: str
    model_id: str
    prompt_version: str
    started_at: datetime


@dataclass(frozen=True, slots=True)
class CloudBatchRunEntry:
    batch_id: str
    page_numbers: tuple[int, ...]
    response_id: str | None = None
    markdown: str | None = None
    telemetry: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class CloudBatchRunState:
    source_sha256: str
    local_markdown_sha256: str
    model_id: str
    prompt_version: str
    plan: tuple[tuple[str, tuple[int, ...]], ...]
    entries: tuple[CloudBatchRunEntry, ...]
    started_at: datetime


def write_cloud_run_state(*, path: Path, source: SourceDocument, local_markdown_sha256: str, model_id: str, prompt_version: str, response_id: str) -> None:
    if not source.sha256:
        raise ValueError("Der Wiederaufnahmezustand benötigt einen Quellhash.")
    if not all(isinstance(value, str) and value for value in (local_markdown_sha256, model_id, prompt_version, response_id)):
        raise ValueError("Der Wiederaufnahmezustand benötigt lokalen Kontext, Modell, Promptvertrag und Response-ID.")
    content = json.dumps({"schema_version": CLOUD_RUN_STATE_SCHEMA_VERSION, "response_id": response_id, "source_sha256": source.sha256, "local_markdown_sha256": local_markdown_sha256, "model_id": model_id, "prompt_version": prompt_version, "started_at": datetime.now().astimezone().isoformat()}, ensure_ascii=False) + "\n"
    write_text_artifact(source_path=source.path, target_path=path, content=content, overwrite=True)


def load_matching_cloud_run_state(*, path: Path, source: SourceDocument, local_markdown_sha256: str, model_id: str, prompt_version: str) -> CloudRunState | None:
    if not path.is_file() or not source.sha256:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        response_id = payload["response_id"]
        source_sha256 = payload["source_sha256"]
        stored_markdown_sha256 = payload["local_markdown_sha256"]
        stored_model_id = payload["model_id"]
        stored_prompt_version = payload["prompt_version"]
        started_at = datetime.fromisoformat(payload["started_at"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != CLOUD_RUN_STATE_SCHEMA_VERSION or not all(isinstance(value, str) and value for value in (response_id, stored_markdown_sha256, stored_model_id, stored_prompt_version)):
        return None
    if (source_sha256, stored_markdown_sha256, stored_model_id, stored_prompt_version) != (source.sha256, local_markdown_sha256, model_id, prompt_version):
        return None
    return CloudRunState(response_id=response_id, source_sha256=source_sha256, local_markdown_sha256=stored_markdown_sha256, model_id=stored_model_id, prompt_version=stored_prompt_version, started_at=started_at)


def write_cloud_batch_run_state(*, path: Path, source: SourceDocument, local_markdown_sha256: str, model_id: str, prompt_version: str, plan: tuple[tuple[str, tuple[int, ...]], ...], entries: tuple[CloudBatchRunEntry, ...]) -> None:
    if not source.sha256 or not all(isinstance(value, str) and value for value in (local_markdown_sha256, model_id, prompt_version)):
        raise ValueError("Der Batch-Wiederaufnahmezustand benötigt Quelle, lokalen Kontext, Modell und Promptvertrag.")
    _validate_batch_state(plan, entries)
    content = json.dumps({
        "schema_version": CLOUD_BATCH_RUN_STATE_SCHEMA_VERSION,
        "source_sha256": source.sha256,
        "local_markdown_sha256": local_markdown_sha256,
        "model_id": model_id,
        "prompt_version": prompt_version,
        "plan": [{"batch_id": batch_id, "page_numbers": list(page_numbers)} for batch_id, page_numbers in plan],
        "entries": [{
            "batch_id": entry.batch_id,
            "page_numbers": list(entry.page_numbers),
            **({"response_id": entry.response_id} if entry.response_id is not None else {}),
            **({"markdown": entry.markdown} if entry.markdown is not None else {}),
            **({"telemetry": entry.telemetry} if entry.telemetry is not None else {}),
        } for entry in entries],
        "started_at": datetime.now().astimezone().isoformat(),
    }, ensure_ascii=False) + "\n"
    write_text_artifact(source_path=source.path, target_path=path, content=content, overwrite=True)


def load_matching_cloud_batch_run_state(*, path: Path, source: SourceDocument, local_markdown_sha256: str, model_id: str, prompt_version: str, plan: tuple[tuple[str, tuple[int, ...]], ...]) -> CloudBatchRunState | None:
    if not path.is_file() or not source.sha256:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored_plan = _parse_plan(payload["plan"])
        entries = _parse_entries(payload["entries"])
        state = CloudBatchRunState(
            source_sha256=payload["source_sha256"],
            local_markdown_sha256=payload["local_markdown_sha256"],
            model_id=payload["model_id"],
            prompt_version=payload["prompt_version"],
            plan=stored_plan,
            entries=entries,
            started_at=datetime.fromisoformat(payload["started_at"]),
        )
        _validate_batch_state(state.plan, state.entries)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != CLOUD_BATCH_RUN_STATE_SCHEMA_VERSION:
        return None
    if (state.source_sha256, state.local_markdown_sha256, state.model_id, state.prompt_version, state.plan) != (source.sha256, local_markdown_sha256, model_id, prompt_version, plan):
        return None
    return state


def _parse_plan(value: object) -> tuple[tuple[str, tuple[int, ...]], ...]:
    if not isinstance(value, list):
        raise ValueError
    result: list[tuple[str, tuple[int, ...]]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError
        result.append((_nonempty_string(item["batch_id"]), _page_numbers(item["page_numbers"])))
    return tuple(result)


def _parse_entries(value: object) -> tuple[CloudBatchRunEntry, ...]:
    if not isinstance(value, list):
        raise ValueError
    result: list[CloudBatchRunEntry] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError
        response_id = item.get("response_id")
        markdown = item.get("markdown")
        telemetry = item.get("telemetry")
        if response_id is not None and not isinstance(response_id, str):
            raise ValueError
        if markdown is not None and not isinstance(markdown, str):
            raise ValueError
        if telemetry is not None and not isinstance(telemetry, dict):
            raise ValueError
        result.append(CloudBatchRunEntry(_nonempty_string(item["batch_id"]), _page_numbers(item["page_numbers"]), response_id, markdown, telemetry))
    return tuple(result)


def _validate_batch_state(plan: tuple[tuple[str, tuple[int, ...]], ...], entries: tuple[CloudBatchRunEntry, ...]) -> None:
    if not plan or len(plan) != len(entries) or tuple(entry.batch_id for entry in entries) != tuple(batch_id for batch_id, _ in plan):
        raise ValueError("Der Batch-Wiederaufnahmezustand enthält keinen passenden Plan.")
    if tuple(entry.page_numbers for entry in entries) != tuple(page_numbers for _, page_numbers in plan):
        raise ValueError("Der Batch-Wiederaufnahmezustand enthält abweichende Seitenbereiche.")
    for entry in entries:
        completed = entry.markdown is not None or entry.telemetry is not None
        if completed and (entry.markdown is None or entry.telemetry is None):
            raise ValueError("Ein erfolgreicher Batch benötigt Markdown und Telemetrie.")
        if entry.response_id is not None and not entry.response_id:
            raise ValueError("Eine Response-ID darf nicht leer sein.")


def _nonempty_string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError
    return value


def _page_numbers(value: object) -> tuple[int, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(page, int) or page < 1 for page in value):
        raise ValueError
    return tuple(value)


__all__ = ["CLOUD_BATCH_RUN_STATE_SCHEMA_VERSION", "CLOUD_RUN_STATE_SCHEMA_VERSION", "CloudBatchRunEntry", "CloudBatchRunState", "CloudRunState", "load_matching_cloud_batch_run_state", "load_matching_cloud_run_state", "write_cloud_batch_run_state", "write_cloud_run_state"]
