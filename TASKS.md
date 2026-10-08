# Zentrale Aufgabenliste für DocToMD

Diese Datei steuert die Entwicklung der eigenständigen lokalen Dokument-zu-Markdown-Engine. Die fachliche Ausgangsbeschreibung ist die nicht versionierte Vault-Note „PDF-to-Markdown für RAG“.


## Regeln für Codex

- Immer nur eine offene Aufgabe gleichzeitig bearbeiten.
- Die erste offene Aufgabe der aktuellen Phase wählen.
- Vor jeder Implementierung Plan und betroffene Dateien nennen.
- Nur die für die Aufgabe notwendigen Dateien ändern.
- Aufgaben erst nach angemessener Validierung mit `[x]` markieren.
- Neue Aufgaben nur ergänzen, wenn sie für das Projektziel notwendig sind.

---

## Phase 1 – Projektgrundlage

Ziel: Das eigenständige Projekt ist dokumentiert und kann kontrolliert gestartet werden.

- [x] Projektordner anlegen
- [x] Steuerungsdateien `AGENTS.md`, `PROJECT.md` und `TASKS.md` anlegen
- [x] Python-Projektgrundgerüst mit `main.py`, `app/` und `tests/` anlegen
- [x] Python-Version und Abhängigkeitsverwaltung verbindlich festlegen
- [x] Virtuelle Umgebung `.venv` anlegen und einen Start ohne Argumente validieren
- [x] Minimalen `README.md` mit Entwicklungsstart erstellen
- [x] Fortlaufende technische Begleitnote `ENGINEERING_NOTES.md` anlegen

Akzeptanz:

- Das Projekt startet ohne Fehler und zeigt eine verständliche CLI-Hilfe.
- Es gibt noch keine Konvertierungsabhängigkeiten oder Verarbeitung von Dokumenten.

---

## Phase 2 – Stabile CLI und Datenmodell

Ziel: Die Konvertierung ist als stabile lokale Schnittstelle beschrieben, bevor PDF-spezifische Logik entsteht.

- [x] CLI-Befehl `convert` mit Eingabepfad und Ausgabeordner definieren
- [x] Option für Ausgabeformat und Konfliktverhalten festlegen
- [x] Optionsmodell für OCR-Modus und OCR-Sprache festlegen, ohne OCR zu implementieren
- [x] Domänenmodelle für Quelle, Konvertierungsergebnis, Asset, Seitenreferenz und Warnung definieren
- [x] JSON-Ausgabe und Exit-Codes für Erfolg, Warnung und Fehler spezifizieren
- [x] Ausgabeordner und Schreibschutz für Originaldokumente validieren
- [x] Unit-Tests für CLI- und Pfadvalidierung ergänzen

Akzeptanz:

- Ungültige Pfade und unsichere Ausgabeziele führen zu klaren Fehlern.
- Der CLI-Vertrag ist maschinenlesbar und für Plugin sowie CodexCLI nutzbar.

---

## Phase 3 – Manifest und Artefaktverwaltung

Ziel: Jede Konvertierung erzeugt nachvollziehbare und aktualisierbare Artefakte.

- [x] Versioniertes Schema für `*.conversion.json` festlegen
- [x] Quellfingerabdruck aus Pfad, Hash, Größe und Änderungszeit implementieren
- [x] Standardnamen für Markdown, Asset-Ordner und Manifest festlegen
- [x] Atomisches Schreiben von Markdown und Manifest umsetzen
- [x] Konflikt- und Wiederholungspolitik festlegen: abbrechen, aktualisieren oder explizit überschreiben
- [x] Qualitätsstatus und Warnungen in Manifest und CLI-Ausgabe abbilden
- [x] Tests für unveränderte, geänderte und fehlende Quellen ergänzen

Akzeptanz:

- Eine Konvertierung ist anhand des Manifests vollständig nachvollziehbar.
- Ein späterer Aufrufer kann veraltete Derivate erkennen.

