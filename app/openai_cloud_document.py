"""Sicherer OpenAI-Transport für eine vollständige PDF als ``input_file``."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from time import perf_counter_ns
from time import monotonic, sleep
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from app.cloud_document_telemetry import CloudDocumentTelemetry, telemetry_from_response

FILES_URL = "https://api.openai.com/v1/files"
RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_FILE_BYTES = 512 * 1024 * 1024
_SENSITIVE_REMOTE_ERROR_VALUE = re.compile(
    r"(?:bearer\s+\S+|sk-[A-Za-z0-9_-]+|file-[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_MAX_REMOTE_ERROR_MESSAGE_LENGTH = 500


class OpenAICloudDocumentError(OSError):
    """Die Cloud-Dokumentanfrage konnte nicht sicher abgeschlossen werden."""

    def __init__(self, message: str, *, code: str = "CLOUD_REQUEST_FAILED") -> None:
        super().__init__(message)
        self.code = code


class CloudDocumentResponse:
    """Vollständige Providerantwort mit manifestfähiger Telemetrie."""

    def __init__(self, payload: dict[str, Any], telemetry: CloudDocumentTelemetry) -> None:
        self.payload = payload
        self.telemetry = telemetry


def request_document_response(
    *,
    source_path: Path,
    model_id: str,
    timeout_seconds: int,
    max_output_tokens: int,
    instructions: str,
    on_response_started: Callable[[str], None] | None = None,
    on_status: Callable[[str], None] | None = None,
) -> CloudDocumentResponse:
    """Überträgt eine PDF einmal und übergibt sie als ``input_file`` an Responses.

    Der Aufrufer bestimmt den versionierten Ausgabevertrag. Die temporäre OpenAI-Datei
    wird nach der Anfrage bestmöglich gelöscht und nie lokal persistiert.
    """
    started_at = _utc_now()
    started_ns = perf_counter_ns()
    api_key = _require_api_key()
    _validate_source(source_path)
    file_id = _upload_pdf(source_path=source_path, api_key=api_key, timeout_seconds=timeout_seconds)
    try:
        started_response = _create_background_response(
            file_id=file_id,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            instructions=instructions,
            api_key=api_key,
        )
        response_id = started_response.get("id")
        if not isinstance(response_id, str) or not response_id:
            raise OpenAICloudDocumentError("Die Hintergrundanfrage lieferte keine verwendbare Response-ID.")
        if on_response_started is not None:
            on_response_started(response_id)
        _report_status(started_response, on_status)
        payload = (
            started_response
            if started_response.get("status") not in {"queued", "in_progress"}
            else _poll_response(
                response_id=response_id,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
                on_status=on_status,
            )
        )
        completed_at = _utc_now()
        telemetry = telemetry_from_response(
            response=payload,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=(perf_counter_ns() - started_ns) // 1_000_000,
        )
        return CloudDocumentResponse(payload, telemetry)
    finally:
        _delete_file(file_id=file_id, api_key=api_key, timeout_seconds=timeout_seconds)


def retrieve_document_response(*, response_id: str, timeout_seconds: int, on_status: Callable[[str], None] | None = None) -> CloudDocumentResponse:
    """Setzt einen kurzzeitig unterbrochenen Hintergrundlauf ohne Neu-Upload fort."""
    started_at = _utc_now()
    started_ns = perf_counter_ns()
    payload = _poll_response(response_id=response_id, api_key=_require_api_key(), timeout_seconds=timeout_seconds, on_status=on_status)
    completed_at = _utc_now()
    return CloudDocumentResponse(payload, telemetry_from_response(response=payload, started_at=started_at, completed_at=completed_at, duration_ms=(perf_counter_ns() - started_ns) // 1_000_000))


def _require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OpenAICloudDocumentError(
            "OPENAI_API_KEY ist für den Cloud-Dokumentmodus nicht gesetzt."
        )
    return api_key


def _utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _validate_source(source_path: Path) -> None:
    if not source_path.is_file():
        raise OpenAICloudDocumentError("Die Cloud-Dokumentquelle muss eine vorhandene Datei sein.")
    if source_path.suffix.lower() != ".pdf":
        raise OpenAICloudDocumentError("Der Cloud-Dokumentmodus akzeptiert ausschließlich PDF-Dateien.")
    if source_path.stat().st_size > MAX_FILE_BYTES:
        raise OpenAICloudDocumentError("Die PDF überschreitet die zulässige Uploadgröße von 512 MiB.")


def _upload_pdf(*, source_path: Path, api_key: str, timeout_seconds: int) -> str:
    boundary = f"----doctomd-{uuid4().hex}"
    body = _build_multipart_body(boundary=boundary, source_path=source_path)
    request = Request(
        FILES_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    payload = _send_json(request, timeout_seconds=timeout_seconds, operation="PDF-Upload")
    file_id = payload.get("id")
    if not isinstance(file_id, str) or not file_id:
        raise OpenAICloudDocumentError("Der PDF-Upload lieferte keine verwendbare File-ID.")
    return file_id


def _build_multipart_body(*, boundary: str, source_path: Path) -> bytes:
    separator = boundary.encode("ascii")
    prefix = (
        b"--" + separator + b"\r\n"
        b'Content-Disposition: form-data; name="purpose"\r\n\r\n'
        b"user_data\r\n"
        b"--" + separator + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="source.pdf"\r\n'
        b"Content-Type: application/pdf\r\n\r\n"
    )
    return prefix + source_path.read_bytes() + b"\r\n--" + separator + b"--\r\n"


def _create_background_response(
    *,
    file_id: str,
    model_id: str,
    timeout_seconds: int,
    max_output_tokens: int,
    instructions: str,
    api_key: str,
) -> dict[str, Any]:
    payload = {
        "model": model_id,
        "store": False,
        "background": True,
        "max_output_tokens": max_output_tokens,
        "instructions": instructions,
        "input": [{"role": "user", "content": [
            {"type": "input_file", "file_id": file_id},
        ]}],
    }
    request = Request(
        RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    return _send_json(request, timeout_seconds=min(timeout_seconds, 60), operation="Start der Cloud-Dokumentanfrage")


def _poll_response(*, response_id: str, api_key: str, timeout_seconds: int, on_status: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Fragt einen Hintergrundlauf mit kurzen, wiederholbaren Requests ab."""
    deadline = monotonic() + timeout_seconds
    last_status: str | None = None
    while True:
        if monotonic() >= deadline:
            raise OpenAICloudDocumentError(
                f"Die OpenAI-Cloud-Dokumentanfrage überschritt das Gesamtzeitlimit von {timeout_seconds} Sekunden."
            )
        request = Request(
            f"{RESPONSES_URL}/{response_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        payload = _send_json(request, timeout_seconds=min(60, max(1, int(deadline - monotonic()))), operation="Statusabfrage der Cloud-Dokumentanfrage")
        status = payload.get("status")
        if isinstance(status, str) and status != last_status:
            _report_status(payload, on_status)
            last_status = status
        if status not in {"queued", "in_progress"}:
            return payload
        sleep(2)


def _report_status(payload: dict[str, Any], callback: Callable[[str], None] | None) -> None:
    status = payload.get("status")
    if callback is not None and isinstance(status, str):
        callback(status)


def _delete_file(*, file_id: str, api_key: str, timeout_seconds: int) -> None:
    request = Request(
        f"{FILES_URL}/{file_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        method="DELETE",
    )
    try:
        _send_json(request, timeout_seconds=timeout_seconds, operation="Löschen der temporären PDF")
    except OpenAICloudDocumentError:
        pass


def _send_json(request: Request, *, timeout_seconds: int, operation: str) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        remote_code, detail = _http_error_details(error)
        if remote_code == "insufficient_quota":
            raise OpenAICloudDocumentError(
                "OpenAI-Guthaben nicht ausreichend. Bitte Billing und Credit Balance prüfen.",
                code="CLOUD_INSUFFICIENT_CREDITS",
            ) from error
        suffix = f" ({detail})" if detail else ""
        raise OpenAICloudDocumentError(
            f"Die OpenAI-{operation} wurde mit HTTP {error.code} abgelehnt{suffix}."
        ) from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise OpenAICloudDocumentError(f"Die OpenAI-{operation} ist fehlgeschlagen.") from error
    if not isinstance(payload, dict):
        raise OpenAICloudDocumentError(f"Die OpenAI-{operation} lieferte kein JSON-Objekt.")
    return payload


def _http_error_details(error: HTTPError) -> tuple[str | None, str | None]:
    """Liest nur bereinigte, strukturierte Fehlerdetails aus einer HTTP-Antwort."""
    try:
        payload = json.loads(error.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    remote_error = payload.get("error")
    if not isinstance(remote_error, dict):
        return None, None
    code = remote_error.get("code")
    message = remote_error.get("message")
    details: list[str] = []
    safe_code = _sanitize_remote_error_value(code) if isinstance(code, str) and code else None
    if safe_code:
        details.append(safe_code)
    if isinstance(message, str) and message:
        details.append(_sanitize_remote_error_value(message))
    return safe_code, ": ".join(details) if details else None


def _sanitize_remote_error_value(value: str) -> str:
    """Entfernt schutzbedürftige Kennungen und begrenzt fremde Fehlermeldungen."""
    normalized = " ".join(value.split())
    redacted = _SENSITIVE_REMOTE_ERROR_VALUE.sub("[redacted]", normalized)
    return redacted[:_MAX_REMOTE_ERROR_MESSAGE_LENGTH]


__all__ = ["CloudDocumentResponse", "OpenAICloudDocumentError", "request_document_response", "retrieve_document_response"]
