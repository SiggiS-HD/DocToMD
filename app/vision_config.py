"""Explizite, providerneutrale Konfiguration für optionale Vision-Schritte."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class VisionProvider(str, Enum):
    """Unterstützte Anbieter für opt-in Vision-Vorschläge."""

    NONE = "none"
    LM_STUDIO = "lm-studio"
    OPENAI = "openai"


class VisionMode(str, Enum):
    """Zeitpunkt, zu dem ein explizit gewählter Provider genutzt werden darf."""

    OFF = "off"
    AUTO = "auto"
    FORCE = "force"


@dataclass(frozen=True, slots=True)
class VisionConfig:
    """Netzwerkfreie Konfiguration ohne Zugangsdaten.

    Der Schlüssel für OpenAI gehört ausschließlich in ``OPENAI_API_KEY`` und
    wird hier weder gelesen noch gespeichert.
    """

    provider: VisionProvider = VisionProvider.NONE
    mode: VisionMode = VisionMode.OFF
    model_id: str | None = None
    render_dpi: int = 144
    timeout_seconds: int = 480
    lm_studio_endpoint: str | None = None

    def __post_init__(self) -> None:
        if not 72 <= self.render_dpi <= 600:
            raise ValueError("render_dpi muss zwischen 72 und 600 liegen.")
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds muss zwischen 1 und 3600 liegen.")
        if self.provider is VisionProvider.NONE:
            if self.mode is not VisionMode.OFF:
                raise ValueError("provider none erlaubt nur den Vision-Modus off.")
            if self.model_id is not None or self.lm_studio_endpoint is not None:
                raise ValueError("provider none darf weder Modell-ID noch LM-Studio-Endpoint erhalten.")
            return
        if self.mode is not VisionMode.OFF and not self.model_id:
            raise ValueError("Ein aktiver Vision-Provider benötigt eine Modell-ID.")
        if self.provider is VisionProvider.LM_STUDIO:
            if self.mode is not VisionMode.OFF and not self.lm_studio_endpoint:
                raise ValueError("Ein aktiver LM-Studio-Provider benötigt einen Endpoint.")
            if self.lm_studio_endpoint is not None:
                _validate_lm_studio_endpoint(self.lm_studio_endpoint)
        elif self.lm_studio_endpoint is not None:
            raise ValueError("Der LM-Studio-Endpoint ist ausschließlich für provider lm-studio zulässig.")

    def public_options(self) -> dict[str, object]:
        """Liefert manifesteignbare Konfiguration ohne Geheimnisse."""
        options: dict[str, object] = {
            "provider": self.provider.value,
            "mode": self.mode.value,
            "model_id": self.model_id,
            "render_dpi": self.render_dpi,
            "timeout_seconds": self.timeout_seconds,
        }
        if self.provider is VisionProvider.LM_STUDIO:
            options["lm_studio_endpoint"] = self.lm_studio_endpoint
        return options


def _validate_lm_studio_endpoint(endpoint: str) -> None:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        raise ValueError("Der LM-Studio-Endpoint muss eine absolute HTTP(S)-Basis-URL sein.")


__all__ = ["VisionConfig", "VisionMode", "VisionProvider"]
