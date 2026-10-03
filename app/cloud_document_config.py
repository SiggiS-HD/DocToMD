"""Explizite, geheimnisfreie Konfiguration für Cloud-Dokumentkonvertierungen."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CloudDocumentMode(str, Enum):
    """Zulässige Ausführungsmodi für die vollständige Cloud-Konvertierung."""

    OFF = "off"
    OPENAI = "openai"


@dataclass(frozen=True, slots=True)
class CloudDocumentConfig:
    """Konfiguriert den optionalen Cloud-Dokumentmodus ohne Zugangsdaten.

    Der Schlüssel für OpenAI wird ausschließlich später im Adapter aus
    ``OPENAI_API_KEY`` gelesen. Diese Konfiguration liest, speichert und
    veröffentlicht ihn nicht.
    """

    mode: CloudDocumentMode = CloudDocumentMode.OFF
    model_id: str | None = None
    timeout_seconds: int = 900
    max_output_tokens: int = 32_768

    def __post_init__(self) -> None:
        if not 1 <= self.timeout_seconds <= 3_600:
            raise ValueError("cloud_document timeout_seconds muss zwischen 1 und 3600 liegen.")
        if not 1_024 <= self.max_output_tokens <= 32_768:
            raise ValueError(
                "cloud_document max_output_tokens muss zwischen 1024 und 32768 liegen."
            )
        if self.mode is CloudDocumentMode.OFF:
            if self.model_id is not None:
                raise ValueError("cloud_document mode off darf keine Modell-ID erhalten.")
            return
        if not self.model_id:
            raise ValueError("Der Cloud-Dokumentmodus openai benötigt eine Modell-ID.")

    def public_options(self) -> dict[str, object]:
        """Liefert manifesteignbare Einstellungen ohne Geheimnisse."""
        return {
            "mode": self.mode.value,
            "model_id": self.model_id,
            "timeout_seconds": self.timeout_seconds,
            "max_output_tokens": self.max_output_tokens,
        }


__all__ = ["CloudDocumentConfig", "CloudDocumentMode"]