---

## Phase 4 – MVP: digitale PDFs nach strukturiertem Markdown

Ziel: Textbasierte PDFs werden lokal in brauchbares Markdown mit Seitenbezug überführt.

- [x] PDF-Extraktionsbibliothek nach Test mit repräsentativen Dokumenten auswählen
- [x] Seitenweise Textextraktion mit Lesereihenfolge implementieren
- [x] Seitenmarker im Markdown und in den Strukturmodellen definieren
- [x] Grundlegende Blöcke für Überschriften, Absätze und Listen erzeugen
- [x] Textnormalisierung so gestalten, dass Quelleninhalt nicht stillschweigend verfälscht wird
- [x] Ergebnis-Markdown, Manifest und Warnungen schreiben
- [x] Kleine digitale PDF-Fixtures und Regressionstests ergänzen
- [x] Qualitätswarnungen für mehrspaltiges Layout und nicht dekodierbare PDF-Zeichen ausgeben
- [x] Markdown-Ausgabe visuell und inhaltlich gegen die Originalseiten prüfen

Akzeptanz:

- Eine digitale PDF erzeugt ein lesbares Markdown-Derivat mit Seitenbezug.
- Probleme bei Lesereihenfolge oder nicht extrahierbarem Text erscheinen als Warnung.

---

## Phase 5 – Bilder, Bildunterschriften und Tabellen

Ziel: Für RAG relevante nichtlineare Inhalte bleiben nachvollziehbar erhalten.

- [x] Strategie für Bildextraktion versus Seitenrendering festlegen
- [x] Abbildungen mit stabilen Dateinamen in den Asset-Ordner exportieren
- [x] Bildreferenzen, Seitenbezug und vorhandene Bildunterschriften in Markdown ausgeben
- [x] Einfach erkennbare Tabellen nach Markdown übertragen
- [x] Komplexe oder unsichere Tabellen sichtbar markieren statt plausibel wirkende Daten zu erfinden
- [x] Editierbares Feld bzw. Erweiterungspunkt für Bildbeschreibungen vorsehen
- [x] Tests für Bildreferenzen, Tabellen und Warnungen ergänzen

Akzeptanz:

- Bilder sind als Assets und Markdown-Referenzen erhalten.
- Tabellen und Bildzuordnungen bleiben überprüfbar.

---

## Phase 6 – Wissenschaftliche PDFs und mathematische Inhalte

Ziel: Wissenschaftliche Papers mit Mehrspaltenlayout, Formeln und komplexen Tabellen werden als nachvollziehbare, strukturerhaltende Markdown-Derivate verarbeitet.

