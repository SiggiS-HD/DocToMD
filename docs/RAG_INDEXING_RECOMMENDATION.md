# Empfehlung für die RAG-Indexierung

DocToMD erstellt keinen RAG-Index und startet keinen Indexer. Für jede neu ausgeführte Konvertierung liefert das Top-Level-Feld `rag_indexing` im `*.conversion.json` jedoch eine maschinenlesbare Empfehlung, welches genau eine Markdown-Derivat indexiert werden soll.

```json
{
  "rag_indexing": {
    "schema_version": "1.0",
    "recommended_markdown_path": "Quelle.cloud.md",
    "selection_reason": "validated_cloud_has_more_structure",
    "candidates": []
  }
}
```

Der aufrufende Workflow übergibt ausschließlich `recommended_markdown_path` an seinen Indexer. `Quelle.md` und `Quelle.cloud.md` derselben Quelle dürfen nicht gemeinsam indexiert werden, weil sie doppelte Retrieval-Treffer erzeugen können.

## Auswahlregel

Das lokale Derivat ist der datensparsame, netzwerkfreie Ausgangspunkt. Ohne vorhandenes und technisch validiertes Cloud-Derivat empfiehlt DocToMD daher `Quelle.md` mit dem Grund `cloud_derivative_not_available`.

Existieren beide Derivate, misst DocToMD pro Kandidat Seitenmarker, Überschriften, DocToMD-Tabellenmarker oder GFM-Tabellen, Display-Formelmarker und nicht dekodierbare Zeichen der Form `(cid:`. Tabellen und Display-Formeln erhalten bei der transparent ausgewiesenen Strukturwertung ein höheres Gewicht; nicht dekodierbare Zeichen senken sie. Das Cloud-Derivat wird nur bei einer strikt höheren Wertung mit `validated_cloud_has_more_structure` empfohlen. Bei Gleichstand oder besserem lokalem Ergebnis bleibt `Quelle.md` mit `local_structure_is_equal_or_better` die Empfehlung.

Die Kennzahlen sind Diagnose- und Auswahlhilfen. Sie behaupten weder semantische Richtigkeit noch Vollständigkeit, ersetzen keine Fachprüfung und bewerten weder Datenschutz noch Kosten. Der Qualitätsstatus und die seitenbezogenen Warnungen des Manifests müssen beim Indexierungsworkflow weiterhin sichtbar bleiben.

## Beispiel SentencePiece

Bei der überprüften Konvertierung von `SentencePiece_D18-2012.pdf` enthielt das lokale Derivat keine Tabellen oder Display-Formeln und 27 nicht dekodierbare Zeichen. Das vorhandene Cloud-Derivat enthielt zwei Tabellen, 23 Display-Formelmarker und keine solchen Zeichen. Die Regel würde deshalb nur das bereits technisch validierte Cloud-Derivat als RAG-Quelle empfehlen; beide Varianten zugleich zu indexieren wäre falsch.

Bestehende Manifeste erhalten das Feld erst bei einer erneuten Konvertierung. Eine reine Indexierung verändert weder Original-PDF noch DocToMD-Artefakte.
