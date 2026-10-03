# CLI- und Manifestbeispiel

Dieses Beispiel beschreibt den vollständig lokalen Standardpfad für eine digitale PDF. Es aktiviert weder OCR noch Vision oder Cloud-Verarbeitung. Die Primärquelle bleibt unverändert.

## Aufruf

Der Ausgabeordner darf noch nicht existieren. `--on-conflict error` verhindert das Ersetzen vorhandener abgeleiteter Artefakte. `--progress none` hält dieses Beispiel kurz; interaktiv ist `human` der Standard.

```powershell
.\.venv\Scripts\python.exe main.py convert `
  "D:\Dokumente\Projektbericht.pdf" `
  --output-dir "D:\Dokumente\Projektbericht-Export" `
  --on-conflict error `
  --ocr-mode off `
  --ocr-language de `
  --json `
  --progress none
```

Bei Erfolg entstehen mindestens diese abgeleiteten Artefakte:

```text
Projektbericht-Export/
├─ Projektbericht.md
└─ Projektbericht.conversion.json
```

`Projektbericht.assets` entsteht nur bei tatsächlich exportierbaren Bildern. Die Original-PDF wird nicht kopiert, überschrieben oder gelöscht.

## JSON-Antwort der CLI

`stdout` enthält mit `--json` genau ein eingerücktes JSON-Dokument. Fortschrittsmeldungen stehen, sofern aktiviert, ausschließlich auf `stderr`.

```json
{
  "error": null,
  "exit_code": 0,
  "result": {
    "cloud_markdown_path": null,
    "conversion_status": "success",
    "manifest_path": "Projektbericht.conversion.json",
    "markdown_path": "Projektbericht.md",
    "quality": {
      "error_codes": {},
      "error_count": 0,
      "status": "ok",
      "warning_codes": {},
      "warning_count": 0
    },
    "rag_indexing": {
      "candidates": [
        {
          "display_formula_count": 0,
          "heading_count": 4,
          "kind": "local",
          "page_marker_count": 3,
          "path": "Projektbericht.md",
          "structure_score": 4,
          "table_count": 1,
          "unreadable_glyph_count": 0
        }
      ],
      "recommended_markdown_path": "Projektbericht.md",
      "schema_version": "1.0",
      "selection_reason": "cloud_derivative_not_available"
    },
    "rag_readiness": {
      "local_derivative_suitable": true,
      "reasons": [],
      "recommended_derivative_path": "Projektbericht.md",
      "recommended_next_step": {
        "kind": "none",
        "message": "Keine weitere Rekonstruktion erforderlich; das empfohlene Derivat kann vor der Indexierung regulär geprüft werden.",
        "requires_explicit_opt_in": false
      },
      "schema_version": "1.0",
      "status": "ready",
      "suggested_next_steps": []
    },
    "reused": false,
    "vision_pages": []
  },
  "schema_version": "1.1",
  "status": "success",
  "warnings": []
}
```

`success`/`0` steht für einen Erfolg ohne Qualitätswarnung, `warning`/`1` für einen erfolgreichen Lauf mit Warnungen und `error`/`2` für einen Fehler. Die CLI fasst Qualitätsdaten zusammen; die vollständigen Einzelbefunde stehen im Manifest.

## Beispielmanifest

Das Manifest heißt stets `<Quellbasisname>.conversion.json`. Pfad, Hash, Zeitstempel, Komponentenstände und Strukturkennzahlen werden pro Lauf ermittelt. Das folgende gekürzte, aber vollständige Beispiel zeigt die Werteform eines erfolgreichen lokalen Laufs.

```json
{
  "manifest_schema_version": "1.0",
  "created_at": "2026-09-22T13:02:00+00:00",
  "source": {
    "path": "D:\\Dokumente\\Projektbericht.pdf",
    "media_type": "application/pdf",
    "size_bytes": 18432,
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "modified_at": "2026-09-22T12:55:00+00:00"
  },
  "conversion": {
    "status": "success",
    "output_format": "markdown",
    "started_at": "2026-09-22T13:01:58+00:00",
    "completed_at": "2026-09-22T13:02:00+00:00",
    "components": {
      "engine": {"name": "doctomd", "version": "0.1.0"},
      "extractor": {"name": "pdfplumber", "version": "0.11.10"}
    },
    "options": {"ocr_mode": "off", "ocr_language": "de", "page_range": "all"},
    "ocr": {"min_word_confidence": 70, "pages": []}
  },
  "artifacts": {
    "markdown_path": "Projektbericht.md",
    "assets": [],
    "content_references": [
      {"kind": "text", "page": {"page_number": 1}},
      {"kind": "table", "page": {"page_number": 2}}
    ],
    "references": [],
    "vision_proposals": []
  },
  "quality": {"status": "ok", "warnings": [], "errors": []},
  "rag_indexing": {
    "schema_version": "1.0",
    "recommended_markdown_path": "Projektbericht.md",
    "selection_reason": "cloud_derivative_not_available",
    "candidates": [
      {
        "kind": "local",
        "path": "Projektbericht.md",
        "heading_count": 4,
        "table_count": 1,
        "display_formula_count": 0,
        "page_marker_count": 3,
        "unreadable_glyph_count": 0,
        "structure_score": 4
      }
    ]
  },
  "rag_readiness": {
    "schema_version": "1.0",
    "status": "ready",
    "local_derivative_suitable": true,
    "recommended_derivative_path": "Projektbericht.md",
    "reasons": [],
    "suggested_next_steps": [],
    "recommended_next_step": {
      "kind": "none",
      "message": "Keine weitere Rekonstruktion erforderlich; das empfohlene Derivat kann vor der Indexierung regulär geprüft werden.",
      "requires_explicit_opt_in": false
    }
  }
}
```

Alle Artefaktpfade sind relativ zum Ausgabeordner. Ein aufrufender Indexer übernimmt ausschließlich `rag_indexing.recommended_markdown_path` und prüft zusätzlich `quality`. Details zur Übergabe stehen in [[CODEXCLI_HANDOFF|Übergabe an CodexCLI]].

Bei aktiver OCR enthält `conversion.ocr.pages` Metriken für die tatsächlich verarbeiteten Seiten. Ein ausdrücklich aktivierter und erfolgreich validierter Cloud-Lauf ergänzt `artifacts.cloud_markdown_path` sowie `conversion.cloud_document`; er ersetzt niemals das lokale Markdown oder die Original-PDF.