- [x] Repräsentative, rechtlich unbedenkliche wissenschaftliche PDF-Fixtures und Evaluationskriterien festlegen
- [x] Leseordnung für zweispaltige Seiten mit Kopf-, Fuß- und Randbereichen verbessern
- [x] Wortabstände, Silbentrennungen und Absatzgrenzen für wissenschaftlichen Fließtext qualitätsgesichert verbessern
- [x] Strategien zur Erkennung und Ausgabe von Inline- und Display-Formeln als LaTeX bewerten und festlegen
- [x] Optionales lokales Vision-Backend über LM Studio bewerten: `qwen/qwen3.5-9b` am konfigurierbaren LAN-Endpoint gegen die wissenschaftlichen Evaluations-PDFs prüfen
- [x] Optionales OpenAI-Vision-Backend als wählbaren Cloud-Provider bewerten; Übertragung von Seitenbildern, API-Kosten und Datenschutz gegenüber der lokalen LM-Studio-Variante klar ausweisen
- [x] Opt-in-Konfiguration für Vision-Provider definieren: Provider `none|lm-studio|openai`, Modus `off|auto|force`, Modell-ID, Renderauflösung und Timeout; LM-Studio-Endpoint nur für den lokalen Provider, OpenAI-Schlüssel ausschließlich über `OPENAI_API_KEY` und niemals im Manifest speichern
- [x] Seitenbilder nur bei erkannten wissenschaftlichen Qualitätsrisiken an das Vision-Backend übergeben; Standardverarbeitung bleibt vollständig lokal und netzwerkfrei
- [x] Versioniertes JSON-Schema für vom Vision-Backend vorgeschlagene Absätze, LaTeX-Formeln, Tabellen, Captions, Seitenbezug und Konfidenz festlegen
- [x] Lokale Validierung und sichtbare Warnungen für nicht erreichbares Backend, ungültiges JSON, Timeout, niedrige Konfidenz und nicht überprüfbare Inhalte ergänzen
- [x] Nur zuverlässig rekonstruierbare Formeln als LaTeX ausgeben; unsichere Formeln seitenbezogen warnen
- [x] Mehrzeilige, mehrspaltige und wissenschaftliche Tabellen separat bewerten und sicher übertragen oder warnen
- [x] Zitationen, Fußnoten, Abbildungs- und Tabellenreferenzen mit Seitenbezug evaluieren
- [x] Regressionstests sowie visuelle und inhaltliche Qualitätsprüfung gegen Originalseiten ergänzen

Akzeptanz:

- Ein repräsentatives wissenschaftliches PDF erzeugt ein strukturiertes Markdown-Derivat mit nachvollziehbaren Seitenbezügen.
- Formeln und komplexe Tabellen werden entweder überprüfbar übertragen oder mit konkretem Seitenbezug sichtbar gewarnt.
- Text, Layout und Formelinhalt werden niemals stillschweigend erfunden oder als verlustfrei ausgegeben.

---

## Phase 6 – Fortsetzung: Validierter Vision-Fallback

Ziel: Für ausdrücklich freigegebene wissenschaftliche Risikoseiten erzeugt ein Vision-Provider überprüfbare Vorschläge, ohne lokale Inhalte oder Originalquellen stillschweigend zu ersetzen.

- [x] Ausgewählte Seiten mit OpenAI Vision rendern, anfragen und als lokal validierte Vorschlagsdateien ablegen
- [x] Akzeptierte Vorschläge nur mit expliziter Übernahmeregel in ein abgeleitetes Markdown-Derivat integrieren
- [x] Review-Datei für verworfene oder nicht sicher übernehmbare Vorschläge erzeugen
- [x] Reale Evaluation gegen das ausgewählte Tokenizer-Paper durchführen und Kosten, Seitenumfang sowie Qualitätsgrenzen dokumentieren

Akzeptanz:

- Ohne aktivierten OpenAI-Opt-in findet keine Netzwerkanfrage statt.
- Jede übertragene Seite, Antwort und Übernahmeentscheidung bleibt im Manifest oder Review-Artefakt nachvollziehbar.
- Modellantworten ersetzen keine lokalen Inhalte ohne erfolgreiche lokale Validierung und explizite Übernahmeregel.

---

## Phase 6 – Fortsetzung: Cloud-Dokumentkonvertierung

Ziel: Ein ausdrücklich freigegebener OpenAI-Modus verarbeitet ein vollständiges wissenschaftliches PDF als zusammenhängende Eingabe und erzeugt ein separates, hochwertiges Markdown-Derivat.

