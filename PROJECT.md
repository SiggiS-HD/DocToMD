# Projektbeschreibung: DocToMD

## Projektziel

DocToMD ist eine lokale Python-Engine, die Dokumente in strukturiertes Markdown überführt. Der erste unterstützte Eingabetyp ist PDF, einschließlich digital erzeugter PDFs und gescannter Bild-PDFs. Später können weitere Dokumenttypen wie DOCX oder HTML folgen.

Die Engine erzeugt aus einer unveränderten Primärquelle eine durchsuchbare, überprüfbare Arbeitskopie:

```text
Original.pdf
    │
    ▼
DocToMD
    ├─ Dokument.md
    ├─ Dokument.assets/
    │   ├─ page-001-figure-01.png
    │   ├─ page-001-figure-01-description.md
    │   └─ …
    └─ Dokument.conversion.json
```

Das abgeleitete Markdown soll strukturiertes Chunking und zuverlässigeres RAG ermöglichen. Insbesondere sollen Überschriften, Absätze, Listen, Tabellen, Bildreferenzen und Seitenbezug so weit wie möglich erhalten bleiben. Das Original-PDF wird niemals ersetzt.

## Fachlicher Hintergrund

Die nicht versionierte Vault-Startnote „PDF-to-Markdown für RAG“ ist die fachliche Grundlage dieses Projekts.

Sie beschreibt das Problem harter PDF-Zeichenchunks: Text bleibt zwar vorhanden, aber ein Embedding kann Kontext nur innerhalb seines eigenen Chunks repräsentieren. Strukturierte Markdown-Derivate ermöglichen dagegen eine Zerlegung entlang von Überschriften, Absätzen und Sätzen. Das senkt das Risiko, dass Definition, Einschränkung, Begründung oder Beispiel getrennt abgerufen werden.

DocToMD ersetzt kein gutes Chunking und kein Retrieval mit Neighbor Expansion. Es liefert jedoch eine deutlich bessere, strukturierte Eingabe für diese späteren Schritte.

## Nicht-Ziele der ersten Version

- Kein RAG-Index und kein Retrieval: Das ist Aufgabe von CodexCLI oder einer anderen konsumierenden Anwendung.
- Kein Obsidian-Plugin: Das Plugin wird ein separates Desktop-only-Projekt und ruft DocToMD über dessen CLI auf.
- Keine Veränderung oder Löschung des Originaldokuments.
- Keine Garantie auf pixelgenaue Wiederherstellung des PDF-Layouts.
- Keine stillschweigende Cloud-Verarbeitung; die Standardverarbeitung bleibt lokal.

## Verantwortlichkeiten und Projektgrenzen

| Komponente | Verantwortung |
| --- | --- |
| DocToMD | Extraktion, OCR, Layoutanalyse, Markdown, Assets, Manifest, Qualitätshinweise und CLI |
| Obsidian-Plugin | Auswahl, Konfiguration, Fortschritt, Vorschau, Öffnen der Ergebnisse und Auslösen einer Konvertierung |
| CodexCLI | Indexierung und Retrieval der erzeugten Markdown-Datei |

Die Projekte kommunizieren über Dateien und eine versionierte CLI-/Manifest-Schnittstelle. Sie dürfen keine gegenseitigen internen Python- oder TypeScript-Module importieren.

Der hochwertige Rekonstruktionsschritt für komplexe Scanlayouts ist eine austauschbare, ausdrücklich aktivierte Providergrenze. Aktuell implementiert DocToMD dafür den OpenAI-API-Adapter mit `OPENAI_API_KEY`; ein späterer lokaler Inferenzserver soll ausschließlich diesen Adapter ersetzen. CLI, Seitenmarker, editierbares Markdown, lokale Validierung, Qualitätswarnungen und Manifest bleiben dabei unverändert. Die lokale Standardkonvertierung und Tesseract-OCR bleiben netzwerkfrei.

## Funktionale Anforderungen

### Digitale PDFs

