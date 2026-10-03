"""Nachvollziehbare, geheimnisfreie Telemetrie für Cloud-Dokumentantworten."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class CloudCostEvidence:
    """Belegter Kostenbetrag mit Quelle und Abrufzeitpunkt."""

    amount_usd: Decimal
    source_url: str
    retrieved_at: datetime

    def __post_init__(self) -> None:
        if self.amount_usd < 0:
            raise ValueError("amount_usd darf nicht negativ sein.")
        parsed = urlparse(self.source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("source_url muss eine absolute HTTPS-URL sein.")
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at benötigt eine Zeitzone.")


@dataclass(frozen=True, slots=True)
class CloudDocumentTelemetry:
    """Antwortdaten ohne Zugangsdaten, File-ID oder Quelldokumentinhalt."""

    response_id: str
    model_id: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    cost: CloudCostEvidence | None = None

    def __post_init__(self) -> None:
        if not self.response_id or not self.model_id:
            raise ValueError("response_id und model_id dürfen nicht leer sein.")
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("Telemetriezeitpunkte benötigen eine Zeitzone.")
        if self.duration_ms < 0:
            raise ValueError("duration_ms darf nicht negativ sein.")
        for value in (self.input_tokens, self.output_tokens, self.total_tokens):
            if value is not None and value < 0:
                raise ValueError("Tokenzähler dürfen nicht negativ sein.")


def telemetry_from_response(
    *, response: dict[str, Any], started_at: datetime, completed_at: datetime, duration_ms: int
) -> CloudDocumentTelemetry:
    """Extrahiert nur dokumentierte Responses-Metadaten ohne Ersatzwerte."""
    response_id = response.get("id")
    model_id = response.get("model")
    if not isinstance(response_id, str) or not response_id:
        raise ValueError("Die OpenAI-Antwort enthält keine Response-ID.")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("Die OpenAI-Antwort enthält keine Modell-ID.")
    usage = response.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return CloudDocumentTelemetry(
        response_id=response_id,
        model_id=model_id,
        input_tokens=_optional_token(usage.get("input_tokens")),
        output_tokens=_optional_token(usage.get("output_tokens")),
        total_tokens=_optional_token(usage.get("total_tokens")),
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )


def serialize_cloud_document_telemetry(telemetry: CloudDocumentTelemetry) -> dict[str, object]:
    """Serialisiert Telemetrie für das versionierte Konvertierungsmanifest."""
    result: dict[str, object] = {
        "response_id": telemetry.response_id,
        "model_id": telemetry.model_id,
        "input_tokens": telemetry.input_tokens,
        "output_tokens": telemetry.output_tokens,
        "total_tokens": telemetry.total_tokens,
        "started_at": telemetry.started_at.isoformat(),
        "completed_at": telemetry.completed_at.isoformat(),
        "duration_ms": telemetry.duration_ms,
    }
    if telemetry.cost is not None:
        result["cost"] = {
            "amount_usd": format(telemetry.cost.amount_usd, "f"),
            "source_url": telemetry.cost.source_url,
            "retrieved_at": telemetry.cost.retrieved_at.isoformat(),
        }
    return result


def _optional_token(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Responses-Tokenzähler müssen nichtnegative Ganzzahlen sein.")
    return value


__all__ = [
    "CloudCostEvidence",
    "CloudDocumentTelemetry",
    "serialize_cloud_document_telemetry",
    "telemetry_from_response",
]