- [x] Stabilen Konfigurations- und CLI-Vertrag für den expliziten Cloud-Dokumentmodus festlegen
- [x] Vollständiges PDF sicher als OpenAI-`input_file` übergeben, ohne den Schlüssel oder Quelldatei-Daten im Manifest zu speichern
- [x] Prompt- und Ausgabevertrag für vollständiges Markdown mit Seitenmarkern, Überschriften, Tabellen und LaTeX-Formeln definieren
- [x] Konfliktgeschütztes Derivat `Quelle.cloud.md` und Manifest-Referenz implementieren; lokales Markdown niemals überschreiben
- [x] Response-ID, Modell, Ein-/Ausgabe-Tokens, Laufzeit und nur belegbare Kostenangaben nachvollziehbar im Manifest erfassen
- [x] Technische Mindestvalidierung für Markdown, Seitenmarker, unzulässige Ausgabebefehle und Antworttrunkierung ergänzen
- [x] Mock-basierte Regressionen für Konfiguration, API-Adapter, Manifest und Konfliktverhalten ergänzen
- [x] Reale Vergleichsevaluation gegen das Tokenizer-Paper und das vorhandene ChatGPT-Markdown durchführen
- [x] Cloud-Dokumentmodus in die CLI-Orchestrierung integrieren und den ausführbaren CLI-Aufruf dokumentieren
- [x] Kompakte CLI-Telemetrie für Cloud-Läufe ausgeben und doppelte Qualitätswarnungen unterdrücken
- [x] JSON-CLI-Ausgabe für Menschen lesbar einrücken, ohne den Datenvertrag zu ändern
- [x] Implementierten Ablauf der Cloud-Dokumentkonvertierung mit getrennten Derivaten und Qualitätsprüfungen grafisch dokumentieren
- [x] Cloud-Ablaufgraph für die Darstellung ohne Navigationsleisten verdichten

Akzeptanz:

- Ohne expliziten Cloud-Modus bleibt die Konvertierung lokal und netzwerkfrei.
- Das Cloud-Derivat ist vollständig getrennt, seitenbezogen und nachvollziehbar; weder Primärquelle noch lokales Markdown werden verändert.
- Laufzeit, Modell-Usage, Fehler und erkennbare Qualitätsgrenzen sind im Manifest sichtbar.

---

## Phase 7 – OCR für gescannte PDFs

Ziel: Bild-PDFs ohne verwertbaren Textlayer erzeugen ein überprüfbares Markdown-Derivat.

- [x] OCR-Backend und lokale Installationsstrategie bewerten und festlegen
- [x] Textlayer-Erkennung und expliziten OCR-Fallback implementieren
- [x] OCR-Sprache, Seitenbereich und Qualität konfigurierbar machen
- [x] OCR-Ergebnis, Parameter und Qualitätswarnungen im Manifest speichern
- [x] Fehler bei fehlenden Systemwerkzeugen verständlich melden
- [x] Scan-Fixtures bzw. Mock-basierte Tests ergänzen
- [x] Manuelle Qualitätsprüfung mit deutschem Scan durchführen und erkannte Layoutmängel korrigieren; separate englische Prüfung nicht erforderlich

Akzeptanz:

- Ein Scan-PDF wird nicht als leeres Dokument behandelt.
- OCR-Nutzung und Unsicherheiten sind im Ergebnis sichtbar.

---

## Nachträge nach Phase 7 – Stabilisierung ausgelieferter Funktionen

Die folgenden reaktiven Verbesserungen wurden nach dem formalen Abschluss von Phase 7 aus realen Konvertierungsläufen umgesetzt. Sie sind keine als erledigt markierten Phase-8-Evaluationsaufgaben.

- [x] Endbenutzerrelevante Qualitätswarnungen von technischen Manifestwarnungen trennen
- [x] Export eingebetteter Bilder um `FlateDecode`, `DCTDecode` und indizierte PNG-Raster erweitern
- [x] Generische Modellwarnungen zu lokal verifizierten Abbildungen im Cloud-Derivat entfernen
- [x] OpenAI-Hintergrundläufe wiederaufnehmbar machen und Fortschrittsereignisse für CLI-Aufrufer bereitstellen
- [x] Cloud-Antworten mit zulässigen Markdown-Codeblöcken akzeptieren

---

## Phase 8 – Strukturqualität und RAG-Übergabe

Ziel: Die Markdown-Ausgabe ist für strukturorientiertes Chunking und spätere Retrieval-Verbesserungen geeignet.