- Text in nachvollziehbarer Lesereihenfolge extrahieren.
- Überschriften, Absätze, Listen und einfache Tabellen nach Markdown übertragen.
- Seitenmarker oder äquivalente Metadaten bewahren.
- Eingebettete bzw. sichtbare Abbildungen als Assets exportieren und im Markdown referenzieren.
- Bildunterschriften nach Möglichkeit der jeweiligen Abbildung zuordnen.

### Gesannte PDFs

- Wenn kein verwertbarer Textlayer vorliegt, OCR als expliziten Verarbeitungsschritt verwenden.
- OCR-Sprache, Seitenbereich und Qualität im Manifest erfassen.
- Unsichere Ergebnisse als Warnung markieren.

### Bildsemantik

- Ein exportiertes Bild allein ist für textbasiertes RAG nicht ausreichend.
- Vorhandene Bildunterschriften übernehmen.
- Für relevante Diagramme und Screenshots eine editierbare Inhaltsbeschreibung als eigene Sidecar-Note im Asset-Ordner vorsehen. Die Haupt-Note verlinkt diese Note, übernimmt ihren Inhalt aber nicht automatisch.
- Ein konsumierender RAG-Indexer muss Sidecar-Notes unter `*.assets/**/*.md` ausdrücklich einbeziehen, wenn ihre fachlichen Beschreibungen recherchierbar sein sollen. DocToMD erstellt selbst keinen Index.

### Qualität und Rückverfolgbarkeit

- Jede Markdown-Passage, Tabelle und Abbildung muss nach Möglichkeit auf Seite und Originaldokument zurückverweisen.
- Warnungen für OCR, Lesereihenfolge, Tabellen- oder Bildzuordnung sichtbar im Manifest ausgeben.
- Wiederholte Konvertierung derselben unveränderten Quelle soll nachvollziehbar und idempotent sein.

## CLI-Vertrag (Zielbild)

Die Engine muss ohne Obsidian aufrufbar sein:

```powershell
python main.py convert "<input.pdf>" --output-dir "<zielordner>"
```

Der finale CLI-Vertrag wird in Phase 2 festgelegt. Er soll mindestens Eingabepfad, Ausgabeordner, OCR-Modus, Sprache, maschinenlesbares Ergebnis und Exit-Codes definieren.

## Konvertierungsmanifest

Neben Markdown und Assets erzeugt jede erfolgreiche oder teilweise erfolgreiche Konvertierung ein JSON-Manifest. Es enthält mindestens:

- Pfad, Hash, Größe und Änderungszeit der Primärquelle,
- Typ und Versionen der verwendeten Konvertierungs-, OCR- und Layoutkomponenten,
- erzeugte Markdown-Datei und Assets,
- Seitenzuordnung von Text, Tabellen und Abbildungen,
- verwendete OCR-Sprache und relevante Parameter,
- Warnungen, Fehler, Qualitätsstatus und Zeitstempel.

Das Manifest ist die Grundlage für Aktualitätsprüfungen im späteren Obsidian-Plugin und für nachvollziehbare Indexierung in CodexCLI.

## Empfohlene Struktur

```text
DocToMD/
├─ AGENTS.md
├─ PROJECT.md
├─ TASKS.md
├─ README.md
├─ requirements.txt
├─ main.py
├─ app/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ config.py
│  ├─ models.py
│  ├─ conversion_service.py
│  ├─ pdf_extract.py
│  ├─ markdown_writer.py
│  ├─ manifest.py
│  └─ quality.py
└─ tests/
```

OCR, Tabellen- und Bildverarbeitung werden erst eingeführt, wenn ihre jeweilige Phase freigegeben ist. Dadurch bleibt das Grundgerüst testbar und die Abhängigkeiten kontrollierbar.

## Python-Umgebung

- Python 3.12 ist die verbindliche Entwicklungs- und CI-Version. Python 3.11
  bleibt die unterstützte Mindestversion.
- Virtuelle Umgebung: `.venv`.
- Lokale Verarbeitung als Standard.
- Die Abhängigkeitsverwaltung erfolgt über `requirements.txt`; die Datei
  enthält in Phase 1 bewusst keine externen Pakete. Neue Abhängigkeiten werden
  erst nach einer bewussten technischen Entscheidung mit kompatibler
  Versionsuntergrenze ergänzt.
