"""Definition der öffentlichen DocToMD-Kommandozeilenschnittstelle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.cli_output import build_conversion_response, emit_error
from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode
from app.cloud_derive_service import can_reuse_local_context, derive_cloud
from app.cloud_evaluate_service import evaluate_cloud_pages, parse_page_range
from app.conversion_review_service import write_conversion_review
from app.conversion_service import convert_pdf, serialize_run
from app.provenance_migration_service import migrate_markdown_provenance
from app.progress import ProgressReporter
from app.vision_config import VisionConfig, VisionMode, VisionProvider


def create_parser() -> argparse.ArgumentParser:
    """Erstellt den Parser für die öffentliche Kommandozeilenschnittstelle."""
    parser = argparse.ArgumentParser(
        prog="doctomd",
        description="Konvertiert Dokumente lokal in strukturiertes Markdown.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="BEFEHL")

    convert_parser = subparsers.add_parser(
        "convert",
        help="Konvertiert ein Dokument in Markdown.",
        description="Konvertiert ein Dokument in strukturiertes Markdown.",
    )
    convert_parser.add_argument(
        "input_path",
        type=Path,
        metavar="INPUT.pdf",
        help="Pfad zum zu konvertierenden Quelldokument.",
    )
    convert_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        metavar="AUSGABEORDNER",
        help="Zielordner für die abgeleiteten Artefakte.",
    )
    convert_parser.add_argument(
        "--output-format",
        choices=("markdown",),
        default="markdown",
        help="Ausgabeformat; derzeit wird nur Markdown unterstützt (Standard: markdown).",
    )
    convert_parser.add_argument(
        "--on-conflict",
        choices=("error", "update", "overwrite"),
        default="error",
        help="Verhalten bei vorhandenen abgeleiteten Artefakten (Standard: error).",
    )
    convert_parser.add_argument(
        "--ocr-mode",
        choices=("auto", "off", "force"),
        default="auto",
        help="OCR-Verhalten: auto, off oder force (Standard: auto).",
    )
    convert_parser.add_argument(
        "--ocr-language",
        default="de",
        metavar="BCP47",
        help="Sprache für OCR als BCP-47-Kennung (Standard: de).",
    )
    convert_parser.add_argument("--ocr-pages", default="all", metavar="SEITEN", help="OCR-Seiten: all oder Liste wie 1-3,5 (Standard: all).")
    convert_parser.add_argument("--ocr-min-word-confidence", type=int, default=70, metavar="0-100", help="Warnschwelle für mittlere OCR-Wortkonfidenz (Standard: 70).")
    convert_parser.add_argument(
        "--vision-provider",
        choices=tuple(provider.value for provider in VisionProvider),
        default=VisionProvider.NONE.value,
        help="Optionaler Vision-Provider: none, lm-studio oder openai (Standard: none).",
    )
    convert_parser.add_argument(
        "--vision-mode",
        choices=tuple(mode.value for mode in VisionMode),
        default=VisionMode.OFF.value,
        help="Vision-Modus: off, auto oder force (Standard: off).",
    )
    convert_parser.add_argument(
        "--vision-model",
        metavar="MODELL-ID",
        help="Modell-ID für einen aktiven Vision-Provider.",
    )
    convert_parser.add_argument(
        "--vision-render-dpi",
        type=int,
        default=144,
        metavar="DPI",
        help="Renderauflösung für Vision-Seitenbilder, 72 bis 600 (Standard: 144).",
    )
    convert_parser.add_argument(
        "--vision-timeout-seconds",
        type=int,
        default=480,
        metavar="SEKUNDEN",
        help="Timeout je Vision-Anfrage, 1 bis 3600 (Standard: 480).",
    )
    convert_parser.add_argument(
        "--lm-studio-endpoint",
        metavar="URL",
        help="HTTP(S)-Basis-URL, ausschließlich für --vision-provider lm-studio.",
    )
    convert_parser.add_argument(
        "--cloud-document-mode",
        choices=tuple(mode.value for mode in CloudDocumentMode),
        default=CloudDocumentMode.OFF.value,
        help="Vollständige Cloud-Dokumentkonvertierung: off oder openai (Standard: off).",
    )
    convert_parser.add_argument(
        "--cloud-document-model",
        metavar="MODELL-ID",
        help="Modell-ID für den ausdrücklich aktivierten Cloud-Dokumentmodus.",
    )
    convert_parser.add_argument(
        "--cloud-document-timeout-seconds",
        type=int,
        default=900,
        metavar="SEKUNDEN",
        help="Timeout für eine vollständige Cloud-Dokumentanfrage, 1 bis 3600 (Standard: 900).",
    )
    convert_parser.add_argument(
        "--cloud-document-max-output-tokens",
        type=int,
        default=32_768,
        metavar="TOKENS",
        help="Obergrenze für die Cloud-Ausgabe, 1024 bis 32768 (Standard: 32768).",
    )
    convert_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Gibt das Ergebnis als versioniertes JSON aus.",
    )
    convert_parser.add_argument(
        "--progress",
        choices=("human", "jsonl", "none"),
        default="human",
        help="Fortschritt auf stderr: human, jsonl oder none (Standard: human).",
    )

    cloud_derive_parser = subparsers.add_parser(
        "cloud-derive",
        help="Leitet ausdrücklich ein Cloud-Markdown aus einem lokalen Ergebnis ab.",
        description="Leitet ein Cloud-Markdown aus einem vorhandenen lokalen DocToMD-Ergebnis ab.",
    )
    cloud_derive_parser.add_argument(
        "input_path",
        type=Path,
        metavar="INPUT.pdf",
        help="Pfad zur unveränderten PDF-Primärquelle des lokalen Ergebnisses.",
    )
    cloud_derive_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        metavar="AUSGABEORDNER",
        help="Ordner mit dem vorhandenen lokalen Markdown und Basismanifest.",
    )
    cloud_derive_parser.add_argument(
        "--on-conflict",
        choices=("error", "overwrite"),
        default="error",
        help="Verhalten bei vorhandenem Cloud-Derivat (Standard: error).",
    )
    cloud_derive_parser.add_argument(
        "--cloud-document-model",
        metavar="MODELL-ID",
        help="Modell-ID für die ausdrücklich angeforderte Cloud-Ableitung.",
    )
    cloud_derive_parser.add_argument(
        "--cloud-document-timeout-seconds",
        type=int,
        default=900,
        metavar="SEKUNDEN",
        help="Timeout für die Cloud-Ableitung, 1 bis 3600 (Standard: 900).",
    )
    cloud_derive_parser.add_argument(
        "--cloud-document-max-output-tokens",
        type=int,
        default=32_768,
        metavar="TOKENS",
        help="Obergrenze für die Cloud-Ausgabe, 1024 bis 32768 (Standard: 32768).",
    )
    cloud_derive_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Gibt das Ergebnis als versioniertes JSON aus.",
    )
    cloud_derive_parser.add_argument(
        "--progress",
        choices=("human", "jsonl", "none"),
        default="human",
        help="Fortschritt auf stderr: human, jsonl oder none (Standard: human).",
    )

    cloud_evaluate_parser = subparsers.add_parser(
        "cloud-evaluate",
        help="Wertet einen ausdrücklich angeforderten PDF-Seitenbereich in der Cloud aus.",
        description="Erzeugt getrennte Evaluierungsartefakte aus einem geprüften lokalen DocToMD-Ergebnis.",
    )
    cloud_evaluate_parser.add_argument("input_path", type=Path, metavar="INPUT.pdf", help="Unveränderte PDF-Primärquelle.")
    cloud_evaluate_parser.add_argument("--output-dir", type=Path, required=True, metavar="AUSGABEORDNER", help="Ordner mit dem geprüften lokalen Ergebnis.")
    cloud_evaluate_parser.add_argument("--pages", type=parse_page_range, required=True, metavar="SEITEN", help="Zusammenhängender positiver Bereich, etwa 10 oder 9-14.")
    cloud_evaluate_parser.add_argument("--cloud-document-model", default="gpt-5.6-terra", metavar="MODELL-ID", help="Cloud-Modell für die ausdrücklich angeforderte Evaluation (Standard: gpt-5.6-terra).")
    cloud_evaluate_parser.add_argument("--cloud-document-timeout-seconds", type=int, default=900, metavar="SEKUNDEN", help="Timeout für die Cloud-Evaluation, 1 bis 3600 (Standard: 900).")
    cloud_evaluate_parser.add_argument("--cloud-document-max-output-tokens", type=int, default=32_768, metavar="TOKENS", help="Obergrenze für die Cloud-Ausgabe, 1024 bis 32768 (Standard: 32768).")
    cloud_evaluate_parser.add_argument("--json", action="store_true", dest="json_output", help="Gibt das Evaluierungsergebnis als JSON aus.")
    cloud_evaluate_parser.add_argument("--progress", choices=("human", "jsonl", "none"), default="human", help="Fortschritt auf stderr: human, jsonl oder none (Standard: human).")
    review_parser = subparsers.add_parser("review", help="Erzeugt eine lokale Konvertierungsbewertung aus dem Manifest.", description="Erzeugt eine getrennte Markdown-Note aus einem vorhandenen, geprüften DocToMD-Ergebnis.")
    review_parser.add_argument("input_path", type=Path, metavar="INPUT.pdf", help="Unveränderte PDF-Primärquelle des vorhandenen Ergebnisses.")
    review_parser.add_argument("--output-dir", type=Path, required=True, metavar="AUSGABEORDNER", help="Ordner mit Manifest und abgeleiteten Artefakten.")
    review_parser.add_argument("--on-conflict", choices=("error", "overwrite"), default="error", help="Verhalten bei vorhandener Review-Note (Standard: error).")
    review_parser.add_argument("--json", action="store_true", dest="json_output", help="Gibt das Ergebnis als JSON aus.")
    provenance_parser = subparsers.add_parser("migrate-provenance", help="Ergänzt Herkunftsblöcke in vorhandenen Markdown-Derivaten.", description="Ergänzt lokale und vorhandene Cloud-Markdown-Derivate ohne PDF-, OCR- oder Cloud-Lauf.")
    provenance_parser.add_argument("input_path", type=Path, metavar="INPUT.pdf", help="Unveränderte PDF-Primärquelle des vorhandenen Ergebnisses.")
    provenance_parser.add_argument("--output-dir", type=Path, required=True, metavar="AUSGABEORDNER", help="Ordner mit Manifest und vorhandenen Markdown-Derivaten.")
    provenance_parser.add_argument("--json", action="store_true", dest="json_output", help="Gibt die aktualisierten Artefaktpfade als JSON aus.")
    return parser


def run(arguments: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Führt einen bereits erfolgreich geparsten CLI-Befehl aus."""
    if arguments.command is None:
        parser.print_help()
        return 0

    if arguments.command == "convert":
        progress = ProgressReporter(arguments.progress)
        try:
            cloud_document_config = CloudDocumentConfig(
                mode=CloudDocumentMode(arguments.cloud_document_mode),
                model_id=arguments.cloud_document_model,
                timeout_seconds=arguments.cloud_document_timeout_seconds,
                max_output_tokens=arguments.cloud_document_max_output_tokens,
            )
            vision_config = VisionConfig(
                provider=VisionProvider(arguments.vision_provider),
                mode=VisionMode(arguments.vision_mode),
                model_id=arguments.vision_model,
                render_dpi=arguments.vision_render_dpi,
                timeout_seconds=arguments.vision_timeout_seconds,
                lm_studio_endpoint=arguments.lm_studio_endpoint,
            )
            if cloud_document_config.mode is CloudDocumentMode.OPENAI and can_reuse_local_context(input_path=arguments.input_path, output_dir=arguments.output_dir):
                progress("reuse", "redirected", "Gültiger lokaler Wiederverwendungskontext erkannt; cloud-derive wird verwendet.")
                run = derive_cloud(input_path=arguments.input_path, output_dir=arguments.output_dir, on_conflict="overwrite" if arguments.on_conflict == "overwrite" else "error", config=cloud_document_config, progress=progress)
            else:
                local_config = CloudDocumentConfig(mode=CloudDocumentMode.OFF) if cloud_document_config.mode is CloudDocumentMode.OPENAI else cloud_document_config
                local_run = convert_pdf(
                    input_path=arguments.input_path,
                    output_dir=arguments.output_dir,
                    on_conflict=arguments.on_conflict,
                    ocr_mode=arguments.ocr_mode,
                    ocr_language=arguments.ocr_language,
                    ocr_pages=arguments.ocr_pages,
                    ocr_min_word_confidence=arguments.ocr_min_word_confidence,
                    vision_config=vision_config,
                    cloud_document_config=local_config,
                    progress=progress,
                )
                if cloud_document_config.mode is CloudDocumentMode.OPENAI:
                    progress("reuse", "prepared", "Lokale Basis wurde veröffentlicht; cloud-derive verarbeitet die geplanten Batches.")
                    run = derive_cloud(input_path=arguments.input_path, output_dir=arguments.output_dir, on_conflict="overwrite" if arguments.on_conflict == "overwrite" else "error", config=cloud_document_config, progress=progress)
                else:
                    run = local_run
        except (OSError, ValueError) as error:
            return emit_error(
                code=getattr(error, "code", "CONVERSION_FAILED"),
                message=str(error),
                json_output=arguments.json_output,
            )
        response = build_conversion_response(
            result=serialize_run(run),
            warnings=run.result.warnings,
        )
        if arguments.json_output:
            print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            verb = "Wiederverwendet" if run.reused else "Konvertiert"
            print(f"{verb}: {run.result.markdown_path}")
            if run.cloud_markdown_path is not None:
                print(f"Cloud-Derivat: {run.cloud_markdown_path}")
            for warning in run.result.warnings:
                print(f"Warnung [{warning.code}]: {warning.message}")
        return response["exit_code"]

    if arguments.command == "cloud-derive":
        try:
            config = CloudDocumentConfig(
                mode=CloudDocumentMode.OPENAI,
                model_id=arguments.cloud_document_model,
                timeout_seconds=arguments.cloud_document_timeout_seconds,
                max_output_tokens=arguments.cloud_document_max_output_tokens,
            )
        except ValueError as error:
            return emit_error(
                code="CLOUD_DERIVE_CONFIGURATION_INVALID",
                message=str(error),
                json_output=arguments.json_output,
            )
        try:
            run = derive_cloud(input_path=arguments.input_path, output_dir=arguments.output_dir, on_conflict=arguments.on_conflict, config=config, progress=ProgressReporter(arguments.progress))
        except (OSError, ValueError) as error:
            return emit_error(code=getattr(error, "code", "CLOUD_DERIVE_FAILED"), message=str(error), json_output=arguments.json_output)
        response = build_conversion_response(result={**serialize_run(run), "reused_local_context": True}, warnings=run.result.warnings)
        if arguments.json_output:
            print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"Cloud-Derivat: {run.cloud_markdown_path}")
        return response["exit_code"]

    if arguments.command == "cloud-evaluate":
        try:
            config = CloudDocumentConfig(
                mode=CloudDocumentMode.OPENAI,
                model_id=arguments.cloud_document_model,
                timeout_seconds=arguments.cloud_document_timeout_seconds,
                max_output_tokens=arguments.cloud_document_max_output_tokens,
            )
            evaluation = evaluate_cloud_pages(
                input_path=arguments.input_path,
                output_dir=arguments.output_dir,
                page_numbers=arguments.pages,
                config=config,
                progress=ProgressReporter(arguments.progress),
            )
        except (OSError, ValueError) as error:
            return emit_error(code=getattr(error, "code", "CLOUD_EVALUATE_FAILED"), message=str(error), json_output=arguments.json_output)
        response = {"schema_version": "1.0", "status": "success", "exit_code": 0, "evaluation": evaluation}
        if arguments.json_output:
            print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"Lokaler Auszug: {evaluation['local_markdown_path']}")
            print(f"Cloud-Evaluation: {evaluation['cloud_markdown_path']}")
            print(f"Evaluierung: {evaluation['evaluation_path']}")
        return 0

    if arguments.command == "review":
        try:
            review_path = write_conversion_review(input_path=arguments.input_path, output_dir=arguments.output_dir, overwrite=arguments.on_conflict == "overwrite")
        except (OSError, ValueError) as error:
            return emit_error(code=getattr(error, "code", "REVIEW_FAILED"), message=str(error), json_output=arguments.json_output)
        response = {"schema_version": "1.0", "status": "success", "exit_code": 0, "review_path": str(review_path)}
        if arguments.json_output:
            print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"Konvertierungsbewertung: {review_path}")
        return 0

    if arguments.command == "migrate-provenance":
        try:
            changed = migrate_markdown_provenance(input_path=arguments.input_path, output_dir=arguments.output_dir)
        except (OSError, ValueError) as error:
            return emit_error(code=getattr(error, "code", "PROVENANCE_MIGRATION_FAILED"), message=str(error), json_output=arguments.json_output)
        response = {"schema_version": "1.0", "status": "success", "exit_code": 0, "markdown_paths": [str(path) for path in changed]}
        if arguments.json_output:
            print(json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for path in changed:
                print(f"Provenienz ergänzt: {path}")
        return 0

    parser.error(f"Unbekannter Befehl: {arguments.command}")
    return 2


def main() -> int:
    """Parst Argumente und startet den angeforderten CLI-Befehl."""
    parser = create_parser()
    return run(parser.parse_args(), parser)