- [x] Überschriftenhierarchie, Absätze, Listen, Code und Tabellen gegen repräsentative PDFs evaluieren
- [x] Regeln für mehrspaltige Seiten, Fußnoten und Formeln als Qualitätswarnungen oder Erweiterungen definieren
- [x] Seitenreferenzen pro Abschnitt, Tabelle und Bild prüfen
- [x] Handhabbare Bildbeschreibungs-Workflows definieren
- [x] Vereinbarung für die Übergabe an CodexCLI dokumentieren
- [x] Maschinenlesbare Empfehlung für genau ein RAG-Indexderivat anhand transparenter Strukturmerkmale ergänzen
- [x] Optionalen reinen Reindex-Hook als CLI-Ergebnisereignis beschreiben; keine CodexCLI-Interna importieren
- [x] Konvertierte Markdown-Dokumente mit strukturorientiertem Chunking evaluieren

Akzeptanz:

- Der erzeugte Inhalt kann ohne PDF-Sonderpfad durch einen Markdown-RAG-Index verarbeitet werden.
- Bekannte Grenzen bleiben im Qualitätsstatus sichtbar.

---

## Phase 9 – Obsidian-Integration und Veröffentlichungsvorbereitung

Ziel: Die unabhängige Engine lässt sich sicher durch ein separates Desktop-only-Plugin bedienen.

- [x] CLI- und Manifest-Vertrag für externe Aufrufer stabilisieren und versionieren
- [x] Beispielaufruf und Beispielmanifest dokumentieren
- [x] Anforderungen für Fortschritt, Abbruch und Fehlerdarstellung des Plugins dokumentieren
- [x] Ausgabeordner- und Namenskonventionen für Obsidian-Vaults festlegen
- [x] Datenschutz-, Lizenz- und Abhängigkeitsprüfung durchführen
- [x] Installations- und Troubleshooting-Dokumentation erstellen

Akzeptanz:

- Ein separates Obsidian-Plugin kann DocToMD ohne interne Kopplung aufrufen.
- Die Engine bleibt auch außerhalb von Obsidian vollständig nutzbar.

---

## Nachtrag nach Phase 9 – Reaktive Stabilisierung der Layout- und RAG-Bewertung

Ziel: Reale, vom Obsidian-Plugin ausgelöste Konvertierungen dürfen ein einspaltiges Dokument nicht fälschlich als mehrspaltig behandeln oder trotz unsicherer Lesereihenfolge als RAG-geeignet freigeben.

- [x] Fehlklassifikation von `START_PROMPT.pdf` analysieren, die Mehrspaltenerkennung konservativ korrigieren und die RAG-Folgebewertung bei echter Mehrspaltenwarnung sperren
- [x] Typografische Überschriften und fortlaufende nummerierte PDF-Listen konservativ als Markdown-Struktur ableiten
- [x] Umgebrochene Listenelemente zu kompakten Markdown-Listen zusammenführen
- [x] Vektorbasierte PDF-Aufzählungspunkte sicher als ungeordnete Markdown-Listen ableiten
- [x] Vollständige mehrseitige Tabellen mit mehrzeiligen Zellen lokal und nachvollziehbar übertragen
- [x] Einfache displaygesetzte Formeln mit belegbarer Hoch- und Tiefstellung lokal als LaTeX ausgeben
- [x] Nicht lokal rekonstruierte, geometrisch klar gesetzte Formeln als Cloud-relevante Qualitätsgrenze melden
- [x] Strukturarmen OCR-Layoutfallback als Cloud-relevante Qualitätsgrenze melden
- [x] Vollseitige Scan-Assets aus dem Cloud-Derivat ausblenden und als prüfbare Dateien erhalten
- [x] Erschöpftes OpenAI-Guthaben als sicheren, benutzerfreundlichen CLI- und Plugin-Fehler melden

