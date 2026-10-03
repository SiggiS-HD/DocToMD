"""Ausführung des opt-in Vision-Schritts und Ablage geprüfter Vorschläge."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from app.openai_vision import OpenAIVisionError, request_page_proposal
from app.pdf_extract import ExtractedPage
from app.vision_config import VisionConfig, VisionProvider
from app.vision_render import VisionRenderError, render_page
from app.vision_validation import backend_failure_warning, validate_vision_proposal


def execute_vision_proposals(*, source_path: Path, pages: tuple[ExtractedPage, ...], page_numbers: tuple[int, ...], config: VisionConfig, proposal_dir: Path, schema: dict) -> tuple[Path, ... , tuple]:
    """Führt nur für OpenAI und bereits ausgewählte Seiten den Vorschlagslauf aus."""
    if config.provider is not VisionProvider.OPENAI or not page_numbers:
        return (), ()
    page_by_number = {page.page_number: page for page in pages}
    written: list[Path] = []
    warnings = []
    with tempfile.TemporaryDirectory(prefix="doctomd-vision-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        for page_number in page_numbers:
            page = page_by_number[page_number]
            try:
                image_path = render_page(source_path=source_path, page_number=page_number, output_path=temporary_root / f"page-{page_number:03d}.png", dpi=config.render_dpi)
            except VisionRenderError:
                warnings.append(backend_failure_warning(failure="unreachable", page_number=page_number))
                continue
            try:
                response_text = request_page_proposal(image_path=image_path, model_id=config.model_id or "", schema=schema, timeout_seconds=config.timeout_seconds)
            except OpenAIVisionError:
                warnings.append(backend_failure_warning(failure="unreachable", page_number=page_number))
                continue
            outcome = validate_vision_proposal(response_text=response_text, requested_page=page_number, local_page_text=page.text)
            warnings.extend(outcome.warnings)
            if outcome.proposal is not None:
                target = proposal_dir / f"page-{page_number:03d}.proposal.json"
                _write_new_json(target, outcome.proposal)
                written.append(target)
    return tuple(written), tuple(warnings)


def _write_new_json(path: Path, proposal: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Vision-Vorschlagsdatei existiert bereits: {path}")
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


__all__ = ["execute_vision_proposals"]
