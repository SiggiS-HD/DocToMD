---
title: "DocToMD – Engineering Notes"
type: engineering-notes
status: aktiv
created: 2026-09-14
updated: 2026-10-02
tags:
  - doctomd
  - engineering
  - architektur
---

# Engineering Notes

Diese Note hält technische Hintergründe, relevante Entscheidungen, verworfene Alternativen, Schnittstellenbezüge und bekannte Grenzen fest. Sie ergänzt [[PROJECT]], [[TASKS]] und [[README]], ersetzt diese Dateien aber nicht.

## Fortschreibungsregel

Eintragungen erfolgen, wenn eine Umsetzung eine längerfristig relevante Entscheidung, Annahme, Abhängigkeit, Schnittstelle oder Einschränkung einführt oder verändert. Für jeden Kalendertag wird genau ein Tagesabschnitt der Ebene 2 angelegt. Seine Einträge erhalten darunter eine pro Tag bei `01` beginnende, zweistellige Ordnungsnummer der Ebene 3. Jeder Eintrag beschreibt mindestens Kontext, Entscheidung beziehungsweise Erkenntnis sowie die Auswirkung.

## 2026-09-14
## Projektgrundlage - Stabile CLI und Datenmodell

### 01 – Projekt- und Schnittstellengrenzen

**Kontext:** DocToMD soll von Obsidian und CodexCLI nutzbar sein, ohne an eine dieser Anwendungen gekoppelt zu werden.

**Festlegung:** DocToMD bleibt eine eigenständige lokale Python-Engine. Die Integration erfolgt ausschließlich über die versionierte CLI sowie erzeugte Dateien und das Konvertierungsmanifest. Gegenseitige interne Imports mit einem Obsidian-Plugin oder CodexCLI sind ausgeschlossen.

**Auswirkung:** Die Engine muss vollständig über die lokale CLI nutzbar und testbar bleiben. Anforderungen an externe Konsumenten werden als stabiler CLI- und Manifest-Vertrag umgesetzt.

### 02 – Python- und Abhängigkeitsstrategie

**Kontext:** Das Projekt benötigt eine verlässliche, kontrollierte Grundlage, bevor PDF-, OCR- oder Layoutbibliotheken eingeführt werden.

**Festlegung:** Python 3.12 ist die Entwicklungs- und CI-Version; Python 3.11 ist die unterstützte Mindestversion. Abhängigkeiten werden ausschließlich über `requirements.txt` verwaltet. In Phase 1 enthält die Datei bewusst keine externen Pakete.

**Auswirkung:** Neue Abhängigkeiten benötigen vor ihrer Aufnahme eine dokumentierte technische Entscheidung mit kompatibler Versionsuntergrenze. Schwere OCR-, Layout- oder ML-Abhängigkeiten werden nicht stillschweigend installiert.

### 03 – Umgang mit Quellen und abgeleiteten Artefakten

**Kontext:** Die Konvertierung soll nachvollziehbar sein und darf keine Originalinformationen gefährden.

**Festlegung:** Das Originaldokument ist eine unveränderte Primärquelle und wird niemals überschrieben oder gelöscht. Markdown, Assets und Manifest sind versionierte abgeleitete Artefakte.

**Auswirkung:** Die künftige Pfadvalidierung und Konfliktstrategie müssen Schreibzugriffe auf die Originalquelle verhindern und die Herkunft der abgeleiteten Dateien nachvollziehbar machen.

### 04 – Minimaler CLI-Vertrag für Konvertierungen

**Kontext:** Externe Aufrufer benötigen schon vor der PDF-spezifischen Umsetzung einen eindeutigen Einstiegspunkt für Konvertierungen.

**Festlegung:** Der öffentliche Befehl lautet `doctomd convert INPUT.pdf --output-dir AUSGABEORDNER`. Der Eingabepfad und `--output-dir` sind Pflichtargumente. Die CLI akzeptiert den Befehl bereits, führt aber bis zur späteren Implementierung keine Konvertierung aus und meldet diesen Zustand als Fehler.

**Auswirkung:** Obsidian und CodexCLI können den Grundaufbau der Schnittstelle frühzeitig berücksichtigen. Optionen für Ausgabeformat, Konfliktverhalten und OCR werden in den nachfolgenden Aufgaben ergänzt.

### 05 – Ausgabeformat und Konfliktverhalten

**Kontext:** Der CLI-Vertrag muss vor dem Schreiben von Artefakten eindeutig festlegen, welche Ausgabe erzeugt wird und wie vorhandene Derivate geschützt werden.

**Festlegung:** `--output-format markdown` ist das einzige derzeit unterstützte Ausgabeformat und zugleich der Standard. `--on-conflict error` ist der Standard und bricht bei vorhandenen abgeleiteten Artefakten ab. `update` ist für eine nachvollziehbare Aktualisierung anhand des späteren Manifests reserviert; `overwrite` ersetzt Artefakte nur nach expliziter Angabe.

**Auswirkung:** Die Standardausführung kann keine bestehenden abgeleiteten Daten unbemerkt ersetzen. Die konkrete Prüfung und Durchsetzung des Konfliktverhaltens folgt mit der Artefaktverwaltung in Phase 3.

### 06 – OCR-Optionsmodell

**Kontext:** Der CLI-Vertrag soll die künftige OCR-Steuerung festlegen, ohne vorzeitig ein bestimmtes OCR-Backend oder schwere Abhängigkeiten einzuführen.

**Festlegung:** `--ocr-mode auto` ist der Standard und löst künftig OCR nur aus, wenn der Textlayer nicht verwertbar ist. `off` unterbindet OCR vollständig; `force` verlangt sie ausdrücklich. `--ocr-language` nutzt eine einzelne BCP-47-Sprachkennung und hat `de` als Standard. Die Zuordnung zu backendabhängigen Sprachcodes erfolgt erst im jeweiligen Adapter.

**Auswirkung:** Aufrufer können ihr OCR-Verhalten bereits stabil angeben. Die Entscheidung für ein Backend, die Textlayer-Bewertung und die OCR-Ausführung bleiben in Phase 6 isoliert und kontrollierbar.

### 07 – Unveränderliche Domänenmodelle

**Kontext:** CLI, Manifest, Extraktion und Qualitätshinweise benötigen vor der PDF-spezifischen Umsetzung dieselbe präzise Sprache für Quellen und abgeleitete Artefakte.

**Festlegung:** Die Modelle `SourceDocument`, `PageReference`, `Asset`, `ConversionWarning` und `ConversionResult` sind unveränderliche Dataclasses. Seitenzahlen sind einsbasiert. Abgeleitete Pfade werden als relative POSIX-Pfade gespeichert, während die lokale Primärquelle als `Path` geführt wird. Quellfingerabdruckdaten sind optional und werden erst in Phase 3 ermittelt.

**Auswirkung:** Die Schnittstellen bewahren Herkunft und Seitenbezug von Beginn an, bleiben plattformübergreifend serialisierbar und verhindern ungültige Modellzustände frühzeitig.

### 08 – Maschinenlesbare CLI-Antworten und Exit-Codes

**Kontext:** Obsidian und andere Aufrufer müssen Konvertierungsergebnisse ohne Auswertung freier Konsolentexte verarbeiten können.

**Festlegung:** `--json` aktiviert einen versionierten JSON-Envelope auf `stdout` mit `schema_version`, `status`, `exit_code`, `result`, `warnings` und `error`. `success`/`0` steht für Erfolg, `warning`/`1` für Erfolg mit Qualitätswarnungen und `error`/`2` für Fehler. Ohne `--json` erscheinen lesbare Fehler auf `stderr`.

**Auswirkung:** Externe Aufrufer erhalten einen stabilen und explizit versionierten Rückkanal. Fehler beim Parsen einer unvollständigen Befehlszeile verwenden weiterhin die Standardfehlerausgabe von `argparse` und ebenfalls Exit-Code 2.

### 09 – Validierung von Ausgabewegen und Quellschutz

**Kontext:** Die CLI darf keine fehlerhaften Quelleingaben akzeptieren und muss schon vor der Artefakterzeugung einen Überschreibschutz für Primärquellen besitzen.

**Festlegung:** Die Quelle muss als vorhandene reguläre Datei vorliegen. Ein Ausgabeordner darf neu sein, benötigt aber einen vorhandenen Verzeichnisvorfahren und darf nicht auf eine Datei verweisen. Die wiederverwendbare Schutzfunktion `ensure_not_source_target` vergleicht jeden künftigen Schreibpfad kanonisch mit der Quelle und weist Gleichheit zurück. Der Ausgabeordner darf die Quelle enthalten, solange kein konkreter Schreibpfad auf sie zeigt.

**Auswirkung:** Übliche Workflows mit Quelle und abgeleiteten Artefakten im selben Ordner bleiben möglich; ein tatsächlicher Schreibvorgang auf die Primärquelle wird dennoch zuverlässig blockiert.

### 10 – Vertragstests für CLI und Pfadsicherheit

**Kontext:** Die in Phase 2 festgelegten CLI- und Sicherheitsregeln müssen vor dem Beginn der Artefakt- und PDF-Implementierung gegen unbeabsichtigte Änderungen geschützt werden.

**Festlegung:** Unit-Tests prüfen Pflichtargumente und Standardwerte der CLI, explizite Optionen, JSON-Fehlerantworten, Quellen- und Ausgabewegvalidierung sowie den Schutz der Primärquelle.

**Auswirkung:** Änderungen an den öffentlichen Parametern oder der Pfadsicherheit werden früh erkannt, ohne externe Abhängigkeiten oder echte PDF-Fixtures zu benötigen.

## 2026-09-15

## Phase 3 – Manifest und Artefaktverwaltung
### 01 – Versioniertes Konvertierungsmanifest

**Kontext:** Abgeleitete Markdown-Dateien und Assets müssen unabhängig von der späteren Extraktionsimplementierung nachvollziehbar, prüfbar und von externen Aufrufern auswertbar sein.

**Festlegung:** Das formale Schema liegt unter `schemas/conversion-manifest.schema.json` und folgt JSON Schema Draft 2020-12. Die eigenständige Manifestversion heißt `manifest_schema_version` und startet mit dem festen Wert `1.0`; sie ist ausdrücklich von `schema_version` des CLI-JSON-Envelopes getrennt. Pflichtbereiche sind `source`, `conversion`, `artifacts` und `quality`. Sie enthalten den vollständigen Quellfingerabdruck, Zeiten und Komponenten der Verarbeitung, relative abgeleitete Pfade mit Seitenbezügen sowie Qualitätswarnungen und Fehler. Alle Objekte untersagen unbekannte Felder, damit Vertragsänderungen bewusst versioniert werden.

**Auswirkung:** Künftige Manifest-Erzeugung und -Validierung können auf einen präzisen, maschinenlesbaren Vertrag aufbauen. Der Quellfingerabdruck, die Namenskonventionen, das atomische Schreiben und die Konfliktlogik bleiben bewusst nachfolgende, getrennte Aufgaben.

### 02 – Reproduzierbarer Quellfingerabdruck

**Kontext:** Ein Manifest muss erkennen lassen, ob sein Markdown-Derivat noch zur unveränderten Primärquelle gehört.

**Festlegung:** `fingerprint_source` erzeugt aus einer vorhandenen regulären Datei ein `SourceDocument` mit kanonischem Pfad, MIME-Typ, Bytegröße, SHA-256-Hash und UTC-Änderungszeitpunkt. Der Hash wird in 1-MiB-Blöcken gebildet. Größe und Nanosekunden-Zeitstempel werden vor und nach dem Lesen verglichen; eine währenddessen veränderte Quelle führt zu einem sichtbaren Fehler statt zu einem unzuverlässigen Fingerabdruck.

**Auswirkung:** Die spätere Manifest-Erzeugung kann den vollständigen Quellzustand direkt übernehmen. Der Inhaltsschutz bleibt erhalten, da die Funktion die Quelle ausschließlich lesend öffnet.

### 03 – Stabile Namen abgeleiteter Artefakte

**Kontext:** Externe Aufrufer und spätere Wiederholungsläufe benötigen vorhersagbare Namen für die drei Artefaktarten, ohne dass diese bereits erzeugt werden.

**Festlegung:** `plan_artifact_paths` leitet alle Namen aus dem Basenamen der Quelle ab. `Dokument.pdf` wird zu `Dokument.md`, `Dokument.assets` und `Dokument.conversion.json` im Ausgabeordner. Der Basisname bleibt unverändert, einschließlich Leerzeichen, Unicode-Zeichen und weiterer Dateinamensbestandteile. Die Planung kanonisiert die Pfade und schützt jedes Ziel gegen Gleichheit mit der Primärquelle.

**Auswirkung:** Markdown, Assets und Manifest haben eine einfache, stabile Zuordnung zur Quelle. Das tatsächliche Anlegen der Verzeichnisse und Dateien bleibt Aufgabe des atomischen Schreibens.

### 04 – Atomisches Publizieren von Markdown und Manifest

**Kontext:** Unterbrochene Schreibvorgänge dürfen keine teilweise geschriebene Markdown- oder JSON-Datei als gültiges Derivat sichtbar machen.

**Festlegung:** `write_conversion_documents` schreibt jede Datei zunächst als UTF-8-Temporärdatei im jeweiligen Zielordner, leert den Puffer auf das Dateisystem und publiziert sie anschließend atomisch. Im Standardfall wird ein vorhandenes Ziel durch einen atomaren Hard-Link-Vorgang abgewiesen; mit explizitem `overwrite` ersetzt `os.replace` die fertige Datei. Markdown wird vor dem Manifest veröffentlicht, sodass das Manifest als Abschlussmarker dient. Der Schreiber schützt beide Ziele erneut gegen die Primärquelle.

**Auswirkung:** Leser sehen pro Datei entweder die vorherige oder die vollständig neue Fassung. Bei einem Fehler vor dem abschließenden Manifest bleibt ein möglicherweise vorhandenes Markdown-Derivat ohne Abschlussmarker zurück und kann nicht als vollständige Konvertierung gelten.

### 05 – Konflikt- und Wiederholungspolitik

**Kontext:** Wiederholte Konvertierungen dürfen bestehende abgeleitete Daten weder unbemerkt ersetzen noch eine unveränderte Quelle unnötig neu verarbeiten.

**Festlegung:** `--on-conflict error` bricht ab, sobald Markdown, Asset-Ordner oder Manifest bereits existieren. `update` akzeptiert nur ein vollständiges Markdown- und Manifest-Paar; es vergleicht darin kanonischen Pfad, SHA-256, Größe und zeitversetzten UTC-Zeitstempel mit der aktuellen Quelle. Bei Übereinstimmung wird das Derivat wiederverwendet, bei Abweichung eine Ersetzung angefordert. Unvollständige oder ungültige Manifeste werden nicht geraten, sondern verlangen `overwrite`. `overwrite` ist die einzige explizite Freigabe für eine Ersetzung ohne Fingerabdruckvergleich.

**Auswirkung:** Der Standard bleibt verlustfrei, `update` ist für unveränderte Quellen idempotent und `overwrite` macht eine potenziell ersetzende Aktion für Aufrufer sichtbar. Die Entscheidungsfunktion selbst verändert keine Dateien.

### 06 – Einheitliche Qualitätsausgabe

**Kontext:** Warnungen und Fehler aus Extraktion, OCR oder Layoutanalyse müssen für Menschen und externe Aufrufer identisch nachvollziehbar sein.

**Festlegung:** `build_quality_section` erstellt den schema-konformen Bereich `quality` des Manifests. Hinweise und Warnungen werden mit Code, Meldung, Schweregrad und optionalem Seitenbezug in `quality.warnings` gespeichert; Einträge mit Schweregrad `error` stehen in `quality.errors`. Der höchste Schweregrad bestimmt `ok`, `warning` oder `error`. `build_conversion_response` verwendet dieselbe Struktur für die CLI: `ok` wird zu `success`/0, `warning` zu `warning`/1 und `error` zu `error`/2.

**Auswirkung:** Manifest und CLI können nicht mehr unterschiedliche Qualitätsurteile über denselben Warnsatz liefern. Die spätere Konvertierungsorchestrierung muss nur noch ihre `ConversionWarning`-Einträge an beide Funktionen übergeben.

### 07 – Ablaufprüfungen für die Derivataktualität

**Kontext:** Die einzelnen Tests für Fingerabdruck und Konfliktentscheidung reichen nicht aus, um den späteren Update-Ablauf als Ganzes abzusichern.

**Festlegung:** Die Ablauf-Tests erzeugen ein vollständiges Markdown- und Manifest-Paar mit Quellfingerabdruck. Sie prüfen den vollständigen Pfad von der erneuten Fingerabdruckerstellung bis zur Update-Entscheidung: unveränderte Quelle führt zu Wiederverwendung, geänderter Inhalt zu Ersetzung und eine fehlende Quelle beendet den Ablauf vor der Entscheidung. Vorhandene Derivate werden bei fehlender Primärquelle nicht verändert.

**Auswirkung:** Die zentrale Aktualitätsgarantie ist als Verhalten getestet, nicht nur als Implementierungsdetail einzelner Module.

### 08 – Externe Evaluationsquellen für die PDF-Extraktion

**Kontext:** Die Auswahl einer PDF-Extraktionsbibliothek benötigt realistische digitale PDFs, ohne potenziell urheberrechtlich geschützte Dokumente als Repository-Fixtures zu versionieren.

**Festlegung:** Die folgenden Quellen aus einem lokalen, nicht versionierten Evaluierungsverzeichnis werden ausschließlich lesend für die manuelle Bibliotheksbewertung verwendet: `SentencePiece_D18-2012.pdf` für Zweispalten-Fließtext und Fußnoten, `Tokenizer_Unigram_P18-1007.pdf` für Zweispalten-Fließtext mit Tabelle sowie `Neff_Geschirrspüler_9001018584_F.pdf` für deutschsprachige Anleitungstexte, zwei Spalten und Listen. Die PDFs werden nicht kopiert, verändert oder in `tests/` aufgenommen.

**Auswirkung:** Die Bibliotheksauswahl kann an repräsentativen Layouts geprüft werden. Dauerhafte automatisierte Tests erhalten später kleine, rechtlich unbedenkliche eigene PDF-Fixtures.


## Phase 4 – MVP: digitale PDFs nach strukturiertem Markdown
### 09 – Auswahl der PDF-Extraktionsbibliothek

**Kontext:** Die MVP-Extraktion benötigt Text, Wortkoordinaten und eine nachvollziehbare Grundlage für spätere Seiten-, Tabellen- und Bildverarbeitung, ohne OCR- oder ML-Abhängigkeiten einzuführen.

**Festlegung:** `pdfplumber>=0.11.0,<1.0` ist die Bibliothek für die digitale PDF-Extraktion. Der Vergleich mit `pypdf` auf den drei externen Evaluationsquellen zeigte für die beiden wissenschaftlichen Zweispalten-PDFs eine natürlichere Textreihenfolge: `pdfplumber` begann jeweils mit dem Titel, während `pypdf` mit Fußzeilen begann. `pdfplumber` liefert außerdem Wortkoordinaten, die für eigene Leseordnungsheuristiken verfügbar sind. Die Tabelle in `Tokenizer_Unigram_P18-1007.pdf` wurde nicht automatisch erkannt; automatische Tabellenrekonstruktion wird daher nicht als Eigenschaft der Bibliothek angenommen. Beide Kandidaten zeigten in der Neff-Anleitung denselben fehlerhaften Umlaut bei der Textextraktion, obwohl der gerenderte Text korrekt ist; dies wird als quellspezifisches Qualitätsrisiko behandelt.

**Auswirkung:** Die nächste Implementierungsaufgabe kann seitenweise Text und Positionsdaten mit `pdfplumber` auslesen. Komplexe Tabellen und fehlerhafte Schriftkodierungen bleiben sichtbar zu warnende Grenzen und werden nicht stillschweigend korrigiert.

### 10 – Seitenweise Textextraktion und Leseordnung

**Kontext:** Die Markdown-Erzeugung benötigt Text mit nachvollziehbarem Seitenbezug; bei Zweispalten-PDFs darf die geometrische Zeilenreihenfolge nicht beide Spalten ineinander verschränken.

**Festlegung:** `extract_pdf_pages` erzeugt je PDF-Seite ein `ExtractedPage` mit einsbasierter Seitennummer, Rohtext, Wortanzahl und erkannter Spaltenanzahl. Die Funktion liest Wörter mit Positionsdaten, fasst sie zeilenweise zusammen und aktiviert die Spaltenheuristik nur bei mindestens drei überlappenden Zeilen auf jeder klar getrennten Seite. Dann wird der Kopfbereich, die linke und anschließend die rechte Spalte gelesen. Bei uneindeutigem Layout bleibt die geometrische Reihenfolge erhalten.

**Auswirkung:** Nachfolgende Struktur- und Markdown-Schritte erhalten eine kleine, testbare Seite-zu-Text-Schnittstelle. Mehrspaltige, gemischte oder komplexe Seiten bleiben eine später explizit zu warnende Qualitätsgrenze.

### 11 – Stabiler Seitenmarker-Vertrag

**Kontext:** Markdown muss seine Herkunft pro Seite bewahren, ohne den sichtbaren Inhalt mit technischen Überschriften zu verfälschen.

**Festlegung:** `PageMarker` verbindet im Strukturmodell eine `PageReference` mit einem Seitenmarker. Vor jeder extrahierten Seite steht im Markdown exakt der HTML-Kommentar `<!-- doctomd:page=N -->`, wobei `N` einsbasiert ist. `render_pages` akzeptiert ausschließlich streng aufsteigende und eindeutige Seitennummern; leere Seiten behalten ihren Marker.

**Auswirkung:** RAG-Aufrufer können jeden nachfolgenden Markdown-Abschnitt bis zum nächsten Marker auf eine Originalseite zurückführen. Die Kommentare bleiben im Markdown-Quelltext verfügbar, werden aber in üblichen Renderern nicht angezeigt.

### 12 – Grundlegende Strukturblöcke

**Kontext:** Der extrahierte Seitentext benötigt vor der finalen Markdown-Ausgabe eine kleine, nachvollziehbare Struktur für Überschriften, Absätze und Listen.

**Festlegung:** `DocumentBlock` führt Blockart, unveränderten Text und `PageReference`; Überschriften tragen zusätzlich ihre Markdown-Ebene und Listenelemente ihre Sortierung. `build_page_blocks` erkennt nummerierte Überschriften wie `2.1 Details` sowie `Abstract`, `References` und `Acknowledgements`. Zeilen mit Kugelzeichen oder Nummern werden als Listen erkannt. Alle übrigen aufeinanderfolgenden, nichtleeren Zeilen bilden einen Absatz; nur der Zeilenumbruch wird durch ein Leerzeichen ersetzt. `render_blocks` erzeugt daraus Markdown.

**Auswirkung:** Die MVP-Pipeline besitzt eine testbare Grundstruktur, ohne Worttrennungen, Schreibweisen oder Zeichen zu korrigieren. Komplexere Überschriftenformen und Absatzgrenzen bleiben bewusst Gegenstand der nächsten Qualitäts- und Normalisierungsschritte.

### 13 – Verlustarme Textnormalisierung

**Kontext:** PDF-Text kann unterschiedliche Zeilenenden und kanonisch gleichwertige Unicode-Darstellungen enthalten; automatische Eingriffe in Trennungen oder unbekannte Zeichen würden jedoch die Quelle verfälschen können.

**Festlegung:** `normalize_text` vereinheitlicht ausschließlich CRLF- oder CR-Zeilenenden zu LF und Unicode in die kanonische NFC-Form. Jede ausgeführte Umformung wird als Kennung zurückgegeben. Weiche Trennstriche, mögliche Trennungen über einen Zeilenumbruch und Ersatzzeichen bleiben unverändert und erzeugen je eine `ConversionWarning` mit Seitenbezug. `normalize_blocks` übernimmt diesen Vertrag für strukturierte Blöcke, ohne Art, Ebene, Sortierung oder Seitenreferenz zu verändern.

**Auswirkung:** Die spätere Konvertierung kann Zeichendarstellung verlässlich vereinheitlichen, ohne den Wortlaut stillschweigend zu verändern. Potenzielle Extraktionsfehler bleiben für Manifest, CLI und manuelle Prüfung sichtbar.

### 14 – Zusammengeführte digitale PDF-Konvertierung

**Kontext:** Die zuvor getrennt implementierten Schritte für Fingerabdruck, Extraktion, Strukturierung, Normalisierung, Markdown und Manifest müssen als reale CLI-Konvertierung zusammenwirken und ihre Ergebnisse atomisch veröffentlichen.

**Festlegung:** `convert_pdf` führt für digitale PDFs den vollständigen Ablauf aus: Quellfingerabdruck, Artefaktplanung und Konfliktentscheidung, seitenweise `pdfplumber`-Extraktion, Blockbildung, verlustarme Normalisierung, Markdown mit Seitenmarkern sowie Manifest- und Qualitätsausgabe. Die CLI `convert` gibt den bestehenden versionierten JSON-Vertrag weiter und meldet Konvertierungsfehler einheitlich. Ein Prüflauf mit `SentencePiece_D18-2012.pdf` erzeugte erfolgreich ein 24.543 Byte großes Markdown und ein 5.367 Byte großes Manifest, ohne die Quelle zu verändern.

**Auswirkung:** Die Engine kann digitale PDF-Textlayer nun lokal und reproduzierbar als Derivate bereitstellen. Die Sichtprüfung derselben zweispaltigen wissenschaftlichen PDF zeigt weiterhin zusammengezogene Wortabstände und einzelne unsichere Lesereihenfolgen. Diese bekannte Layoutgrenze wird im folgenden Fixture- und Qualitätsarbeitsschritt gezielt abgesichert und sichtbar bewertet, statt Text zu erfinden oder stillschweigend zu korrigieren.

### 15 – Eigene digitale PDF-Fixture für Regressionen

**Kontext:** Automatisierte PDF-Regressionen brauchen eine kleine, rechtlich unbedenkliche und dauerhaft versionierbare Eingabe, dürfen aber keine externen Evaluationsdokumente übernehmen.

**Festlegung:** `tests/fixtures/simple-digital.pdf` ist eine selbst erstellte, zweitseitige ASCII-PDF mit einfachen Überschriften und Absätzen. Der Regressionstest verarbeitet sie ohne Mock über die reale Konvertierung und prüft Seitenmarker, extrahierten Text, die Überschriftenform, die Seitenreferenzen im Manifest sowie einen warnungsfreien Qualitätsstatus.

**Auswirkung:** Änderungen an der digitalen Extraktionskette werden gegen ein reproduzierbares Minimalbeispiel erkannt. Die Fixture deckt absichtlich keine Tabellen, Bilder, Scans oder Mehrspaltenlayouts ab; diese bleiben getrennte Qualitäts- und OCR-Fälle.

### 16 – Sichtbare Grenzen bei Layout und Zeichendekodierung

**Kontext:** Die visuelle und inhaltliche Prüfung der drei externen Evaluationsquellen zeigte, dass aus Zweispalten-PDFs zwar Seitenmarker und großer Textanteil extrahiert werden, Wortabstände, Absatzgrenzen, Tabellen und Randmetadaten aber nicht zuverlässig rekonstruiert werden. Auf Bild- und Indexseiten der Neff-Anleitung sowie in wissenschaftlichen PDFs blieben zudem `(cid:...)`-Platzhalter bestehen.

**Festlegung:** Die Konvertierungsorchestrierung ergänzt für jede als zweispaltig erkannte Seite die seitenbezogene Warnung `MULTI_COLUMN_LAYOUT`; ein enthaltener `(cid:`-Platzhalter erzeugt `UNREADABLE_PDF_GLYPHS`. Beide Warnungen führen zu `partial` im Manifest und zum CLI-Status `warning`, ohne Text zu verändern oder zu erraten. Die reale Prüfung von `SentencePiece_D18-2012.pdf`, `Tokenizer_Unigram_P18-1007.pdf` und `Neff_Geschirrspüler_9001018584_F.pdf` bestätigte die Warnungen; die eigene einfache digitale Fixture bleibt warnungsfrei.

**Auswirkung:** Die digitale MVP-Ausgabe ist für einfache Text-PDFs lesbar und vollständig seitenmarkiert. Komplexe Spaltenlayouts, Tabellen, Formeln, Fußnoten und nicht dekodierbare Zeichen sind keine stillschweigend als hochwertig ausgegebenen Ergebnisse, sondern explizite Qualitätsgrenzen für die folgenden Phasen.

## Phase 5 – Bilder, Bildunterschriften und Tabellen
### 17 – Strategie für Abbildungen: natives Raster vor Seitenrendering

**Kontext:** PDF-Seiten können eingebettete Rasterbilder, vektorbasierte Diagramme und Tabellen sowie reinen Text enthalten. Ein pauschales Rendern jeder Seite zu einem Bild würde Text und Struktur duplizieren und ist für RAG nicht geeignet; eine reine Rasterobjekt-Extraktion erfasst dagegen keine Vektorgrafiken.

**Festlegung:** DocToMD extrahiert native, eindeutig dekodierbare Rasterbildobjekte vorrangig und ordnet sie über ihre Bounding Box der Seite zu. Sie erhalten stabile Namen nach `page-<NNN>-figure-<NN>.<ext>`. Falls ein sichtbares Rasterobjekt nicht sicher dekodierbar ist, wird ausschließlich dessen Bounding Box lokal als PNG gerendert. Eine ganze Seite wird nur dann als ein Asset gerendert, wenn sie praktisch bildbasiert ist und kein brauchbarer Textlayer vorliegt; sie erhält dann eine sichtbare Qualitätswarnung. Vektorgrafiken, Formeln und Tabellen werden in dieser Phase nicht als Bild erraten, sondern bleiben Gegenstand der jeweiligen Tabellen- und Qualitätsaufgaben.

**Auswirkung:** Eingebettete Bilder bleiben möglichst originalgetreu, während der Fallback eine überprüfbare Darstellung komplexer Bildobjekte ermöglicht. Die lokale Prüfung bestätigte 16 Rasterbildobjekte auf 6 von 48 Seiten der Neff-Anleitung; die beiden wissenschaftlichen Vergleichs-PDFs enthalten keine eingebetteten Rasterbilder und illustrieren damit die bewusste Abgrenzung zu vektorbasierten Inhalten.

### 18 – Stabiler Export nativer JPEG-Abbildungen

**Kontext:** Die gewählte Bildstrategie benötigt einen ersten sicheren, reproduzierbaren Exportpfad für tatsächlich eingebettete Rasterbilder, ohne deren Kodierung oder Darstellung zu verändern.

**Festlegung:** `export_embedded_images` übernimmt ausschließlich eingebettete JPEG-Streams mit ihrer originalen Bytefolge. Die Dateien werden atomisch und ohne Ersetzung in `<Dokument>.assets/page-<NNN>-figure-<NN>.jpg` veröffentlicht. Nicht-JPEG-Streams werden nicht mit einer geratenen Dateiendung gespeichert, sondern erzeugen die seitenbezogene Warnung `UNSUPPORTED_EMBEDDED_IMAGE`. Der Konvertierungslauf führt die exportierten Assets bereits im Ergebnisobjekt; ihre Markdown- und Manifestreferenzen sind der nachfolgende Arbeitsschritt.