Akzeptanz:

- Ein einspaltiger Regressionsfall bleibt geometrisch top-to-bottom und erzeugt keine `MULTI_COLUMN_LAYOUT`-Warnung.
- Eine bestätigte Mehrspaltenwarnung führt für ein lokales Derivat zu `local_not_suitable`; Cloud oder Vision bleiben weiterhin ausschließlich Vorschläge mit explizitem Opt-in.
- Sichtbar getrennte Überschriften und nummerierte Listen bleiben für strukturorientiertes Chunking erhalten, ohne aus gewöhnlichem Fließtext Struktur zu erfinden.

---

## Phase 10 – Native PDF-Links und QR-Zielübergabe

Ziel: In PDF-Annotationen hinterlegte externe Ziele, insbesondere QR-Code-Links, bleiben lokal nachvollziehbar und in jedem empfohlenen Markdown-Derivat für RAG nutzbar.

- [x] Versionierten Strukturvertrag für native PDF-Links mit Ziel-URL, Seite, Annotationsrechteck, sicherer Herkunft und optionalem sichtbarem Titel festlegen
- [x] PDF-Link-Annotationen lokal und ohne Aufruf der Ziel-URLs extrahieren; ausschließlich sichere `https`-URLs akzeptieren und ungültige oder lokale Ziele seitenbezogen warnen
- [x] Sichtbare Titel nur bei geometrisch eindeutiger Zuordnung zu einer Annotation übernehmen; sonst eine neutrale, seitenbezogene Linkbezeichnung erzeugen
- [x] Links im lokalen Markdown unter dem zugeordneten Kapitel als kompakte Linkliste ausgeben; QR-Code-Piktogramme weder exportieren noch einbetten
- [x] Links samt Seite, Rechteck, Ziel und Zuordnungsstatus im Manifest speichern und gegen Pfad-, URL- und Quellenregeln validieren
- [x] Derselben lokal validierten Linkliste nach Cloud-Validierung in `Quelle.cloud.md` einfügen; Cloud-Antworten dürfen Links nicht ersetzen, entfernen oder erfinden
- [x] Lokale Vollständigkeitsprüfung ergänzen: Jeder akzeptierte native Link muss im empfohlenen Derivat mit Seitenbezug vertreten sein; bei Abweichung kein Cloud-Derivat als erfolgreich ausgeben
- [x] Mock- und PDF-Regressionen für `Mathe1.pdf` ergänzen: vier Links auf Seite 10, Titelzuordnung, mehrseitige Kapitel, ungültige Annotationen und Cloud-Antwort ohne Links
- [x] Einen separaten, ausdrücklich nicht automatischen Folgeentscheid für QR-Decodierung ohne PDF-Annotation bewerten

Akzeptanz:

- `Mathe1.pdf` enthält im lokalen sowie im Cloud-Derivat unter „Rechengesetze“ eine verifizierte Linkliste für Potenz-, Wurzel- und Logarithmusgesetze sowie „Fakultäten kürzen“.
- Kein Ziel wird abgerufen, kein QR-Bild muss in Markdown erscheinen und kein Linktitel wird geometrisch geraten.
- Die Cloud-Verarbeitung kann keinen lokal extrahierten Link verlieren oder durch eine erfundene URL ersetzen.

---

## Phase 11 – Wiederverwendbare Cloud-Ableitung und mathematische Batch-Verarbeitung

Ziel: Ein explizit angeforderter Cloud-Lauf nutzt ein unverändertes, bereits geprüftes lokales Derivat ohne erneute lokale Konvertierung. Lange mathematische PDFs werden anschließend in validierbaren, wiederaufnehmbaren Batches verarbeitet.

