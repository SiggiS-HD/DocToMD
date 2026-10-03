"""Stabile Benennung abgeleiteter Konvertierungsartefakte."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.path_validation import PathValidationError, ensure_not_source_target


class ArtifactPlanningError(ValueError):
    """Die Namen abgeleiteter Artefakte können nicht sicher geplant werden."""


@dataclass(frozen=True, slots=True)
class ArtifactPaths:
    """Vollständige Zielpfade einer Konvertierung ohne Schreibvorgang."""

    markdown_path: Path
    assets_dir: Path
    manifest_path: Path
    vision_proposals_dir: Path
    vision_markdown_path: Path
    vision_review_path: Path
    cloud_markdown_path: Path
    cloud_run_state_path: Path
    conversion_review_path: Path


def plan_artifact_paths(*, source_path: Path, output_dir: Path) -> ArtifactPaths:
    """Plant Markdown, Asset-Ordner und Manifest anhand des Quellbasenamens."""
    resolved_source = source_path.expanduser().resolve(strict=False)
    resolved_output_dir = output_dir.expanduser().resolve(strict=False)
    base_name = resolved_source.stem
    if not base_name or base_name in {".", ".."}:
        raise ArtifactPlanningError(
            f"Für die Quelle konnte kein sicherer Basisname ermittelt werden: {resolved_source}"
        )

    markdown_path = resolved_output_dir / f"{base_name}.md"
    assets_dir = resolved_output_dir / f"{base_name}.assets"
    manifest_path = resolved_output_dir / f"{base_name}.conversion.json"
    vision_proposals_dir = resolved_output_dir / f"{base_name}.vision-proposals"
    vision_markdown_path = resolved_output_dir / f"{base_name}.vision.md"
    vision_review_path = resolved_output_dir / f"{base_name}.vision-review.md"
    cloud_markdown_path = resolved_output_dir / f"{base_name}.cloud.md"
    cloud_run_state_path = resolved_output_dir / f"{base_name}.cloud-run.json"
    conversion_review_path = resolved_output_dir / f"{base_name}.conversion-review.md"

    try:
        return ArtifactPaths(
            markdown_path=ensure_not_source_target(markdown_path, resolved_source),
            assets_dir=ensure_not_source_target(assets_dir, resolved_source),
            manifest_path=ensure_not_source_target(manifest_path, resolved_source),
            vision_proposals_dir=ensure_not_source_target(vision_proposals_dir, resolved_source),
            vision_markdown_path=ensure_not_source_target(vision_markdown_path, resolved_source),
            vision_review_path=ensure_not_source_target(vision_review_path, resolved_source),
            cloud_markdown_path=ensure_not_source_target(cloud_markdown_path, resolved_source),
            cloud_run_state_path=ensure_not_source_target(cloud_run_state_path, resolved_source),
            conversion_review_path=ensure_not_source_target(conversion_review_path, resolved_source),
        )
    except PathValidationError as error:
        raise ArtifactPlanningError(str(error)) from error


__all__ = ["ArtifactPaths", "ArtifactPlanningError", "plan_artifact_paths"]