**Auswirkung:** Der reale Prüflauf mit der Neff-Anleitung exportierte fünf direkt übernehmbare JPEGs, darunter die vollständig sichtgeprüfte Titelseitenabbildung. Elf weitere eingebettete Objekte blieben bewusst als Warnung offen, bis der festgelegte PNG-Render-Fallback umgesetzt wird. Die Quelle wurde ausschließlich gelesen.

### 19 – Einheitliche Referenzen für Bildassets

**Kontext:** Exportierte Dateien sind für RAG und externe Aufrufer nur nutzbar, wenn Markdown, Manifest und Assetdatei dieselbe Herkunft und stabile Kennung teilen.

**Festlegung:** Jedes exportierte Bild wird nach dem Text seiner Originalseite als Markdown-Bildlink mit dem technischen Kommentar `doctomd:asset=<id> page=<N>` ausgegeben. Das Manifest enthält dazu ein `assets`-Objekt und eine `content_references`-Referenz mit identischer Asset-ID und Seite. Eine Bildunterschrift wird nur übernommen, wenn unmittelbar unter dem Bild eine nahe Textzeile ausdrücklich mit `Figure`, `Fig.` oder `Abbildung` plus Nummer beginnt; andernfalls verwendet Markdown eine neutrale Kennung und das Manifest lässt `caption` aus.

**Auswirkung:** Die Neff-Prüfkonvertierung enthält fünf Markdown-Bildlinks, fünf Manifest-Assets und fünf Assetreferenzen, jeweils mit übereinstimmendem relativen Pfad und Seitenbezug. Die enge Caption-Regel verhindert falsche Zuordnungen; umfangreichere Caption-Heuristiken bleiben eine bewusst spätere Qualitätsverbesserung.

### 20 – Konservative Markdown-Übertragung einfacher Tabellen

**Kontext:** `pdfplumber` erkennt auf den Evaluationsquellen mehrere Tabellenkandidaten, darunter mehrzeilige zusammengefasste Zellen und nicht lesbar dekodierte Zeichen. Eine automatische Übertragung dieser Kandidaten würde plausibel wirkende, aber falsche Markdown-Tabellen erzeugen.

**Festlegung:** `extract_simple_tables` akzeptiert nur rechteckige Tabellen mit mindestens zwei Spalten, vollständig belegter Kopfzeile und Datenzeilen sowie einzeiligen, lesbar dekodierten Zellen. Akzeptierte Tabellen werden als GitHub-Flavored Markdown mit technischem Tabellen- und Seitenmarker ausgegeben; das Manifest enthält eine `table`-Content-Reference. Tabellen mit Lücken, mehrzeiligen Zellen oder `(cid:...)`-Platzhaltern werden nicht übertragen.

**Auswirkung:** Eine eigene Regression deckt die vollständige Übertragung einer einfachen Tabelle ab. Die wissenschaftlichen Vergleichstabellen und die fehlerhaft dekodierte Neff-Tabelle werden beim Realtest sämtlich abgewiesen. Sie bleiben damit für die folgende Aufgabe sichtbar zu warnende, statt stillschweigend verfälschte Fälle.

### 21 – Qualitätswarnungen für abgewiesene Tabellen

**Kontext:** Das bloße Auslassen komplexer Tabellen schützt vor falschem Markdown, ist für Aufrufer aber nicht nachvollziehbar genug: Sie müssen erkennen können, dass auf einer Seite ein nicht übertragener Tabellenkandidat vorlag.

**Festlegung:** Der Tabellenextraktor liefert ein Ergebnisobjekt aus akzeptierten Tabellen und Warnungen. Jede Seite mit einem oder mehreren abgewiesenen Kandidaten erzeugt genau eine seitenbezogene Warnung `UNSUPPORTED_TABLE_STRUCTURE` mit der Anzahl der Kandidaten. Diese Warnungen durchlaufen denselben Manifest-, CLI- und Teilstatusvertrag wie alle übrigen Qualitätswarnungen.

**Auswirkung:** Der Realtest mit `Tokenizer_Unigram_P18-1007.pdf` meldet zwei nicht sicher rekonstruierbare Kandidaten auf Seite 7 und vier auf Seite 8. Statt eine scheinbar korrekte Tabelle zu erzeugen, erhält der Aufrufer `partial`/`warning` mit überprüfbarem Seitenbezug.

## Neue Phase 6 – Wissenschaftliche PDFs und mathematische Inhalte
### 22 – Optionales lokales Vision-Backend für wissenschaftliche PDFs

**Kontext:** Der Vergleich mit dem vorhandenen ChatGPT-Derivat von `Tokenizer_Unigram_P18-1007.pdf` zeigt, dass eine reine Textlayer-Extraktion Formeln, komplexe Tabellen und wissenschaftliche Lesereihenfolge nicht ausreichend rekonstruiert. Im LAN steht nach Benutzerangabe LM Studio mit `qwen/qwen3.5-9b` zur Verfügung.

**Festlegung:** Die Wissenschaftsphase erhält ein optionales lokales Vision-Backend über einen konfigurierbaren LM-Studio-Endpoint. Es wird ausschließlich per explizitem Modus aktiviert und erhält nur Seitenbilder mit erkannten Qualitätsrisiken. Das Backend liefert kein freies Enddokument, sondern schema-konforme Vorschläge für strukturierte Inhalte, die DocToMD lokal validiert, mit Seitenbezug versieht und bei Unsicherheit sichtbar warnt. Endpoint, Modell-ID, Renderauflösung, Timeout und Ergebnisstatus gehören in den nachvollziehbaren Konfigurations- und Manifestvertrag; Zugangsdaten gehören weder in CLI-Ausgabe noch Manifest.

**Auswirkung:** Der lesende Test bestätigte die Modell-ID `qwen/qwen3.5-9b` am angegebenen LM-Studio-Endpoint. Eine schema-konforme Vision-Anfrage mit der ersten gerenderten Tokenizer-Paperseite überschritt jedoch das verwendete 120-Sekunden-Timeout. Die Einbindung benötigt daher adaptive Renderauflösung, konfigurierbare Timeouts und einen sichtbaren Timeout-Warnpfad. Die lokale Standardkonvertierung bleibt ohne Netzwerkzugriff und ohne Modellabhängigkeit reproduzierbar.

### 23 – Wählbarer OpenAI-Vision-Provider

**Kontext:** Für die lokale LM-Studio-Variante mit `qwen/qwen3.5-9b` steht nach Benutzerangabe keine GPU zur Verfügung. Der erste Vision-Test auf einer wissenschaftlichen Seite lief in das 120-Sekunden-Timeout. Der Benutzer verfügt außerdem über einen separaten OpenAI-API-Schlüssel und möchte OpenAI als alternative, ausdrücklich wählbare Verarbeitung zulassen.

**Festlegung:** Die Wissenschaftsphase führt einen providerneutralen Vision-Vertrag mit den auswählbaren Providern `none`, `lm-studio` und `openai`. `lm-studio` bleibt die lokale Variante und verwendet den konfigurierten LAN-Endpoint sowie `qwen/qwen3.5-9b`. `openai` ist ein expliziter Cloud-Opt-in und darf Seitenbilder nur für erkannte Qualitätsrisiken über die OpenAI-API verarbeiten. Der Schlüssel wird ausschließlich aus `OPENAI_API_KEY` gelesen und weder in Konfigurationsdateien, CLI-Ausgaben noch im Manifest gespeichert. Das Manifest darf Provider, Modell-ID, verarbeitete Seiten, Ausführungsmodus und Qualitätswarnungen festhalten, muss die Cloud-Übertragung aber nachvollziehbar ausweisen.

**Auswirkung:** Die lokale Standardkonvertierung bleibt mit `none` vollständig netzwerkfrei. Bei Auswahl von `openai` werden die betreffenden Seitenbilder an einen externen Dienst übertragen und können API-Kosten verursachen; diese Entscheidung wird nicht stillschweigend getroffen. Beide Provider müssen dieselbe versionierte JSON-Schnittstelle für Textvorschläge, LaTeX-Formeln, Tabellen, Captions, Seitenbezug und Konfidenz erfüllen, damit lokale Validierung und Warnungen unabhängig vom Anbieter wirken.

## 2026-09-16

## Phase 5 – Fortsetzung

### 01 – Editierbare Bildbeschreibungen als Sidecar-Dateien

**Kontext:** Exportierte Bilder und vorhandene Captions reichen für textorientiertes RAG nicht immer aus. Eine nachträgliche Inhaltsbeschreibung muss möglich sein, ohne die Primärquelle oder die eigentliche Bilddatei zu verändern.

**Festlegung:** Jedes exportierte Bild erhält im selben Asset-Ordner eine leere, UTF-8-kodierte Sidecar-Datei mit dem stabilen Namen `page-<NNN>-figure-<NN>-description.md`. Das Assetmodell und das Manifest führen deren relativen Pfad als `description_path`; das Ergebnis-Markdown verlinkt sie mit „Bildbeschreibung bearbeiten“. Der bisher optionale Wert `description` bleibt für eine spätere automatisierte oder externe Befüllung erhalten. Sidecar-Dateien werden atomisch erstellt und niemals stillschweigend ersetzt.

**Auswirkung:** Menschliche oder nachgelagerte Workflows erhalten einen sicheren, seiten- und assetgenau zuordenbaren Ort für editierbare Bildsemantik. Die Beschreibung selbst wird nicht erfunden und die Quelldatei bleibt unverändert.

### 02 – Durchgängige Regressionen für nichtlineare Inhalte

**Kontext:** Bildexport, Tabellenextraktion und Markdown-Rendering waren bereits einzeln getestet. Für externe Aufrufer ist jedoch entscheidend, dass ihre Grenzen im vollständigen Konvertierungsergebnis und Manifest erhalten bleiben.

**Festlegung:** Die Regressionen prüfen Bildreferenz, Caption, editierbaren Beschreibungslink und Manifest-Asset gemeinsam. Ein zusätzlicher Orchestrierungstest simuliert jeweils eine nicht exportierbare Abbildung und eine nicht sicher übertragbare Tabelle auf unterschiedlichen Seiten. Er verlangt den Teilstatus sowie beide seitenbezogenen Warnungen im Ergebnis und im Manifest.

**Auswirkung:** Änderungen, die Qualitätswarnungen auf dem Weg von den Extraktoren zur öffentlichen Schnittstelle verlieren, werden erkannt. Bilder und einfache Tabellen bleiben zugleich durch bestehende Einzel- und Integrationsfälle abgedeckt.

## Phase 6 – Fortsetzung

### 01 – Wissenschaftliche Regression-Fixture und Kriterien

**Kontext:** Die bisherigen wissenschaftlichen Vergleichsdokumente sind externe, nicht versionierte Prüfdaten. Eine dauerhafte Regression benötigt dagegen eine rechtlich unbedenkliche Eingabe, deren Layoutmerkmale gezielt und vollständig bekannt sind.

**Festlegung:** `tests/fixtures/scientific-two-column.pdf` wird aus `build_scientific_fixture.py` ausschließlich mit selbst verfasstem ASCII-Text und PDF-Grundobjekten erzeugt; dafür wird keine neue Abhängigkeit benötigt. Die einzelne Seite enthält Kopf- und Fußbereich, zwei Textspalten, eine Display-Formel und eine rechteckige Tabelle. `SCIENTIFIC_FIXTURE_EVALUATION.md` definiert prüfbare Mindestkriterien für Seitenbezug, Inhalte, Warnungen, Tabellen, Formel und die manuelle Layoutprüfung. Die reale Konvertierung liefert alle Referenzwerte und die erwartete Warnung `MULTI_COLUMN_LAYOUT` auf Seite 1.

**Auswirkung:** Die nächste Aufgabe kann Verbesserungen der wissenschaftlichen Leseordnung reproduzierbar messen, ohne urheberrechtlich geschützte Papers in den Testbestand aufzunehmen. Die Fixture legt außerdem LaTeX als verbindlichen Zielzustand für ihre Display-Formel fest; dessen Implementierung und Validierung bleiben die ausdrücklich noch offene Formel-Aufgabe.

### 02 – Leseordnung mit Kopf- und Fußbereich

**Kontext:** Die bisherige Zwei-Spalten-Heuristik ordnete alle Zeilen ausschließlich an der vertikalen Seitenmitte ein. Dadurch konnten Kopf- und Fußzeilen fälschlich vor, zwischen oder innerhalb der beiden Spalten erscheinen.

**Festlegung:** Die Extraktion behandelt den oberen und unteren zwölfprozentigen Seitenrand als geometrische Kopf- beziehungsweise Fußbereiche. Nur Zeilen im zentralen Bereich werden für die konservative Spaltenerkennung aufgeteilt. Bei klaren Spalten erscheinen Kopfzeilen zuerst, danach ein möglicher zentraler Vorspann, die vollständige linke und rechte Spalte, zentrale Nachträge und zuletzt die Fußzeilen. Eine Regression mit Mock-Koordinaten und die reale `scientific-two-column.pdf` sichern die Reihenfolge ab.

**Auswirkung:** Wissenschaftliche Seiten behalten Kopf- und Fußinformationen, ohne sie mit dem Spaltentext zu vermischen. Die Layoutwarnung bleibt bewusst bestehen, da Fußnoten, Randnotizen und komplexere Seiten weiterhin getrennt bewertet werden müssen.

### 03 – Konservative Textqualität für wissenschaftliche Absätze

**Kontext:** Die Spaltenreihenfolge allein erzeugt noch kein brauchbares Markdown: sichtbare vertikale Absatzabstände gingen verloren, und ein harter Bindestrich konnte nach dem Verbinden von Zeilen nicht mehr als mögliche Trennung erkannt werden.

**Festlegung:** Die PDF-Extraktion übernimmt einen vertikalen Abstand von mehr als dem Anderthalbfachen der mittleren Zeilenhöhe als Absatzgrenze. Rücksprünge beim Wechsel zwischen Spalten lösen keine Absatzgrenze aus. Der Blockaufbau verbindet einen expliziten weichen Trennstrich am Zeilenwechsel ohne Leerzeichen; harte Bindestriche bleiben unverändert und erzeugen bei unmittelbar anschließendem Wort eine Warnung `POSSIBLE_HYPHENATION_PRESERVED`. Gedankenstriche mit Leerzeichen werden nicht als Worttrennung fehlinterpretiert.

**Auswirkung:** Die wissenschaftliche Fixture enthält getrennte Markdown-Absätze für sichtbar getrennte Inhalte, während potenziell verlustbehaftete harte Trennungen nachvollziehbar bleiben. Die reale Konvertierung der Fixture hat nach dem Prüflauf ausschließlich die erwartete Mehrspaltenwarnung.

### 04 – Deterministische LaTeX-Strategie mit sichtbarem Fallback

**Kontext:** Die wissenschaftliche Fixture verlangt LaTeX für ihre Display-Formel. In der lokalen Umgebung sind neben `pdfplumber` keine Formel- oder PDF-Mathematikbibliotheken verfügbar. Eine freie Umwandlung von PDF-Text in LaTeX wäre daher nicht überprüfbar und könnte mathematische Inhalte erfinden.

**Festlegung:** `docs/FORMULA_STRATEGY.md` definiert einen lokalen, versionierten Parser für eine kleine ASCII-Grammatik als primären Weg. Er gibt nur vollständig geparste Kandidaten als `$...$` oder `\[...\]` aus; die Fixtureformel hat die verbindliche Darstellung `\[p(x) = \frac{\sum_i w_i x_i}{n}\]`. Nicht erkannte oder nicht vollständig validierbare Formeln bleiben als Originaltext erhalten und erhalten künftig `FORMULA_NOT_RECONSTRUCTED` mit Seitenbezug. Ein späteres Vision-Backend darf ausschließlich strukturierte, lokal zu validierende Vorschläge liefern.

**Auswirkung:** LaTeX ist verbindlich, aber nur bei nachweisbarer Rekonstruktion. Die nachfolgende Implementierung kann mit der kleinen Fixtureformel beginnen und muss für alle anderen Fälle einen sichtbaren, sicheren Fallback bewahren.

### 05 – Lokaler Parser für die Fixture-Display-Formel

**Kontext:** Der Benutzer möchte LaTeX nicht erst nach der Bewertung optionaler KI-Modelle erhalten. Die festgelegte Fixtureformel besitzt eine kleine, eindeutig prüfbare Textform und kann daher lokal verarbeitet werden.

**Festlegung:** `app.formula_parser` akzeptiert ausschließlich eigenständige Absatzblöcke der vollständigen Summenbruch-Grammatik. `p(x) = sum_i w_i * x_i / n` wird zu `$$p(x) = \frac{\sum_i w_i x_i}{n}$$`; der Delimiter ist für Display-Mathematik mit Obsidian kompatibel. Multiplikationszeichen werden innerhalb des bereits vollständig geparsten Zählers als mathematischer Zwischenraum wiedergegeben. Nicht passende Formeln und Formeltext innerhalb eines normalen Satzes bleiben unverändert. Unit-Tests und eine reale Konvertierung der wissenschaftlichen Fixture sichern Ausgabe und Seitenbezug.

**Auswirkung:** DocToMD erzeugt jetzt tatsächliches Display-LaTeX für den unterstützten Fall, ohne neue Abhängigkeiten oder KI-Modelle. Die offene Aufgabe für nur zuverlässig rekonstruierbare Formeln bleibt bestehen, bis nicht unterstützte Formelkandidaten zusätzlich mit seitenbezogenen Warnungen erkannt werden.

### 06 – LM-Studio-Vision-Evaluierung: Serverantwort ausstehend

**Kontext:** Für die erste lokale Vision-Bewertung ist `qwen/qwen3.5-9b` am LAN-Endpoint `http://192.168.2.52:1234` geladen. Die native Modellabfrage bestätigt Vision-Fähigkeit, Q4_K_M-Quantisierung, Kontextlänge 8192, Evaluierungs-Batchgröße 8192, physischen Batch 512 und `parallel: 1`.

**Festlegung:** Die Evaluation verwendet ein lokales, mit 144 dpi gerendertes Bild der rechtlich unbedenklichen wissenschaftlichen Fixture, `reasoning: off`, `temperature: 0`, einen festen Seed und eine auf 200 bis 600 Tokens begrenzte JSON-Antwort. Mehrere Aufrufe an `/v1/chat/completions`, einschließlich einer Minimaltextanfrage, lieferten innerhalb von rund 90 Sekunden keinen Antwortkörper und keinen HTTP-Fehler. Der eigene Hintergrundlauf wurde danach beendet, ohne Modell- oder Servereinstellungen zu verändern.

**Auswirkung:** Die Konfiguration ist als Ausgangspunkt plausibel, aber die Qualitätsbewertung des Vision-Modells ist noch nicht möglich. Vor einem weiteren Versuch müssen Serverlog, Auslastung und die erfolgreiche Beantwortung einer kurzen Chat-Anfrage in LM Studio geprüft werden. Die Aufgabe bleibt offen.

### 07 – OpenAI-Vision-Evaluierung mit der wissenschaftlichen Fixture