- [x] Versionierten lokalen Wiederverwendungskontext aus Manifest, Markdown, Assets, Qualitätsbefunden und nativen PDF-Links festlegen und sicher rehydrieren
- [x] Lokales Markdown und Basismanifest vor jeder Cloud-Anfrage atomisch veröffentlichen; Cloud-Fehler dürfen das lokale Ergebnis nicht verhindern oder verändern
- [x] Stabile CLI-Schnittstelle `cloud-derive` für einen ausdrücklich angeforderten Cloud-Lauf aus einem vorhandenen lokalen Ergebnis definieren
- [x] Cloud-Opt-in in `convert` automatisch auf `cloud-derive` umleiten, wenn Quellfingerabdruck, lokale Artefakte und Wiederverwendungskontext gültig sind; Fortschrittshinweis ausgeben
- [x] Wiederaufnahmezustand an Quellhash, lokalen Kontext, Modell und Promptvertrag binden; offene `response_id` ohne Neu-Upload weiter abfragen
- [x] Inhaltsbasierte Cloud-Vollständigkeitsprüfung gegen lokale Seitenbefunde ergänzen; dünne Warnungs- oder Überschriftenableitungen nicht als erfolgreich oder RAG-empfohlen veröffentlichen
- [x] Lokale Batch-Planung für lange mathematische PDFs festlegen: Kapitelgrenzen bevorzugen, zunächst höchstens sechs Seiten je Batch und dichte Formel-/Tabellenseiten begrenzen
- [x] Temporäre Batch-PDFs, einzelne Cloud-Anfragen, batchweise Validierung und deterministische Zusammenführung implementieren; Original-PDF unverändert lassen
- [x] Erfolgreiche Batches, offene `response_id` und Batch-Telemetrie persistent speichern; bei Neustart nur fehlende oder offene Batches verarbeiten
- [x] Unit-, Mock- und Wiederaufnahme-Regressionen für Wiederverwendung, Quelländerungen, Budgetfehler, Timeout, unvollständige Cloud-Inhalte und Batchzusammenführung ergänzen
- [x] Kontrollierte reale Evaluation mit `Mathe1.pdf` zunächst für Seite 9–14 durchführen; Kosten, Laufzeit, Formelerhalt und RAG-Empfehlung dokumentieren, bevor ein Gesamtlauf erfolgt

Akzeptanz:

- Ein expliziter Cloud-Lauf nach einem unveränderten lokalen Lauf wiederholt weder PDF-Textextraktion noch OCR-, Tabellen-, Bild- oder native Linkanalyse.
- Ohne Cloud-Opt-in bleibt jeder Lauf lokal und netzwerkfrei.
- Ein Timeout oder Budgetfehler erhält das lokale Derivat und verarbeitet bei Wiederaufnahme keine bereits erfolgreichen Cloud-Batches erneut.
- Ein Cloud-Derivat wird nur bei vollständig validierten Batches veröffentlicht und kann keine lokal autoritativen Links verlieren oder verändern.

---

## Nachtrag nach Phase 11 – Reale Batch-Korrekturen

- [x] Reale Seitenmarkerabweichung, Überschriftenfragmentierung und Erstlauf-Umgehung des Batchpfads korrigieren; Wiederaufnahme bei endgültig markerungültiger Antwort sicher zurücksetzen
- [x] Separaten, ausdrücklich aktivierten Befehl `cloud-evaluate` für einen zusammenhängenden Originalseitenbereich implementieren; lokalen Wiederverwendungskontext rehydrieren, Teil-PDF und Promptseiten prüfen, bereichsspezifische Artefakte schreiben und reguläres Cloud-Derivat, Manifest sowie Batchzustand unverändert lassen
- [x] Inhaltsbasierte Mindestvollständigkeit zusätzlich je Cloud-Batch vor der Wiederverwendung prüfen; einen gespeicherten, marker-korrekten aber inhaltlich unvollständigen Batch gezielt zurücksetzen und ausschließlich diesen erneut anfragen
- [x] PDF-Formelreste mit senkrechten Strichen nicht als GFM-Tabellen fehlklassifizieren; Batch-18-Fehlalarm lokal regressionsgesichert korrigieren
- [x] Deterministische Konvertierungsbewertung als getrennte Markdown-Note automatisch nach Veröffentlichung und separat über `doctomd review` erzeugen
- [x] Lokale und Cloud-Laufzeiten aus Manifest und Batch-Telemetrie in der Konvertierungsbewertung ausweisen
- [x] Beispielaufruf für die nachträgliche Konvertierungsbewertung im README dokumentieren
- [x] Marker-gültige, aber inhaltlich verworfene Cloud-Batches als getrennte Diagnoseartefakte sichern
---

