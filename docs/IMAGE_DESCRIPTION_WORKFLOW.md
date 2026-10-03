# Workflow für Bildbeschreibungen

Eine Bildbeschreibung ergänzt ein exportiertes Bildasset für die spätere Suche und das Retrieval. Sie ist eine editierbare Sidecar-Note, keine Änderung des Original-PDFs, des Bildassets oder der automatisch erkannten Bildunterschrift.

## Ablauf

1. In der Haupt-Note den Link „Bildbeschreibung bearbeiten“ direkt unter dem Bild öffnen.
2. Die stabile Datei `page-NNN-figure-MM-description.md` im zugehörigen `.assets`-Ordner bearbeiten. Dateiname, Asset-ID und Seitenbezug bleiben unverändert.
3. Unter „Kurzbeschreibung“ knapp festhalten, was sichtbar ist.
4. Unter „Fachliche Einordnung“ nur den Zusammenhang ergänzen, der für fachliche Suche oder Retrieval wichtig ist.
5. Unter „Sichtbare Details“ klar lesbare Beschriftungen, Legenden, Achsen, Abkürzungen oder Werte erfassen.
6. Unter „Unsicherheiten“ fehlende, unlesbare oder nicht sicher interpretierbare Informationen benennen.

## Regeln

- Nur belegbare Bildinhalte beschreiben; keine Werte, Beziehungen oder Schlussfolgerungen erfinden.
- Die vorhandene Bildunterschrift nicht stillschweigend ersetzen. Ergänzungen gehören in die Sidecar-Note.
- Die Haupt-Note bleibt kompakt: Der Beschreibungstext wird nicht automatisch als Alt-Text oder Fließtext kopiert.
- Ein RAG-Indexer muss `Quelle.assets/**/*.md` zusätzlich zur Haupt-Note einbeziehen, wenn Bildbeschreibungen recherchierbar sein sollen.
- Bei einer erneuten Konvertierung bleiben vorhandene Sidecar-Notes unverändert. Die Vorlage wird nur für eine noch nicht vorhandene Beschreibungsdatei angelegt.

## Entscheidungshilfe

Eine Beschreibung ist besonders sinnvoll für Diagramme, Tabellen als Bild, Screenshots, Prozessgrafiken und fachlich relevante Fotos. Rein dekorative oder bereits eindeutig aus der Caption verständliche Bilder können leer bleiben. Eine leere Vorlage ist kein Qualitätsfehler und behauptet keine Bildsemantik.