**Kontext:** Als Vergleich zur lokalen LM-Studio-Variante sollte ein ausdrücklich freigegebener Cloud-Opt-in an genau einer selbst erzeugten, rechtlich unbedenklichen wissenschaftlichen Fixture getestet werden. Die [offizielle OpenAI-API-Referenz](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) beschreibt den Responses-Endpunkt für Bild- und Textinput; die [Modellübersicht](https://developers.openai.com/api/docs/models) nennt `gpt-5.6-terra` als ausgewogene Variante für Qualität und Kosten.

**Festlegung:** Der Test sendete ausschließlich das vorhandene PNG der einen Fixture-Seite (73 KB) als `input_image` an `gpt-5.6-terra`, mit `store: false` und einer auf 900 Tokens begrenzten Ausgabe. Die Aufforderung verlangte ausschließlich JSON zu Leseordnung, Display-Formeln, Tabelle und Unsicherheiten. `OPENAI_API_KEY` wurde nur aus der Prozessumgebung bezogen und weder protokolliert noch gespeichert. Der erste Aufruf wurde vor Bildverarbeitung mit HTTP 400 abgewiesen, weil dieses Modell `temperature` nicht akzeptiert; der zweite Aufruf ohne diesen Parameter war erfolgreich.

**Auswirkung:** Die Antwort war gültiges JSON und rekonstruierte die Formel als `p(x) = \frac{\sum_i w_i x_i}{n}`, die Tabelle `precision | 0.80` sowie `recall | 0.75` und die erwartete Kopf-, Spalten- und Fußreihenfolge. Der erfolgreiche Lauf verbrauchte 2.480 Eingabe- und 381 Ausgabetokens. Im Unterschied zu LM Studio war die Antwort nach rund neun Sekunden verfügbar. Der Provider ist dennoch kein Standardpfad: Jede ausgewählte Seite wird an OpenAI übertragen und verursacht nutzungsabhängige API-Kosten. Eine spätere Implementierung muss deshalb den expliziten Opt-in, `store: false`, Seitenminimierung, Timeout und lokale JSON-Validierung verbindlich erzwingen.

### 08 – LM-Studio-Vision-Evaluierung: Antwort und Formelgrenze

**Kontext:** Nach dem vorherigen clientseitig abgebrochenen Versuch wurde die lokale Evaluation von `qwen/qwen3.5-9b` mit unverändertem, 144-dpi-gerendertem Bild der eigenen wissenschaftlichen Fixture wiederholt. Die Anfrage war bewusst auf die sichtbare Display-Formel beschränkt, verlangte JSON mit `formula_latex`, verwendete `reasoning: off`, `max_tokens: 200`, `seed: 42` und hatte einen Client-Timeout von acht Minuten.

**Festlegung:** LM Studio lieferte nach rund acht Minuten eine regulär beendete Antwort mit gültigem JSON. Der Lauf verarbeitete 1.936 Prompt- und 27 Completion-Tokens. Die Antwort lautete `p(x) = \sum_i w_i * x_i / n`; sie erkannte somit die Summation, rekonstruierte den sichtbaren Bruch aber nicht und ließ das Quell-Multiplikationszeichen unverändert.

**Auswirkung:** Der lokale Provider ist erreichbar und kann schemaähnliches JSON liefern, ist unter der aktuellen CPU-basierten Konfiguration für diese Seite jedoch deutlich langsamer als der Cloud-Vergleich und mathematisch nicht ausreichend für eine automatische Formelübernahme. DocToMD darf diese Ausgabe nur als lokal zu validierenden Vorschlag behandeln; für die Fixture bleibt der deterministische lokale Formelparser maßgeblich. Ein späterer lokaler Provider muss mit mindestens acht Minuten Timeout oder einer niedrigeren Renderauflösung konfigurierbar sein; bei abweichender LaTeX-Validierung ist eine sichtbare Warnung erforderlich.

### 09 – Gemma-3-12B-Vergleich im lokalen Vision-Backend

**Kontext:** Als zweiter lokaler Kandidat stand am selben LM-Studio-Endpoint `google/gemma-3-12b` bereit. Die Metadaten weisen die Vision-Fähigkeit, die Q4_K_M-Quantisierung und eine Modellgröße von rund 8,15 GB aus. Der Vergleich verwendete exakt das 144-dpi-Fixturebild und dieselbe schmale Formelaufforderung wie der Qwen-Lauf.

**Festlegung:** Gemma beendete den Aufruf nach rund drei Minuten regulär mit 289 Prompt- und 37 Completion-Tokens. Die Antwort enthielt zwar einen JSON-ähnlichen Codeblock, verstieß aber gegen die Anforderung „nur JSON“, weil sie Markdown-Code-Fences enthielt. Nach dem Entfernen dieser Hülle blieb als Formel `p(x) = \sum_{i} w_i * x_i / n`; auch hier fehlen die Bruchdarstellung und die erforderliche Umformung des Multiplikationszeichens.

**Auswirkung:** Gemma ist unter dieser lokalen Konfiguration wesentlich schneller als Qwen, aber nicht zuverlässig genug für eine automatische Formelübernahme und nicht strikt genug für eine ungeprüfte JSON-Schnittstelle. Die spätere Providerintegration muss beide Fälle durch lokale JSON-Normalisierung beziehungsweise Validierung abweisen und die bekannte Formelgrenze als seitenbezogene Warnung ausweisen. Der lokale deterministische Parser bleibt für die unterstützte Fixtureformel verbindlich.

### 10 – Expliziter Vision-Konfigurationsvertrag mit Cloud-Opt-in

**Kontext:** Der gewünschte Fallback darf nur bei unsicherer lokaler Verarbeitung greifen und darf die lokale, netzwerkfreie Standardkonvertierung nicht verändern. Die [offizielle OpenAI-API-Referenz](https://developers.openai.com/api/reference/overview) verlangt zudem, API-Schlüssel als Geheimnis aus einer Umgebungsvariable oder einem Schlüsselmanagementdienst zu laden.

**Festlegung:** `app.vision_config.VisionConfig` führt die Provider `none`, `lm-studio` und `openai` sowie die Modi `off`, `auto` und `force` ein. Der sichere Standard ist verbindlich `none/off`. Eine aktive Konfiguration benötigt eine Modell-ID; sie führt außerdem Renderauflösung (72 bis 600 dpi) und Timeout (1 bis 3.600 Sekunden). Der LM-Studio-Endpoint ist ausschließlich für den lokalen Provider zulässig und muss eine absolute HTTP(S)-Basis-URL sein. Die CLI bildet den Vertrag mit `--vision-provider`, `--vision-mode`, `--vision-model`, `--vision-render-dpi`, `--vision-timeout-seconds` und `--lm-studio-endpoint` ab. Die öffentliche Konfigurationsdarstellung enthält keine Zugangsdaten; insbesondere gibt es weder eine CLI-Option noch ein Konfigurations- oder Manifestfeld für `OPENAI_API_KEY`.

**Auswirkung:** Eine Konvertierung bleibt ohne zusätzliche Optionen vollständig lokal und netzwerkfrei. `auto` kann im folgenden Verarbeitungsschritt gezielt unsichere Seiten an den explizit gewählten Provider übergeben, während `force` einen bewusst vollständigen Vision-Lauf beschreibt. Der Konfigurationsschritt selbst löst noch keine Netzwerkanfrage aus. 75 Unit-Tests sichern Standardwerte, Providergrenzen, Wertebereiche, CLI-Parsing und die Abwesenheit des API-Schlüssels aus der öffentlichen Konfiguration.

### 11 – Lokale Auswahl von Vision-Seiten nach Qualitätsrisiko

**Kontext:** Ein konfigurierter Cloud-Provider darf nicht dazu führen, dass jede Seite eines Dokuments übertragen wird. Die bestehende lokale Pipeline meldet wissenschaftliche Qualitätsrisiken bereits seitenbezogen, etwa `MULTI_COLUMN_LAYOUT`, `UNREADABLE_PDF_GLYPHS`, `UNSUPPORTED_TABLE_STRUCTURE` und `UNSUPPORTED_EMBEDDED_IMAGE`.

**Festlegung:** `app.vision_planner` erzeugt aus den lokalen Warnungen eine deterministische Seitenliste. Bei `none` oder `off` bleibt sie leer. Bei `auto` enthält sie nur vorhandene Seiten mit einem anerkannten wissenschaftlichen Risiko; bei `force` enthält sie alle vorhandenen Seiten. Die Liste wird als `vision_pages` am Konvertierungslauf und in der JSON-CLI-Antwort ausgegeben. Sie rendert keine Bilddaten und ruft keinen Provider auf.

**Auswirkung:** Die reale Konvertierung der wissenschaftlichen Fixture mit OpenAI-Provider im Modus `auto` plante ausschließlich Seite 1, weil deren Mehrspaltenwarnung bereits lokal vorlag. Unauffällige Seiten bleiben damit außerhalb eines späteren Cloud-Fallbacks. 79 Unit-Tests sichern die Auswahl für `none`, `off`, `auto` und `force` sowie die Integration in den Konvertierungslauf. Der folgende Schritt definiert erst das versionierte Antwortschema, bevor die ausgewählten Seiten tatsächlich gerendert und an einen Provider übergeben werden dürfen.

### 12 – Versionierter, providerneutraler Vision-Vorschlagsvertrag

**Kontext:** OpenAI und lokale Provider können unterschiedliche Antwortformen erzeugen. DocToMD benötigt deshalb vor jeder Providerintegration eine einheitliche, streng begrenzte Struktur, die Vorschläge von einer späteren lokalen Übernahme trennt.

**Festlegung:** `schemas/vision-proposal-1.0.schema.json` definiert den eigenständigen Vertrag `schema_version: "1.0"` für genau eine gerenderte Seite. Er verlangt die Bereiche `paragraphs`, `formulas`, `tables` und `captions`, auch wenn sie leer sind; unbekannte Felder sind ausgeschlossen. Jeder einzelne Vorschlag enthält eine einsbasierte Seite und eine Konfidenz von 0 bis 1. Formeln enthalten zusätzlich sichtbaren Quelltext und vorgeschlagenes LaTeX, Tabellen mindestens zwei Kopfzellen und eine Datenzeile, Captions optional nur einen unverbindlichen `target_hint` statt einer erfundenen Asset-ID.

**Auswirkung:** Adapter können künftig unabhängig vom Provider dieselbe Antwortstruktur liefern. Das Schema allein macht keine Inhalte vertrauenswürdig und übernimmt nichts in Markdown oder Manifest. `docs/VISION_PROPOSAL_SCHEMA.md` beschreibt die erforderliche nächste lokale Prüfung auf Seite, Konfidenz, Tabellenrechteck und sicher verwendbares LaTeX. Drei Vertragstests und die vollständige Regression mit 82 Tests sichern die Version, Pflichtbereiche und Grenzwerte.

### 13 – Konservative lokale Validierung von Vision-Vorschlägen

**Kontext:** Ein Provider kann trotz JSON-Aufforderung Code-Fences, falsche Seitenangaben, unvollständige Tabellen oder zu selbstsichere, nicht am lokalen Text belegbare Formeln liefern. Solche Vorschläge dürfen weder unbemerkt in Markdown noch in das Manifest gelangen.

**Festlegung:** `app.vision_validation` akzeptiert eine Antwort nur, wenn sie vollständig dem Vertrag `1.0` entspricht, ausschließlich die angefragte Seite nennt, alle Konfidenzen mindestens 0,85 betragen und jedes Tabellenrechteck vollständig ist. Für Formeln muss der vorgeschlagene Quelltext nach Whitespace-Normalisierung im lokalen Seitentext vorkommen; eigene Display-Delimiter sowie LaTeX-Dateibefehle werden abgewiesen. Jeder Fehler verwirft die vollständige Antwort und liefert eine seitenbezogene `ConversionWarning`: `VISION_BACKEND_UNREACHABLE`, `VISION_TIMEOUT`, `VISION_INVALID_JSON`, `VISION_LOW_CONFIDENCE` oder `VISION_UNVERIFIABLE_CONTENT`.

**Auswirkung:** Die bestehenden Qualitätsausgaben können die Warnungen ohne Sonderpfad in Manifest und CLI sichtbar machen. Eine hochkonfidente, vollständig belegbare Antwort bleibt nur als lokaler Validierungsausgang verfügbar; die folgende Formelaufgabe entscheidet separat über die konkrete Übernahme in Markdown. Vier neue Tests decken Annahme, JSON- und Versionsfehler, niedrige Konfidenz, Seiten- und Inhaltsabweichungen sowie beide Adapterfehler ab. Die vollständige Regression umfasst 86 Tests.

### 14 – Sichtbarer Fallback für nicht rekonstruierbare Formeln

**Kontext:** Der lokale Parser unterstützt absichtlich nur eine kleine, vollständig prüfbare Summenbruch-Grammatik. Wissenschaftliche PDFs enthalten jedoch auch Matrizen und andere Gleichungen, deren LaTeX aus dem Textlayer nicht ohne Raten abgeleitet werden kann.

**Festlegung:** `app.formula_parser` unterscheidet nun zwischen sicher geparsten Formeln und kurzen, eigenständigen Gleichungskandidaten. Nur die vollständig geparste Summenbruchform wird als Obsidian-kompatibles `$$…$$` ausgegeben. Ein nicht unterstützter Kandidat wie `A = [a_ij]` bleibt unverändert und erzeugt `FORMULA_NOT_RECONSTRUCTED` mit der Herkunftsseite. Normale Fließtextabsätze mit Gleichheitszeichen werden nicht als Formel klassifiziert. Die Formelwarnung gehört zu den lokalen Visionrisiken und selektiert bei aktivem `auto` genau diese Seite für einen späteren Provider-Fallback.

**Auswirkung:** Markdown und Manifest unterscheiden verlässlich zwischen übertragener und unsicherer Mathematik, ohne LaTeX zu erfinden. Die wissenschaftliche Fixture rendert weiterhin ihre unterstützte Formel ohne Formelwarnung; ein Integrationsfall prüft Originaltext, seitenbezogene Warnung und Manifest. Weitere Regressionen prüfen die Kandidatengrenze sowie die automatische Seitenauswahl. Die vollständige Suite umfasst 90 Tests.

### 15 – Konservative Übertragung wissenschaftlicher Tabellen

**Kontext:** Die vorhandene Tabellenextraktion konnte einfache rechteckige Tabellen übertragen, fasste aber mehrzeilige Zellen und andere Strukturfehler in einer einzigen Warnung zusammen. Dadurch war weder klar, warum eine Tabelle ausgelassen wurde, noch konnte der Vision-Fallback diesen häufigen wissenschaftlichen Sonderfall gezielt auswählen.

**Festlegung:** `app.table_extract` überträgt rechteckige, vollständig belegte Tabellen jeder Spaltenzahl, sofern alle Zellen einzeilig sind. Mehrzeilige Zellen werden nicht zusammengezogen oder geraten: Sie erzeugen die seitenbezogene Warnung `MULTILINE_TABLE_CELLS`. Fehlende Zellen, ungleich lange Zeilen, unlesbare Glyphen und andere unklare Strukturen bleiben unter `UNSUPPORTED_TABLE_STRUCTURE`. Beide Warnungen werden pro Seite separat zusammengefasst. `MULTILINE_TABLE_CELLS` ist ein Vision-Risiko und selektiert bei aktivem `auto` diese Seite für den späteren, ausdrücklich gewählten Provider.

**Auswirkung:** Eine sichere dreispaltige wissenschaftliche Tabelle wird vollständig als Markdown-Tabelle übertragen. Mehrzeilige oder strukturell nicht belegbare Tabellen bleiben sichtbar als Quelle erhalten und werden nicht stillschweigend verfälscht. Unit-Tests prüfen die Dreispaltenübertragung, beide Warnklassen und die Seitenauswahl. Die visuelle Prüfung der gerenderten Fixture sowie die reale Konvertierung bestätigen die Tabelle `Metric | Value`; die vollständige Regression umfasst 92 Tests.

### 16 – Nachvollziehbare Referenzen ohne erfundene Ziele

**Kontext:** Wissenschaftliche Markdown-Derivate benötigen für Zitationen, Fußnoten und Verweise auf Abbildungen oder Tabellen mehr als den unveränderten Fließtext: Ein späterer Konsument muss Quelle und, falls sicher möglich, Zielseite nachvollziehen können. Die bisherige Konvertierung enthielt dafür kein Strukturmodell.

**Festlegung:** `app.reference_analysis` erfasst ausschließlich sichtbare, enge Muster: nummerierte Zitationen `[n]` mit einer sichtbaren Literaturdefinition, Fußnoten `[^n]` mit einer sichtbaren Definition sowie `Figure`/`Fig.`- und `Table`-Verweise mit einer vorhandenen, stabil nummerierten Abbildung beziehungsweise Tabelle. Jeder Eintrag erhält die Quellseite sowie nur bei belegtem Ziel dessen Seite und stabile Asset- oder Tabellen-ID. Die Liste steht als `artifacts.references` im Manifest. Ein sichtbarer Marker ohne eindeutiges Ziel bleibt unverändert und erzeugt die seitenbezogene Warnung `UNRESOLVED_DOCUMENT_REFERENCE`.

**Auswirkung:** Die wissenschaftliche Fixture löst ihren sichtbaren Verweis `Table 1` auf Quelle Seite 1, Zielseite 1 und `page-001-table-01` auf. Tests decken Zitationen, Fußnoten, Abbildungs- und Tabellenverweise sowie fehlende Ziele ab; die visuelle PDF-Prüfung bestätigt, dass der Referenztext und die Tabelle unverändert lesbar bleiben. Die vollständige Regression umfasst 95 Tests.

### 17 – Wissenschaftliche End-to-End-Regression und Sichtprüfung

**Kontext:** Einzeltests für Formel-, Tabellen- und Referenzmodule schützen deren lokale Regeln, sichern aber nicht den vollständigen Konvertierungsweg der wissenschaftlichen PDF-Fixture einschließlich Manifest und Qualitätssignal.

**Festlegung:** `tests/test_scientific_fixture_regression.py` konvertiert die versionierte Fixture in einen neuen temporären Ausgabeordner und prüft Seitenmarker, Kopf- und Fußreihenfolge, das unterstützte Display-LaTeX, alle Tabellenzellen, die aufgelöste Tabellenreferenz sowie exakt die erwartete Warnung `MULTI_COLUMN_LAYOUT`. Die Evaluationsnote verlinkt diesen Test als verbindlichen inhaltlichen Prüfschritt. Zusätzlich wird die Originalseite mit Poppler gerendert und visuell auf Überschneidungen, abgeschnittene Inhalte, Kopf/Fußbereich, Spalten, Formel und Tabelle kontrolliert.

**Auswirkung:** Die wissenschaftliche Phase besitzt nun eine wiederholbare Gesamtprüfung gegen die ursprüngliche, rechtlich unbedenkliche Seite. Die aktuelle Sichtprüfung zeigt keine Layoutfehler; die Strukturgrenze der Mehrspaltenseite bleibt bewusst als einzige Qualitätswarnung erhalten. Die vollständige Suite umfasst 96 Tests.

### 18 – Vision-Ausführung als überprüfbarer Vorschlagskanal

**Kontext:** Die reale Konvertierung des ausgewählten Tokenizer-Papers zeigt, dass der digitale Textlayer für komplexe Tabellen, mathematische Glyphen und zweispaltige Leseordnung nicht genügt. Die bestehende Vision-Konfiguration plant zwar Risikoseiten, rendert sie aber noch nicht und ruft keinen Provider auf.

**Festlegung:** Die Fortsetzung von Phase 6 führt den OpenAI-Vision-Lauf nur bei ausdrücklich aktivem Provider ein. Jede geplante Seite wird lokal gerendert, einzeln mit `store: false` und dem versionierten JSON-Schema angefragt und vor jeder weiteren Verwendung durch die bestehende lokale Validierung geprüft. Akzeptierte Antworten werden zunächst als abgeleitete, seitenbezogene Vorschlagsdateien abgelegt. Sie ersetzen weder Original-PDF noch lokales Markdown. Erst ein folgender, gesonderter Schritt darf validierte Vorschläge nach einer expliziten Übernahmeregel in ein neues Markdown-Derivat integrieren; verworfene Antworten erhalten anschließend eine Review-Datei.

**Auswirkung:** Der Cloud-Opt-in bleibt datensparsam, kosten- und seitenbezogen nachvollziehbar. Ein Modell kann ungenaue oder unvollständige PDF-Extraktion verbessern, ohne dass seine Antwort als verlustfreie Wahrheit ausgegeben wird. Für die API-Ausführung wird der Responses-Endpunkt mit Bildinput und schemaerzwungener Struktur verwendet, wie in der [offiziellen OpenAI-API-Referenz](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses) beschrieben.

### 19 – Opt-in OpenAI-Ausführung mit validierten Seitenvorschlägen

**Kontext:** Die Vision-Planung und die Validierung waren vorhanden, wurden aber von der Konvertierung nicht ausgeführt. Damit konnten die erkannten Risikoseiten eines realen wissenschaftlichen Dokuments nicht als überprüfbare Modellvorschläge vorliegen.

**Festlegung:** `app.vision_render` erzeugt pro ausgewählter Seite ein temporäres PNG mit lokalem Poppler. `app.openai_vision` sendet dieses Bild ausschließlich bei aktivem OpenAI-Provider an `POST /v1/responses`, liest den Schlüssel nur aus `OPENAI_API_KEY`, setzt `store: false` und fordert das bestehende JSON-Schema per Structured Outputs an. `app.vision_service` validiert jede Antwort lokal und legt nur akzeptierte Antworten als `Quelle.vision-proposals/page-XXX.proposal.json` ab. Der Ordner ist ein konfliktgeschütztes abgeleitetes Artefakt, und seine relativen Pfade stehen im Manifest unter `artifacts.vision_proposals`. Render- oder Providerfehler werden als seitenbezogene Vision-Warnung sichtbar; sie brechen die lokale Konvertierung nicht ab.

**Auswirkung:** Die Standardkonvertierung bleibt vollständig lokal. Ein OpenAI-Lauf erzeugt noch kein geändertes Markdown, sondern eine überprüfbare Grundlage für die folgende Übernahmeregel. Der Adaptertest verwendet ausschließlich Mocks und bestätigt, dass nur lokal validiertes JSON geschrieben wird. Die vollständige Regression umfasst 97 Tests.

### 20 – Explizites Vision-Markdown-Derivat

**Kontext:** Ein gültiger Vision-Vorschlag darf nicht das lokale Markdown oder die Primärquelle ersetzen. Gleichzeitig müssen zuverlässig rekonstruierte Formeln und Tabellen für einen späteren Endbenutzer nutzbar werden.

**Festlegung:** `app.vision_merge` erzeugt ausschließlich ein zweites abgeleitetes Markdown `Quelle.vision.md`. Eine Formel wird nur ersetzt, wenn ihr bereits lokal validierter Quelltext exakt einmal im lokalen Markdown vorkommt. Tabellen erhalten keine erfundene Einfügeposition: Sie werden unter `# Vision-Ergänzungen` als mit Seite und Herkunft markierte Vorschläge angehängt. Der neue Pfad ist konfliktgeschützt und wird bei vorhandenen Vorschlägen unter `artifacts.vision_markdown_path` im Manifest gespeichert.

**Auswirkung:** Die reguläre Markdown-Ausgabe bleibt der überprüfbare lokale Stand. Das Vision-Derivat macht sichere Ergänzungen separat sichtbar, ohne den Eindruck einer verlustfreien Rekonstruktion zu erzeugen. Die vollständige Regression umfasst 98 Tests.

### 21 – Sichtbare Review für nicht übernommene Vision-Ergebnisse

**Kontext:** Ein Vision-Lauf kann durch Rendering, Providerantwort oder lokale Validierung scheitern. Ohne eigenes Artefakt wäre für Endbenutzer nicht erkennbar, welche Risikoseiten keinen automatisch übernehmbaren Vorschlag erhalten haben.

**Festlegung:** `app.vision_review` erzeugt bei einer Vision-Seitenauswahl `Quelle.vision-review.md`. Die Datei listet jede ausgewählte Seite, vorhandene akzeptierte Vorschläge und alle `VISION_*`-Warnungen auf. Sie wird konfliktgeschützt geschrieben und unter `artifacts.vision_review_path` im Manifest referenziert. Weder die Originalquelle noch das lokale Markdown werden dadurch verändert.

**Auswirkung:** Verworfene, ungültige oder nicht erreichbare Vision-Ergebnisse sind für eine manuelle Nachprüfung direkt sichtbar. Ein Unit-Test deckt akzeptierte und verworfene Seiten ab; die vollständige Regression umfasst 99 Tests.

### 22 – Reale OpenAI-Evaluation des Tokenizer-Papers

**Kontext:** Der Cloud-Fallback sollte gegen das ausdrücklich ausgewählte Paper `Tokenizer_Unigram_P18-1007.pdf` unter realen Bedingungen geprüft werden. Die lokale Textausgabe weist auf allen zehn Seiten wissenschaftliche Qualitätsrisiken auf; daher wählte der Modus `openai/auto` alle zehn Seiten aus.

**Festlegung:** Der saubere Evaluierungslauf verwendete `gpt-5.6-terra`, 144 dpi, `store: false` und einen Timeout von 120 Sekunden pro Seite. Er dauerte 174,8 Sekunden. Von zehn übertragenen Seiten wurde nur Seite 1 lokal akzeptiert; sie lieferte eine rechteckige Tabelle mit fünf Datenzeilen und eine Caption. Das separate Derivat `Tokenizer_Unigram_P18-1007.vision.md` hängt diese Tabelle als klar markierte Vision-Ergänzung an. Die Seiten 2 bis 10 wurden jeweils mit `VISION_INVALID_JSON` verworfen. Das Review und das Manifest nennen alle betroffenen Seiten. Der ursprüngliche Markdown-Export und die PDF-Primärquelle blieben unverändert.

**Kosten und Qualitätsgrenzen:** Die tatsächlich übertragenen zehn Seiten verursachen nutzungsabhängige OpenAI-API-Kosten. Der aktuelle Adapter speichert jedoch keine `usage`-Zähler der Responses-Antworten und der gewählte Modellbezeichner liefert hier keinen zuverlässig zuordenbaren öffentlichen Preis. Die exakten Kosten dieses abgeschlossenen Laufs sind deshalb nicht nachträglich belegbar und werden nicht geschätzt. Für künftige Läufe ist eine datensparsame Erfassung von Response-ID und Tokenzählern erforderlich. Die Evaluation belegt zugleich die zentrale Grenze: Structured Outputs allein garantiert keine lokal akzeptierbare Antwort; bei neun von zehn Seiten blieb der Fallback sichtbar verworfen. Er darf daher das lokale Markdown nicht automatisch ersetzen.

**Auswirkung:** Der OpenAI-Pfad funktioniert technisch und kann eine komplexe Tabelle sicher als separates, überprüfbares Derivat ergänzen. Für ein perfekt rekonstruiertes Paper reicht die aktuelle Vollseitenaufforderung und Validierungsgrenze jedoch nicht aus. Die vorhandenen Artefakte bilden einen nachvollziehbaren Referenzstand für eine spätere Verbesserung der Anfrage und der Kostenmessung.

## Phase 6 – Fortsetzung: Cloud-Dokumentkonvertierung

### 01 – Vollständige PDF als expliziter Cloud-Konvertierungsweg

**Kontext:** Die reale Seiten-Vision-Evaluation übertrug beim Tokenizer-Paper faktisch alle zehn Seiten, erzeugte aber nur einen akzeptierten Sidecar-Vorschlag. Das vom Benutzer bereitgestellte ChatGPT-Derivat zeigt hingegen, dass eine zusammenhängende Modellverarbeitung Formeln, Überschriften und Tabellen für dieses Dokument wesentlich brauchbarer wiedergeben kann. Der seitenweise, gegen den lokalen Textlayer geprüfte Vorschlagsvertrag ist daher nicht der geeignete Qualitätsweg für ein vollständiges Endnutzer-Markdown.

**Festlegung:** DocToMD erhält zusätzlich zum lokalen und zum bisherigen Vision-Sidecar-Pfad einen eigenständigen, nur per CLI aktivierbaren Cloud-Dokumentmodus. Er übergibt die unveränderte PDF genau einmal als OpenAI-`input_file` an den Responses-Endpunkt und setzt `store: false`. Der Prompt verlangt ausschließlich vollständiges Markdown mit einsbasierten `<!-- doctomd:page=N -->`-Markern, Überschriftenhierarchie, Markdown-Tabellen, `$$…$$`-Display-LaTeX und sichtbaren Unsicherheiten. Das Ergebnis wird ausschließlich als konfliktgeschütztes `Quelle.cloud.md` abgelegt; es ersetzt niemals `Quelle.md`, `Quelle.vision.md` oder die Primärquelle.

**Implementierungsschritte:**

1. Konfiguration und CLI erhalten einen expliziten Cloud-Dokumentmodus mit Modell, Timeout und einer sicheren Obergrenze für die Ausgabe; ohne diese Opt-in-Option findet keine Netzwerkanfrage statt.
2. Ein separater OpenAI-Adapter übergibt das PDF als Datei, wertet die Responses-Antwort aus und unterscheidet API-, Timeout-, Trunkierungs- und Markdown-Ausgabefehler.
3. Artefaktplanung, Konfliktprüfung und Manifest werden um `cloud_markdown_path` ergänzt. Das Manifest enthält Response-ID, Modell, Eingabe- und Ausgabetokens, Start- und Endzeit sowie nur dann einen Geldbetrag, wenn eine belastbare Preisquelle für das konkrete Modell konfiguriert ist.
4. Eine technische lokale Validierung prüft die vollständige Markdown-Antwort auf nichtleeren Inhalt, fortlaufende Seitenmarker, unzulässige Datei- oder HTML-Befehle und eine als unvollständig markierte API-Antwort. Sie verlangt keine Zeichen-für-Zeichen-Gleichheit zum lokalen PDF-Textlayer.
5. Mocks sichern Konfiguration, API-Payload, Usage-Erfassung, Fehlermeldungen, Manifest und Konfliktverhalten. Erst danach folgt ein einzelner realer Vergleichslauf gegen `Tokenizer_Unigram_P18-1007.pdf` und das vorliegende ChatGPT-Markdown als Qualitätsreferenz.

**Auswirkung:** Der Standardpfad bleibt lokal, datensparsam und netzwerkfrei. Wer eine vollständige Cloud-Rekonstruktion bewusst freigibt, erhält ein separates, messbares und überprüfbares Markdown-Derivat statt vieler serieller Seitenanfragen. Die semantische Qualität kann dadurch deutlich steigen, bleibt aber als Modellresultat kenntlich und wird mit Seitenmarkern, Usage, Laufzeit und erkannten Grenzen nachvollziehbar dokumentiert.

### 02 – Stabiler Opt-in-Vertrag für die Cloud-Dokumentkonvertierung

**Kontext:** Die vollständige Cloud-Verarbeitung benötigt vor jeder API- oder Dateiübertragung einen vom Vision-Sidecar unabhängigen, rückwärtskompatiblen und geheimnisfreien CLI-Vertrag. Große wissenschaftliche Dokumente benötigen außerdem klare Zeit- und Ausgabegrenzen.

**Festlegung:** `app.cloud_document_config.CloudDocumentConfig` führt den eigenständigen Modus `off|openai`. `off` ist der Standard und weist eine Modell-ID zurück; `openai` verlangt eine explizite Modell-ID. Die öffentliche CLI verwendet `--cloud-document-mode`, `--cloud-document-model`, `--cloud-document-timeout-seconds` und `--cloud-document-max-output-tokens`. Der Timeout liegt zwischen 1 und 3600 Sekunden und hat den Standard 900 Sekunden. Die Ausgabe ist auf 1024 bis 32768 Tokens begrenzt; der Standard und zugleich die sichere Obergrenze sind 32768 Tokens. Der Schlüssel bleibt vollständig außerhalb der Konfiguration: Ein künftiger Adapter darf ihn ausschließlich aus `OPENAI_API_KEY` lesen, aber weder CLI noch `public_options` noch Manifest enthalten ihn. Der neue Konfigurationswert wird durch die lokale Konvertierung geführt, löst in diesem Schritt aber ausdrücklich keine Netzwerkanfrage aus.

**Auswirkung:** Bestehende Aufrufe ohne Cloud-Option bleiben unverändert lokal und netzwerkfrei; der Vision-Provider bleibt ein separater Seitenvorschlagsweg. Aufrufer können die spätere vollständige Cloud-Konvertierung bewusst, mit begrenzter Antwortgröße konfigurieren. Unit-Tests sichern Standard, Opt-in, Modellpflicht, Wertebereiche, JSON-Fehlerausgabe und Geheimnisfreiheit. Die vollständige Regression umfasst 104 Tests.

### 03 – Einmaliger PDF-Transport mit temporärer File-ID

**Kontext:** Der Cloud-Dokumentmodus muss eine vollständige PDF für eine Responses-Anfrage bereitstellen, ohne Quelldaten, Zugangsdaten oder eine wiederverwendbare File-ID als lokales Artefakt zu hinterlassen. Der konkrete Markdown-Prompt gehört bewusst erst in den folgenden Arbeitsschritt.

**Festlegung:** `app.openai_cloud_document.request_document_response` liest `OPENAI_API_KEY` erst bei einem tatsächlichen Aufruf und ausschließlich aus der Umgebung. Es akzeptiert nur vorhandene PDF-Dateien bis 512 MiB, lädt sie einmal als Multipart-Upload mit `purpose=user_data` hoch und hält die erhaltene File-ID nur im Arbeitsspeicher. Die anschließende Responses-Payload verwendet `store: false`, die konfigurierte Ausgabeobergrenze sowie einen `input_file`-Eintrag mit dieser ID. Nach erfolgreicher Antwort ebenso wie nach einem Responses-Fehler versucht der Adapter im `finally`-Block, die hochgeladene Datei wieder zu löschen. Fehler beim bestmöglichen Löschen überdecken das Ergebnis der eigentlichen Anfrage nicht. Weder Schlüssel, Quelldaten noch File-ID werden in Konfiguration, Manifest oder abgeleiteten Dateien geschrieben.

**Auswirkung:** Ein späterer Prompt-/Ausgabeschritt kann die vollständige PDF zusammenhängend verarbeiten, ohne sie seitenweise zu rendern oder zu übertragen. Die Mock-Tests prüfen einmaligen Upload, `input_file`, `store: false`, fehlende Umgebungsvariable und das Löschen bei erfolgreich beantworteter oder fehlgeschlagener Responses-Anfrage. Die vollständige Regression umfasst 107 Tests.

### 04 – Versionierter Markdown-Prompt für vollständige Cloud-Dokumente

**Kontext:** Die vollständige PDF-Übergabe benötigt vor ihrer Anbindung an die Konvertierung einen präzisen Ausgabevertrag. Der Vertrag muss Strukturqualität fördern, ohne eine Zeichen-für-Zeichen-Prüfung gegen den lokalen Textlayer oder eine stillschweigende inhaltliche Erfindung zu verlangen.

**Festlegung:** `app.cloud_document_prompt.build_cloud_markdown_instructions` definiert den Vertrag `1.0` als `instructions` der Responses-Anfrage. Er verlangt ausschließlich UTF-8-Markdown ohne Vorbemerkung, Code-Fences, HTML-Wrapper oder Datei- und Shell-Befehle. Jede Originalseite erhält genau einen einsbasierten, aufsteigenden Marker `<!-- doctomd:page=N -->`, auch bei nicht wiederherstellbarem Text. Sichtbare Überschriftenhierarchie, Absätze, Listen, Zitationen, Fußnoten, Captions und Tabellen sollen erhalten bleiben. Inline- und Display-Mathematik verwenden `$…$` beziehungsweise `$$…$$`. Bei unlesbaren oder strukturell unsicheren Stellen verlangt der Vertrag einen sichtbaren Hinweis `> [!warning]`; Inhalte, Tabellenzellen, Formelteile oder Verlustfreiheit dürfen nicht erfunden oder behauptet werden. Der OpenAI-Adapter übergibt den Vertrag als `instructions`, während die PDF selbst weiterhin der einzige `input_file` bleibt.

**Auswirkung:** Prompt und Transport bleiben getrennt testbar und können künftig unabhängig versioniert werden. Der Adaptertest sichert `instructions`, `input_file`, `store: false` und Tokenobergrenze; Vertragstests sichern alle Struktur-, Mathematik-, Unsicherheits- und Sicherheitsregeln. Die vollständige Regression umfasst 109 Tests.

### 05 – Getrenntes, konfliktgeschütztes Cloud-Derivat

**Kontext:** Das Ergebnis einer vollständigen Cloud-Rekonstruktion muss nutzbar sein, ohne den lokalen Markdown-Export, bereits erzeugte Vision-Derivate oder die Primärquelle zu ersetzen. Auch ein teilweise implementierter Cloud-Pfad darf kein bestehendes Ergebnis stillschweigend überschreiben.

**Festlegung:** `ArtifactPaths` plant ergänzend den festen Namen `Quelle.cloud.md` und schützt ihn wie alle anderen Ziele erneut gegen Gleichheit mit der Primärquelle. Die Konfliktentscheidung betrachtet ein vorhandenes Cloud-Derivat als bestehendes abgeleitetes Artefakt; im Standardfall wird deshalb abgebrochen, und nur `--on-conflict overwrite` erlaubt eine Ersetzung. `write_cloud_markdown_derivative` publiziert das Derivat atomisch über den bestehenden quellsicheren Textartefaktschreiber. `build_manifest` nimmt optional `cloud_markdown_path` an; das Manifest und sein Schema speichern ausschließlich den relativen Pfad unter `artifacts.cloud_markdown_path`.

**Auswirkung:** Der künftige Cloud-Lauf kann sein Markdown konfliktgeschützt veröffentlichen, ohne `Quelle.md` oder die PDF zu berühren. Tests sichern Namensplanung, Konfliktfall, getrenntes Schreiben und die relative Manifestreferenz. Die vollständige Regression umfasst 112 Tests.

### 06 – Belegbare Cloud-Response-Telemetrie ohne Kostenschätzung

**Kontext:** Ein Cloud-Derivat muss für Endnutzer nachvollziehbar machen, welche Response es erzeugt hat, wie viele Tokens die API tatsächlich meldete und wie lange der Lauf dauerte. Ein Modellname oder eine Tokenzahl allein genügt nicht für eine belastbare Kostenbehauptung.

**Festlegung:** `CloudDocumentTelemetry` extrahiert aus einer erfolgreichen Responses-Antwort nur Response-ID, tatsächlich zurückgegebenes Modell sowie die optionalen Zähler `input_tokens`, `output_tokens` und `total_tokens`. Fehlende Zähler werden als `null` bewahrt und nie als null Kosten oder null Tokens gedeutet. Der Adapter misst UTC-Start-/Endzeit und eine monotone Laufzeit in Millisekunden über Upload und Responses-Anfrage. Das Manifest speichert diese Werte optional unter `conversion.cloud_document`. Ein Kostenbetrag wird grundsätzlich nicht geschätzt. `CloudCostEvidence` erlaubt eine Kostenangabe nur mit nichtnegativem Decimal-Betrag, absoluter HTTPS-Quellen-URL und zeitlich referenziertem Abruf; ohne dieses vollständige Belegobjekt fehlt das Feld `cost` vollständig.

**Auswirkung:** Der spätere integrierte Cloud-Lauf kann belastbare technische Usage im Manifest ausweisen, ohne File-ID, PDF-Inhalt, API-Schlüssel oder unbewiesene Preisannahmen zu speichern. Mock- und Manifesttests sichern Usage, fehlende Usage, Laufzeit und die strenge Kostenbelegregel. Die vollständige Regression umfasst 113 Tests.

### 07 – Technische Mindestvalidierung vor dem Cloud-Derivat

**Kontext:** Ein vollständiger Cloud-Output muss keine Zeichen-für-Zeichen-Kopie des lokalen Textlayers sein. Er muss jedoch technisch vollständig, seitenbezogen und ungefährlich als Markdown-Datei verwendbar sein, bevor er als abgeleitetes Artefakt veröffentlicht wird.

**Festlegung:** `validate_cloud_markdown_response` akzeptiert nur Responses mit `status: completed` und ohne `incomplete_details`. Der Status `incomplete`, insbesondere mit dem Grund `max_output_tokens`, wird als `CLOUD_RESPONSE_TRUNCATED` abgewiesen. Der Validator extrahiert den Text entweder aus `output_text` oder aus den dokumentierten verschachtelten `output[].content[].output_text`-Teilen. Er fordert nichtleeren Inhalt, den ersten relevanten Marker der Seite 1, ausschließlich alleinstehende und exakt formatierte Marker sowie eine lückenlose Sequenz. Optional lässt sich diese Sequenz gegen eine erwartete PDF-Seitenzahl prüfen. Code-Fences, `file:`-URLs sowie HTML-Dokument-, Script- und Iframe-Ausgabe werden als unzulässige Ausgabeformen verworfen. Jeder Fehler hat einen stabilen `CLOUD_*`-Code und verhindert die Derivatveröffentlichung.

**Auswirkung:** Die spätere Cloud-Orchestrierung kann strukturell unvollständige, abgeschnittene oder potenziell ausführbare Antworten sicher zurückweisen, ohne deren Markdown zu speichern. Vertragstests decken gültige Ausgabe, alternative Responses-Textform, leere und fehlerhafte Seitenmarker, verbotene Ausgabeformen, Trunkierung und Seitenzahlabweichung ab. Die vollständige Regression umfasst 118 Tests.

### 08 – Zusammenhängende Mock-Regressionen für den Cloud-Vertrag

**Kontext:** Die einzelnen Unit-Tests decken Konfiguration, HTTP-Adapter, Manifestfelder und Konfliktregeln bereits getrennt ab. Für den sicheren Dokumentmodus ist zusätzlich wichtig, dass diese Grenzen in ihrem gemeinsamen Ablauf nicht auseinanderlaufen.

**Festlegung:** `test_cloud_document_regression.py` simuliert den vollständigen HTTP-Transport lokal und prüft einen erfolgreichen Ablauf von der expliziten OpenAI-Konfiguration über `input_file`, technische Markdown-Validierung und das getrennte `Quelle.cloud.md` bis zur Manifest-Referenz samt Telemetrie. Eine unvollständige Antwort wird vor jedem Schreibvorgang abgewiesen. Ein vorhandenes Cloud-Derivat ist im Fehlermodus ein Konflikt und bleibt unverändert. Alle Fälle prüfen zusätzlich, dass Primärquelle und lokales Markdown unverändert bleiben.

**Auswirkung:** Der Cloud-Vertrag ist ohne Netzverkehr, echte Zugangsdaten oder reale Anbieterantworten zusammenhängend regressionsgesichert. Die vollständige Regression umfasst 121 Tests.

### 09 – Bereinigte HTTP-Fehlerdiagnose für Cloud-Anfragen

**Kontext:** Der erste freigegebene Realversuch mit dem Tokenizer-Paper erreichte nach dem PDF-Upload den Responses-Endpunkt, wurde dort aber mit HTTP 400 abgewiesen. Der bisherige Adapter zeigte nur den HTTP-Status und verwarf damit die für eine gezielte Korrektur erforderliche API-Ursache.

**Festlegung:** Bei `HTTPError` liest der Adapter ausschließlich das strukturierte OpenAI-Objekt `error.code` und `error.message`. Beide Werte werden auf eine einzelne, höchstens 500 Zeichen lange Meldung begrenzt; Bearer-Werte, schlüsselähnliche Kennungen und File-IDs werden durch `[redacted]` ersetzt. Die Antwort wird weder gespeichert noch im Manifest abgelegt. Nicht als JSON lesbare Fehlerantworten bleiben bei der bisherigen reinen HTTP-Statusmeldung. Der bestehende `finally`-Pfad zum bestmöglichen Löschen des temporären Uploads bleibt unverändert.

**Auswirkung:** Ein erneuter, ausdrücklich freigegebener Realversuch kann die serverseitige Ursache sichtbar machen, ohne API-Schlüssel, PDF-Inhalt oder temporäre File-ID preiszugeben. Der Mock-Test sichert Fehlercode, bereinigte Meldung und Löschversuch; die vollständige Regression umfasst 122 Tests.

### 10 – Exklusive `input_file`-Referenz für Responses

**Kontext:** Die bereinigte HTTP-Fehlerdiagnose des zweiten Realversuchs zeigte für die Responses-Anfrage HTTP 400 mit `mutually_exclusive_parameters`: Der bisherige Payload enthielt im selben `input_file`-Objekt sowohl `file_id` als auch `filename`.

**Festlegung:** Der Cloud-Adapter übergibt ein hochgeladenes Dokument in `input[0].content` ausschließlich als `{ "type": "input_file", "file_id": "…" }`. Der multipart-Upload behält seinen festen, nicht von der Quelle abgeleiteten Upload-Dateinamen bei; dieser Name wird jedoch nicht zusätzlich in die Responses-Eingabe kopiert. Der Adaptertest verlangt den exakten, exklusiven Inhaltseintrag.

**Auswirkung:** Der Responses-Payload folgt der vom Server bestätigten Ausschließlichkeitsregel und bleibt frei von zusätzlicher Quelldateibenennung. Die lokale Konvertierung und der Vision-Sidecar-Pfad bleiben unverändert; die vollständige Regression umfasst weiterhin 122 Tests.

### 11 – Reale Vergleichsevaluation des vollständigen Cloud-Dokumentmodus

**Kontext:** Nach der Korrektur der exklusiven `input_file`-Referenz wurde das bestätigte zehnseitige Tokenizer-Paper einmal als vollständige PDF über den explizit freigegebenen Cloud-Dokumentmodus verarbeitet. Als Qualitätsreferenz diente das vorhandene ChatGPT-Markdown im selben PDF-Quellordner.

**Festlegung:** Die reale Cloud-Evaluierung erzeugte ausschließlich in einem nicht versionierten Evaluierungsverzeichnis ein getrenntes Cloud-Derivat und eine lokale Bewertung. Sie bestätigte lückenlose Seitenmarker, eine mit der Referenz übereinstimmende Überschriftenfolge sowie die vorhandenen Tabellen. Bei einzelnen Formeln blieb eine abweichende Inline- gegenüber Display-Darstellung als sichtbare Qualitätsgrenze bestehen. Der dokumentierte Strukturvergleich ist kein Nachweis inhaltlicher oder typografischer Verlustfreiheit.

**Kosten und Qualitätsgrenzen:** Das Evaluationsprotokoll speichert keine Kostenschätzung, weil dafür kein belastbares Kostenbelegobjekt hinterlegt wurde. PDF-Primärquelle, lokales Markdown und ChatGPT-Referenz blieben unverändert. Die technische Validierung bestätigt die Seitenabdeckung und die sichere Markdown-Form; die abweichende Display-Formatierung und der sichtbare Diagrammhinweis bleiben als manuelle Qualitätsgrenzen nachvollziehbar.

**Auswirkung:** Der vollständige Cloud-Dokumentmodus hat den vorgesehenen separaten Derivatweg unter realen Bedingungen erfolgreich durchlaufen. Der lokale Standardpfad und der Vision-Sidecar-Pfad wurden dabei nicht ausgeführt oder verändert. Die vollständige Regression umfasst 122 Tests.

### 12 – Vergleich: Codex-App, ChatGPT-Referenz und OpenAI-API

**Kontext:** Dieselbe zehnseitige PDF `Tokenizer_Unigram_P18-1007.pdf` liegt als vom Benutzer bereitgestellte ChatGPT-Referenz, als schneller Codex-App-Versuch und als explizit validiertes OpenAI-API-Cloud-Derivat vor. Die PDF bleibt die alleinige Primärquelle; die beiden anderen Markdown-Dateien sind Qualitätsvergleichsartefakte und keine verlustfreie Wahrheit.

| Weg | Messbare Stärken | Festgestellte Grenzen |
| --- | --- | --- |
| ChatGPT-Referenz | 39445 Zeichen, 21 Überschriften, 6 Tabellen und 14 Display-Formelblöcke. | Keine Seitenmarker, keine sichtbare Qualitätswarnung. Abbildung 1 fehlt vollständig und wird nicht als Auslassung oder Unsicherheit genannt. |
| Codex-App | 21 Überschriften, lesbares Markdown, mehrere Tabellen und LaTeX. | Nur 24278 Zeichen, 5 Tabellen und 9 Display-Formelblöcke. Tabelle 3 ist ausdrücklich nur ein Auszug, Tabelle 4 wird zusammengefasst statt übertragen, Abbildung 1 fehlt ohne Warnung, Seitenmarker fehlen. Der Inhalt ist daher teils Rekonstruktion und Zusammenfassung statt vollständigem Derivat. |
| OpenAI-API-Cloudmodus | 39318 Zeichen, 21 Überschriften, 6 Tabellen, vollständige Seitenmarker 1 bis 10, mathematischer Inhalt einschließlich zweier inline statt als Block gesetzter Formeln sowie ein sichtbarer Hinweis zu Abbildung 1. Transport, Outputgrenze, Laufzeit, Usage und Derivatpfad sind nachvollziehbar. | Die Diagrammwerte von Abbildung 1 werden bewusst nicht erfunden. Die endgültige Darstellung einzelner Formeln und Diagramme kann weiterhin manuelle Nacharbeit erfordern. |

**Bewertung:** Für strukturerhaltendes wissenschaftliches Markdown und RAG ist die Transparenz über Unsicherheiten entscheidender als eine scheinbar vollständige Ausgabe. Die ChatGPT-Referenz ist für Text, Tabellen und Formeln sehr reichhaltig, verliert aber die Abbildung stillschweigend. Der Codex-App-Versuch bietet eine gute Lesefassung, verdichtet jedoch messbar und ersetzt Tabelleninhalte teilweise durch Interpretationen. Der API-Cloudmodus erreicht im Vergleich die beste Verbindung aus Umfang, Struktur, Seitenbezug und sichtbaren Qualitätsgrenzen.

**Fazit:** Der explizite OpenAI-API-Cloudmodus ist für dieses Paper der qualitativ beste getestete Konvertierungsweg. Er bleibt wegen Datenschutz, Kosten und Netzabhängigkeit ein bewusst aktivierter Zusatz; die lokale Konvertierung bleibt der netzwerkfreie Standard. Ein künftig denkbarer Codex-CLI-Weg muss außerhalb von DocToMD als Connector oder Aufrufer liegen, denselben strengen Ausgabevertrag und dieselbe lokale Validierung erfüllen und zunächst gegen diese Evaluationskriterien geprüft werden. Er ist kein pauschal kostenfreier Ersatz, weil die Abrechnung und Nutzungsgrenzen vom verwendeten Codex-Anmeldeweg abhängen.

### 13 – Ausführbarer CLI-Pfad für die Cloud-Dokumentkonvertierung

**Kontext:** Der ursprüngliche Cloud-Vertrag war bis zur realen Evaluierung durch einen separaten Aufruf nutzbar, aber die öffentliche CLI führte trotz akzeptierter Cloud-Optionen noch ausschließlich den lokalen Ablauf aus. Ein dokumentierter CLI-Befehl hätte deshalb keine tatsächliche Cloud-Konvertierung ausgelöst.

**Festlegung:** `convert_pdf` ruft den vorhandenen OpenAI-Adapter ausschließlich bei `CloudDocumentConfig.mode == openai` auf. Der Ablauf übergibt die vollständige PDF einmal mit dem versionierten Prompt, validiert das erhaltene Markdown gegen die lokal extrahierte Seitenzahl und schreibt erst danach `Quelle.cloud.md`. Das Manifest erhält in diesem Fall den relativen Cloud-Derivatpfad und die Response-Telemetrie. `ConversionRun` und die JSON-Ausgabe führen `cloud_markdown_path`; die menschenlesbare CLI-Ausgabe nennt das Cloud-Derivat zusätzlich. Bei `off` wird der Adapter nicht aufgerufen und der Standardpfad bleibt netzwerkfrei.

**Auswirkung:** Der in README dokumentierte Aufruf mit `--cloud-document-mode openai`, Modell, Timeout und Ausgabeobergrenze ist nun der tatsächlich ausführbare Opt-in-Vertrag. Die neuen Orchestrierungstests sichern sowohl die ausbleibende Adapteranfrage im Standardmodus als auch den vollständig gemockten Erfolgsfall mit Validierung, getrenntem Derivat, Manifest und JSON-Pfad. Die vollständige Regression umfasst 124 Tests.

### 14 – Kompakte CLI-Telemetrie ohne doppelte Qualitätslisten

**Kontext:** Bei einem erfolgreichen Cloud-Lauf enthielt die JSON-CLI-Antwort die vollständige Qualitätswarnliste sowohl unter `result.quality.warnings` als auch im Top-Level-Feld `warnings`. Wissenschaftliche Mehrspalten-PDFs erzeugen erwartbar viele Warnungen; die Antwort wurde dadurch unnötig groß. Zugleich war die bereits im Manifest vorhandene Cloud-Telemetrie nicht Teil des CLI-Ergebnisses.

**Festlegung:** Der JSON-Vertrag verwendet ab `schema_version` `1.1` eine kompakte `result.quality`-Zusammenfassung mit Status, Anzahl und nach Code gruppierten Warnungen beziehungsweise Fehlern. Die Einzelwarnungen verbleiben ausschließlich im Manifest; das Top-Level-Feld `warnings` ist für Konvertierungsantworten leer. So bleiben Qualitätsgrenzen sichtbar, ohne Daten doppelt zu übertragen. `serialize_run` übernimmt bei einem vorhandenen Cloud-Derivat zusätzlich die serialisierte Manifest-Telemetrie als `result.cloud_document`, einschließlich Response-ID, Modell, Tokenzählern, Zeitpunkten, Laufzeit sowie ausschließlich eventuell bereits belegter Kosten. Es werden keine Kosten geschätzt oder neu abgerufen.

**Auswirkung:** Der Cloud-Opt-in und der netzwerkfreie Standardpfad bleiben unverändert. Ein Wiederverwendungslauf mit dem bestehenden SentencePiece-Manifest bestätigte die kompakte Schema-`1.1`-Antwort mit Cloud-Telemetrie, ohne `OPENAI_API_KEY` und ohne erneute Cloud-Anfrage. Unit-Tests sichern die Warnverdichtung, den Exit-Code und die Telemetrieübergabe; die vollständige Regression umfasst 125 Tests.

### 15 – Eingerückte JSON-Ausgabe für interaktive CLI-Nutzung

**Kontext:** Die kompakte Schema-`1.1`-Antwort reduzierte die Informationsmenge erheblich, erschien auf der Konsole aber weiterhin als eine lange JSON-Zeile. Das ist für interaktive Nutzung schwer lesbar, obwohl die Daten selbst korrekt und maschinenlesbar sind.

**Festlegung:** Erfolgs-, Warn- und Fehlerantworten der Option `--json` werden mit zwei Leerzeichen eingerückt ausgegeben. Feldnamen, Werte, Exit-Codes und die Schema-Version bleiben unverändert; JSON-Parser behandeln den zusätzlichen Whitespace ohne Anpassung.

**Auswirkung:** Menschen können Cloud-Telemetrie und Qualitätszusammenfassung direkt in PowerShell prüfen, während externe Aufrufer weiterhin denselben JSON-Datenvertrag verarbeiten. Der neue CLI-Test prüft die mehrzeilige Fehlerantwort; die vollständige Regression umfasst 126 Tests.

### 16 – Ablaufgraph für die vollständige Cloud-Dokumentkonvertierung

**Kontext:** Die Cloud-Dokumentkonvertierung kombiniert den netzwerkfreien lokalen Standardpfad mit einem optionalen, einmaligen Cloud-Pfad. Die beiden resultierenden Markdown-Dateien und die lokale Validierungsgrenze müssen für Anwender unmittelbar nachvollziehbar sein.

**Festlegung:** README enthält im Abschnitt „Vollständige Cloud-Dokumentkonvertierung“ einen Mermaid-Graphen. Er zeigt die unveränderte PDF als gemeinsame Quelle, die lokale Extraktion zu `Quelle.md` samt lokalen Qualitätswarnungen, den ausschließlich durch `openai` aktivierten Upload als `input_file` mit `store: false`, die Cloud-Response, die lokale Mindestvalidierung sowie das nur bei Erfolg geschriebene `Quelle.cloud.md`. Beide Derivate und die Cloud-Telemetrie münden in `Quelle.conversion.json`; ein ungültiges oder unvollständiges Cloud-Ergebnis führt zu keinem Cloud-Derivat.

**Auswirkung:** Die Dokumentation macht die Trennung der Derivate, die fortbestehende Netzfreiheit des Standardpfads und die Schutzwirkung der Qualitätsprüfung sichtbar. Eine README-Prüfung sichert Mermaid-Block, Artefakte und Validierungsknoten; die vollständige Regression umfasst 126 Tests.

### 17 – Kompakte Darstellung des Cloud-Ablaufgraphs

**Kontext:** Der erste Ablaufgraph enthielt alle Einzelschritte, konnte in schmalen Markdown-Vorschauen jedoch Navigationsleisten erfordern.

**Festlegung:** Der Mermaid-Graph verwendet `useMaxWidth: true` und fasst die lokale Extraktion mit ihrer Qualitätsprüfung sowie den Cloud-Upload mit der Response in jeweils einem Knoten zusammen. Die beiden getrennten Markdown-Derivate, die lokale Cloud-Prüfung, der Verwerfungsweg und das Manifest bleiben sichtbar.

**Auswirkung:** Der Graph benötigt weniger Höhe und passt sich an die Breite der README-Vorschau an, ohne den implementierten Ablauf zu verändern. Die README-Prüfung und die vollständige Regression mit 126 Tests sind erfolgreich.

## 2026-09-17

## Phase 7 – OCR für gescannte PDFs

### 01 – Lokales OCR-Backend und Installationsstrategie

**Kontext:** Gescannte PDFs benötigen eine lokale Texterkennung, die weder Cloud-Zugriff noch eine Veränderung der PDF-Primärquelle voraussetzt. Die vorhandene CLI kennt bereits `--ocr-mode` und `--ocr-language`, doch die Wahl des Backends sowie das Verhalten bei einer unvollständigen Installation waren noch offen.

**Festlegung:** DocToMD verwendet ab der folgenden Implementierungsaufgabe die Tesseract-CLI der Hauptversion 5 als lokales OCR-Backend. Der Adapter ruft das externe Programm direkt über `subprocess` auf; ein zusätzlicher Python-Wrapper wie `pytesseract` wird nicht eingeführt. Seiten werden im Arbeitsspeicher mit `pypdfium2` gerendert, das bereits als transitive Abhängigkeit von `pdfplumber` vorliegt und vor seiner direkten Verwendung mit einer eigenen Versionsgrenze in `requirements.txt` festgeschrieben wird. Tesseract bleibt eine dokumentierte Systemvoraussetzung, nicht eine stillschweigend durch Python installierte Abhängigkeit. Die unterstützte Installationsbasis lautet Tesseract 5 mit den Sprachdaten `deu`, `eng` und `osd`; weitere Sprachdaten werden nur auf ausdrückliche Anforderung ergänzt.

**Installations- und Prüfstrategie:** Unter Windows wird der Tesseract-5-Installer von UB Mannheim verwendet und dessen Programmordner, üblicherweise `C:\\Program Files\\Tesseract-OCR`, in `PATH` aufgenommen. Der Adapter ermittelt vor dem ersten OCR-Lauf mit `tesseract --version` die Verfügbarkeit und liest mit `tesseract --list-langs` die installierten Sprachcodes. Die BCP-47-Eingaben `de` und `en` werden zu `deu` beziehungsweise `eng` abgebildet; für nicht installierte oder nicht abbildbare Sprachen wird kein OCR-Ergebnis erfunden. Stattdessen erhält der Lauf eine konkrete, handlungsorientierte Warnung beziehungsweise einen Fehler. Die Ausführung nutzt Tesseracts LSTM-Modus (`--oem 1`) und für die erste Scan-MVP-Stufe die automatische Seitensegmentierung (`--psm 3`). Wortkonfidenzen werden über TSV-Ausgabe erhoben, damit die folgende Aufgabe die OCR-Qualität sichtbar im Manifest ablegen kann.

**Bewertung:** Tesseract ist lokal, quelloffen und unterstützt die benötigten Sprachdaten. Die direkte CLI-Anbindung macht fehlende Engine, fehlende Sprachdateien, Prozessfehler und Timeouts ohne versteckte Python-Abstraktion sichtbar. `pypdfium2` vermeidet zusätzlich benötigte Poppler- oder ImageMagick-Systemwerkzeuge beim seitenweisen Rendering. OCRmyPDF wird nicht als Laufzeitbackend gewählt, weil es ein neues PDF-Derivat erzeugt und dessen Orchestrierung für den Markdown-Extraktionspfad unnötig wäre. Die lokale Prüfung dieser Arbeitsumgebung ergab Tesseract 5.4.0 unter `C:\\Program Files\\Tesseract-OCR\\tesseract.exe` sowie die Sprachdaten `deu`, `eng` und `osd`; dies ist nur ein Entwicklungsbefund, keine Voraussetzung für andere Installationen.

**Auswirkung:** Der nächste Schritt implementiert ausschließlich Textlayer-Erkennung und den expliziten Tesseract-Fallback auf gerenderten Seiten. Er ergänzt die direkte `pypdfium2`-Abhängigkeit erst zusammen mit dem verwendenden Code, ohne OCR-, Layout- oder ML-Pakete stillschweigend zu installieren. Die Original-PDF bleibt unverändert; nur die bestehenden abgeleiteten Markdown-, Manifest- und gegebenenfalls temporären Arbeitsartefakte werden erzeugt.

### 02 – Textlayer-Erkennung und expliziter Tesseract-Fallback

**Kontext:** Die digitale PDF-Extraktion liefert für gescannte PDFs keine Wörter. Solche Seiten dürfen nicht als erfolgreich leere Markdown-Seiten ausgegeben werden; zugleich darf der etablierte digitale Extraktionspfad nicht durch OCR ersetzt werden.

**Festlegung:** `app.pdf_extract` bleibt für die positionsgestützte Textlayer-Extraktion zuständig. `app.ocr_extract.apply_ocr_fallback` erhält deren Seitenresultate und greift nur bei `--ocr-mode auto` ohne Wörter auf allen Seiten oder bei `--ocr-mode force` ein; `off` lässt den ursprünglichen Pfad unverändert. Der Fallback rendert jede Originalseite ausschließlich im Arbeitsspeicher mit `pypdfium2` bei 300 dpi und übergibt PNG-Bytes direkt an die lokale Tesseract-CLI mit `--oem 1 --psm 3`. Die anfängliche Sprachabbildung ist BCP-47 `de`/`de-*` zu `deu` und `en`/`en-*` zu `eng`. Nicht unterstützte Kennungen, fehlendes Tesseract, Prozessfehler und ein Überschreiten des festen 60-Sekunden-Limits werden als sichtbare Konvertierungsfehler abgebrochen; sie erzeugen kein stillschweigend leeres Derivat.

**Manuelle Referenzprüfung:** Ein vom Benutzer ausdrücklich freigegebener, lokal eingebundener deutschsprachiger zweiseitiger Untersuchungsbefund ohne Textlayer wurde ausschließlich als nicht versionierte manuelle Referenz verwendet. Der Lauf mit `--ocr-mode auto --ocr-language de` erzeugte für beide Seiten Marker und nichtleeren OCR-Text. Weder Quelldatei noch ein Abbild oder Textauszug daraus wurden in das Repository übernommen. Die sichtbare Dreispaltenstruktur auf Seite 2 ist als OCR-Text verarbeitbar, wird in dieser Stufe aber noch nicht als sicher rekonstruierte Markdown-Tabelle ausgegeben.

**Auswirkung:** Digitale PDFs bleiben im Standardpfad; reine Scan-PDFs werden nicht mehr als leer behandelt. `pypdfium2>=5.13.0,<6.0` ist nun als direkte Laufzeitabhängigkeit festgeschrieben. Sechs neue Unit-Tests decken Textlayer-Erhalt, automatischen und erzwungenen Fallback, Sprachabbildung, fehlende Engine sowie den Tesseract-Aufruf ab. Die vollständige Regression umfasst 133 Tests. Die folgenden Aufgaben ergänzen konfigurierbare Seitenbereiche und Qualitätsbewertung, Manifestdetails sowie Scan-Fixtures.

### 03 – Konfigurierbare OCR-Seiten und Wortkonfidenz

**Kontext:** Ein Dokument kann OCR nur auf ausgewählten Seiten benötigen. Zudem darf ein lesbar wirkendes Ergebnis mit schwacher Zeichenerkennung nicht ohne sichtbaren Qualitätshinweis als zuverlässig gelten.

**Festlegung:** Die CLI ergänzt `--ocr-pages` mit `all` als Standard oder einer einsbasierten, kommagetrennten Auswahl wie `1-3,5`. Ungültige, leere oder außerhalb des Dokuments liegende Bereiche werden vor der OCR abgewiesen. `--ocr-min-word-confidence` akzeptiert Werte von 0 bis 100 und verwendet 70 als Standard. Tesseract liefert dafür TSV statt nur Klartext; DocToMD rekonstruiert Zeilen aus den Wortdaten und bildet die mittlere Wortkonfidenz pro OCR-Seite. Liegt sie unter dem Grenzwert, erhält die Konvertierung `OCR_LOW_CONFIDENCE` mit Seitenbezug. Unsichere Wörter werden nicht ersetzt, normalisiert oder erfunden.

**Auswirkung:** Die Seitenauswahl begrenzt nur die OCR; nicht ausgewählte Seiten behalten ihren lokalen Textlayer-Inhalt. Die Warnung nutzt bereits den bestehenden Qualitätskanal, während die vollständige Speicherung von OCR-Parametern und Ergebnissen im Manifest bewusst die nächste Aufgabe bleibt. Neue Tests decken Bereichsparser, Grenzwerte, selektierte OCR und die Warnung ab.

### 04 – Nachvollziehbare OCR-Daten im Manifest

**Kontext:** Ein OCR-Derivat muss später erkennen lassen, ob OCR verwendet wurde, auf welche Seiten es angewandt wurde und welche maschinelle Qualitätsmessung vorlag.

**Festlegung:** Das Manifest speichert die angegebene Seitenauswahl unter `conversion.options.page_range`. Wurde OCR ausgeführt, enthält `conversion.ocr` zusätzlich den Konfidenzgrenzwert und für jede tatsächlich OCRte Seite Seitennummer, Wortanzahl sowie mittlere Wortkonfidenz; fehlen erkannte Wörter, bleibt deren Konfidenz `null`. Die bestehende Qualitätsliste enthält weiterhin seitenbezogene `OCR_LOW_CONFIDENCE`-Warnungen. Der JSON-Schema-Vertrag beschreibt diese Felder mit Wertebereichen von 0 bis 100.

**Auswirkung:** Externe Aufrufer können OCR-Umfang und messbare Qualität prüfen, ohne Textinhalte, gerenderte Seitenbilder oder temporäre Dateien im Manifest zu speichern. Die Schema-JSON-Prüfung und die vollständige Regression mit 136 Tests sind erfolgreich.

### 05 – Verständliche Diagnose fehlender OCR-Voraussetzungen

**Kontext:** Ein allgemeiner Prozessfehler hilft nicht dabei, eine fehlende lokale OCR-Installation oder Sprachdatei zu beheben.

**Festlegung:** Vor dem Rendering prüft der Adapter `tesseract --version` und `tesseract --list-langs`. Eine fehlende oder nicht startende Engine erklärt die erforderliche Installation von Tesseract 5 und `PATH`. Fehlende Sprachdaten nennen den konkreten Tesseract-Code und den `tessdata`-Ordner. Zeitüberschreitungen der Prüfaufrufe werden gesondert gemeldet.

**Auswirkung:** Fehlende Systemvoraussetzungen führen vor der langlaufenden Seitenerkennung zu einer klaren, lokal behebbaren Fehlermeldung. Zwei neue Tests sichern Installations- und Sprachdatenhinweis; die vollständige Regression umfasst 138 Tests.

### 06 – Mock-basierte Scan-OCR-Regression

**Kontext:** Persönliche Scans dürfen nicht als Testfixture im Repository liegen; dennoch muss der vollständige OCR-Ablauf gegen Regressionen geschützt werden.

**Festlegung:** Die Konvertierungsregression simuliert ein zweiseitiges PDF ohne Textlayer sowie ein OCR-Ergebnis mit einer sicheren und einer unsicheren Seite. Sie prüft die Markdown-Seitenmarker und Texte, OCR-Metriken im Manifest sowie die sichtbare Warnung `OCR_LOW_CONFIDENCE`.

**Auswirkung:** Die zentrale Scan-Pipeline bleibt ohne sensible oder urheberrechtlich belastete Fixture reproduzierbar testbar. Die vollständige Regression umfasst 139 Tests.

### 07 – Editierbares OCR-Layout statt zusammengezogenen Texts

**Kontext:** Die deutsche manuelle Referenzprüfung zeigte, dass reiner, von Tesseract nach Blöcken gelieferter Text Kopfbereiche und Tabellen nicht lesbar erhält. Eine eingebettete Seitenkopie wäre keine editierbare Markdown-Ausgabe.

**Festlegung:** OCR-Seiten speichern zusätzlich ein HTML-`pre`-Layout innerhalb der Markdown-Datei. Es wird aus den TSV-X- und Y-Koordinaten erzeugt, ist Text und keine Bildkopie. Wörter werden unabhängig von Tesseracts Blocknummer nach ihrer visuellen vertikalen Position zu Zeilen gruppiert; ihre X-Position bestimmt die Leerraumausrichtung. Dadurch stehen bei der geprüften dreispaltigen Tabelle Parameter, Messwert und Referenzbereich wieder in derselben Zeile.

**Deutsche Qualitätsprüfung:** Der erneute Lauf mit der freigegebenen lokalen Referenz zeigt eine lesbare, editierbare Dreispaltenstruktur auf Seite 2 und eine positionsnähere Anordnung auf Seite 1. Der Export enthält weiterhin erkennbare OCR-Zeichenfehler; sie werden sichtbar beibehalten und nicht korrigiert. Die vollständige Regression umfasst 139 Tests. Eine separate englische manuelle Prüfung ist auf Benutzerentscheidung nicht Bestandteil der Phase-7-Abnahme.

### 08 – Editierbares Cloud-Derivat mit integrierten Prüfhinweisen

**Kontext:** Die lokale OCR-Ausgabe kann Qualitätsgrenzen finden, ihre positionsnahe Rohdarstellung ist für komplexe Befundlayouts jedoch nicht die gewünschte Bearbeitungsoberfläche. Eine separate Korrekturtabelle würde den Bearbeiter zwingen, Text nochmals abzuschreiben.

**Festlegung:** Der ausdrücklich aktivierte Cloud-Dokumentmodus nutzt Prompt-Vertrag `1.1`. Er verlangt editierbares, strukturiertes Markdown, GFM-Tabellen für Befunde und nur bei Bedarf kleine HTML-Tabellen für Kopf- oder Adressbereiche. Seitenbilder, Screenshots und präformatierte Leerzeichen-Tabellen sind untersagt. Nach der bestehenden technischen Mindestvalidierung fügt `inject_cloud_review_warnings` jede lokale Warnung oder jeden lokalen Fehler mit Seitenbezug direkt nach `<!-- doctomd:page=N -->` als Obsidian-kompatiblen Callout ein. Globale und reine Informationshinweise verbleiben ausschließlich im Manifest, da sie keinem bearbeitbaren Abschnitt sicher zugeordnet werden können.

**Deutsche Qualitätsprüfung:** Der einmalig freigegebene Cloud-Lauf für die nicht versionierte deutsche Scan-Referenz erzeugte ein getrenntes, bildfreies Markdown-Derivat mit strukturiertem Kopfbereich, Abschnitten und einer editierbaren GFM-Labortabelle auf Seite 2. Ein lokaler Hinweis zur möglichen Zeilentrennung wurde sichtbar auf Seite 1 eingefügt. Die Primärquelle blieb unverändert. Dieser Lauf bestätigt Struktur und Warnplatzierung, nicht die medizinische Richtigkeit jedes rekonstruierten Werts.

**Auswirkung:** Bearbeitung und Qualitätsprüfung finden direkt in `Quelle.cloud.md` statt; `Quelle.md`, die Primärquelle und das Manifest bleiben getrennte Artefakte. Drei neue bzw. erweiterte Regressionstests sichern Warnplatzierung, Ausschluss globaler Hinweise und den integrierten Cloud-Ablauf. Die vollständige Regression umfasst 143 Tests. Die deutsche manuelle Qualitätsprüfung dient als Phase-7-Abnahme; eine separate englische Prüfung ist auf Benutzerentscheidung nicht vorgesehen.

### 09 – Austauschbarer Rekonstruktionsadapter

**Kontext:** Für komplexe gescannte Befundlayouts liefert die lokale Tesseract-OCR nachvollziehbaren Text und Qualitätsbefunde, aber nicht durchgehend die gewünschte editierbare Dokumentstruktur. Der OpenAI-API-Modus liefert diese Rekonstruktion derzeit mit expliziter Freigabe und `OPENAI_API_KEY`. Ein späterer leistungsfähiger lokaler KI-Server soll dieselbe Aufgabe ohne diesen Cloud-Adapter übernehmen können.

**Festlegung:** DocToMD behandelt die Rekonstruktion als Providergrenze. Der aktuelle OpenAI-Adapter bleibt der einzige implementierte Rekonstruktionsadapter und übergibt die vollständige PDF einmal als `input_file`. Die lokale OCR, die technische Prüfung von Seitenmarkern und sicherem Markdown, die sichtbaren Qualitätswarnungen, die Derivatnamen und das Manifest bleiben unabhängig vom Provider. Ein zukünftiger lokaler Adapter muss denselben vollständigen, versionierten Markdown-Vertrag erfüllen; er ersetzt weder lokale OCR noch Validierung und verändert keine öffentlichen CLI- oder Manifestfelder.

**Datenschutzgrenze:** Beim OpenAI-Adapter wird die PDF als temporäres File hochgeladen. Der Adapter fordert nach der Antwort dessen Löschung an; ein fehlgeschlagener Löschaufruf wird im aktuellen Code noch nicht bestätigbar protokolliert. Diese Grenze bleibt bis zu einer gesonderten Verbesserung sichtbar. Ein lokaler Inferenzadapter soll diese Übertragung vollständig vermeiden.

**Auswirkung:** Der Wechsel von OpenAI-API zu lokaler Inferenz ist als gezielte Adapterimplementierung vorgesehen, nicht als Wechsel des Bearbeitungs- oder Dokumentformats. Bis ein lokaler Adapter implementiert und gegen denselben Vertrag getestet ist, bleibt der OpenAI-Modus bewusst opt-in und der lokale Standardpfad netzwerkfrei.

### 10 – Keine separate OCR-Korrekturdatei und bedarfsgesteuerte Assets

**Kontext:** Die sichtbaren Prüfhinweise im editierbaren Cloud-Derivat ersetzen die frühere separate Entscheidungsdatei. Für Scan-PDFs ohne eingebettete Rasterbilder darf auch kein leerer Asset-Ordner als scheinbares Ergebnis entstehen.

**Festlegung:** DocToMD plant, prüft und schreibt keine `*.corrections.md` mehr. Qualitätsbefunde verbleiben im Manifest und erscheinen bei einem Cloud-Derivat zusätzlich direkt nach dem zugehörigen Seitenmarker. Der Bildexport legt `*.assets` ausschließlich dann an, wenn mindestens ein eindeutig exportierbares Bildasset vorliegt; PDFs ohne eingebettete Bilder oder nur mit nicht exportierbaren Bildformaten hinterlassen keinen leeren Ordner.

**Auswirkung:** Ein Scanlauf erzeugt nur die tatsächlich genutzten Markdown- und Manifestartefakte. Bestehende, aus früheren Läufen stammende Korrekturdateien oder Asset-Ordner werden durch diese Änderung nicht gelöscht. Regressionstests sichern das Ausbleiben der Korrekturdatei sowie den fehlenden Asset-Ordner bei Bild-freien PDFs.

**Aktualisierung:** Die ursprüngliche JPEG-Beschränkung dieser Festlegung wurde in Phase 8 erweitert: Aktuell zählen auch sicher dekodierbare `FlateDecode`-PNG-Raster, DCT-dekodierte JPEGs und unterstützte indizierte PNG-Raster als exportierbare Bildassets. Die Grundregel, keinen leeren Asset-Ordner anzulegen, bleibt unverändert.

### 11 – Abschluss der Phase 7

**Entscheidung:** Die manuelle Qualitätsprüfung mit dem freigegebenen deutschen Scan, der lokale OCR-Nachweis, die Cloud-Rekonstruktion mit editierbarer Labortabelle und die integrierten Prüfhinweise werden als ausreichende Abnahme der OCR-Phase festgelegt. Eine englischsprachige manuelle Scan-Prüfung wird nicht durchgeführt. Die vorhandene Unterstützung für `en` mit Tesseract-Sprachdaten `eng` bleibt unverändert.

**Auswirkung:** Alle Aufgaben von Phase 7 sind in [[TASKS]] als abgeschlossen markiert. Weitere Sprach- oder Scan-Qualitätsevaluationen sind mögliche spätere Erweiterungen, aber keine offene Voraussetzung für Phase 8.

## Phase 8 – Strukturqualität und RAG-Übergabe

### 01 – Evaluation grundlegender Markdown-Strukturen

**Kontext:** Für die erste Phase-8-Prüfung reichen eine bloße Unit-Test-Eingabe oder ein komplexes wissenschaftliches Layout allein nicht aus. Die vorhandene wissenschaftliche Fixture prüft Mehrspaltenlesereihenfolge, Formel und Tabelle, enthält jedoch weder Listen noch eine Codepassage.

**Festlegung:** `structure-elements.pdf` wird durch `tests/fixtures/build_structure_fixture.py` ausschließlich aus selbst verfasstem ASCII-Text erzeugt. Die einspaltige, visuell geprüfte Seite enthält nummerierte Überschriften der Ebenen 1 und 2, zwei durch sichtbaren Abstand getrennte Absätze, eine ungeordnete und eine geordnete Liste, die einzelne Codezeile `print(42)` sowie eine vollständig belegte rechteckige Tabelle. `test_structure_fixture_regression.py` konvertiert sie vollständig und sichert Seitenmarker, Überschriftenhierarchie, Absatztrennung, Listen, Tabelleninhalt und den Erhalt der Codezeile. Die bestehende `scientific-two-column.pdf` ergänzt die Bewertung um Kopf- und Fußbereich, Zweispaltenreihenfolge, Formel und Tabelle; ihre erwartete Warnung `MULTI_COLUMN_LAYOUT` bleibt erhalten.

**Ergebnis:** Beide Fixtures wurden mit Poppler visuell gerendert und mit der lokalen Pipeline konvertiert. Die einspaltige Fixture erzeugt korrekt `# 1 Overview`, `## 1.1 Details`, getrennte Absätze, `- Bullet item`, `1. Ordered item` und eine GFM-Tabelle mit den Zeilen `Alpha | 1` sowie `Beta | 2`. Das wissenschaftliche Derivat bewahrt die Seitenmarkierung, Kopf- und Fußreihenfolge, die geprüfte LaTeX-Formel und die einfache Tabelle. Die vollständige Testsuite umfasst 159 erfolgreiche Tests.

**Qualitätsgrenze:** Die lokale Pipeline erkennt Code derzeit nicht sicher genug, um aus einer einzelnen typografisch hervorgehobenen oder kurz gesetzten Zeile einen Markdown-Codeblock abzuleiten. `print(42)` bleibt deshalb als editierbarer Absatz erhalten und wird ausdrücklich nicht in eine Fence umgeschrieben. Das verhindert eine plausible, aber unbelegte Strukturbehauptung; eine künftige Codeblock-Erkennung benötigt eigene konservative Regeln und repräsentative Fixtures.

### 02 – Regeln für Mehrspalten, Fußnoten und Formeln

**Kontext:** Frühere wissenschaftliche Auswertungen zeigen die Mehrspaltenheuristik in realen Derivaten: Das Tokenizer-Paper enthält neun, das SentencePiece-Paper sechs `MULTI_COLUMN_LAYOUT`-Warnungen. Die versionierte wissenschaftliche Fixture bestätigt eine einzelne warnende Zweispaltenseite und die sichere Summenbruch-Formel. Für Fußnoten gibt es hingegen keine layoutübergreifende, ohne Risiko verwendbare PDF-Syntax; eine automatische Deutung von tiefgestellten Zeichen, Sternchen oder Randtext würde Referenzziele erfinden können.

**Festlegung:** [[STRUCTURE_QUALITY_RULES|Die Strukturqualitätsregeln]] definieren den lokalen Vertrag. Erkannte Zweispaltenseiten behalten die geometrische Leserichtung mit Kopf- und Fußbereich, erhalten aber immer `MULTI_COLUMN_LAYOUT` und gelten im Vision-Modus `auto` als Risikoseiten. Nur die vollständig lokal prüfbare Summenbruch-Grammatik wird als Display-LaTeX ausgegeben; andere eigenständige Gleichungskandidaten bleiben als Quelltext mit `FORMULA_NOT_RECONSTRUCTED`. DocToMD erzeugt aus visuellen PDF-Fußnoten keine Markdown-Fußnoten. Bereits explizit als `[^n]` extrahierte Marker können nur mit einer ebenfalls sichtbaren Definition verknüpft werden; sonst bleibt der Marker erhalten und `UNRESOLVED_DOCUMENT_REFERENCE` dokumentiert das fehlende Ziel.

**Auswirkung:** Die bestehenden Warnungen und Erweiterungspunkte sind nun als überprüfbarer Qualitätsvertrag dokumentiert, ohne eine scheinbar zuverlässige Fußnoten- oder Formelerkennung vorzutäuschen. Eine spätere automatische Fußnotenrekonstruktion benötigt eine eigene Fixture mit konkurrierender Zitation und vollständiger Seitenprüfung. Die bestehende lokale Standardkonvertierung, die manifestierte Seitenzuordnung und der Opt-in-Charakter von Vision bleiben unverändert.

### 03 – Prüfung der Seitenreferenzen für Text, Tabellen und Bilder

**Kontext:** Für strukturorientiertes Chunking genügt ein allgemeiner Dokumentpfad nicht: Textabschnitte, Tabellen und Bildassets müssen jeweils auf ihre Ursprungsseite zurückgeführt werden können. Neben den Unit-Tests wurden deshalb ein neuer Lauf der wissenschaftlichen Fixture und ein bereits erfolgreiches Gerätehandbuch-Derivat geprüft.

**Ergebnis:** Die wissenschaftliche Fixture enthält einen Seitenmarker und 15 Textreferenzen im Manifest; keine verweist auf eine Seite ohne Markdown-Marker. Ihre Tabelle besitzt sowohl den Marker `page-001-table-01 page=1` als auch einen Tabellen-Content-Reference auf Seite 1. Der sichtbare Verweis `Table 1` ist im Manifest mit Quellseite, Zielseite und derselben stabilen Tabellen-ID aufgelöst. Im Gerätehandbuch-Derivat stimmen alle fünf exportierten Bildassets zwischen Manifestseite, Asset-Marker und relativem Markdown-Pfad überein.

**Festlegung:** [[PAGE_REFERENCE_CONTRACT|Der Seitenreferenzvertrag]] hält die vollständige Zuordnung fest. Der Seitenmarker ist die kleinste stabile Herkunftseinheit im Markdown. Das Manifest erfasst Textblöcke, Tabellen und Assets jeweils seitenbezogen; Tabellen und Assets führen darüber hinaus stabile IDs. Textabschnitte erhalten derzeit keine eigene Block-ID, weshalb ihre Herkunft über den umgebenden Seitenmarker und den entsprechenden Manifesteintrag nachvollziehbar bleibt, nicht über einen zusätzlichen Absatzanker.

**Auswirkung:** Ein konsumierender RAG-Indexer kann die Herkunft jedes Chunk-Inhalts auf Seitenebene erhalten und Tabellen sowie Bildassets stabil referenzieren. Eine spätere Block-ID-Erweiterung ist nur nötig, falls externe Aufrufer einzelne Absätze unabhängig von ihrem Markdown-Kontext adressieren müssen.

### 04 – Handhabbarer Workflow für Bildbeschreibungen

**Kontext:** Die bestehende Sidecar-Datei war technisch stabil und konfliktgeschützt, bestand jedoch nur aus einem kurzen Kommentar. Für eine fachliche Nachbearbeitung fehlte eine kompakte Struktur, die sichtbare Fakten von Einordnung und Unsicherheiten trennt.

**Festlegung:** Jede neu anzulegende Bildbeschreibungs-Note enthält nun die editierbaren Bereiche „Kurzbeschreibung“, „Fachliche Einordnung“, „Sichtbare Details“ und „Unsicherheiten“. [[IMAGE_DESCRIPTION_WORKFLOW|Der Workflow für Bildbeschreibungen]] beschreibt die Bearbeitungsreihenfolge und die Regel, nur klar belegbare Inhalte zu ergänzen. Der stabile Dateiname, Asset-ID, Seitenbezug, die automatisch erkannte Caption und der Link aus der Haupt-Note bleiben unverändert. Vorhandene Beschreibungs-Notes werden auch mit der neuen Vorlage niemals überschrieben.

**Auswirkung:** Fachliche Bildsemantik kann schnell und nachvollziehbar ergänzt werden, ohne aus einer leeren Beschreibung eine Qualitätsbehauptung zu machen. Ein RAG-Indexer muss die Sidecar-Notes unter `Quelle.assets/**/*.md` explizit einbeziehen; DocToMD selbst erstellt weiterhin keinen Index und kopiert den Text nicht automatisch in die Haupt-Note.

### 05 – Vereinbarung für die Übergabe an CodexCLI

**Kontext:** DocToMD und CodexCLI besitzen bereits getrennte Verantwortlichkeiten und passende lokale Artefakte, aber der Übergabeweg musste festlegen, welches Derivat indexiert wird, wie Qualitätsgrenzen erhalten bleiben und wie Bildbeschreibungen ohne doppelte Treffer einbezogen werden.

**Festlegung:** [[CODEXCLI_HANDOFF|Die Übergabevereinbarung]] legt `Quelle.md` als Standardquelle für CodexCLI `index_md` fest. Ein vorhandenes `Quelle.cloud.md` wird nur bewusst anstelle des lokalen Derivats indexiert, nie zusätzlich. Vor der Übergabe prüft der Aufrufer das Manifest, den Quellfingerabdruck, die Artefaktpfade und den Qualitätsstatus. `<!-- doctomd:page=N -->` sowie Tabellen- und Bildmarker bleiben als Herkunftskontext im Markdown erhalten. Bildbeschreibungen werden nur bei fachlichem Bedarf durch einen getrennten Indexlauf für `Quelle.assets` aufgenommen.

**Auswirkung:** Die Übergabe ist über einen stabilen CLI- und Dateivertrag dokumentiert, ohne interne Imports, automatische Prozesse oder gegenseitige Indexmanipulation. Qualitätswarnungen bleiben beim Manifest und werden nicht als Tatsachenbehauptungen indexiert. Die Entscheidung über lokalen oder Cloud-Inhalt und über Bildbeschreibungen bleibt beim aufrufenden Workflow.

### 06 – Empfehlung für ein RAG-Indexderivat

**Kontext:** Die reale Gegenüberstellung des SentencePiece-Papers zeigte, dass `Quelle.md` nicht in jedem Fall das strukturell geeignetste Derivat ist: Die lokale Ausgabe enthielt keine Tabellen oder Display-Formeln und 27 nicht dekodierbare `(cid:`-Zeichen, während das bereits technisch validierte Cloud-Derivat zwei Tabellen, 23 Display-Formelmarker und keine solchen Zeichen enthielt. Eine ausschließlich konventionelle Auswahl des lokalen Derivats würde diese Qualitätsdifferenz vor dem Indexer verbergen.

**Festlegung:** Jede neu ausgeführte Konvertierung schreibt im Manifest ein versioniertes Top-Level-Feld `rag_indexing`. Es enthält `recommended_markdown_path`, einen maschinenlesbaren Auswahlgrund und die gemessenen Kennzahlen beider Kandidaten. Ohne Cloud-Derivat bleibt das lokale Markdown die Empfehlung. Ein Cloud-Derivat wird nur bei einer strikt höheren, transparenten Strukturwertung empfohlen; bei Gleichstand bleibt die lokale Variante maßgeblich. Ein konsumierender Workflow indexiert ausschließlich den empfohlenen Pfad, niemals beide Derivate derselben Quelle.

**Qualitätsgrenze:** Die Wertung bevorzugt sichtbare Überschriften, Tabellenmarker und Display-Formelmarker und berücksichtigt nicht dekodierbare Zeichen negativ. Sie ist keine Aussage über semantische Korrektheit, Vollständigkeit, Datenschutz oder Kosten. Qualitätsstatus und Seitenwarnungen des Manifests bleiben daher verpflichtender Prüfkontext. Bestehende Manifeste erhalten die Empfehlung erst mit einer erneuten Konvertierung.

**Auswirkung:** [[RAG_INDEXING_RECOMMENDATION|Die Indexempfehlung]] und [[CODEXCLI_HANDOFF|die Übergabevereinbarung]] machen die Auswahl für CodexCLI und andere Indexer nachvollziehbar, ohne einen Index zu erzeugen oder einen Cloud-Lauf zu aktivieren. Die Primärquelle und alle vorhandenen Derivate bleiben unverändert.

### 07 – Geplanter Verzeichnis-Hook für die Indexierung

**Kontext:** Ein Aufrufer soll nicht zwischen `Quelle.md` und `Quelle.cloud.md` raten oder den im Manifest bereits begründeten Auswahlpfad selbst nachbauen müssen. Gleichzeitig darf ein Komfortbefehl die Verantwortungsgrenze nicht verschieben: DocToMD konvertiert und empfiehlt, CodexCLI indexiert.

**Festlegung:** [[CODEXCLI_HANDOFF|Die Übergabevereinbarung]] beschreibt den späteren CodexCLI-Befehl `index_doctomd_output <ausgabeordner>`. Er liest ausschließlich das Manifest der angegebenen DocToMD-Ausgabe, löst `rag_indexing.recommended_markdown_path` sicher innerhalb dieses Ordners auf und ruft genau einmal `index_md` für dieses Derivat auf. Fehlendes oder ungültiges Manifest, fehlende Empfehlung, fehlendes Markdown, ein aus dem Ausgabeordner führender Pfad oder eine fehlende Artefakt-Übereinstimmung führen zu einem Abbruch mit Diagnose.

**Grenze:** Der Hook ist ein dokumentiertes Zielbild, noch nicht implementiert. Er löst weder eine Konvertierung noch einen Cloud-Lauf aus, sucht keine beliebigen Markdown-Dateien, errät keine Dateinamen und indexiert nicht beide Derivate. Bildbeschreibungs-Notes bleiben ein separater, bewusst gewählter Indexlauf. Quellfingerabdruck, Qualitätsstatus und Warnungen werden nicht als Erfolgsbehauptung übergangen.

**Auswirkung:** Ein späterer CodexCLI-Aufrufer kann den Konvertierungsordner statt eines konkreten Markdown-Dateinamens übergeben, ohne dass DocToMD CodexCLI-Interna importiert oder einen Index verändert. Die Aufgabe ist als Spezifikation abgeschlossen; die eigentliche Implementierung gehört in das separate CodexCLI-Projekt.

### 08 – Evaluation strukturorientierten Chunkings

**Kontext:** Nach der Auswahl eines geeigneten Derivats musste geprüft werden, ob ein externer Indexer dessen Markdown-Struktur tatsächlich als sichere Chunk-Grenzen verwenden kann. Die kontrollierte Struktur-Fixture deckt Überschriften, Absätze, Listen und eine einfache Tabelle ab; das bereits vorhandene SentencePiece-Cloud-Derivat ergänzt sechs Seiten, 16 Überschriften, eingerückte Codepassagen, eine Display-Formel und zwei GFM-Tabellen. Die Originalseiten 5 und 6 wurden visuell gegen Tabelle 1 beziehungsweise Tabelle 2 verglichen.

**Ergebnis:** [[STRUCTURED_CHUNKING_EVALUATION|Die Chunking-Evaluation]] bestätigt Seitenmarker als harte Herkunftsgrenze sowie Überschriften, Absätze und Listen als sinnvolle weiche Grenzen. Tabellen, Display-Formeln und zusammenhängende Codepassagen bleiben atomar; sie werden nicht auf ein blindes Zeichenlimit zerschnitten. Beide SentencePiece-Tabellen bleiben im Cloud-Derivat als geschlossene GFM-Strukturen mit Captions erhalten und müssen nicht aus der PDF rekonstruiert werden.

**Qualitätsgrenze:** Die Prüfung bewertet keinen Embedding-Index und keine Retrieval-Treffer. Mehrspalten-, OCR- und Referenzwarnungen bleiben verpflichtender Metadatenkontext. Die lokale Pipeline erkennt eine einzelne typografische Codezeile weiterhin nicht sicher als Codeblock; ein Chunker darf sie nicht ohne eigene dokumentierte Regel umdeuten. Bei übergroßen Tabellen, Formeln oder Codeblöcken ist ein gekennzeichneter Überlängen-Chunk sicherer als eine Trennung innerhalb der Struktur.

**Auswirkung:** Die letzte Phase-8-Aufgabe ist als Evaluation abgeschlossen. Ein späterer Indexer kann das über `rag_indexing.recommended_markdown_path` ausgewählte Markdown strukturerhaltend verarbeiten, ohne dass DocToMD selbst Chunking, Indexierung oder Retrieval übernimmt.

### 09 – Endbenutzerwarnungen und dekodierte Flate-Bildassets

**Kontext:** Die Qualitätsprüfung eines 73-seitigen digitalen LaTeX-PDFs zeigte eine vollständig strukturierte Cloud-Ausgabe, aber 121 sichtbare Callouts. Davon waren 56 mögliche Trennungen, 33 Mehrspaltenheuristiken und 25 nicht automatisch verknüpfte Zitationen; diese Befunde sind für die technische Nachvollziehbarkeit wertvoll, aber nicht für die direkte Markdown-Bearbeitung. Dasselbe Dokument enthielt einen direkten JPEG- und vier `FlateDecode`-Bildstreams; bislang wurde nur das JPEG exportiert.

**Festlegung:** `inject_cloud_review_warnings` veröffentlicht ausschließlich explizit endbenutzerrelevante Unsicherheiten mit Seitenbezug: niedrige OCR-Konfidenz, nicht dekodierbare PDF-Zeichen, nicht rekonstruierbare Formeln sowie abgewiesene oder unsichere Vision-Vorschläge. Alle übrigen Warnungen verbleiben unverändert im Manifest. Der Bildexport übernimmt direkte JPEGs und dekodiert einfache 8-Bit-`FlateDecode`-Streams in `DeviceRGB` oder `DeviceGray` mit Pillow verlustfrei als PNG. Verifizierte lokale Abbildungsassets werden nach der Cloud-Validierung direkt hinter einer erhaltenen Caption oder ersatzweise am Ende ihrer Seite in das Cloud-Derivat eingefügt. Vollständige PDF-Seiten werden weiterhin nie als Bild eingebettet.

**Qualitätsprüfung:** Der reale lokale Asset-Export für `Valentinsherz.pdf` erzeugte fünf Assets ohne Bildexportwarnung: ein JPEG sowie vier PNGs. Die Sichtprüfung eines dekodierten PNGs gegen die gerenderte Originalseite bestätigte identische Farben und Geometrie des Herz-Renderings. Unit-Tests sichern PNG-Kodierung, Asset-Referenz im Cloud-Markdown und die Ausblendung technischer Mehrspaltenwarnungen aus dem Endbenutzerderivat.

**Auswirkung:** Cloud-Markdown bleibt für Endbenutzer lesbar, während das Manifest alle diagnostischen Details bewahrt. Der Cloud-Prompt-Vertrag ist auf `1.2` erhöht: Das Modell bewahrt Bildunterschriften, erfindet aber keine lokalen Bildpfade und warnt nicht mehr allein wegen fehlender Einbettung; DocToMD fügt ausschließlich tatsächlich exportierte Assets ein.

### 10 – Markdown-Codeblöcke in Cloud-Antworten

Die Mindestvalidierung akzeptiert ab Prompt-Vertrag `1.3` sichtbare Quellcodeblöcke mit Markdown-Fences. Zuvor löste bereits ein fachlich zulässiger Codeblock die pauschale Fehlermeldung `CLOUD_MARKDOWN_FORBIDDEN_OUTPUT` aus. Weiterhin abgewiesen werden Datei-URIs sowie HTML-Dokument-, Meta-, Iframe- und Script-Elemente. Damit bleibt die Ausgabe ein editierbares Markdown-Derivat und wissenschaftliche oder technische Quellcodepassagen gehen nicht verloren.

### 11 – Wiederaufnehmbare OpenAI-Hintergrundläufe

Vollständige Cloud-Dokumentkonvertierungen starten als OpenAI-Responses-Hintergrundlauf. Nach der sofort verfügbaren Response-ID fragt DocToMD den Status mit kurzen Requests ab, statt eine einzelne lange HTTP-Verbindung offen zu halten. `Quelle.cloud-run.json` enthält Response-ID, Quellhash, Fingerabdruck des lokalen Wiederverwendungskontexts, Modell, Promptvertragsversion und Startzeit; eine Wiederaufnahme fragt die temporäre Hintergrundantwort nur bei exakter Übereinstimmung dieser Bindungen ab. Nach Erfolg entfernt DocToMD diese abgeleitete Statusdatei. Das Verfahren verwendet weiterhin `store: false`; die für das Polling erforderliche temporäre Aufbewahrung beträgt laut OpenAI ungefähr zehn Minuten.

### 12 – Fortschrittsvertrag

`convert` bietet `--progress human|jsonl|none` mit Standard `human`. Fortschritt wird ausschließlich auf `stderr` geschrieben, das finale Ergebnis bleibt auf `stdout`; `--json` bleibt damit ein einzelner stabiler JSON-Envelope. JSONL-Ereignisse enthalten keine Zugangsdaten oder Dokumentinhalte, sondern nur Schema-Version, Phase, Status, Meldung und vergangene Laufzeit. Der OpenAI-Adapter meldet nur Statuswechsel (`queued`, `in_progress`, `completed`); ein Prozentfortschritt wird nicht erfunden. Ein externes Obsidian-Plugin kann die Ereignisse ohne interne Imports konsumieren. Ein expliziter Cloud-Abbruch bleibt bewusst ein separater, noch nicht implementierter API-Schritt.

### 13 – DCT-Filterketten bei eingebetteten Bildern

Ein Enterprise-PDF verwendete fachliche Diagramme mit der Filterkette `FlateDecode` und `DCTDecode`. Die Rohbytes sind dabei kein JPEG, während `get_data()` korrekt dekodierte JPEG-Bytes liefert. Der Export prüft deshalb beide Repräsentationen. Sehr kleine Raster unter 50.000 Pixeln werden als wiederholte Kopf- oder Fußdekoration ausgelassen; sie erzeugen weder Asset noch Warnung. Dadurch bleiben Diagramme als editierbar referenzierte JPEG-Assets erhalten, ohne jede Seitenkopf-Grafik mehrfach auszugeben.

### 14 – Redundante Modellwarnungen bei verifizierten Abbildungen

Manche Cloud-Antworten enthalten generische englische Callouts der Form `The page contains …` oder `A figure … is visible on this page`, obwohl DocToMD anschließend ein lokal verifiziertes Asset derselben Seite einfügt. Beim Asset-Insertion-Schritt werden genau diese Modellblöcke auf Seiten mit mindestens einem Asset entfernt. DocToMD-eigene Prüfhinweise und andere Modellwarnungen bleiben erhalten.

### 15 – GFM-Tabellen und wahrheitsgemäße Glyphenhinweise im Cloud-Derivat

**Kontext:** Der zweite reale Unigram-Lauf erzeugte ein deutlich besseres Cloud-Derivat mit sechs GFM-Tabellen, 71 Tabellenzeilen und keinen `(cid:`-Zeichen. Die RAG-Kennzahl `table_count` meldete dennoch null, weil sie nur DocToMD-Tabellenmarker kannte. Zugleich wurden endbenutzerseitig Glyphenwarnungen aus der lokalen Analyse sichtbar eingefügt, obwohl das Cloud-Markdown der jeweiligen Seite keine solchen Zeichen mehr enthielt.

**Festlegung:** Die RAG-Bewertung zählt nun sowohl DocToMD-Tabellenmarker als auch GFM-Tabellenköpfe; ein unmittelbar zugehöriger Marker und eine GFM-Tabelle werden nur einmal gezählt. `UNREADABLE_PDF_GLYPHS` wird im Cloud-Derivat nur noch auf einer Seite als sichtbarer Prüfhinweis eingefügt, wenn das bereits validierte Cloud-Markdown auf genau dieser Seite weiterhin `(cid:` enthält. Der ursprüngliche lokale Qualitätsbefund verbleibt unverändert im Manifest.

**Auswirkung:** Die Kennzahlen der RAG-Empfehlung bilden Cloud-Tabellen korrekt ab, und sichtbare Glyphenhinweise behaupten nicht mehr fälschlich eine unveränderte Übernahme. Bestehende Derivate und Manifeste werden nicht migriert oder überschrieben; die Änderung wirkt bei der nächsten Konvertierung. Regressionstests sichern GFM-Tabellen ohne Marker sowie beide Varianten der Glyphenwarnung.

## Phase 9 – Obsidian-Integration und Veröffentlichungsvorbereitung

### 01 – Vault-Ausgabeordner und Artefaktnamen

**Kontext:** Ein separates Obsidian-Plugin benötigt eine nachvollziehbare Ablage für abgeleitete Artefakte, ohne DocToMD an Vault-Interna zu koppeln oder bestehende Notes zu gefährden.

**Festlegung:** Das Plugin empfiehlt pro Quelle den neuen Vault-Unterordner `<Vault>/_DocToMD/<PDF-Basisname>/`. Der Ordner ist vom Vault-Stamm, `.obsidian` und allgemeinen Dokumentenordnern getrennt. DocToMD behält innerhalb dieses Ordners seine bestehenden, aus dem Quellbasisnamen abgeleiteten Namen unverändert bei. Gleichnamige, unterschiedliche PDFs erhalten verschiedene Ausgabeordner; eine erneute Konvertierung derselben Quelle verwendet denselben Ordner und verlangt eine explizite Konfliktentscheidung.

**Auswirkung:** Die Integration bleibt eine reine CLI-/Dateigrenze. Relative Markdown-, Asset- und Manifestreferenzen bleiben beim Verschieben des gesamten Ausgabeordners gültig. Das Plugin bestimmt das zu öffnende oder zu indexierende Derivat ausschließlich über das Manifest und nicht über Dateinamen. [[OBSIDIAN_VAULT_OUTPUT_CONVENTIONS|Die Vault-Konvention]] dokumentiert Zielort, Kollisionen und den sicheren Prozessvertrag.

### 02 – Datenschutz-, Lizenz- und Abhängigkeitsprüfung

**Kontext:** Vor einer späteren Verteilung müssen lokaler Standardpfad, explizite Providergrenzen, Systemwerkzeuge und transitiven Python-Abhängigkeiten nachvollziehbar sein. Eine technische Prüfung darf dabei keine rechtliche Freigabe simulieren.

**Festlegung:** Der Standardlauf bleibt vollständig lokal und netzwerkfrei. LM Studio, OpenAI-Vision und der Cloud-Dokumentmodus sind jeweils explizite Datenübertragungsgrenzen. Die Prüfung inventarisiert die direkte Abhängigkeitsmenge sowie die installierten transitiven Pakete und hält die von deren Paketmetadaten ausgewiesenen Lizenzkennzeichnungen fest. Für einen Installer sind ein exaktes Lockfile, Drittanbieter-Notices einschließlich PDFium und eine gesonderte Tesseract-Prüfung zwingende Freigabebedingungen.

**Auswirkung:** Der aktuelle Entwicklungsumfang ist für bewusste lokale Nutzung dokumentiert; eine öffentliche Bündelung bleibt bis zur versionsexakten Lizenz- und Datenschutzprüfung offen. [[PRIVACY_LICENSE_DEPENDENCY_AUDIT|Die Prüfungsnote]] nennt Datenflüsse, Inventar, Grenzen und konkrete Release-Aufgaben.

### 03 – Installation und Fehlerbehebung

**Kontext:** Die CLI ist unabhängig nutzbar, benötigt für Scan-OCR jedoch ein bewusst lokal installiertes Tesseract-Systemwerkzeug. Aufrufer und ein späteres Plugin müssen Erfolge mit Warnungen von Fehlern unterscheiden und sichere Diagnosen erhalten.

**Festlegung:** Die Installationsnote beschreibt den Python-Start, den lokalen Testlauf, die optionale Tesseract-Prüfung über `--version` und `--list-langs`, die ausschließlich expliziten Cloud-Voraussetzungen sowie die öffentliche Exit-Code-Semantik. Sie fordert bei Konflikten Manifestprüfung vor `update` oder `overwrite` und schließt Original-PDFs, Zugangsschlüssel und vertrauliche Inhalte aus technischen Fehlerberichten aus.

**Auswirkung:** Lokale Anwender und ein späteres Plugin können den verbindlichen CLI-Vertrag mit nachvollziehbaren, nicht destruktiven Reaktionen anwenden. [[INSTALLATION_AND_TROUBLESHOOTING|Die Installations- und Troubleshooting-Note]] verweist auf Vault-Ablage, Manifest und RAG-Übergabe.

### 04 – Versionierter RAG-Eignungsvertrag für externe Aufrufer

**Kontext:** Der reale Unigram-Lauf zeigte, dass Einzelwarnungen zwar korrekt vorlagen, aber ein aufrufender Workflow daraus nicht zuverlässig ableiten konnte, dass das lokale Derivat für RAG nicht ausreicht und welche sicheren Alternativen verfügbar sind. Die Entscheidung musste als stabiler Manifest- und CLI-Vertrag verfügbar werden, ohne die Projektgrenze zu einem Indexer oder automatischen Cloud-Client zu überschreiten.

**Festlegung:** Jede neue Konvertierung enthält `rag_readiness` mit Schema-Version, Status, lokaler RAG-Eignung, empfohlenem Derivat, nach Code und Seite verdichteten Gründen sowie vorschlagenden Folgeoptionen. Die Sperrcodes für das lokale Derivat umfassen nicht dekodierbare Zeichen, unsichere OCR, nicht rekonstruierte Formeln und unsichere komplexe Tabellen. Bei fehlendem Cloud-Derivat kann `force_ocr` oder `cloud_document` vorgeschlagen werden; beide verlangen ausdrücklich `requires_explicit_opt_in: true`. Bei empfohlenem Cloud-Derivat bleibt der Status `review_required`, bis dessen kritische Seiten bewusst geprüft sind.

**Qualitätsgrenze:** Die Eignungsprüfung verwendet lokale Analysebefunde aus Original-PDF und Derivaten; sie ist keine semantische Vollständigkeitsgarantie und startet keine neue Verarbeitung. Insbesondere werden weder Cloud-Upload noch Kosten, OCR, Vision, Indexierung oder Retrieval automatisch ausgelöst. Bestehende Manifeste werden nicht rückwirkend verändert.

**Auswirkung:** [[RAG_READINESS|Der RAG-Eignungsvertrag]] ergänzt [[RAG_INDEXING_RECOMMENDATION|die Derivatauswahl]] für CodexCLI, Obsidian und andere Aufrufer. Das lokale Unigram-Derivat würde als `local_not_suitable` mit expliziten OCR- und Cloud-Optionen erscheinen; nach einem besseren Cloud-Lauf verlangt der Vertrag weiterhin eine gezielte Sichtprüfung. Unit- und Integrationsregressionen sichern die Manifest- und CLI-Übergabe.

### 05 – Priorisierte Folgeaktion in der CLI-Ausgabe

**Kontext:** Die erste Unigram-CLI-Ausgabe enthielt bereits mehrere technisch korrekte `suggested_next_steps`, verlangte aber vom Benutzer die Priorisierung zwischen OCR und Cloud-Dokumentlauf. Bei zugleich nicht dekodierbaren Zeichen, Mehrspaltenlayout und unsicheren Tabellen war die sinnvolle nächste Handlung nicht unmittelbar sichtbar.

**Festlegung:** `rag_readiness.recommended_next_step` ergänzt die Liste um genau eine priorisierte Folgeaktion mit Typ, Opt-in-Flag und deutschsprachiger Handlungsaufforderung. Bei lokalen RAG-Sperren mit verfügbarer Cloud-Option wird `cloud_document` vor einem OCR-Forcelauf priorisiert, weil OCR komplexe Tabellen und Mehrspaltenstruktur nicht zuverlässig rekonstruiert. Bei sauberem Lauf lautet der Typ `none`; bei bereits empfohlenem Cloud-Derivat ist er `review_recommended_derivative`.

**Auswirkung:** Ein JSON-CLI-Aufrufer kann den nächsten Schritt direkt anzeigen oder als bewusste Benutzerentscheidung weiterreichen, ohne aus mehreren Vorschlägen selbst eine Qualitätsentscheidung ableiten zu müssen. Das Feld startet keine Aktion und verändert keine Exit-Codes, Artefakte oder Zugangsdaten.

## 2026-09-23

## Reaktive Stabilisierung nach Obsidian-Plugin-Abnahme

### 01 – Mittelgasse statt bloßer Seitenmitte als Mehrspaltenkriterium

**Kontext:** Der reale, über das separate Obsidian-Plugin ausgelöste Lauf von `START_PROMPT.pdf` klassifizierte die einspaltige erste Seite als zweispaltig. Die bisherige Heuristik teilte eine Zeile bereits dann in linke und rechte Spalten, wenn einzelne Wörter auf beiden Seiten der Seitenmitte lagen. Dadurch wurde normaler, breiter Fließtext in falscher Leserichtung ausgegeben.

**Festlegung:** `app.pdf_extract` teilt eine Zeile nur noch, wenn eine sichtbare Mittelgasse die Seitenmitte einschließt und mindestens acht Prozent der Seitenbreite beträgt. Ohne diese Gasse bleibt eine Zeile vollständig; die Spaltenerkennung verlangt weiterhin mindestens drei vertikal überlappende Zeilen auf jeder Seite. Ein neuer Mock-Regressionsfall enthält einspaltigen Fließtext über die Seitenmitte; die bestehende wissenschaftliche Zwei-Spalten-Fixture bleibt unverändert als positiver Fall erhalten.

**Auswirkung:** Der reale Prüflauf von `START_PROMPT.pdf` erzeugt keine `MULTI_COLUMN_LAYOUT`-Warnung mehr und bewahrt die top-to-bottom-Leserichtung. Eine tatsächlich bestätigte Mehrspaltenwarnung gehört jetzt zu den lokalen RAG-Sperren: Das lokale Derivat erhält `local_not_suitable` und schlägt ausschließlich einen ausdrücklich zu bestätigenden Cloud-Dokumentlauf vor. Weder OCR, Vision, Cloud noch Indexierung werden automatisch gestartet. Die vollständige Testsuite umfasst 170 erfolgreiche Tests.

### 02 – Typografiegestützte Überschriften und fortlaufende Listen

**Kontext:** Der reale lokale Lauf von `START_PROMPT.pdf` enthielt sichtbare Überschriften nur als Fließtext. Außerdem gab der Renderer jedes geordnete Listenelement mit `1.` und trennte Elemente durch Leerzeilen; bei einem Seitenwechsel begann dieselbe Vertragsliste erneut bei `1.`.

**Festlegung:** Die PDF-Extraktion übernimmt die lokale Schriftgröße jedes Wortes. Sie markiert nur kurze Zeilen als Überschriften, deren mittlere Schriftgröße mindestens zwanzig Prozent über der mittleren Satzschrift liegt. Gleiche gerundete Größen erhalten dieselbe Ebene. Der Markdown-Renderer zählt direkt aufeinanderfolgende geordnete Elemente sichtbar hoch, rendert zusammenhängende Listen zeilenweise und behält den Zähler über einen Seitenmarker hinweg.

**Auswirkung:** Der Prüflauf erzeugt `# Start-Prompt …`, Abschnittsüberschriften der Ebene 2 sowie die Vertragsliste `1.` bis `14.` über die ersten beiden Seiten ohne künstliche Leerzeilen zwischen den Elementen. Die Primärquelle bleibt unverändert. Mock-Tests sichern Schriftgrößenhierarchie, Listenformatierung und Seitenfortsetzung; der reale CLI-Lauf bleibt mit sieben Silbentrennungswarnungen RAG-bereit.

### 03 – Umgebrochene Zeilen innerhalb von Listenelementen

**Kontext:** Die PDF enthält im Abschnitt „Technischer Mindestumfang des ersten MVP“ neun nummerierte Elemente, deren längere Texte optisch umgebrochen sind. Die Extraktion erkannte den Beginn jedes Elements richtig, behandelte die nicht nummerierte Folgezeile aber als eigenständigen Absatz. Das unterbrach die Markdown-Liste und ließ die Anzeige der nachfolgenden Überschriften uneindeutig werden.

**Festlegung:** `build_page_blocks` führt eine nicht nummerierte Zeile nur dann mit dem unmittelbar vorangehenden Listenelement zusammen, wenn zwischen beiden keine explizite Leerzeile liegt. Eine echte Leerzeile beendet diese Bindung, sodass ein nachfolgender eigenständiger Absatz erhalten bleibt.

**Auswirkung:** Der reale Prüflauf fasst die neun MVP-Anforderungen jeweils zu einem kompakten Listenelement zusammen und rendert sie fortlaufend `1.` bis `9.`. Anschließend stehen „Tests und Abnahme“ und „Nicht-Ziele des ersten MVP“ wieder als reguläre Markdown-Überschriften. Neue Tests sichern sowohl das Zusammenführen als auch die Abgrenzung eines ausdrücklich getrennten Absatzes; die vollständige Suite umfasst 177 erfolgreiche Tests.

### 04 – Gefüllte Vektorformen als PDF-Aufzählungspunkte

**Kontext:** Im realen `START_PROMPT.pdf` sind die Aufzählungspunkte unter „Tests und Abnahme“ und „Nicht-Ziele des ersten MVP“ als kleine gefüllte blaue Vektorformen gezeichnet. Sie gehören nicht zum extrahierten Textlayer und gingen deshalb im bisherigen Markdown als Absätze verloren.

**Festlegung:** Die positionsgestützte Extraktion ordnet nur kleine, gefüllte Vektorformen links einer geometrisch passenden Textzeile als Bullet-Signal zu. Das Signal wird seitenbezogen an den Blockaufbau weitergegeben und erzeugt eine ungeordnete Markdown-Liste. Beginnt eine auf Seite 2 gestartete Liste mit einer Folgezeile auf Seite 3, bleibt der Seitenmarker eingerückt innerhalb dieses Listenelements.

**Auswirkung:** Die reale Prüfung überträgt die acht Vektor-Bullets als Markdown-Listen: vier Testpunkte und vier Nicht-Ziele, einschließlich des Seitenumbruchs im dritten Testpunkt. Die Quelle bleibt unverändert. Mock-Tests sichern Formzuordnung, Blockerzeugung und listeninterne Seitenmarker; die vollständige Suite umfasst 180 erfolgreiche Tests.

### 05 – Mehrseitige Tabellen mit sicher belegten Zellumbrüchen

**Kontext:** `Instruction_Tuning_und_KI_Interfaces.pdf` enthält eine vollständige vierspaltige Tabelle über zwei Seiten. Beide Seiten besitzen dieselbe Kopfzeile; alle Zellen sind belegt, mehrere enthalten sichtbare Zeilenumbrüche. Die bisherige Regel verwarf jede mehrzeilige Zelle und die Tabellengeometrie löste auf Seite 1 zusätzlich einen falschen Mehrspaltenbefund aus.

**Festlegung:** Vollständig belegte Zellen dürfen lokale Umbrüche als `<br>` bewahren. Direkt benachbarte Tabellen mit identischer Kopfzeile werden als eine Tabelle zusammengeführt. Für die Leseordnungsheuristik werden bestätigte Tabellenzeilen nicht als Fließtextspalten gewertet; ihr Rohtext wird nicht zusätzlich als Absatz gerendert.

**Auswirkung:** Der reale Prüflauf erzeugt eine einzelne GFM-Tabelle mit zehn Datenzeilen, ohne Tabellenwarnung oder falschen Mehrspaltenbefund. Das lokale Derivat ist dadurch wieder RAG-bereit; die Formel- und Diagrammrekonstruktion bleibt ein separater nächster Schritt. Tests sichern Zellumbrüche, Tabellenfortsetzung, Layoutabgrenzung und Rohtextunterdrückung. Die vollständige Suite umfasst 183 erfolgreiche Tests.

### 06 – Geometrisch belegte Zustandsformel als Display-LaTeX

**Kontext:** Auf Seite 2 von `Instruction_Tuning_und_KI_Interfaces.pdf` steht die zentrierte Formel `P(x_{t+1} | x_1,\ldots,x_t)`. Der Textlayer gab sie als Teil eines Fließtextabsatzes aus und verlor dabei die Script-Beziehung zwischen Basiszeichen sowie hoch- und tiefgestellten Zeichen.

**Festlegung:** Die lokale Extraktion erkennt ausschließlich eine enge, zentrierte Zustandsformel-Grammatik. Alle drei Script-Zeichen müssen gegenüber den Basiszeichen kleiner und mindestens um einen Punkt nach unten versetzt sein. Erst dann wird der belegte Inhalt als eigener Markdown-Displayblock `$$P(x^{t+1} \mid x_{1}, \ldots, x_{t})$$` ausgegeben. Fehlt eines dieser geometrischen Signale, bleibt der extrahierte Text unverändert.

**Auswirkung:** Der reale Prüflauf trennt die Formel sichtbar vom vorangehenden und nachfolgenden Fließtext und zählt genau einen Display-Formelblock. Die lokale Konvertierung bleibt ohne Warnungen RAG-bereit. Tests sichern sowohl den positiven geometrischen Befund als auch die Ablehnung gleich großer, nicht versetzter Zeichen; die vollständige Suite umfasst 186 erfolgreiche Tests. Komplexere mathematische Anordnungen und Diagramme bleiben ausdrücklich außerhalb dieser lokalen Regel.

### 07 – Sichtbare Formelgrenze als Cloud-relevanter Befund

**Kontext:** Das lokale Derivat von `Instruction_Tuning_und_KI_Interfaces.pdf` übertrug mehrere zentrierte mathematische Ausdrücke mit Pfeil- und Mengenzeichen als Text, meldete jedoch keine Qualitätsgrenze. Dadurch erhielt ein externer Aufrufer trotz nachweisbaren Rekonstruktionspotenzials keinen Cloud-Hinweis.

**Festlegung:** Die lokale Extraktion markiert ausschließlich kurze, zentrierte Zeilen mit höchstens sechs Wortgruppen und `→` oder `∈` als nicht rekonstruierte mathematische Layoutkandidaten. DocToMD erzeugt pro betroffener Seite den Befund `DISPLAY_FORMULA_LAYOUT_NOT_RECONSTRUCTED`; dieser ist eine RAG-Sperre und schlägt ausschließlich den weiterhin ausdrücklich zu bestätigenden Schritt `cloud_document` vor. Die Regel rekonstruiert oder verändert keine zusätzliche Formel.

**Auswirkung:** Der reale Prüflauf meldet den Befund auf den Seiten 3 bis 7, setzt `local_not_suitable` und empfiehlt `cloud_document`. `START_PROMPT.pdf` bleibt trotz seiner Silbentrennungswarnungen RAG-bereit mit Folgeschritt `none`. Zieltests und die vollständige Suite mit 189 Tests bestehen; die PDF-Primärquellen bleiben unverändert.

### 08 – Strukturarmer OCR-Layoutfallback als Cloud-Grenze

**Kontext:** Der lokale Lauf eines zweiseitigen, vollständig eingescannten urologischen Untersuchungsbefunds erzeugte OCR-Layoutblöcke ohne semantische Absätze, Überschriften oder nachweisbar rekonstruierte Tabelle. Die bisherige Silbentrennungswarnung ließ das Derivat dennoch als RAG-bereit erscheinen, sodass das Plugin keinen Cloud-Opt-in anbieten konnte.

**Festlegung:** Für eine OCR-Seite mit `layout_html` erzeugt DocToMD den seitenbezogenen Befund `OCR_LAYOUT_FALLBACK`, wenn weder eine semantische Überschrift noch eine verifizierte lokale Tabelle vorliegt. Der Befund ist eine lokale RAG-Sperre und priorisiert ausschließlich den weiterhin explizit zu bestätigenden Schritt `cloud_document`. Die Regel ersetzt, korrigiert oder sendet keinen Inhalt selbst.

**Auswirkung:** Der reale lokale Befundlauf meldet `OCR_LAYOUT_FALLBACK` auf Seite 1 und bietet im Plugin den getrennten Cloud-Lauf an. Unit-Tests sichern den Warnfall sowie das Ausbleiben bei erkannter Überschrift; die vollständige Testsuite umfasst 192 erfolgreiche Tests. Primärquelle, lokales Derivat und bestehende Cloud-Derivate bleiben unverändert.

### 09 – Vollseitige Scans nicht im Cloud-Derivat duplizieren

**Kontext:** Der Cloud-Lauf für einen vollständig gescannten urologischen Befund rekonstruierte Text und Labortabelle korrekt, bettete anschließend aber die beiden als PDF-Raster eingebetteten Originalseiten erneut in `Quelle.cloud.md` ein. Das ist für textorientiertes RAG redundant und beeinträchtigt die Lesbarkeit.

**Festlegung:** `inject_cloud_assets` erhält eine seitenbezogene Ausschlussmenge. Die Konvertierungsorchestrierung gibt alle Seiten weiter, die lokal als `layout_html`-OCR-Fallback erkannt wurden. Ihre Bildassets werden im Cloud-Derivat nicht verlinkt. Assets, Beschreibungs-Notes und Manifestreferenzen werden unverändert erzeugt; unbetroffene, native Abbildungen in digitalen PDFs werden weiterhin eingebettet.

**Auswirkung:** Das neue Cloud-Derivat eines gescannten Dokuments enthält nur den rekonstruierten editierbaren Inhalt. Die Scanbilder verbleiben im Asset-Ordner als visueller Prüfbeleg, ohne automatisch im empfohlenen RAG-Derivat aufzutauchen. Regressionstests sichern den Ausschluss sowie die bestehende Abbildungsübernahme; die vollständige Suite umfasst 193 erfolgreiche Tests.

### 10 – UTF-8 als CLI-Streamvertrag unter Windows

**Kontext:** Die Obsidian-Prozessbrücke dekodiert `stdout` und `stderr` korrekt als UTF-8. Der Windows-Pythonprozess konnte seine Fortschrittsmeldung dennoch in einer lokalen Codepage schreiben, wodurch beispielsweise `geprüft` als `gepr�ft` erschien.

**Festlegung:** `main.py` konfiguriert vor dem CLI-Start die reconfigurierbaren Standardstreams explizit auf UTF-8. Damit sind finaler JSON-Envelope, JSONL-Fortschritt und menschenlesbare Diagnosen bei Pipe-Aufrufen eindeutig kodiert. Importierte Test- oder eingebettete Streams ohne `reconfigure` bleiben unangetastet.

**Auswirkung:** Der Obsidian-Adapter benötigt keine Zeichenersetzung oder Sonderbehandlung. Ein realer Pipe-Lauf bestätigt die UTF-8-Bytefolge von `OCR-Prüfung wurde abgeschlossen.` bei gleichzeitig gültigem JSON-Envelope.

### 11 – Erschöpftes OpenAI-Guthaben als eigener Fehlervertrag

**Kontext:** Eine von OpenAI mit HTTP 429 abgelehnte Cloud-Anfrage wurde bisher technisch abgefangen, aber unter dem allgemeinen CLI-Code `CONVERSION_FAILED` mit einer Providerdiagnose an das Plugin weitergereicht. Der Benutzer konnte ein Guthabenproblem nicht sicher von einem zeitweisen Rate-Limit oder anderen Cloud-Fehlern unterscheiden.

**Festlegung:** Der OpenAI-Adapter wertet ausschließlich den strukturierten Remote-Code `insufficient_quota` als Guthabenproblem und erzeugt den sicheren deutschen Fehler `OpenAI-Guthaben nicht ausreichend. Bitte Billing und Credit Balance prüfen.` mit dem stabilen CLI-Code `CLOUD_INSUFFICIENT_CREDITS`. Andere HTTP-429-Fälle bleiben allgemeine Cloud-Anfragefehler. Die CLI erhält spezifische, vom Adapter gesetzte Fehlercodes, ohne Providerdaten, API-Schlüssel oder Dokumentinhalt zu protokollieren.

**Auswirkung:** Das Plugin erhält den bestehenden JSON-Fehlervertrag mit Exit-Code 2 und zeigt die deutschsprachige Meldung in seinem vorhandenen Fehlerdialog an; eine Plugin-Änderung ist nicht erforderlich. Mock-Tests sichern Klassifizierung, Bereinigung und temporäres File-Löschen; die vollständige Engine-Suite umfasst 195 erfolgreiche Tests.

### 12 – Geplante lokale Linkerhaltung vor Cloud-Rekonstruktion

**Kontext:** `Mathe1.pdf` enthält auf Seite 10 QR-Code-Piktogramme, deren Ziele als native PDF-Link-Annotationen vorliegen. Ein Cloud-Modell kann sichtbare QR-Codes beschreiben, muss aber deren eingebettete Linkziele nicht erkennen oder unverändert wiedergeben. Für RAG sind das Ziel und ein belegbarer sichtbarer Titel wichtiger als das Piktogramm.

**Festlegung:** Die geplante Phase 10 extrahiert akzeptierte `https`-Annotationen lokal vor jeder Cloud-Anfrage mit Seite und Rechteck. Sie ordnet sichtbaren Text nur bei belegbarer Geometrie zu, erzeugt sonst eine neutrale Seitenbezeichnung und speichert die vollständige Linkliste im Manifest. Dieselbe lokale Liste wird nach der Cloud-Validierung in das Cloud-Derivat injiziert und auf Vollständigkeit geprüft; sie ist nicht Teil der Modellentscheidung.

**Auswirkung:** Native QR-Ziele können als kompakte Markdown-Links im passenden Kapitel erscheinen, ohne QR-Bilder zu exportieren, URLs abzurufen oder eine QR-Decodierung zu starten. QR-Codes ohne Annotationen bleiben eine separate, noch nicht freigegebene Erweiterung. Diese Entscheidung definiert ausschließlich den Folgeumfang und verändert noch keine Konvertierung.

## 2026-09-23

## Phase 10 – Native PDF-Links und QR-Zielübergabe

### 01 – Versionierter Strukturvertrag für native PDF-Links

**Kontext:** Native PDF-Link-Annotationen enthalten ein lokal auslesbares Ziel, das nicht aus einem sichtbaren QR-Code abgeleitet werden muss. Ein unversioniertes oder koordinatenunklares Zwischenformat würde eine spätere Extraktion, lokale Markdown-Ausgabe, Manifestierung und die unveränderliche Übergabe in ein Cloud-Derivat unnötig koppeln. Die Ziel-URL darf dabei niemals zur Validierung abgerufen werden.

**Festlegung:** `NativePdfLink` ist der versionierte Strukturvertrag `1.0`. Seine Manifestdarstellung wird künftig als Container `native_pdf_links` mit `schema_version: "1.0"` und einer `items`-Liste geführt. Jedes Element enthält `target_url`, `page.page_number`, `annotation_rect` mit `left`, `bottom`, `right` und `top`, sowie `source: "native_pdf_link_annotation"`. Die Rechteckkoordinaten verwenden explizit den PDF-User-Space mit Ursprung links unten und müssen endlich sowie positiv ausgedehnt sein. `visible_title` ist optional und darf nur gesetzt werden, wenn eine spätere geometrische Zuordnung sichtbaren Text belegt; fehlender Titel bedeutet keine negative Qualitätsaussage. Die `source`-Enumeration erlaubt in dieser Version ausschließlich eine native PDF-Link-Annotation und verhindert so, dass ein Modell, eine QR-Decodierung oder ein URL-Abruf als Herkunft ausgegeben wird. Die HTTPS- und Zielvalidierung ist bewusst die nächste, getrennte Phase-10-Aufgabe.

**Auswirkung:** Extraktion und Ausgabe erhalten einen kleinen, stabilen Datentransfervertrag, ohne bereits PDFs zu lesen, QR-Codes zu decodieren oder URLs aufzurufen. Künftige Manifest- und Cloud-Schritte können nur lokal belegte, positionsgenaue Linkdaten übernehmen; sie müssen den Container mit derselben Schema-Version verwenden. Unit-Tests sichern Serialisierung, den optionalen Titel und die Rechteckgrenzen.

### 02 – Lokale Annahmeregel für externe native PDF-Ziele

**Kontext:** Eine PDF-Link-Annotation kann neben einem regulären externen Ziel auch nicht sichere Schemas, lokale Hosts, private IP-Adressen oder ein ungültiges Rechteck enthalten. Ein Aufruf oder eine DNS-Auflösung des Ziels wäre weder für die Prüfung notwendig noch mit dem lokalen Standardpfad vereinbar.

**Festlegung:** `extract_native_pdf_links` liest ausschließlich mit `pdfplumber` und ruft keine Ziel-URL auf. Es akzeptiert nur syntaktisch vollständige `https`-URLs ohne Zugangsdaten und mit nicht lokalem Host. `localhost`, `.localhost`, Loopback-, private, Link-Local-, reservierte, nicht spezifizierte und Multicast-IP-Adressen gelten als lokal und werden verworfen; Hostnamen werden nicht aufgelöst. Nicht-HTTPS-, fehlende oder syntaktisch unsichere Ziele erhalten `NATIVE_PDF_LINK_UNSAFE_URL`, lokale Ziele `NATIVE_PDF_LINK_LOCAL_TARGET`, jeweils mit Seite. Native Link-Annotationen mit fehlendem oder degeneriertem Rechteck erhalten `NATIVE_PDF_LINK_INVALID_ANNOTATION`. Gleichartige Ablehnungen werden pro Seite gezählt und zu genau einer Warnung zusammengefasst. Das Rechteck wird unmittelbar aus den PDF-Koordinaten `x0`, `y0`, `x1`, `y1` in den Strukturvertrag übernommen.

**Auswirkung:** Der nächste Schritt kann geprüfte, lokal vorhandene Annotationen ohne Netzwerkabhängigkeit weiterreichen. Die Sichttitelzuordnung, Markdown-Ausgabe, Manifestpersistenz und Cloud-Injektion bleiben ausdrücklich getrennte Folgeaufgaben. Der lesende Befund von `Mathe1.pdf` bestätigt vier akzeptierte native `https`-Annotationen auf Seite 10; deren Ziele wurden nicht abgerufen.

### 03 – Konservative geometrische Zuordnung sichtbarer Linktitel

**Kontext:** Die vier QR-Annotationen auf Seite 10 von `Mathe1.pdf` besitzen keine PDF-Annotationstitel. Die Sichtprüfung zeigt drei Beschriftungen direkt unter ihrem QR-Rechteck und die Überschrift „Fakultäten kürzen“ unmittelbar oberhalb rechts des vierten Rechtecks. Eine rein inhaltliche oder modellgestützte Zuordnung könnte dagegen einen unzutreffenden Titel erzeugen.

**Festlegung:** Die lokale Zuordnung liest lediglich Wortrechtecke derselben PDF-Seite. Sie übernimmt einen Titel nur, wenn genau ein Kandidat eines der zwei geprüften Muster erfüllt: vollständig horizontal im QR-Rechteck und höchstens 18 PDF-Punkte darunter, gegebenenfalls mit unmittelbar folgenden, ebenso enthaltenen Zeilen; oder höchstens 18 Punkte oberhalb und rechts des Rechtecks beginnend. Mehrdeutige oder weiter entfernte Texte ergeben keinen `visible_title`. `link_display_label` liefert dann ausschließlich die neutrale Bezeichnung `Externer Link auf Seite N`. Die Wortabstände werden mit der engen lokalen Toleranz von einem Punkt gelesen; voneinander getrennte Bereiche einer Zeile werden erst ab 18 Punkten Lücke getrennt, damit sichtbare Wortgrenzen wie „Fakultäten kürzen“ erhalten bleiben, aber die separate QR-Beschriftung nicht mit einer Tabellenüberschrift verschmilzt. Ein sichtbarer Zeilenendtrennstrich wird nur bei unmittelbar folgender klein geschriebener Fortsetzung entfernt; dadurch wird etwa „Logarithmus-“ plus „gesetze“ ohne sprachliche Interpretation wieder zusammengeführt.

**Auswirkung:** Alle vier Referenzlinks erhalten einen lokal geometrisch belegten sichtbaren Titel, ohne QR-Analyse, URL-Aufruf oder semantische Vermutung. Bei anderen Dokumenten bleibt ein unsicherer Titel nicht leergeraten, sondern wird später mit der neutralen Seitenbezeichnung ausgegeben. Unit-Tests sichern beide erlaubten Muster und den mehrdeutigen Ablehnungsfall.

### 04 – Kompakte lokale Markdown-Ausgabe nativer PDF-Links

**Kontext:** Ein akzeptiertes Ziel und ein geometrisch belegter Titel müssen in der lokalen Arbeitskopie für RAG sichtbar sein. QR-Piktogramme selbst enthalten für textorientiertes Retrieval keinen zusätzlichen Textnutzen und dürfen nicht als Ersatz für das lokale Linkziel in die Markdown-Ausgabe gelangen.

**Festlegung:** Die lokale Konvertierungsorchestrierung extrahiert native Links vor dem Markdown-Rendering und gibt ausschließlich akzeptierte Elemente der lokalen Liste weiter. `render_document` fügt sie je Ursprungsseite nach dem strukturierten Seiteninhalt ein, somit innerhalb des zuletzt auf dieser Seite begonnenen Kapitels. Die kompakte Liste trägt den stabilen Marker `<!-- doctomd:native-pdf-links page=N -->`, die sichtbare Bezeichnung `Lokale PDF-Links` und Markdown-Links mit der bereits validierten URL in spitzen Klammern. Ohne belegten Titel verwendet sie `Externer Link auf Seite N`. Die Rendererlogik erzeugt keine Bildreferenz aus einer Annotation; auf Seite 10 von `Mathe1.pdf` sind die QR-Codes Vektorinhalt und werden vom vorhandenen Rasterexport ohnehin nicht als Assets erkannt.

**Auswirkung:** Lokale Derivate erhalten die vier RAG-nutzbaren Ziele unter „Rechengesetze“, ohne QR-Decodierung oder Netzverkehr. Warnungen aus der lokalen Linkprüfung bleiben Teil der Qualitätsbefunde. Manifestpersistenz sowie die getrennte Cloud-Injektion folgen erst in den nächsten Aufgaben.

### 05 – Manifestvertrag und erneute Validierung nativer PDF-Links

**Kontext:** Die Markdown-Liste allein reicht für Aktualitätsprüfung, RAG-Herkunft und die nachfolgende unveränderliche Cloud-Übergabe nicht aus. Der Manifestvertrag muss deshalb das lokal ermittelte Ziel, dessen räumliche Herkunft und die Titelzuordnung maschinenlesbar bewahren, ohne neue externe Datenquellen zu nutzen.

**Festlegung:** `artifacts.native_pdf_links` ist ein optionaler Container mit `schema_version: "1.0"` und `items`. Jedes Element enthält den vertraglichen Linkkern (`target_url`, Seite, Annotationsrechteck und Herkunft) sowie `title_assignment_status`: `geometrically_verified` bei vorhandenem `visible_title`, sonst `neutral_page_label`. Vor dem Schreiben validiert `build_manifest` den sicheren relativen Markdown-Pfad, die PDF-Primärquelle und erneut Herkunft sowie HTTPS-/Nicht-Lokal-Regeln jedes Links. Die Validierung nutzt ausschließlich die lokale URL-Syntax- und IP-Prüfung; sie ruft weder URL noch DNS auf.

**Auswirkung:** Manifestkonsumenten können jeden in Markdown ausgegebenen nativen Link auf Annotation, Seite und Rechteck zurückführen und erkennen, ob sein Titel geometrisch belegt oder neutral ist. Unsichere Ziele, Nicht-PDF-Quellen und Traversalpfade werden vor der Publikation abgewiesen. Die Cloud-Übergabe verwendet diesen Container erst in der folgenden, getrennten Aufgabe.

### 06 – Autoritative lokale Linkinjektion in das Cloud-Derivat

**Kontext:** Eine technisch gültige Cloud-Antwort kann QR-Piktogramme übersehen oder vorhandene Linkinformationen umformulieren. Die Linkliste ist jedoch bereits lokal aus den nativen PDF-Annotationen validiert und darf nicht Teil einer Modellentscheidung sein.

**Festlegung:** Nach `validate_cloud_markdown_response` fügt `inject_cloud_native_pdf_links` die unveränderte, erneut lokal validierte Liste am Ende ihrer jeweiligen Seite in `Quelle.cloud.md` ein. Die Darstellung verwendet denselben stabilen Native-Link-Marker und denselben Renderer wie das lokale Derivat. Enthält die Cloud-Antwort selbst einen solchen Marker, wird der Lauf abgewiesen; nur DocToMD darf eine Native-Linkliste erzeugen. Fehlt ein erwarteter Seitenmarker für einen lokalen Link, wird ebenfalls abgebrochen. Die Funktion fragt keine URL ab und übernimmt weder Ziele noch Titel aus der Cloud-Antwort.

**Auswirkung:** Ein akzeptierter lokaler Link kann durch die Cloud-Antwort weder entfernt noch ersetzt werden; die Cloud-Ausgabe erhält stets die maßgebliche, seitenbezogene lokale Liste. Die umfassende Vollständigkeits- und Abweichungsprüfung bleibt die nächste Phase-10-Aufgabe.

### 07 – Vollständigkeitsprüfung vor der RAG-Empfehlung

**Kontext:** Die lokale Injektion schützt die normale Cloud-Ausgabe, doch eine spätere Änderung am Renderer oder an der Cloud-Nachbearbeitung könnte die seitenbezogene Linkliste dennoch auslassen, verändern oder doppelt einfügen. In diesem Fall dürfte ein fehlerhaftes Cloud-Derivat nicht als erfolgreiches oder empfohlenes RAG-Derivat erscheinen.

**Festlegung:** `verify_native_pdf_link_coverage` erzeugt für jede Seite die kanonische Liste erneut mit dem lokalen Renderer und verlangt sie im jeweiligen Markdown genau einmal. Dadurch werden Marker, Seite, Ziel-URL sowie belegter oder neutraler Titel gemeinsam und ohne URL-Abruf geprüft. Das lokale Derivat wird unmittelbar nach dem Rendering geprüft. Das Cloud-Derivat wird nach allen lokalen Ergänzungen und noch vor RAG-Empfehlung, Manifest- und Derivatschreiben geprüft. Eine Cloud-Abweichung wird als `CLOUD_NATIVE_LINK_COVERAGE` abgewiesen.

**Auswirkung:** Jeder akzeptierte native Link ist im möglichen RAG-Derivat mit seinem Seitenbezug nachweisbar vertreten. Ein unvollständiges, verändertes oder doppelt vorhandenes Cloud-Listenartefakt wird weder geschrieben noch empfohlen; die Standardverarbeitung bleibt lokal und netzwerkfrei.

### 08 – Regressionsbasis für native QR-Ziele

**Kontext:** Die vier Ziele auf Seite 10 von `Mathe1.pdf` verbinden reale Annotationsgeometrie, mehrzeilige Titelzuordnung und die spätere Cloud-Übergabe. Die proprietäre Referenzquelle gehört jedoch nicht zu den versionierten Testfixtures und darf weder kopiert noch verändert werden.

**Festlegung:** Der PDF-Regressionstest prüft die Referenzquelle ausschließlich lesend und wird nur ausgeführt, wenn sie am festgelegten lokalen Pfad vorhanden ist. Er fordert die vier akzeptierten `https`-Ziele auf Seite 10 einschließlich ihrer geometrisch belegten Titel und gültiger Rechtecke. Ergänzende stets ausführbare Mock-Tests sichern die Linkausgabe in einem mehrseitig fortgesetzten Kapitel, ungültige Annotationen und die Ergänzung einer Cloud-Antwort, die selbst keine Links enthält.

**Auswirkung:** Die CI bleibt ohne externe oder proprietäre PDF lauffähig, während der lokale Prüflauf den realen QR-Annotationsbefund zuverlässig gegen künftige Änderungen absichert. Kein Test ruft eine Ziel-URL ab oder decodiert einen QR-Code.

### 09 – QR-Decodierung ohne native PDF-Annotation bleibt außerhalb des Standardpfads

**Kontext:** Ein sichtbarer QR-Code kann ein Ziel enthalten, wenn die PDF selbst keine Link-Annotation bereitstellt. Seine Decodierung wäre jedoch eine neue Bildanalyse mit eigener Erkennungsunsicherheit und könnte aus einem Piktogramm ein nicht anderweitig belegtes Ziel erzeugen. Sie ist weder erforderlich, um die lokal vorliegenden nativen Annotationen von `Mathe1.pdf` zu bewahren, noch Teil der netzwerkfreien Standardkonvertierung.

**Festlegung:** DocToMD implementiert in Phase 10 keine QR-Decodierung. Fehlt eine akzeptierte native Annotation, entsteht kein Link aus einem QR-Piktogramm und keine Warnung, die ein Ziel behauptet. Eine spätere Erweiterung erfordert einen eigenen, ausdrücklich freigegebenen Auftrag mit separatem Strukturvertrag, lokalem Opt-in, Bildherkunft und Rechteck, Decodierungsstatus beziehungsweise Konfidenz, sichtbarer Qualitätswarnung sowie Mock- und realen PDF-Regressionen. Auch dann darf eine decodierte URL nicht abgerufen, durch ein Cloud-Modell bestätigt oder mit einer nativen PDF-Annotation gleichgesetzt werden.

**Auswirkung:** Die derzeitige Linkliste enthält ausschließlich sicher herkunftsbelegte Annotationen. Der Standardpfad bleibt klein, lokal und netzwerkfrei; QR-Codes ohne Annotationen werden weder stillschweigend ignoriert als Link noch als erfundene Ziele ausgegeben.

## 2026-09-24

## Phase 11 – Wiederverwendbare Cloud-Ableitung und mathematische Batch-Verarbeitung

### 01 – Geplante Trennung lokaler Basis und Cloud-Ableitung

**Kontext:** Der aktuelle `convert`-Ablauf berechnet den lokalen Konvertierungskontext erneut, wenn ein Benutzer nach einem bereits abgeschlossenen lokalen Lauf den Cloud-Modus auswählt. Bei einem erstmalig cloud-aktivierten Lauf wird das lokale Ergebnis zudem erst nach der Cloud-Phase veröffentlicht. Das verursacht unnötige lokale Arbeit und erschwert eine sichere Wiederaufnahme bei Budget- oder Zeitfehlern.

**Festlegung:** Phase 11 führt einen versionierten, aus dem lokalen Manifest sicher rehydrierbaren Kontext sowie eine eigenständige, ausdrücklich anzufordernde `cloud-derive`-Ableitung ein. Bei gültigem Quellfingerabdruck darf ein Cloud-Opt-in diesen Kontext automatisch wiederverwenden und muss den Benutzer darüber als Fortschrittsereignis informieren. Ohne Cloud-Opt-in startet keine Netzwerkanfrage. Lokales Markdown und Basismanifest werden vor einer Cloud-Anfrage atomisch veröffentlicht. Die spätere Batch-Verarbeitung baut auf demselben Kontext auf und speichert Erfolge beziehungsweise offene Response-IDs einzeln.

**Auswirkung:** Ein unverändertes lokales Ergebnis kann als stabile, prüfbare Basis für Cloud-Qualität und Wiederaufnahme dienen, ohne die lokale Extraktion zu wiederholen. Fehler eines Cloud-Laufs beschädigen oder verstecken keine lokalen Artefakte. Die genaue Batchgröße und der überarbeitete mathematische Prompt bleiben getrennte Folgeaufgaben mit realer Evaluation.

### 02 – Versionierter lokaler Wiederverwendungskontext

**Kontext:** Eine spätere Cloud-Ableitung darf ein bereits geprüftes lokales Ergebnis nur verwenden, wenn weder die PDF-Primärquelle noch das technische Markdown, die Manifestreferenzen, Assets, Qualitätsbefunde oder nativen PDF-Links unbemerkt verändert wurden. Das bisherige Manifest enthielt keinen eigenen Nachweis für den unveränderten Markdown-Inhalt.

**Festlegung:** `artifacts.local_reuse` führt den lokalen Vertrag `1.0` mit SHA-256 des UTF-8-Markdowns und der lückenlosen Seitenmarkerfolge. `rehydrate_local_reuse_context` bestimmt den Quellfingerabdruck erneut und verlangt Übereinstimmung von kanonischem PDF-Pfad, MIME-Typ, Größe, Hash und Änderungszeit. Es akzeptiert nur sichere, im Manifestordner auflösbare relative Markdown-, Asset- und Beschreibungsdateipfade, prüft deren Existenz, rekonstruiert Qualitätsbefunde ausschließlich bei konsistentem Status und prüft alle Seitenbezüge gegen die Markdown-Marker. Native PDF-Links werden aus dem versionierten Manifestcontainer erneut in Domänenmodelle überführt, mit der bestehenden HTTPS-/Nicht-Lokal-Validierung geprüft und mit `verify_native_pdf_link_coverage` exakt gegen das Markdown abgeglichen. Fehlt der Vertrag oder weicht das Markdown von seinem Hash ab, wird die Wiederverwendung abgewiesen; eine manuelle Bearbeitung gilt damit nicht stillschweigend als unveränderte technische Basis.

**Auswirkung:** Der Kontext ist rein lokal und löst weder PDF-Textextraktion, OCR, Tabellen-, Bild- oder Linkanalyse noch Netzverkehr aus. Er stellt einer folgenden, ausdrücklich getrennten `cloud-derive`-Aufgabe eine unveränderliche, typisierte Basis mit Markdown, Assets, Qualitätsbefunden und autoritativen nativen Links bereit. Bestehende Artefakte ohne `local_reuse` bleiben bewusst nicht rehydrierbar und müssen nicht verändert werden. Die Suite umfasst 221 erfolgreiche Tests.

### 03 – Lokale Basis vor der Cloud-Grenze veröffentlichen

**Kontext:** Der frühere `convert`-Ablauf hielt Markdown und Manifest bis nach Cloud-Anfrage und Cloud-Validierung zurück. Ein Netzwerk-, Budget- oder Validierungsfehler konnte damit ein bereits vollständig ermitteltes lokales Ergebnis unsichtbar lassen, obwohl die Primärquelle und die lokale Verarbeitung erfolgreich waren.

**Festlegung:** Nach lokaler Extraktion, Qualitätsprüfung, Native-Link-Abdeckung und Aufbau des Wiederverwendungskontexts veröffentlicht `convert_pdf` zunächst Atomar `Quelle.md` und ein Basismanifest ohne Cloud-Derivat oder Cloud-Telemetrie. Lokale Vision-Sidecars werden vor dem Basismanifest geschrieben. Erst danach darf der ausdrücklich aktivierte Cloud-Pfad beginnen. Bei Cloud-Erfolg wird zunächst ausschließlich `Quelle.cloud.md` geschrieben und danach das Manifest mit Cloud-Pfad, Telemetrie und aktualisierter RAG-Empfehlung atomar ersetzt; das lokale Markdown wird dabei nicht erneut geschrieben. Cloud-Fehler beenden den Lauf, lassen die veröffentlichte lokale Basis aber unverändert bestehen.

**Auswirkung:** Ein Cloud-Ausfall verhindert oder verändert keine geprüfte lokale Arbeitskopie. Die spätere `cloud-derive`-Schnittstelle kann auf ein vollständiges, lokales Markdown-/Manifest-Paar aufbauen. Mock-Tests sichern Anfrage- und Native-Link-Validierungsfehler mit erhaltener lokaler Basis sowie den manifest-only Abschluss bei Cloud-Erfolg. Die Suite umfasst 223 erfolgreiche Tests.

### 04 – Expliziter CLI-Vertrag `cloud-derive`

**Kontext:** Ein Cloud-Lauf aus einer vorhandenen lokalen Basis darf weder über versteckte Optionen noch über einen erneuten `convert`-Durchlauf ausgelöst werden. Aufrufer benötigen vor der Rehydrierungsintegration einen kleinen, stabilen und geheimnisfreien Befehl, der klar von lokaler Extraktion, OCR und Vision getrennt ist.

**Festlegung:** `doctomd cloud-derive INPUT.pdf --output-dir AUSGABEORDNER` erhält ausschließlich `--on-conflict error|overwrite`, `--cloud-document-model`, `--cloud-document-timeout-seconds`, `--cloud-document-max-output-tokens`, `--json` und `--progress`. Der Befehl impliziert den ausdrücklich aktivierten OpenAI-Modus; eine Modusoption, OCR-, Vision- und lokale Konvertierungsoptionen sind ausgeschlossen. Modell, Timeout und Tokenlimit werden bereits über `CloudDocumentConfig` lokal validiert. Bis die folgende Aufgabe die sichere Rehydrierung und Ableitung verbindet, liefert ein ansonsten gültiger Aufruf den stabilen Fehlercode `CLOUD_DERIVE_NOT_AVAILABLE` und startet weder `convert` noch eine Cloud-Anfrage.

**Auswirkung:** Externe Aufrufer können die endgültige Befehlsform jetzt fest integrieren, ohne dass ein noch nicht rehydrierter Aufruf stillschweigend Arbeit wiederholt oder Daten überträgt. Die nächste Aufgabe ersetzt ausschließlich den vorläufigen Verfügbarkeitsfehler durch die aus dem geprüften lokalen Kontext ausgeführte Ableitung. Die Suite umfasst 226 erfolgreiche Tests.

### 05 – Automatische Cloud-Ableitung aus einem gültigen lokalen Kontext

**Kontext:** Ein Nutzer kann bei `convert` nach einem lokalen Lauf bewusst den Cloud-Modus aktivieren. Der bisherige Ablauf würde in diesem Fall trotz vorhandener lokaler Basis erneut PDF-Text extrahieren, OCR prüfen sowie Tabellen, Bilder und native Links analysieren.

**Festlegung:** Bei `convert --cloud-document-mode openai` prüft die CLI vor dem lokalen Ablauf rein lesend, ob Quellfingerabdruck, Basismanifest, Markdown, Assets, Qualitätsbefunde und Native-PDF-Links den Wiederverwendungskontext erfüllen. Nur bei Erfolg meldet sie das Fortschrittsereignis `reuse/redirected` und ruft den neuen `cloud_derive_service` auf. Dieser nutzt ausschließlich den rehydrierten Kontext, validiert die Cloud-Antwort gegen dessen Seitenzahl, ergänzt autoritative lokale Assets, Warnungen und Links und aktualisiert danach Cloud-Derivat und Manifest; das lokale Markdown wird nicht neu geschrieben. Ein ungültiger oder fehlender Kontext lässt `convert` unverändert im vollständigen lokalen Ablauf weiterlaufen.

**Auswirkung:** Ein expliziter Cloud-Opt-in nach einem unveränderten lokalen Lauf wiederholt keine lokale PDF-Pipeline und informiert den Aufrufer darüber. Direkte `cloud-derive`-Aufrufe verwenden denselben Dienst. Mock-Tests sichern die unterlassene lokale Konvertierung, den Fortschrittshinweis, die Manifestaktualisierung und die Unveränderlichkeit des lokalen Markdown. Die Suite umfasst 228 erfolgreiche Tests.

### 06 – Gebundene Wiederaufnahme von Cloud-Hintergrundläufen

**Kontext:** Eine gespeicherte `response_id` allein darf nicht zur Wiederaufnahme berechtigen: Die PDF, das technische lokale Markdown, das ausgewählte Modell oder der Promptvertrag können sich zwischen Anfrage und Fortsetzung geändert haben. Eine Antwort unter abweichenden Voraussetzungen würde ansonsten unbemerkt als Ableitung der falschen technischen Basis veröffentlicht.

**Festlegung:** `Quelle.cloud-run.json` erhält den versionierten Vertrag `1.0` mit Response-ID, Quell-SHA-256, SHA-256 des durch `artifacts.local_reuse` abgesicherten Markdown, Modell-ID, `CLOUD_DOCUMENT_PROMPT_VERSION` und Startzeit. `cloud_derive_service` rehydriert den lokalen Kontext zuerst und fragt eine offene Response ausschließlich ab, wenn alle fünf Bindungen exakt übereinstimmen. Bei jeder Abweichung oder einem ungültigen Statusobjekt wird die gespeicherte ID ignoriert und eine neue Anfrage normal vorbereitet; sie wird nicht blind weiterverwendet. Nach erfolgreicher Validierung und atomischer Veröffentlichung von Cloud-Derivat und Manifest wird der Zustand entfernt. Der direkte lokale Erstlauf speichert dieselben Bindungen, damit die nachfolgende `cloud-derive`-Wiederaufnahme denselben Vertrag verwendet.

**Auswirkung:** Wiederaufnahme löst weder PDF-Neu-Upload noch lokale Extraktion, OCR, Tabellen-, Bild- oder Linkanalyse aus, sofern die technische Basis identisch ist. Änderungen am Markdown, an der Quelle, dem Modell oder dem Prompt erzwingen dagegen bewusst keine Verwendung einer alten Cloud-Antwort. Mock-Regressionen prüfen die exakte Wiederaufnahme ohne Upload sowie die Ablehnung jeder abweichenden Bindung. Die Suite umfasst 230 erfolgreiche Tests.

### 07 – Inhaltsbasierte Mindestvollständigkeit des Cloud-Derivats

**Kontext:** Lückenlose Seitenmarker und ein abgeschlossener API-Status beweisen nicht, dass eine Cloud-Antwort den lokalen Seiteninhalt bewahrt. Eine Seite, die nur eine Überschrift oder einen Warn-Callout enthält, konnte bisher technisch gültig sein und durch ihre Überschrift sogar als strukturreicheres RAG-Derivat empfohlen werden.

**Festlegung:** Vor Asset-, Warnungs- und Native-Link-Injektion vergleicht `verify_cloud_content_completeness` jede Cloud-Seite mit dem rehydrierten lokalen Markdown derselben Seite. Seiten mit lokalem Fließ- oder Listeninhalt benötigen mindestens ein Fünftel ihrer lokalen Wortdichte, mindestens jedoch ein bis drei nicht aus Überschriften, Bildern oder Warn-Callouts stammende Wörter. Lokal sichtbare GFM-Tabellen und `$`-/`$$`-Formelstrukturen benötigen außerdem jeweils einen gleichartigen Markdown-Strukturträger im Cloud-Derivat. Lokal leere Seiten dürfen weiterhin mit einem sichtbaren Warnhinweis erscheinen. Die Prüfung bewertet keine semantische Gleichheit und ruft keine Quelle oder URL ab.

**Auswirkung:** Dünne Warnungs- oder Überschriftenableitungen, verlorene Tabellen und verlorene Formelstrukturen werden mit `CLOUD_MARKDOWN_CONTENT_INCOMPLETE` abgewiesen, bevor Cloud-Datei, Manifest oder RAG-Empfehlung geschrieben werden. Die unveränderte lokale Basis bleibt erhalten. Der gleiche Check schützt sowohl den direkten lokalen Cloud-Lauf als auch `cloud-derive`. Die Suite umfasst 235 erfolgreiche Tests.

### 08 – Deterministische lokale Batch-Planung für mathematische Seiten

**Kontext:** Lange mathematische PDFs dürfen nicht in beliebig große Cloud-Anfragen zerfallen. Die spätere Batch-Ausführung benötigt deshalb vorab eine stabile, aus der bereits geprüften lokalen Basis ableitbare Seiteneinteilung, ohne die PDF erneut zu analysieren oder temporäre Dateien zu erzeugen.

**Festlegung:** `plan_math_cloud_batches` verarbeitet ausschließlich Markdown mit lückenlosen, kanonischen Seitenmarkern und liefert einen versionierten Vertrag `1.0`. Ein Batch enthält höchstens sechs fortlaufende Seiten. Ein H1- oder H2-Start auf einer nachfolgenden Seite beendet den vorherigen Batch bevorzugt. Seiten mit mindestens zwei sichtbaren Display-Formeln oder mindestens einer Tabelle gelten als dicht; jeder Batch enthält höchstens eine solche Seite. Batch-IDs sind aus fortlaufender Nummer und erstem/letztem Seitenbezug deterministisch gebildet. Ungültige Seitenmarker brechen die Planung ab.

**Auswirkung:** Die nächste Aufgabe kann genau diese Seitenbereiche in temporäre Ableitungen überführen, ohne Kapitelgrenzen zu erraten oder die Primärquelle zu verändern. Der Plan selbst besitzt keinen Cloud-Zustand, führt keine Dateioperationen außerhalb von Tests aus und aktiviert keinen Netzwerkzugriff. Unit-Tests sichern Sechs-Seiten-Limit, Kapiteltrennung, Dichtebegrenzung und Markerablehnung. Die Suite umfasst 239 erfolgreiche Tests.

### 09 – Kurzlebige Batch-PDFs und vollständige Zusammenführung

**Kontext:** Ein geplanter Seitenbereich muss als echte PDF an den bestehenden Cloud-Adapter übergeben werden, darf dabei aber weder die Primärquelle verändern noch aus Batch-seitiger Sicht die Originalseitennummern verlieren. Einzelne gültige Antworten dürfen nicht zu einem veröffentlichten Gesamtergebnis führen, solange ein anderer Batch fehlt oder ungültig ist.

**Festlegung:** Bei mehr als einem geplanten Batch erstellt `execute_cloud_batches` unter einem automatisch bereinigten System-Temp-Verzeichnis mit `pypdf` für jeden Bereich eine neue PDF aus unveränderten Originalseiten. Nach dem Schreiben prüft es lokal die erwartete Seitenzahl. Jede Cloud-Anfrage enthält einen ergänzten Promptvertrag mit den erwarteten Originalseitennummern; `validate_cloud_markdown_response` akzeptiert dafür explizite, nicht bei eins beginnende Markerfolgen. Erst wenn jede einzelne Antwort ihren jeweiligen Batch vollständig und kanonisch erfüllt, werden die Batches in Planreihenfolge mit genau einer Leerzeile zwischen den Abschnitten zusammengeführt. Ein Fehler bricht vor Cloud-Derivat und Manifestveröffentlichung ab; das temporäre Verzeichnis wird in jedem Fall entfernt.

**Auswirkung:** Mehrseitige mathematische Dokumente werden in kleine, lokal nachvollziehbare Einzelanfragen zerlegt, ohne die Original-PDF oder das lokale Markdown zu ändern. Ein-Batch-Läufe bleiben beim bisherigen vollständigen PDF- und Wiederaufnahmeweg. Batch-Response-IDs und die detaillierte Telemetrie werden bewusst noch nicht persistent gespeichert; dies ist die unmittelbar folgende Aufgabe. Tests prüfen die unberührte Quelle, Seitenreihenfolge, temporäre Bereinigung, Batch-Validierung und die Einbindung in `cloud-derive`. Die Suite umfasst 242 erfolgreiche Tests.

### 10 – Persistente Wiederaufnahme einzelner Cloud-Batches

**Kontext:** Nach einer Unterbrechung eines Mehrbatch-Laufs darf weder ein bereits validierter Batch erneut hochgeladen noch eine offene Hintergrundanfrage durch eine zweite Anfrage ersetzt werden. Der bisherige einwertige Wiederaufnahmezustand kann jedoch weder Batchplan noch einzelne Ergebnisse ausdrücken.

**Festlegung:** `Quelle.cloud-run.json` verwendet für Mehrbatch-Läufe den separaten Schema-Vertrag `2.0`. Er bindet Quellhash, lokalen Markdown-Hash, Modell, Promptvertragsversion und die vollständige Reihenfolge aus Batch-ID und Originalseiten. Jeder Eintrag enthält entweder keinen Zustand, eine offene `response_id` oder nach lokaler Markerprüfung das Batch-Markdown samt serialisierter Antworttelemetrie. Vor jedem neuen Upload wird der Zustand atomar geschrieben; ein Neustart lädt ihn nur bei exakter Bindung, validiert erfolgreiche gespeicherte Inhalte erneut, fragt offene IDs ab und lädt nur zustandslose Batches hoch. Nach der vollständigen Zusammenführung erscheinen die einzelnen Telemetrien als `conversion.cloud_document.mode: "batched"` im Abschlussmanifest; erst nach dessen Veröffentlichung wird die Zustandsdatei entfernt.

**Auswirkung:** Unterbrochene Mehrbatch-Läufe können sicher fortgesetzt werden, ohne Erfolgsergebnisse zu duplizieren. Ungültige, unvollständige oder an Quelle, Kontext, Modell, Prompt oder Plan nicht exakt gebundene Statusdateien werden nicht wiederverwendet. Die lokale Basis und die Original-PDF bleiben unverändert. Mock-Tests sichern die Wiederverwendung eines erfolgreichen ersten Batches, das Weiterabfragen eines offenen zweiten Batches sowie die Planbindung. Die Suite umfasst 244 erfolgreiche Tests.

### 11 – Regressionen für Batchfehler und Wiederaufnahme

**Kontext:** Die Batch-Ausführung besitzt mehrere Ausfallgrenzen, die sich ohne echte Cloud-Anfrage reproduzierbar absichern lassen müssen: abweichende Primärquelle, ausgeschöpftes Guthaben, Timeout nach erhaltener Response-ID, unvollständige Antwort sowie Reihenfolge und Vollständigkeit der Zusammenführung.

**Festlegung:** Die Tests verwenden ausschließlich temporäre lokale Blanko-PDFs und gemockte Transportantworten. Sie prüfen, dass ein veränderter Quellfingerabdruck keinen Batchzustand wiederverwendet, ein Budgetfehler den erfolgreichen ersten Batch erhält und den fehlenden zweiten nicht als Erfolg markiert, ein Timeout mit gespeicherter Response-ID beim nächsten Lauf nur diese ID weiter abfragt und keinen Batch erneut hochlädt sowie eine als `incomplete` markierte Antwort weder zusammenführt noch als erfolgreich speichert. Die bestehende Batch-Regression sichert zusätzlich originale Seitenreihenfolge, temporäre Bereinigung, deterministisches Merge-Ergebnis und erhaltene Telemetrie.

**Auswirkung:** Fehlerpfade bleiben lokal nachvollziehbar und können keine teilweise Cloud-Ableitung publizieren. Die Tests benötigen weder API-Schlüssel noch Netzverkehr und verändern keine reale Quelle. Die Suite umfasst 246 erfolgreiche Tests.

### 12 – Kontrollierte reale Evaluation des mathematischen Cloud-Derivats

**Kontext:** Vor einem Cloud-Gesamtlauf mit dem langen mathematischen Referenzdokument musste die praktische Eignung des wiederverwendbaren lokalen Kontexts, der Formelerhaltung und der RAG-Empfehlung an einem kleinen, anspruchsvollen Ausschnitt belegt werden. Die Seiten 9–14 enthalten neben Fließtext mehrspaltige Rechengesetze, Tabellenstrukturen, Polynomdivisionen, Partialbruchzerlegung, vollständige Induktion und native PDF-Links.

**Festlegung:** Eine lokale mathematische Referenzquelle wurde ausschließlich lesend in einem neuen, isolierten und nicht versionierten Ausgabeordner verarbeitet; vorhandene Artefakte blieben unverändert. Ein ausdrücklich freigegebener Cloud-Test für einen begrenzten Seitenbereich erfüllte die Seitenmarker-, Mindestvollständigkeits- und Native-Link-Prüfungen. Das Transportprotokoll enthielt keinen belastbaren Preisbetrag; Kosten werden deshalb nicht geschätzt oder aus externen Preisen abgeleitet. Die Sichtprüfung bestätigte Tabellen, LaTeX-Arrays und strukturierte Formelabschnitte als erhaltene Strukturmerkmale, nicht als Behauptung verlustfreier Rekonstruktion.

**Auswirkung:** Die Evaluation empfiehlt das validierte Cloud-Derivat für diesen Ausschnitt: Es enthält 34 Display-Formeln und drei Tabellen bei einem Strukturscore von 86 gegenüber 0 Display-Formeln, 0 Tabellen und Score 17 im lokalen Derivat. Die Qualitätsentscheidung bleibt absichtlich `review_required`, weil die lokale Basis auf mehreren Seiten mehrspaltiges Layout, nicht rekonstruierte Formelgeometrie, ungültige Glyphen und nicht unterstützte Tabellen meldet. Damit ist die Evaluationsaufgabe abgeschlossen, aber kein Gesamtlauf freigegeben oder ausgelöst; eine gesonderte fachliche Entscheidung muss vor einem solchen Lauf Kostenrahmen und die verbleibende Stichprobenprüfung berücksichtigen.

### 13 – Korrekturen nach realem Batchversuch

**Kontext:** Der reale Budgettest mit `Mathe1.pdf` zeigte vor einem Budgetfehler zwei produktive Grenzen: Die lokale H1/H2-Heuristik behandelte Laufköpfe, Inhaltsverzeichniszeilen und aus Formelresten entstandene Überschriften als Kapitelgrenzen und erzeugte dadurch 152 Batches. Zudem antwortete der zweite Einseitenbatch nicht mit dem verlangten Originalseitenmarker. Der erstmalige Cloud-Opt-in startete davor noch eine vollständige PDF-Anfrage statt des Batchpfads.

**Festlegung:** Die Batchplanung erkennt Kapitelstarts nur noch bei aussagekräftigen H1/H2-Zeilen und ignoriert Kopfzeilen mit der aktuellen Seitenzahl, Punktführer des Inhaltsverzeichnisses, `cid`-Reste und sehr kurze Formelüberschriften. Der Batch-Promptvertrag `1.4` verlangt für jeden Batch zusätzlich als erste nichtleere Zeile den konkreten Originalseitenmarker, auch wenn die Teil-PDF physisch bei Seite eins beginnt; die Versionsanhebung verhindert die Wiederverwendung älterer Antworten. Eine abgeschlossene Antwort mit abweichendem ersten, fehlendem oder nichtkanonischem Seitenmarker wird aus dem Wiederaufnahmeeintrag entfernt, während Timeout- und Trunkierungszustände weiterhin weiter abgefragt werden. Ein neuer `convert --cloud-document-mode openai` veröffentlicht zuerst die lokale Basis und ruft danach `cloud-derive` auf, sodass auch der Erstlauf die Batchplanung verwendet.

**Auswirkung:** Der lokale Plan für die vorhandene Mathe1-Basis sinkt von 152 auf 72 Batches, ohne eine semantische Kapitelstruktur zu erfinden. Ein endgültig markerungültiger Batch blockiert einen späteren ausdrücklich gestarteten Wiederholungsversuch nicht mehr, ein unklarer Hintergrundzustand wird dagegen nicht doppelt hochgeladen. Die lokale Basis und das Original-PDF bleiben bei jeder dieser Grenzen unverändert.

### 14 – Separater Cloud-Seitenbereichstest ohne Batch-Wiederaufnahme

**Kontext:** Die vollständige Batch-Ausführung ist absichtlich an eine lückenlose Abdeckung aller Originalseiten und einen persistenten Wiederaufnahmezustand gebunden. Ein kontrollierter Test einzelner Seiten darf diese Semantik weder umgehen noch das reguläre Cloud-Derivat, das Konvertierungsmanifest oder einen eventuell offenen Batchlauf verändern.

**Festlegung:** Der ausdrücklich aktivierte Befehl `doctomd cloud-evaluate INPUT.pdf --output-dir AUSGABEORDNER --pages SEITEN` akzeptiert ausschließlich eine positive Seite oder einen aufsteigenden zusammenhängenden Bereich. Er rehydriert den bestehenden lokalen Kontext vollständig, wählt dessen Markdown-Seiten aus, erstellt mit `pypdf` eine automatisch bereinigte Teil-PDF und verwendet `build_batch_cloud_markdown_instructions` mit den Originalseitennummern. Die Antwort wird gegen genau diese Marker und gegen die lokale Mindestvollständigkeit geprüft. Danach werden nur Assets, sichtbare Qualitätswarnungen und native PDF-Links des Bereichs ergänzt; die Linkabdeckung wird erneut lokal verifiziert. Es entstehen konfliktgeschützt ausschließlich `Quelle.pages-<Bereich>.local.md`, `Quelle.pages-<Bereich>.cloud.md` und `Quelle.pages-<Bereich>.evaluation.json`. Der Dienst liest oder schreibt keine `Quelle.cloud.md`, `Quelle.conversion.json` oder `Quelle.cloud-run.json` und ruft keine Linkziele ab.

**Auswirkung:** Ein kleiner, separat nachvollziehbarer Cloud-Test kann aus einer technisch unveränderten lokalen Basis erfolgen, ohne PDF-Extraktion, OCR, Tabellen-, Bild- oder Linkanalyse erneut auszuführen und ohne einen späteren Gesamtlauf zu beeinflussen. Die Regressionen verwenden nur temporäre Blanko-PDFs und gemockte Cloud-Transportantworten; sie sichern Bereichsparser, Originalseiten-Prompt, getrennte Artefakte sowie die bytegenaue Unveränderlichkeit von Manifest und regulärem Cloud-Derivat. Die Suite umfasst 252 erfolgreiche Tests.

### 15 – Inhaltsprüfung vor Batch-Wiederverwendung

**Kontext:** Eine batchweise Markerprüfung kann eine abgeschlossene Antwort als wiederverwendbar speichern, obwohl ihr eine lokal sichtbare Tabelle oder Formelstruktur fehlt. Die bisherige Gesamtprüfung erkannte diesen Verlust erst nach der Zusammenführung aller Batches. Ein einzelner inhaltlich fehlerhafter Batch blockierte dadurch den Abschluss, ohne dass der Wiederaufnahmezustand den betroffenen Bereich automatisch präzise identifizierte.

**Festlegung:** `execute_cloud_batches` erhält die bereits rehydrierte lokale Markdown-Basis und prüft jede gespeicherte sowie jede frisch empfangene Batchantwort mit `verify_cloud_content_completeness` gegen genau ihre Originalseiten. Eine gespeicherte, marker-korrekte aber inhaltlich unvollständige Antwort wird aus ihrem einzelnen Wiederaufnahmeeintrag entfernt und im selben ausdrücklich gestarteten Lauf erneut angefragt. Bleibt die frische Ersatzantwort unvollständig, wird nur dieser Eintrag zurückgesetzt und der Lauf mit `CLOUD_MARKDOWN_CONTENT_INCOMPLETE` abgebrochen. Alle anderen geprüften Batchantworten, Telemetrien und Response-IDs bleiben unverändert.

**Auswirkung:** Ein Verlust wie die fehlende Tabelle auf Seite 40 führt nicht mehr erst nach der teuren Gesamtzusammenführung zu einer manuellen Zustandsanalyse. Ein expliziter Folgelauf überträgt ausschließlich den betroffenen Batch erneut; erfolgreiche Nachbarbatches werden nicht wieder hochgeladen. Die Mock-Regression sichert sowohl die gezielte Rücksetzung als auch die Wiederverwendung eines anderen gespeicherten Batches. Die Suite umfasst 253 erfolgreiche Tests.

### 16 – Konservative Erkennung von GFM-Tabellen in der Cloud-Vollständigkeitsprüfung

**Kontext:** Beim realen Batch 18 für die Originalseiten 39–41 enthielt die lokale Textextraktion auf Seite 40 eine Formelrestzeile wie `|5| 5`. Die bisherige Heuristik wertete jede mit `|` beginnende Zeile als Tabelle. Dadurch verlangte sie von der Cloud-Antwort fälschlich eine GFM-Tabelle und verwarf eine ansonsten marker-gültige Antwort als unvollständig.

**Festlegung:** `verify_cloud_content_completeness` erkennt eine lokale GFM-Tabelle ausschließlich anhand einer gültigen Markdown-Tabellentrennzeile mit mindestens drei Bindestrichen je Spalte. Einzelne senkrechte Striche, wie sie aus Formeln oder fehlerhafter PDF-Textdekodierung entstehen können, sind kein Tabellenbeleg. Die Prüfung bleibt weiterhin konservativ: Liegt eine echte GFM-Tabellentrennzeile vor, muss das Cloud-Derivat weiterhin einen gleichartigen Strukturträger enthalten.

**Auswirkung:** Batch 18 wird nicht mehr wegen einer vermeintlichen Tabelle auf Seite 40 abgewiesen. Der reale lokale Profilcheck bestätigt für die Seiten 39, 40 und 41 keine GFM-Tabellen oder `$`-Formelstrukturen. Eine gezielte Mock-Regression sichert, dass `|5| 5` keine Tabellenpflicht auslöst; die vollständige Suite umfasst 254 erfolgreiche Tests.

### 17 – Deterministische Konvertierungsbewertung als separates Artefakt

**Kontext:** Das Konvertierungsmanifest enthält umfangreiche, maschinenlesbare Befunde zu Quelle, Derivaten, Qualitätswarnungen, RAG-Entscheidung und gegebenenfalls Cloud-Batches. Für eine menschliche Abschlussprüfung fehlte bisher eine kompakte, nachvollziehbare Markdown-Zusammenfassung. Sie darf weder eine erneute PDF-Analyse noch eine Cloud-Anfrage auslösen oder die fachliche Qualität über die Manifestdaten hinaus bewerten.

**Festlegung:** `conversion_review_service` erzeugt `Quelle.conversion-review.md` ausschließlich aus dem bestehenden Manifest. Vor dem Schreiben wird der Fingerabdruck der angegebenen PDF gegen den Manifest-Hash geprüft; die Note fasst Status, Quelle, Seiten aus `artifacts.local_reuse.page_numbers`, Assets, Native-PDF-Links, Cloud-Modus und Batchzahl sowie nach Code und Seiten gruppierte Qualitätswarnungen zusammen. Die Note enthält nur die vorhandene RAG-Empfehlung, keine neu erfundene Bewertung. Sie wird automatisch nach der lokalen Manifestveröffentlichung und nach einer erfolgreichen Cloud-Manifestaktualisierung atomar erneuert. Der separate, netzwerkfreie Befehl `doctomd review INPUT.pdf --output-dir AUSGABEORDNER` nutzt dieselbe Logik und ersetzt eine vorhandene Note ausschließlich mit `--on-conflict overwrite`.

**Auswirkung:** Jede erfolgreiche lokale oder Cloud-Konvertierung erhält eine lesbare Abschlussnote, ohne das lokale Markdown, das Cloud-Derivat oder das Manifest zu verändern. Bestehende Ergebnisse lassen sich nachträglich mit identischer Bewertung erneut dokumentieren. Mock-Tests sichern Quellhashbindung, Manifest-Unveränderlichkeit, Cloud-Batchdarstellung und Konfliktverhalten; der reale Mathe1-Lauf erzeugte die Note mit 153 Seiten, 72 validierten Batches und 137 Native-PDF-Links. Die Suite umfasst 256 erfolgreiche Tests.

### 18 – Belegbare Laufzeiten in der Konvertierungsbewertung

**Kontext:** Eine Abschlussnote mit nur Status und Qualitätsbefunden macht die operative Dauer eines lokalen oder Cloud-basierten Laufs nicht sichtbar. Bei wiederaufnehmbaren Batches wäre eine aus erstem und letztem Zeitstempel abgeleitete Wanduhrzeit jedoch irreführend, da Pausen und spätere Einzelwiederholungen darin enthalten sein können.

**Festlegung:** Die Review-Note berechnet die lokale Verarbeitung aus `conversion.started_at` und `conversion.completed_at`. Für ein Cloud-Derivat summiert sie ausschließlich die vorhandenen `duration_ms`-Werte der einzelnen Telemetrien und weist bei mehreren Batches zusätzlich die minimale und maximale Batchlaufzeit aus. Fehlende oder ungültige Zeitfelder werden nicht geschätzt und nicht dargestellt.

**Auswirkung:** Die Note trennt klar lokale Verarbeitung von gemessener Cloud-API-Laufzeit und bleibt auch nach Batch-Wiederaufnahme nachvollziehbar. Für Mathe1 werden 2 min 16,594 s lokal sowie 27 min 10,813 s summierte Cloud-API-Laufzeit über 72 Batches ausgewiesen. Die vollständige Suite umfasst 256 erfolgreiche Tests.

### 19 – Diagnoseartefakte für inhaltlich verworfene Cloud-Batches

**Kontext:** Eine marker-gültige Cloud-Antwort kann wegen lokaler Mindestvollständigkeit verworfen werden. Der Wiederaufnahmezustand darf sie nicht als Erfolg behalten, doch ohne getrennte Ablage war ihr genauer Inhalt nach dem Abbruch nicht mehr lokal untersuchbar.

**Festlegung:** Wenn eine frische, marker-gültige Batchantwort an `verify_cloud_content_completeness` scheitert, schreibt DocToMD vor dem Rücksetzen des Wiederaufnahmeeintrags zwei response-spezifische Diagnoseartefakte neben der Zustandsdatei: `Quelle.batch-XXX-pages-AAA-BBB.rejected-<Hash>.md` mit dem geprüften Cloud-Markdown und eine gleichnamige JSON-Datei mit Batch-ID, Originalseiten, Fehlercode, Fehlergrund, Response-ID und Telemetrie. Der Dateisuffix ist aus der Response-ID gehasht; identische Antworten können idempotent aktualisiert werden.

**Auswirkung:** Reguläres Cloud-Derivat, Konvertierungsmanifest und Wiederaufnahmezustand bleiben weiterhin frei von verworfenen Ergebnissen. Erfolgreiche Batches werden unverändert wiederverwendet, während eine spätere lokale Diagnose den exakten verworfenen Inhalt auswerten kann. Die Mock-Regression prüft Inhalt, Fehlercode und die getrennte Ablage; die vollständige Suite umfasst 257 erfolgreiche Tests.

## 2026-09-29

## Geplante Phase 12 – Vektor-Abbildungen und Asset-Integrität

### 01 – Konservative Erweiterung für vektorbasierte Abbildungen

**Kontext:** Der Befund für `2501.10322v2_HAT.pdf` zeigt über 24 Seiten keine eingebetteten PDF-Image-XObjects. Seine Abbildungen, etwa Figure 2 auf Seite 5, sind sichtbare Vektorgrafiken. Die bestehende, in Phase 5 bewusst festgelegte Rasterstrategie exportiert daher korrekt keine Dateien; Bildunterschriften und Abbildungsreferenzen allein ergeben jedoch kein RAG-nutzbares Bildasset. Zugleich enthielt das Cloud-Derivat nicht vorhandene Modellverweise wie `figure-2.png`, obwohl kein lokales Asset autorisiert war.

**Festlegung:** Die Folgephase trennt zwei Verantwortlichkeiten. Erstens ermittelt ein lokaler, rein geometrischer Planer auf Seiten ohne exportierbares Rasterbild ausschließlich dann einen Vektor-Abbildungskandidaten, wenn eine eindeutige Figure-/Fig.-Caption und ein zugehöriger Bereich signifikanter Vektorprimitiven belegbar sind. Der Bereich wird zwischen Grafik und Caption bestimmt, darf keine vollständige Seite sein und muss die Caption eindeutig zuordnen. Unsichere, mehrdeutige oder textdominierte Bereiche werden weder geraten noch als Seitenbild exportiert, sondern mit einer seitenbezogenen Warnung `VECTOR_FIGURE_NOT_EXPORTED` sichtbar gemacht. Zweitens wird jedes veröffentlichte Markdown – lokal wie Cloud – gegen die autoritative Assetliste validiert: Eine Bildreferenz muss auf einen vorhandenen, sicheren relativen Assetpfad desselben Ausgabeordners zeigen und zu einem Manifest-Asset passen. Eine nicht autorisierte oder fehlende Referenz wird vor der Veröffentlichung mit `CLOUD_UNAUTHORIZED_IMAGE_REFERENCE` abgewiesen; sie wird nicht stillschweigend durch einen erfundenen Platzhalter ersetzt.

**Auswirkung:** Die Standardverarbeitung bleibt lokal und netzwerkfrei; zur Erkennung und zum Rendern werden keine Ziel-URLs abgerufen und keine neue schwere Abhängigkeit eingeführt. Für bestätigte Kandidaten rendert der vorhandene lokale PDF-Renderer ausschließlich den ermittelten Ausschnitt als PNG. Die Veröffentlichung nutzt die bestehenden stabilen Assetnamen, Sidecar-Notes, Markdown-Marker und Manifestreferenzen. Vollseitenbilder bleiben bei textbasierten PDFs ausgeschlossen, sodass Text nicht als doppelte Bildkopie in das RAG-Derivat gelangt. Unit-, Mock- und kleine rechtlich unbedenkliche Vektor-PDF-Regressionen prüfen Kandidatenerkennung, Crop-Grenzen, Caption- und Seitenzuordnung, fehlende Vollseiten-Assets sowie die Ablehnung erfundener Cloud-Bildpfade. Eine visuelle Prüfung an einem wissenschaftlichen Vektordiagramm ergänzt die automatisierten Tests.

## 2026-10-01

### Phase 12.01 – Kandidatenerkennung ohne Vektor-Export

**Kontext:** Für `2501.10322v2_HAT.pdf` existieren keine exportierbaren Rasterbildassets, obwohl die PDF sichtbare Vektordiagramme mit Figure-Captions enthält. Bis zur gesonderten Crop- und Exportaufgabe darf kein Seitenrendering als Ersatzbild veröffentlicht werden. Die Konvertierung benötigt dennoch einen lokalen, prüfbaren Befund und eine sichtbare Qualitätsgrenze.

**Festlegung:** `app.vector_figure_detection` prüft ausschließlich lokal und nur auf Seiten ohne bereits exportiertes Rasterasset. Es akzeptiert je Caption einen Kandidaten nur bei einer `Figure`-/`Fig.`-Caption und genau einem unmittelbar darüber liegenden, zusammenhängenden Bereich aus mindestens drei signifikanten Vektorprimitiven. Die Caption-Regel akzeptiert den sichtbar belegten Doppelpunktabschluss sowohl mit als auch ohne Leerzeichen vor der Zahl, etwa `Figure 2:` und `Figure1:`. Nebeneinander gesetzte Captions werden über ihre Textgeometrie getrennt und zusätzlich nur mit horizontal überlappenden Grafikbereichen verbunden. Der Bereich braucht eine Mindestbreite und -höhe relativ zur Seite, darf keine Vollseite sein und wird bei textdominierter Fläche verworfen. Fehlender, mehrdeutiger oder nicht eindeutig caption-naher Geometriebeleg erzeugt ebenso wie ein bestätigter, in dieser Phase bewusst nicht exportierter Kandidat die seitenbezogene Warnung `VECTOR_FIGURE_NOT_EXPORTED`. Der Befund erzeugt weder PNGs noch Assets, Sidecar-Notes, Manifest-Asseteinträge oder Markdown-Bildreferenzen.

**Auswirkung:** Die lokale Konvertierungsorchestrierung reicht nur die Seiten mit tatsächlich exportierten Rasterassets als Ausschlussmenge an den Detektor weiter. Die rechtlich unbedenkliche, temporär erzeugte Vektor-PDF-Fixture sichert positiven Kandidatenbefund, eine nicht zuordenbare zusätzliche Caption, die kompakte Textlayerform und die Unterdrückung auf einer Rasterassetseite. Ein reiner Lesecheck an einer externen wissenschaftlichen Referenz bestätigte Kandidaten auf mehreren Seiten; jede dieser Seiten erhält bis zur separaten Exportaufgabe die sichtbare Warnung. Es wurden keine Ziel-URLs aufgerufen und keine nicht versionierten Artefakte verändert.

### Phase 12.02 – Lokaler PNG-Crop für bestätigte Vektorbereiche

**Kontext:** Ein bestätigter Vektorbereich ist ohne publiziertes Asset noch nicht RAG-nutzbar. Ein Seitenrendering als vollständiges Bild würde jedoch Text, Caption und Seitendekoration doppelt in das Derivat übernehmen. Bereits exportierte Rasterbilder besitzen außerdem eine stabile Asset-, Sidecar- und Manifestkonvention, die für Vektorcrops erhalten bleiben muss.

**Festlegung:** `app.vector_figure_export` rendert die Quelle ausschließlich lokal mit dem bereits verwendeten PDFium-Renderer bei 144 dpi und schneidet danach exakt die vom Detektor belegte Bounding-Box aus. Der vollständige Render verbleibt nur im Arbeitsspeicher; geschrieben wird ausschließlich der PNG-Crop. Bounding-Boxen außerhalb der Seite sowie Vollseiten-Crops werden abgewiesen und als `VECTOR_FIGURE_NOT_EXPORTED` sichtbar. Erfolgreiche Crops erhalten die bestehende stabile Benennung `page-XXX-figure-YY.png`, eine editierbare Beschreibungs-Note, Seiten- und Caption-Bezug sowie reguläre Markdown- und Manifestreferenzen. Raster- und Vektorassets werden gemeinsam, aber ohne Namenskollisionen pro Seite nummeriert. Eine zuvor nur wegen des aufgeschobenen Exports erzeugte Vektorwarnung entfällt bei erfolgreichem Crop; tatsächlich unsichere oder fehlgeschlagene Fälle bleiben gewarnt.

**Auswirkung:** Die kleine lokale Vektorfixture erzeugt für einen bestätigten Bereich ein 716×500-Pixel-PNG statt eines 1224×1584-Pixel-Seitenbilds. Ein End-to-End-Test prüft Asset, Sidecar, Markdown und Manifest; ein separater Test verweigert einen Vollseiten-Crop. Die vollständige Suite umfasste bei der Prüfung 265 erfolgreiche Tests. Es wurden keine externen Quellen, Ziel-URLs oder Cloud-Dienste aufgerufen und keine nicht versionierten Artefakte verändert.

### Phase 12.03 – Autoritative Bildreferenzen vor Veröffentlichung

**Kontext:** Ein Cloud-Modell kann syntaktisch gültige Bildpfade wie `figure-2.png` erzeugen, obwohl diese Datei weder lokal existiert noch im Manifest als Asset autorisiert ist. Auch lokales Markdown darf keine Bildreferenz veröffentlichen, die vom tatsächlichen Assetbestand abweicht. Ohne eine gemeinsame Prüfung könnten RAG-Konsumenten defekte oder erfundene Bildverweise erhalten.

**Festlegung:** `app.asset_reference_validation` untersucht GFM- und HTML-Bildreferenzen vor jeder Veröffentlichung. Jeder Bildpfad muss exakt einem `Asset.relative_path` der autoritativen Liste entsprechen, sicher relativ sein, innerhalb des Ausgabeordners aufgelöst werden und als reguläre Datei vorhanden sein. Die reguläre lokale Konvertierung prüft ihr Markdown vor Manifest- und Markdownveröffentlichung; die Wiederverwendung eines lokalen Kontexts prüft dies erneut. Die Cloud-Pfade `convert`, `cloud-derive` und `cloud-evaluate` prüfen ihr fertiges, lokal ergänztes Cloud-Markdown unmittelbar vor dem Schreiben. Eine nicht autorisierte Cloud-Bildreferenz wird mit `CLOUD_UNAUTHORIZED_IMAGE_REFERENCE` abgewiesen; das Cloud-Derivat und dessen Manifeständerung werden nicht veröffentlicht.

**Auswirkung:** Die Testfälle akzeptieren einen vorhandenen autoritativen Assetpfad und verwerfen erfundene relative sowie externe HTML-Bildpfade. Die Cloud-Integrationsregression sichert, dass `![Erfundene Abbildung](figure-2.png)` die lokale Basis erhält, aber keine `Quelle.cloud.md` erzeugt. Die vollständige Suite umfasste bei der Prüfung 269 erfolgreiche Tests. Es wurden weder Cloud-Dienste noch Ziel-URLs aufgerufen und keine nicht versionierten Artefakte verändert.

### Phase 12.04 – Regressionen für Vektorassets und Referenzintegrität

**Kontext:** Die neue Erkennung, der Crop-Export und die Assetreferenzprüfung besitzen mehrere voneinander abhängige Sicherheitsgrenzen. Ein einzelner positiver Grafikfall genügt nicht, um nebeneinander gesetzte Captions, die stabile Nummerierung, fehlende Dateien, Vollseiten-Crops oder von Cloudantworten erfundene Bildpfade dauerhaft abzusichern.

**Festlegung:** Die lokale Vektorfixture kann zwei getrennte Diagramme auf derselben Seite erzeugen. Tests prüfen deren eigene Caption- und Seitenzuordnung sowie die stabilen Namen `page-001-figure-01` und `page-001-figure-02`. Ein End-to-End-Fall vergleicht beide Manifestassetpfade mit ihren Markdown-Markern und Bildreferenzen. Weitere Tests verwerfen einen Vollseiten-Crop, simulieren einen lokalen Renderfehler ohne erzeugten Assetordner und prüfen fehlende bzw. externe Bildreferenzen. Die Cloud-Integrationsregression verwendet eine gemockte Antwort mit `figure-2.png` und sichert den stabilen Ablehncode vor jeder Cloud-Veröffentlichung.

**Auswirkung:** Die Vektorassetgrenzen sind ohne externe PDFs, Netzverkehr oder Änderung realer Artefakte regressionsgesichert. Die vollständige Suite umfasst 273 erfolgreiche Tests. Damit ist für Phase 12 nur noch der isolierte reale HAT-Lauf mit visueller Prüfung offen; erst dieser Schritt erzeugt bewusst neue, zu prüfende Ableitungen.

### 2026-10-01 – Cloud-Bildreferenzen vor Batch-Persistierung abweisen

**Kontext:** Beim HAT-Cloud-Lauf enthielt ein ansonsten marker- und inhaltsgültiger Batch auf Seite 5 die vom Modell erfundene Referenz `![...](figure-2.png)`. Die abschließende Asset-Validierung verhinderte zwar korrekt die Veröffentlichung von `cloud.md`, aber der bereits als erfolgreich gespeicherte Batch hätte bei einem Wiederanlauf erneut dieselbe ungültige Antwort geliefert. Die Fehlermeldung erklärte außerdem nicht, wie der Lauf fortgesetzt werden kann.

**Festlegung:** Der Cloud-Promptvertrag wurde auf Version `1.5` angehoben und verbietet Markdown- und HTML-Bildreferenzen ausdrücklich. Rohes Cloud-Markdown wird vor Inhaltsprüfung, Asset-Injektion und Persistierung darauf geprüft. Eine solche Referenz führt zu `CLOUD_UNAUTHORIZED_IMAGE_REFERENCE` mit der Anweisung, die Cloud-Ableitung erneut zu starten. Ein gespeicherter Mehrbatch-Eintrag wird vor seiner Wiederverwendung zurückgesetzt und nur dieser Batch erneut angefragt; eine frisch fehlerhafte Antwort wird nicht als erfolgreich gespeichert. Beim Einbatch-Ablauf wird der zugehörige Wiederaufnahmezustand entfernt, damit nicht dieselbe fehlerhafte Response erneut abgefragt wird. DocToMD ergänzt Bilder weiterhin ausschließlich nachträglich aus der lokalen autoritativen Assetliste.

**Auswirkung:** Der vorhandene HAT-Batchzustand mit Promptversion `1.4` wird wegen der Versionsbindung nicht wiederverwendet. Der nächste ausdrücklich gestartete Cloud-Lauf verwendet den neuen Vertrag und veröffentlicht bei erfolgreicher Validierung `2501.10322v2_HAT.cloud.md` mit den zehn lokal geprüften Abbildungsassets. Der Lauf benötigt wegen der Promptversion einen neuen Satz Cloud-Batches; es wird kein Original-PDF und kein lokales Asset geändert. Unit- und Mock-Regressionen sichern das Promptverbot, die konkrete Wiederanlaufmeldung und das Zurücksetzen eines fehlerhaften Batches vor der Persistierung. Die vollständige Suite umfasst 276 erfolgreiche Tests.

### 2026-10-01 – Robuste Caption-Platzierung von Vektorassets im Cloud-Derivat

**Kontext:** Auf Seite 2 des HAT-Papers liegt Figure 1 oberhalb der Caption. Der PDF-Textlayer liefert für das Asset jedoch die verdichtete Caption `Figure1:Schematic…`, während das Cloud-Derivat sichtbar `**Figure 1:** Schematic…` schreibt. Die bisherige Einfügung verlangte eine vollständige, zeichengetreue Caption und setzte das Bild bei Abweichung ans Seitenende. Der gleiche Unterschied betraf neun weitere HAT-Assets.

**Festlegung:** `inject_cloud_assets` bestimmt bei Figure-, Fig.- und Abbildung-Captions zunächst deren Nummer. Es fügt ein Asset nur dann direkt nach einer sichtbaren, am Zeilenanfang stehenden Caption mit derselben Nummer ein, wenn diese auf der Seite eindeutig ist. Markdown-Hervorhebung, Leerraum und die im PDF-Textlayer fehlende Leerstelle zwischen Label und Zahl beeinflussen die Zuordnung nicht. Bei fehlender oder mehrdeutiger Nummer bleibt der bisherige konservative Fallback ans Seitenende bestehen; Captions ohne Figure-Nummer verwenden weiterhin ausschließlich einen eindeutigen exakten Texttreffer.

**Auswirkung:** Die Unit-Tests sichern die verdichtete Figure-1-Caption sowie zwei in anderer Assetreihenfolge vorliegende Captions auf derselben Seite. Eine rein lokale Simulation mit dem vorhandenen HAT-Cloud-Markdown ordnet alle zehn Assets unmittelbar nach Figure 1 bis Figure 10 ein. Die Korrektur wirkt bei jeder lokalen Asset-Injektion eines Cloud-Derivats und erfordert keine neue Vektor- oder Netzverarbeitung. Das damals veröffentlichte HAT-Derivat wurde anschließend im dokumentierten Abschlussschritt lokal repariert. Die vollständige Suite umfasst 278 erfolgreiche Tests.

### 2026-10-01 – Abschluss der visuellen Phase-12-Prüfung am HAT-Paper

**Kontext:** Das wissenschaftliche Referenzdokument `2501.10322v2_HAT.pdf` enthält auf 24 Seiten keine eingebetteten Rasterbildobjekte, aber zehn caption-gebundene Vektordiagramme. Nach dem ausdrücklich gestarteten Cloud-Lauf lag `2501.10322v2_HAT.cloud.md` vor. Die Sichtprüfung meldete zunächst für Figure 1 auf Seite 2 eine unpassende Platzierung am Seitenende; die anschließende Diagnose zeigte die Textlayer-/Cloud-Captionabweichung als Ursache.

**Festlegung:** Der reale HAT-Lauf wird mit zehn erfolgreichen lokalen Vektorassets auf den Seiten 2, 5, 7, 9, 19, 21 und 23 abgeschlossen. Die lokale, kostenfreie Reparatur von `2501.10322v2_HAT.cloud.md` verschiebt ausschließlich die vorhandenen Asset-Blöcke. Vor dem atomaren Überschreiben wurde `2501.10322v2_HAT.cloud.before-caption-repair.md` als unveränderte Sicherung angelegt. Danach wurde jedes Asset von Figure 1 bis Figure 10 gegen seine sichtbare Caption geprüft; alle zehn stehen unmittelbar nach ihrer eindeutigen Caption und verweisen weiterhin auf vorhandene autoritative PNG-Dateien.

**Auswirkung:** Phase 12 ist abgeschlossen. Die lokale und Cloud-Markdown-Ausgabe enthält die zugeschnittenen Vektorassets mit korrektem Seitenbezug und ohne Vollseitenbilder. Die verbleibenden Grenzen sind bewusst erhalten: Nur lokal-geometrisch eindeutig belegte Figure-/Fig.-Bereiche werden exportiert, mehrdeutige oder textdominierte Fälle führen weiterhin zu `VECTOR_FIGURE_NOT_EXPORTED`, und eine Caption ohne eindeutige Nummer wird nicht normalisiert geraten. Es wurden keine Original-PDFs verändert und nach dem Cloud-Lauf keine weitere Netzwerkanfrage ausgelöst.

## 2026-10-02

### 01 – Portabler Provenienzblock und lokale Nachrüstung

**Kontext:** Das Manifest ordnet Markdown-Derivate bereits sicher einer PDF-Primärquelle zu, doch ein für RAG kuratiertes oder kopiertes Markdown verlor diesen Bezug ohne das nebenliegende JSON. Insbesondere soll ein späterer Indexer `Quelle.index.md` auf das fachlich erwartete Original `Quelle.pdf` zurückführen können, ohne absolute lokale Pfade offenzulegen.

**Festlegung:** `app.markdown_provenance` setzt vor neue lokale, Cloud- und Vision-Derivate einen idempotenten YAML-Block mit `doctomd_source_document`, `doctomd_source_sha256` und `doctomd_derivative_kind`. Der lokale Wiederverwendungskontext akzeptiert diesen verwalteten Kopf, prüft aber weiterhin den vollständigen Dateihash. `doctomd migrate-provenance INPUT.pdf --output-dir AUSGABEORDNER` prüft vorhandene Artefakte gegen die Primärquelle, ergänzt ausschließlich `Quelle.md` und eine vorhandene `Quelle.cloud.md` und aktualisiert den Wiederverwendungs-Hash im Manifest. Auch frühere Manifeste ohne `artifacts.local_reuse` werden über ihren vorhandenen Quellfingerabdruck und die sicheren Artefaktpfade nachgerüstet. Weder PDF-Analyse noch OCR oder Cloud-Anfrage werden dabei ausgelöst.

**Auswirkung:** Neue Derivate und daraus angelegte Indexkopien sind außerhalb ihres Ausgabeordners nachvollziehbar einer portablen Originalkennung zugeordnet. Bereits erfolgreiche Konvertierungen können ohne Kosten oder Qualitätsneuberechnung nachgerüstet werden. Der reale Mathe1-Ausgabeordner wurde mit beiden Köpfen aktualisiert; der Wiederverwendungstest für den späteren Cloud-Pfad bleibt gültig.
