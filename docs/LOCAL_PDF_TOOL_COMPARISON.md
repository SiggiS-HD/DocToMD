# Vergleich der lokalen PDF-Werkzeuge: CodexCLI und DocToMD

Stand: 2. Oktober 2026

## Anlass und Ergebnis

Die beiden Projekte wurden daraufhin verglichen, welche lokalen Programme und Bibliotheken sie bei PDF-Verarbeitung einsetzen und ob CodexCLI-Komponenten die lokale PDF-zu-Markdown-Konvertierung von DocToMD verbessern könnten.

Das Ergebnis ist eindeutig: Aus CodexCLI lässt sich kein stärkeres lokales Konvertierungswerkzeug nach DocToMD übernehmen. DocToMD besitzt bereits die deutlich umfangreichere Pipeline für strukturierte, nachprüfbare Markdown-Derivate. CodexCLI verarbeitet PDFs dagegen als Eingabe für seinen Suchindex; seine PDF-Funktionen sind keine allgemeine Markdown-Konvertierung.

Diese Aussage bedeutet nicht, dass jedes lokale DocToMD-Ergebnis für RAG geeignet ist. [Die RAG-Eignungsprüfung](RAG_READINESS.md) stuft Ergebnisse mit konkreten Qualitätsgrenzen, etwa Mehrspaltenlayout, unsicherer OCR-Struktur, nicht rekonstruierbaren Formeln oder komplexen Tabellen, bewusst als nicht lokal geeignet ein. Einfache und ausreichend strukturierte PDFs können dagegen lokal als RAG-geeignet bewertet werden.

## Vergleich

| Bereich | CodexCLI | DocToMD | Bewertung |
| --- | --- | --- | --- |
| Primäre Textextraktion | `pypdf` | `pdfplumber` mit Wortkoordinaten | DocToMD erhält Geometrie als Grundlage für Lesereihenfolge und Struktur. |
| Text-Fallback | Direkter Aufruf von `pdfminer.six` bei leerem `pypdf`-Text | `pdfplumber`, das auf `pdfminer.six` aufbaut | Kein unabhängiger Gewinn durch Übernahme des CodexCLI-Fallbacks. |
| Digitale Struktur | Seitenbezogener Rohtext für Zeichen-Chunking | Überschriften, Absätze, Listen, Tabellen, Formelkandidaten, Spalten- und Layoutwarnungen | Nur DocToMD erzeugt ein editierbares Strukturderivat. |
| OCR-Renderer | Poppler über `pdf2image`, 150 DPI, höchstens zwei Seiten | PDFium über `pypdfium2`, 300 DPI, auswählbare Seiten | DocToMD ist vollständiger und benötigt kein zusätzliches Poppler-Systemwerkzeug für OCR. |
| OCR-Engine | Tesseract über `pytesseract` | Tesseract 5 direkt über `subprocess`, TSV-Ausgabe | Die direkte CLI-Anbindung von DocToMD bewahrt Wortpositionen und Konfidenzen. |
| OCR-Qualität | Keine strukturierte Auswertung | Wortkonfidenz, seitenbezogene Warnungen und positionsnahes HTML-Layout | DocToMD ist nachvollziehbarer. |
| Tabellen, Bilder und Vektorgrafiken | Keine strukturierte Konvertierung | Tabellenprüfung, Bildassets, Caption-Zuordnung und konservative Vektor-Crops | Nur DocToMD deckt diese Inhalte ab. |
| PDF-Links | URI-Links als Text im Index | Sichere native `https`-Links mit Annotation-Rechteck, Titelzuordnung und Manifest | DocToMD bietet den strengeren, RAG-tauglichen Vertrag. |
| Zielartefakt | SQLite-FTS-/Hybridindex aus Zeichen-Chunks | Markdown, Assets, Manifest, Qualitäts- und RAG-Bewertung | Unterschiedliche, bewusst getrennte Verantwortlichkeiten. |

## Bewertung der CodexCLI-Werkzeuge

### `pypdf`

`pypdf` ist bereits eine direkte DocToMD-Abhängigkeit und wird dort für sichere, kurzlebige Teil-PDFs bei Cloud-Batches verwendet. Die Textextraktion von `pypdf` würde die positionsgestützte `pdfplumber`-Extraktion nicht verbessern. Eine Übernahme als Text-Fallback wird daher nicht empfohlen.

### `pdfminer.six`

DocToMD verfügt über `pdfminer.six` bereits transitiv durch `pdfplumber`. Ein separater Direktaufruf wäre kein unabhängiger Extraktor und würde die in DocToMD benötigten Geometrieinformationen nicht verbessern. Falls einzelne PDFs problematisch sind, ist ein kontrolliertes A/B-Experiment mit `pdfplumber`-Layoutparametern sinnvoller als ein zweiter, gleichartiger Pfad.

### Poppler und `pdf2image`

CodexCLI verwendet Poppler über `pdf2image` als OCR-Renderer. DocToMD rendert OCR-Seiten bereits direkt über PDFium mit höherer Auflösung und ohne temporäre Bilddateien. Poppler bleibt in DocToMD für den ausdrücklich aktivierten Vision-Schritt vorhanden, ist jedoch kein sinnvoller Ersatz für den lokalen OCR-Standardpfad.

