# Automatische RAG-Eignungsprüfung

Nach jeder neu ausgeführten Konvertierung schreibt DocToMD das versionierte Top-Level-Feld `rag_readiness` in das Manifest und die kompakte CLI-JSON-Ausgabe. Die Prüfung fasst Befunde zusammen, die während der Verarbeitung der Original-PDF und ihrer Derivate entstanden sind. Sie startet keine weitere Verarbeitung und aktiviert insbesondere niemals OCR, Vision oder Cloud-Dokumentverarbeitung.

```json
{
  "rag_readiness": {
    "schema_version": "1.0",
    "status": "local_not_suitable",
    "local_derivative_suitable": false,
    "recommended_derivative_path": "Quelle.md",
    "reasons": [
      {"code": "UNREADABLE_PDF_GLYPHS", "count": 66, "pages": [1, 2, 3]}
    ],
    "suggested_next_steps": [
      {
        "kind": "cloud_document",
        "requires_explicit_opt_in": true,
        "reason_codes": ["UNREADABLE_PDF_GLYPHS"]
      }
    ],
    "recommended_next_step": {
      "kind": "cloud_document",
      "requires_explicit_opt_in": true,
      "message": "Das lokale Derivat ist nicht RAG-geeignet. Starte bei bewusster Freigabe einen Cloud-Dokumentlauf und prüfe danach das empfohlene Derivat."
    }
  }
}
```

## Status und Vorschläge

`ready` bedeutet, dass keine festgelegte lokale RAG-Sperre erkannt wurde. `local_not_suitable` bedeutet, dass das lokale Derivat wegen nicht dekodierbarer Zeichen, unsicherer OCR, nicht rekonstruierter Formeln, unsicherer komplexer Tabellen oder bestätigtem Mehrspaltenlayout nicht als alleinige RAG-Quelle empfohlen wird. `review_required` bedeutet, dass ein Cloud-Derivat als besseres Derivat empfohlen wird, dessen kritische Originalseiten aber weiterhin geprüft werden müssen.

Die Gründe enthalten Code, Anzahl und betroffene Seiten. `recommended_next_step` priorisiert genau eine Folgeaktion und enthält eine deutschsprachige Handlungsaufforderung. Bei nicht dekodierbaren Zeichen schlägt DocToMD einen bewusst aktivierten OCR-Forcelauf vor. Bei Mehrspalten-, Tabellen-, Formel- oder Zeichendekodierungsrisiken priorisiert es den expliziten Schritt `cloud_document`. Beide Vorschläge haben immer `requires_explicit_opt_in: true`: Ein Hinweis löst weder Upload noch Kosten aus.

`recommended_derivative_path` stammt aus [der Indexempfehlung](RAG_INDEXING_RECOMMENDATION.md). Ein Indexer verwendet nur diesen Pfad und behandelt `rag_readiness` als Entscheidungs- und Prüfkontext. Die Prüfung ist keine semantische Vollständigkeitsgarantie; besonders Diagramme, komplexes Layout und fachliche Aussagen können weiterhin manuelle Sichtprüfung benötigen.
