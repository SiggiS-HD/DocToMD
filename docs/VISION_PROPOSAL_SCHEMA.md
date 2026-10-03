# Vision-Vorschlagsvertrag

Das Schema `schemas/vision-proposal-1.0.schema.json` beschreibt ausschließlich unverbindliche Vorschläge eines Vision-Providers für genau eine gerenderte Seite. Es ist getrennt vom Konvertierungsmanifest versioniert und beginnt mit `schema_version: "1.0"`.

Jede Antwort muss `page`, `paragraphs`, `formulas`, `tables` und `captions` enthalten. Leere Arrays sind zulässig; ausgelassene Felder und unbekannte Felder sind es nicht. Jeder Vorschlag enthält seine eigene einsbasierte `page`-Referenz und eine numerische `confidence` von 0 bis 1. Dadurch kann die lokale Verarbeitung Seitenbezug und Konfidenz unabhängig vom Provider prüfen.

Eine Formel enthält immer sowohl den sichtbaren `source_text` als auch das vorgeschlagene `latex`. Tabellen enthalten mindestens zwei Kopfzellen und mindestens eine Datenzeile. Captions bleiben ohne technische Asset-ID; ein optionales `target_hint` ist nur ein Hinweis und darf lokal nicht als sichere Zuordnung behandelt werden.

Das Schema macht keinen Vorschlag verbindlich. Eine spätere lokale Validierung muss insbesondere prüfen, dass alle inneren Seitenangaben der angefragten Seite entsprechen, Tabellenzeilen zur Kopfzeile passen, LaTeX sicher verwendbar ist und die Konfidenz die konfigurierte Schwelle erreicht. Ungültige Antworten werden sichtbar gewarnt statt übernommen.
