"""Minimaler, expliziter OpenAI-Adapter für validierbare Seitenvorschläge."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OpenAIVisionError(OSError):
    """Die Vision-Anfrage konnte nicht erfolgreich abgeschlossen werden."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def request_page_proposal(*, image_path: Path, model_id: str, schema: dict[str, Any], timeout_seconds: int) -> str:
    """Sendet genau ein lokales Seitenbild mit ``store: false`` an Responses."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIVisionError("OPENAI_API_KEY ist für den OpenAI-Vision-Provider nicht gesetzt.")
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    payload = {
        "model": model_id,
        "store": False,
        "max_output_tokens": 4000,
        "instructions": "Liefere ausschließlich einen vollständigen JSON-Vorschlag gemäß dem vorgegebenen Schema. Erfinde keine Inhalte.",
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": "Analysiere diese einzelne PDF-Seite."},
            {"type": "input_image", "image_url": f"data:image/png;base64,{image_data}", "detail": "high"},
        ]}],
        "text": {"format": {"type": "json_schema", "name": "doctomd_vision_proposal", "strict": True, "schema": schema}},
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        detail = " ".join(detail.split())[:500]
        message = f"Die OpenAI-Vision-Anfrage wurde mit HTTP {error.code} abgelehnt."
        if detail:
            message = f"{message} {detail}"
        raise OpenAIVisionError(message, status_code=error.code) from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise OpenAIVisionError("Die OpenAI-Vision-Anfrage ist fehlgeschlagen.") from error
    output_text = body.get("output_text")
    if isinstance(output_text, str):
        return output_text
    for output_item in body.get("output", []):
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content", []):
            if (
                isinstance(content_item, dict)
                and content_item.get("type") == "output_text"
                and isinstance(content_item.get("text"), str)
            ):
                return content_item["text"]
    raise OpenAIVisionError("Die OpenAI-Vision-Antwort enthält keinen Textvorschlag.")


__all__ = ["OpenAIVisionError", "request_page_proposal"]
