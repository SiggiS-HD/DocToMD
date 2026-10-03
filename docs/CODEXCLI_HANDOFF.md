# Vereinbarung für die Übergabe an CodexCLI

DocToMD erzeugt strukturierte, seitenbezogene Markdown-Derivate. CodexCLI indexiert diese Dateien lokal über seine eigene CLI. Beide Projekte bleiben über Dateien und versionierte Ausgabeformate gekoppelt; sie importieren keine internen Python- oder TypeScript-Module voneinander.

## Übergabeobjekt auswählen

Der maßgebliche Übergabegegenstand steht im Top-Level-Feld `rag_indexing.recommended_markdown_path` des Manifests. Ohne vorhandenes Cloud-Derivat empfiehlt DocToMD das lokal erzeugte `Quelle.md`; ein bereits technisch validiertes `Quelle.cloud.md` wird nur bei messbar besser erhaltener Struktur empfohlen. Beide Varianten derselben Quelle dürfen nicht gleichzeitig indexiert werden, weil sie sonst inhaltlich doppelte Retrieval-Treffer erzeugen können. [Die Auswahlregel](RAG_INDEXING_RECOMMENDATION.md) ist transparent dokumentiert.

`Quelle.conversion.json` ist kein Indexdokument. Es ist die Prüf- und Aktualitätsgrundlage für den Aufrufer. Vor der Indexierung muss er prüfen, dass das gewählte Markdown existiert, als Artefakt im Manifest geführt wird und der Quellfingerabdruck noch zur unveränderten PDF-Primärquelle passt. Der Qualitätsstatus und die seitenbezogenen Warnungen bleiben sichtbar; ein Status `warning` verhindert die Übergabe nicht automatisch, muss aber im Arbeitsablauf kenntlich sein.

Zusätzlich muss der Aufrufer `rag_readiness` berücksichtigen. Bei `local_not_suitable` wird das lokale Derivat nicht indexiert, bevor ein ausdrücklich gewählter Folgeschritt oder eine fachliche Prüfung erfolgt. Bei `review_required` wird nur `recommended_derivative_path` geprüft und anschließend bewusst indexiert. [Die automatische RAG-Eignungsprüfung](RAG_READINESS.md) löst selbst keine weitere Verarbeitung aus.

## Ausführung

Der Aufrufer liest den empfohlenen relativen Pfad aus `rag_indexing.recommended_markdown_path`, löst ihn gegen den Ausgabeordner auf und verwendet für genau dieses eine Markdown-Derivat den CodexCLI-Befehl `index_md` mit absolutem Pfad:

```cmd
cmd /V:ON /C ""<CodexCLI-Startskript>" index_md "<Ausgabedatei.md>""
```

Der Aufrufer prüft das Ergebnis von CodexCLI mit `index_md_status` für denselben Pfad. Aktualisiert sich das Derivat nach einer erneuten DocToMD-Konvertierung, wird `index_md` erneut ausgeführt. Die Indexierungsdaten bleiben unter der Verantwortung von CodexCLI; DocToMD löscht, erstellt oder verändert keinen CodexCLI-Index.

## Geplanter Verzeichnis-Hook

CodexCLI kann später einen reinen Komfortbefehl wie `index_doctomd_output <ausgabeordner>` anbieten. Der Befehl erhält ausschließlich den Ordner einer einzelnen DocToMD-Konvertierung und führt intern die bereits beschriebene Auswahl aus; er ist keine neue DocToMD-CLI-Funktion und startet keine Konvertierung.

Der Hook muss das Manifest im angegebenen Ordner eindeutig bestimmen, dessen JSON lesen und `rag_indexing.recommended_markdown_path` gegen genau diesen Ordner auflösen. Er bricht mit einer verständlichen Diagnose ab, wenn das Manifest fehlt oder ungültig ist, das Feld fehlt, der empfohlene Pfad nicht existiert, außerhalb des Ordners liegt oder nicht mit einem Manifest-Artefakt übereinstimmt. Bei Erfolg ruft er genau einmal `index_md` für den aufgelösten Pfad auf und reicht dessen Ergebnis unverändert weiter.

Der Hook wählt nie anhand eines Dateinamens wie `Quelle.md` oder `Quelle.cloud.md`, durchsucht keine Unterverzeichnisse nach beliebigen Markdown-Dateien und indexiert keine Alternative zusätzlich. Bildbeschreibungs-Notes in `Quelle.assets` bleiben ein getrennter, ausdrücklich gewünschter Indexlauf. Die Prüfung des Quellfingerabdrucks, des Qualitätsstatus und der sichtbaren Warnungen bleibt vor dem Aufruf Teil des Workflows; der Hook darf diese Befunde nicht als fehlerfreie Konvertierung interpretieren.

## Seitenbezug und Chunking

`<!-- doctomd:page=N -->` bleibt im zu übergebenden Markdown erhalten. Ein konsumierender Chunker muss diesen Marker zusammen mit jedem daraus gebildeten Chunk bewahren, damit Treffer auf die Ursprungsseite zurückgeführt werden können. Tabellen- und Bildmarker sowie ihre relativen Asset-Pfade dürfen nicht entfernt werden. Detailregeln stehen im [Vertrag für Seitenreferenzen](PAGE_REFERENCE_CONTRACT.md).

Überschriften, Absätze, Listen und Tabellen dienen als primäre Chunk-Grenzen. Starre Zeichenlimits dürfen nur als Fallback innerhalb eines zu großen Strukturblocks eingesetzt werden. Mehrspalten-, Formel-, OCR- und Referenzwarnungen aus dem Manifest sind Qualitätskontext und keine zu indexierenden Tatsachenbehauptungen.

## Bildbeschreibungen

Die Haupt-Note bleibt ohne kopierten Sidecar-Text. Sollen fachliche Bildbeschreibungen recherchierbar sein, indexiert der Aufrufer den spezifischen Asset-Ordner zusätzlich und getrennt:

```cmd
cmd /V:ON /C ""<CodexCLI-Startskript>" index_md "<Asset-Ordner>""
```

Der Ordner enthält Bilddateien und `*.md`-Sidecar-Notes; der Markdown-Indexer verarbeitet nur die Notes. Die Entscheidung folgt [dem Workflow für Bildbeschreibungen](IMAGE_DESCRIPTION_WORKFLOW.md). Nicht beschriebene oder rein dekorative Bilder erzeugen keinen künstlichen Retrieval-Inhalt.

## Grenzen

DocToMD erstellt keinen RAG-Index, führt keine Suche aus und löst keinen CodexCLI-Prozess automatisch aus. CodexCLI verändert weder die Primärquelle noch die DocToMD-Artefakte. Eine erfolgreiche Indexierung ist keine Behauptung, dass die PDF fehlerfrei rekonstruiert wurde; die maßgeblichen Grenzen stehen weiterhin im Conversion-Manifest.
