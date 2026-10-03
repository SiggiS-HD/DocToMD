# AGENTS.md
# DocToMD – Agent Instructions

## Sprachregel

- Antworte dem Benutzer auf Deutsch.
- Verwende in allen natürlichsprachlichen Antworten und erzeugten Markdown-Dateien echte deutsche Umlaute (`ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`, `ß`).
- Verwende Englisch für Code, Bezeichner, Bibliotheksnamen, APIs und CLI-Optionen.

## Markdown-Konventionen

- Schreibe Fließtext innerhalb eines Absatzes ohne harte Zeilenumbrüche. Zeilenumbrüche dienen nur der inhaltlichen Gliederung, etwa bei Absätzen, Listen, Überschriften, Tabellen und Codeblöcken.
- Verwende für Verweise auf Notes im Vault immer Wiki-Links wie `[[PROJECT]]` oder `[[ENGINEERING_NOTES|Engineering Notes]]`.

## Arbeitsweise

Arbeite in kleinen, kontrollierten und testbaren Schritten.

Für jede neue Implementierungsaufgabe:

1. Lies zuerst `PROJECT.md` und `TASKS.md`.
2. Bearbeite nur die erste offene Aufgabe der aktuellen Phase.
3. Erkläre Plan, betroffene Dateien und erwartetes Ergebnis.
4. Warte vor Implementierungen auf ausdrückliche Freigabe, sofern sie nicht bereits eindeutig erteilt wurde.
5. Implementiere inkrementell und validiere die Änderung in angemessenem Umfang.
6. Markiere eine Aufgabe erst nach erfolgreicher Validierung in `TASKS.md` als erledigt.

## Projektgrenzen

- DocToMD ist eine eigenständige lokale Konvertierungs-Engine; es enthält keine CodexCLI-Connector-Logik und kein Obsidian-Plugin.
- Das Originaldokument ist eine unveränderte Primärquelle und darf niemals überschrieben oder gelöscht werden.
- Markdown, Assets und Manifest sind versionierte abgeleitete Artefakte.
- Die Engine muss ohne Obsidian über eine stabile CLI nutzbar sein.
- Die Anbindung an Obsidian und CodexCLI erfolgt ausschließlich über definierte Schnittstellen, nicht über gegenseitige interne Imports.

## Python-Umgebung

- Python 3.12 bevorzugen; Python >= 3.11 unterstützen.
- Virtuelle Umgebung: `.venv`.
- Abhängigkeiten nur über `requirements.txt` oder einen später bewusst gewählten Paketmanager verwalten.
- Schwere OCR-, Layout- oder ML-Abhängigkeiten nicht ohne ausdrückliche Freigabe installieren.

Typische Windows-Befehle:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest
```

## Code- und Architekturregeln

Prioritäten: Lesbarkeit, Wartbarkeit, Einfachheit, erst danach Optimierung.

- Kleine Module mit klarer Verantwortung bevorzugen.
- Keine monolithische Konvertierungsfunktion bauen.
- Öffentliche CLI-Ausgaben und das Konvertierungsmanifest als stabile Schnittstellen behandeln.
- Jeden Konvertierungsschritt nachvollziehbar protokollieren.
- Seitennummern und die Herkunft von Text, Tabellen und Bildern bewahren.
- Fehler und Qualitätswarnungen sichtbar ausgeben; niemals stillschweigend Daten erfinden oder Fehler kaschieren.

## Sicherheitsregeln

Niemals ohne Rückfrage:

- Originaldokumente, erzeugte Artefakte oder Benutzerdaten löschen,
- vorhandene Dateien außerhalb eines explizit bestätigten Ausgabeordners überschreiben,
- große Codebereiche blind ersetzen,
- schwere Abhängigkeiten, externe Modelle oder Systemwerkzeuge installieren,
- Netzwerkanfragen oder Cloud-Dienste als Standardverhalten einführen.

## Qualität

- Für Parser, Manifest, Pfadvalidierung und Konvertierungsplanung Unit-Tests ergänzen.
- Für echte PDF-Konvertierung kleine, rechtlich unproblematische Testfixtures verwenden.
- Digitale PDFs, gescannte PDFs und fehlerhafte Eingaben getrennt testen.
- Ausgabe vor einer Erfolgsmeldung auf Markdown, Assets, Seitenreferenzen und Manifest prüfen.
