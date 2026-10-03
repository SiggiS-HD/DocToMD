# Installation und Fehlerbehebung

Diese Anleitung richtet sich an lokale Windows-Installationen von DocToMD. Die Standardkonvertierung verarbeitet PDFs lokal und benötigt weder ein Obsidian-Plugin noch einen Cloud-Zugang.

## Grundinstallation

Voraussetzung ist Python 3.12 für Entwicklung und CI; Python 3.11 oder neuer wird unterstützt. Im Projektordner ausführen:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Der letzte Befehl zeigt die CLI-Hilfe. Eine lokale, digitale PDF lässt sich danach so konvertieren:

```powershell
.\.venv\Scripts\python.exe main.py convert `
  "D:\Dokumente\Quelle.pdf" `
  --output-dir "D:\Dokumente\Quelle-Export" `
  --on-conflict error `
  --json `
  --progress human
```

Der Ausgabeordner muss noch nicht existieren, aber sein übergeordnetes Verzeichnis muss vorhanden sein. Der Aufruf schreibt abgeleitetes Markdown und ein Manifest; die PDF-Primärquelle wird nie überschrieben oder gelöscht. Ein vollständiges Ergebnisbeispiel steht in [[CLI_MANIFEST_EXAMPLE|CLI- und Manifestbeispiel]].

## Optionale OCR für Scan-PDFs

OCR benötigt zusätzlich Tesseract 5 als lokal installiertes Systemwerkzeug. Nach der Installation muss dessen Programmordner in `PATH` liegen. In einem neuen PowerShell-Fenster prüfen:

```powershell
tesseract --version
tesseract --list-langs
```

Für `--ocr-language de` muss die Sprachdatei `deu` und für `--ocr-language en` die Sprachdatei `eng` verfügbar sein. DocToMD verwendet bei einem fehlenden Textlayer standardmäßig `--ocr-mode auto`; `--ocr-mode force` erzwingt OCR. Es lädt keine Modelle nach und überträgt keine Seitenbilder.

## Optionale Cloud- und Vision-Modi

Ohne zusätzliche Optionen findet keine Netzwerkübertragung statt. Für OpenAI-Modi muss `OPENAI_API_KEY` ausschließlich in der aufrufenden Umgebung gesetzt sein:

```powershell
if (-not $env:OPENAI_API_KEY) { throw "OPENAI_API_KEY ist nicht gesetzt." }
```

Der Cloud-Dokumentmodus verlangt zusätzlich `--cloud-document-mode openai` und eine Modell-ID. OpenAI-Vision verlangt `--vision-provider openai`, einen aktiven Vision-Modus und eine Modell-ID. LM Studio wird nur mit `--vision-provider lm-studio`, einer Modell-ID und einem expliziten HTTP(S)-Endpoint aktiv. Vor dem Einsatz vertraulicher Dokumente müssen Datenfluss und Freigabe in [[PRIVACY_LICENSE_DEPENDENCY_AUDIT|Datenschutz-, Lizenz- und Abhängigkeitsprüfung]] geprüft werden.

## Häufige Diagnosen

| Beobachtung | Ursache oder Prüfung | Nächste sichere Maßnahme |
| --- | --- | --- |
| `python` oder `.venv\Scripts\python.exe` fehlt | Python oder virtuelle Umgebung ist nicht verfügbar | Unterstützte Python-Version installieren beziehungsweise die Schritte unter „Grundinstallation“ erneut ausführen. |
| `Die Quelldatei existiert nicht` | Eingabepfad ist falsch oder nicht zugreifbar | Absoluten Pfad prüfen; nur eine vorhandene reguläre PDF-Datei übergeben. |
| `Der Ausgabeordner verweist auf eine Datei` | `--output-dir` zeigt auf eine Datei | Einen neuen Ordnerpfad wählen. |
| Ausgabeordner hat keinen vorhandenen Verzeichnisvorfahren | Ein Elternordner existiert nicht | Zuerst den gewünschten übergeordneten Ordner anlegen oder einen vorhandenen Zielort wählen. |
| Konflikt mit abgeleiteten Artefakten | Ziel enthält bereits ein früheres Ergebnis | Zunächst Manifest und Quelle vergleichen. Danach bewusst `--on-conflict update` für dieselbe Quelle oder `overwrite` für einen ausdrücklichen Ersatz verwenden. |
| Tesseract ist nicht installiert oder nicht über `PATH` erreichbar | OCR-Systemwerkzeug fehlt | Tesseract 5 installieren, Programmordner in `PATH` aufnehmen und `tesseract --version` erneut ausführen. |
| Tesseract-Sprachdaten fehlen | `deu` oder `eng` ist nicht installiert | Passende `.traineddata` in den Tesseract-`tessdata`-Ordner installieren und mit `tesseract --list-langs` prüfen. |
| `OCR_LOW_CONFIDENCE` | OCR hat unsicheren Text erkannt | Betroffene Seite im Markdown und Manifest prüfen; bei Bedarf Qualität des Scans verbessern oder ein ausdrücklich freigegebenes Cloud-Derivat separat bewerten. |
| `OPENAI_API_KEY ist ... nicht gesetzt` | Cloud- oder OpenAI-Vision-Modus ohne Schlüssel | Schlüssel ausschließlich als Umgebungsvariable der aufrufenden Sitzung setzen; niemals in Kommandozeile oder Manifest eintragen. |
| Cloud-Antwort erzeugt kein `*.cloud.md` | Lokale Mindestvalidierung hat die Antwort abgewiesen oder sie war unvollständig | Manifest und CLI-Fehler lesen; den lokalen Export unverändert nutzen und erst nach Ursachenprüfung einen neuen opt-in-Lauf starten. |
| Exit-Code `1` | Konvertierung erfolgreich, aber mit Qualitätswarnungen | Manifest öffnen, Warnungen nach Seite prüfen und Ergebnis erst danach weitergeben oder indexieren. |
| Exit-Code `2` | Technischer oder Validierungsfehler | `--json` verwenden, `error.code` und `error.message` auswerten; bestehende Artefakte nicht löschen. |

## Prüfen eines Ergebnisses

Bei `--json` enthält `result.manifest_path` den relativen Manifestnamen. Vor der Übergabe an ein Plugin oder einen Indexer prüfen:

1. Die Manifestdatei und das darin empfohlene `rag_indexing.recommended_markdown_path` existieren im Ausgabeordner.
2. `source.sha256` passt zur unveränderten PDF-Primärquelle.
3. `quality.status` und seitenbezogene Warnungen sind bekannt und akzeptiert.
4. Nur das empfohlene Derivat wird indexiert; ein lokales und ein Cloud-Derivat derselben Quelle werden nie parallel indexiert.

Ein Obsidian-Plugin verwendet zusätzlich [[OBSIDIAN_VAULT_OUTPUT_CONVENTIONS|die Vault-Ausgabe- und Namenskonventionen]]. Die Übergabe an CodexCLI folgt [[CODEXCLI_HANDOFF|dem separaten Übergabevertrag]].

## Informationen für eine Fehlermeldung

Für eine technische Diagnose genügen normalerweise DocToMD-Version, Betriebssystem, Python-Version, vollständiger CLI-Aufruf ohne Geheimnisse, Exit-Code, JSON-Fehlerobjekt und das zugehörige Manifest. Original-PDFs, API-Schlüssel und vertrauliche Markdown-Inhalte gehören nicht ungefragt in einen Fehlerbericht.
