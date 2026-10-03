# Datenschutz-, Lizenz- und Abhängigkeitsprüfung

Stand der Prüfung: 22. September 2026. Diese Note ist eine technische Bestandsaufnahme und keine Rechtsberatung. Vor einer öffentlichen Verteilung oder Verarbeitung personenbezogener Dokumente muss der Betreiber die anwendbaren Rechts-, Lizenz- und Vertragsanforderungen eigenständig prüfen.

## Ergebnis

Der lokale Standardlauf ist netzwerkfrei: Digitale PDFs werden mit `pdfplumber` verarbeitet; lokale OCR verwendet nach ausdrücklicher Auswahl PDFium und Tesseract. Externe Übertragungen sind nicht Standardverhalten. Ein Release ist technisch erst dann freigabereif, wenn die genaue Abhängigkeitsauflösung eingefroren, die zugehörigen Lizenztexte beziehungsweise Notices bereitgestellt und der konkrete Cloud-Auftragsverarbeitungsprozess geprüft wurden.

## Datenflüsse

| Verarbeitung | Aktivierung | Übertragene Daten | Lokale Artefakte |
| --- | --- | --- | --- |
| Text, Tabellen und eingebettete Bilder | Standard | keine Netzwerkübertragung | Markdown, Manifest, optionale Bildassets |
| Tesseract-OCR | `--ocr-mode auto` bei fehlendem Textlayer oder `force` | keine Netzwerkübertragung; Seitenbild bleibt im Arbeitsspeicher | Markdown, OCR-Metriken und Warnungen im Manifest |
| LM-Studio-Vision | expliziter Provider `lm-studio` mit Modus `auto` oder `force` | gerenderte Risikoseiten an den konfigurierten LAN-Endpoint | nur lokal validierte Vorschläge, Review-Artefakte und Manifestreferenzen |
| OpenAI-Vision | expliziter Provider `openai` mit Modus `auto` oder `force` | gerenderte Risikoseiten an die OpenAI-API | nur lokal validierte Vorschläge, Review-Artefakte und Manifestreferenzen |
| OpenAI-Cloud-Dokument | `--cloud-document-mode openai` | vollständige PDF an die OpenAI-API | getrenntes Cloud-Markdown, Telemetrie und Qualitätsbefunde |

Die Primärquelle bleibt in jedem Pfad unverändert. `OPENAI_API_KEY` wird ausschließlich aus der Prozessumgebung gelesen; der Schlüssel gehört weder in CLI-Argumente, Konfigurationsdateien, Markdown noch Manifest. Cloud- und Vision-Modi sind vor dem Start im Plugin sichtbar zu bestätigen. Für vertrauliche oder personenbezogene PDFs sollte der Betreiber den lokalen Pfad wählen, sofern keine dokumentierte Rechtsgrundlage und kein geprüfter Vertrag für den gewählten Provider vorliegen.

Die Cloud-Adapter verwenden die OpenAI-API und versuchen nach Abschluss, temporär hochgeladene Dateien zu löschen. Das ist keine Zusage über Aufbewahrung, Region, Sicherheitsmaßnahmen oder Trainingsnutzung beim Provider. Diese Punkte richten sich nach dem zum Einsatzzeitpunkt gültigen Vertrag und den offiziellen [OpenAI-API-Datenkontrollen](https://platform.openai.com/docs/guides/your-data).

## Python-Abhängigkeiten

Die direkte Laufzeitabhängigkeit ist absichtlich klein und in `requirements.txt` begrenzt. Die Tabelle zeigt die bei der Prüfung installierten Versionen und die von deren Paketmetadaten genannten Lizenzkennzeichnungen.

| Paket | Installierte Version | Rolle | Lizenzkennzeichnung laut Paketmetadaten |
| --- | ---: | --- | --- |
| `pdfplumber` | `0.11.10` | PDF-Text, Geometrie, Tabellen- und Bildanalyse | Lizenzfeld leer; Lizenzdatei des Projekts vor Veröffentlichung prüfen |
| `pypdfium2` | `5.13.0` | PDFium-Rendering für OCR | `BSD-3-Clause`, `Apache-2.0`, weitere Abhängigkeitslizenzen |
| `Pillow` | `12.3.0` | sichere PNG-Kodierung von Bildassets | `MIT-CMU` |
| `pdfminer.six` | `20260107` | transitive Textanalyse von `pdfplumber` | `MIT` |
| `cryptography` | `50.0.1` | transitiv über `pdfminer.six` | `Apache-2.0 OR BSD-3-Clause` |
| `cffi` | `2.1.1` | transitiv über `cryptography` | `MIT-0` |
| `charset-normalizer` | `3.5.1` | transitiv über `pdfminer.six` | `MIT` |
| `pycparser` | `3.0` | transitiv über `cffi` | `BSD-3-Clause` |

Die Tabellenwerte sind keine Ersatzquelle für die jeweiligen Lizenztexte. Maßgeblich sind die Release-Artefakte und die Lizenzinformationen der konkret ausgelieferten Versionen. Relevante Primärquellen sind die Projekte [pdfplumber](https://github.com/jsvine/pdfplumber), [pypdfium2](https://github.com/pypdfium2-team/pypdfium2), [Pillow](https://github.com/python-pillow/Pillow) und [pdfminer.six](https://github.com/pdfminer/pdfminer.six).

Tesseract ist keine Python-Abhängigkeit und wird nur bei OCR benötigt. Es ist als separates Systemwerkzeug zu installieren; seine Lizenz- und Notice-Pflichten müssen für die konkrete Tesseract-Distribution einschließlich Sprachdaten geprüft werden. Die Referenzimplementation liegt bei [tesseract-ocr](https://github.com/tesseract-ocr/tesseract).

## Freigabebedingungen für eine Verteilung

Vor dem Bau eines Installers oder einer gebündelten Anwendung sind diese Punkte offen und verpflichtend:

1. Die direkten und transitiven Pakete mit einem reproduzierbaren Lockfile oder Hash-gesicherten Constraints auf exakte Versionen festschreiben.
2. Für die exakt ausgelieferten Wheels und nativen Komponenten eine vollständige Drittanbieterdatei mit Lizenztexten und erforderlichen Notices erzeugen; insbesondere die mit `pypdfium2` gelieferte PDFium-Komponente separat prüfen.
3. Die verwendete Tesseract-Distribution sowie gegebenenfalls Sprachdaten lizenzrechtlich dokumentieren und deren Hinweise mitliefern, falls sie gebündelt werden.
4. Für OpenAI- und LM-Studio-Modi einen sichtbaren Zustimmungsdialog, die aktuelle Datenschutzerklärung und eine organisationsspezifische Prüfung von Vertragsgrundlage, Datenkategorie, Speicherort und Aufbewahrung vorsehen.
5. Einen Abhängigkeits- und Sicherheitscheck in die Release-Pipeline aufnehmen und dessen Ergebnis mit der Release-Version archivieren.

Bis diese Bedingungen erfüllt sind, ist der geeignete Umfang die lokale Entwicklungs- und Einzelnutzung mit bewusster Installation der Abhängigkeiten. Der netzwerkfreie Standardlauf bleibt davon unberührt.

Siehe auch [PROJECT](../PROJECT.md), [CLI- und Manifestbeispiel](CLI_MANIFEST_EXAMPLE.md) und [Ausgabeordner und Namenskonventionen für Obsidian-Vaults](OBSIDIAN_VAULT_OUTPUT_CONVENTIONS.md).