## Phase 12 – Vektor-Abbildungen und Asset-Integrität

Ziel: Sichtbare, caption-gebundene Vektorgrafiken werden als nachvollziehbare lokale PNG-Assets erhalten, ohne vollständige Textseiten als Bilder zu duplizieren. Cloud-Derivate dürfen ausschließlich auf lokal autoritative Assetdateien verweisen.

- [x] Für Seiten ohne eingebettetes Rasterbild konservativ ermitteln, ob eine caption-gebundene Vektorgrafik vorliegt; unsichere Fälle als seitenbezogene Qualitätswarnung ausweisen und keine Vollseite exportieren
- [x] Den belegten Grafikbereich mit dem vorhandenen lokalen Renderer als PNG ausschneiden, als reguläres Asset mit stabilem Namen, Seitenbezug, Sidecar-Note und Manifestreferenz veröffentlichen
- [x] Lokales und Cloud-Markdown ausschließlich aus der autoritativen Assetliste referenzieren; nicht vorhandene oder von der Cloud erfundene relative Bildpfade vor der Veröffentlichung mit einem stabilen Fehlercode abweisen
- [x] Regressionsfixtures und Mock-Tests für Vektor-Crop, Seiten- und Caption-Zuordnung, Manifest-/Markdown-Konsistenz, fehlende Vollseiten-Assets sowie unerlaubte Cloud-Bildreferenzen ergänzen
- [x] Cloud-Antworten ohne eigene Bildreferenzen vertraglich durchsetzen; unerlaubte Referenzen vor Batch-Persistierung zurücksetzen und mit einer konkreten Wiederanlaufanweisung abweisen
- [x] Vektorasset-Captions im Cloud-Derivat anhand einer eindeutigen Figure-/Fig.-Nummer trotz abweichendem PDF-Textlayer direkt zuordnen
- [x] Die Ergebnisse an einem wissenschaftlichen PDF mit Vektordiagrammen visuell prüfen und verbleibende Grenzen oder Warnungen dokumentieren

Akzeptanz:

- Eine eindeutig erkannte Vektor-Abbildung erscheint als vorhandenes, zugeschnittenes PNG-Asset mit korrektem Seitenbezug und ohne duplizierten Seitentext.
- Unsichere Vektorbereiche werden nicht geraten oder als ganze Seite exportiert, sondern nachvollziehbar gewarnt.
- Kein veröffentlichtes lokales oder Cloud-Markdown enthält eine Bildreferenz, die nicht auf ein lokales autoritatives Asset innerhalb des Ausgabeordners zeigt.


---

## Nachtrag nach Phase 12 – Provenienz in Markdown-Derivaten

Ziel: Jeder Markdown-Ableitung ist ihre unveränderte PDF-Primärquelle auch ohne separates Manifest maschinenlesbar zugeordnet.

- [x] YAML-Provenienzblock für neue lokale und Cloud-Markdown-Derivate erzeugen und vorhandene Derivate ohne PDF- oder Cloud-Lauf lokal nachrüsten

---

## Nachtrag nach Phase 12 – Wiederaufnahme fortgesetzter Listen

- [x] Eingerückte Seitenmarker aus lokal fortgesetzten Markdown-Listen bei Cloud-Batches akzeptieren und regressionsgesichert prüfen