### `pytesseract`

`pytesseract` ist ein Python-Wrapper um dieselbe Tesseract-Engine. DocToMD ruft Tesseract direkt auf, erhält die TSV-Ausgabe und verarbeitet daraus Wortpositionen und Konfidenzen. Ein zusätzlicher Wrapper würde keine Erkennungsqualität erhöhen und die Fehlerbehandlung eher indirekter machen.

## Mögliche Ergänzungen für DocToMD

### Docling: sinnvoller Kandidat für einen optionalen lokalen Fallback

Docling ist kein einzelnes KI-Modell, sondern ein Dokumentverarbeitungs-Framework. Es bietet mehrere Pipelines:

- Die Native-Pipeline liest vorhandenen PDF-Text und eingebettete Bilder ohne Layout-, OCR- oder Tabellenmodelle.
- Die Standard-Pipeline kann lokale Modelle für Layout, Tabellenstruktur und OCR einsetzen.
- Die VLM-Pipeline verwendet ein lokales Vision-Language-Model, das Seiten visuell interpretiert und strukturiertes Markdown erzeugen kann.

Docling könnte für wissenschaftliche Mehrspaltenseiten, komplexe Tabellen und problematische Scanlayouts einen erheblichen Qualitätsgewinn liefern. Es wäre jedoch kein Ersatz für den robusten, leichtgewichtigen DocToMD-Standardpfad, sondern ein ausdrücklich aktivierter Rekonstruktions-Fallback. Die benötigten Modellgewichte und die PyTorch-Abhängigkeit sind schwergewichtig; Modellgewichte werden standardmäßig beim ersten Einsatz geladen oder müssen vorab für einen Offline-Betrieb bereitgestellt werden. Deshalb darf Docling nicht ohne eine separate Evaluation an repräsentativen Problem-PDFs und ohne ausdrückliche Freigabe eingeführt werden.

Docling kann lokal arbeiten. Remote-Dienste sind davon getrennt und müssen explizit aktiviert werden. Die Primärquelle muss auch bei einer späteren Integration unverändert bleiben; übernommene Inhalte benötigen Seitenbezug, Validierung, Manifest-Protokollierung und sichtbare Qualitätsgrenzen entsprechend [PROJECT](../PROJECT.md).

### Camelot: möglicher, eng begrenzter Tabellen-Fallback

Camelot ist nur dann ein Kandidat, wenn die vorhandene Tabellenextraktion für digitale PDFs mit klaren Linien- oder Spaltenstrukturen nachweislich scheitert. Seine Verfahren `Lattice`, `Stream`, `Network` und `Hybrid` lösen weder OCR- noch Formel- oder allgemeine Lesereihenfolgeprobleme. Vor einer Aufnahme wäre ein Vergleich gegen die bestehenden Tabellen-Fixtures erforderlich.

### Nicht empfohlen

- OCRmyPDF erzeugt ein neues PDF mit OCR-Textlayer. Das kann Suchbarkeit von Scans verbessern, ist aber kein direkter Gewinn für die strukturierte Markdown-Erzeugung und führt eine zusätzliche abgeleitete PDF-Kette ein.
- PyMuPDF wäre zwar ein unabhängiger A/B-Extraktor mit Tabellen- und Linkzugriff, steht jedoch unter AGPL oder einer kommerziellen Lizenz. Ohne bewusste Lizenzentscheidung ist es keine geeignete Standardabhängigkeit.

## Empfehlung

1. Keine Komponente aus CodexCLI in die lokale DocToMD-Konvertierung übernehmen.
2. Zuerst die vorhandene Pipeline anhand konkreter Problem-PDFs evaluieren und bei Bedarf OCR-Parameter oder bestehende Layoutheuristiken gezielt verbessern.
3. Nur bei messbarem Mehrwert einen optionalen Docling-Fallback evaluieren; die lokale Standardverarbeitung bleibt leichtgewichtig, netzwerkfrei und unverändert.
4. Camelot ausschließlich als tabellenspezifischen Kandidaten bewerten, nicht als allgemeine PDF-zu-Markdown-Lösung.

## Primärquellen

- [pdfplumber: Architektur und Layoutparameter](https://github.com/jsvine/pdfplumber/blob/stable/README.md)
- [Docling: lokale Modelle und Offline-Betrieb](https://docling-project.github.io/docling/usage/advanced_options/)
- [Docling: VLM-Pipeline](https://docling-project.github.io/docling/usage/vision_models/)
- [Docling: Installation und PyTorch-Abhängigkeit](https://docling-project.github.io/docling/getting_started/installation/)
- [Camelot: Extraktionsverfahren](https://camelot-py.readthedocs.io/)
- [OCRmyPDF: OCR-Textlayer](https://ocrmypdf.readthedocs.io/en/latest/)
- [PyMuPDF: Lizenzmodell](https://pymupdf.readthedocs.io/en/latest/faq/index.html)

Siehe auch [RAG-Eignungsprüfung](RAG_READINESS.md), [Regeln zur Strukturqualität](STRUCTURE_QUALITY_RULES.md) und [Datenschutz-, Lizenz- und Abhängigkeitsprüfung](PRIVACY_LICENSE_DEPENDENCY_AUDIT.md).
