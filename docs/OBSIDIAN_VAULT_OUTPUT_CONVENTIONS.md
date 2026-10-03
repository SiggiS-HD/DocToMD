# Ausgabeordner und Namenskonventionen für Obsidian-Vaults

Dieser Vertrag beschreibt ausschließlich die Dateigrenze zwischen einem separaten Obsidian-Plugin und DocToMD. DocToMD bleibt ohne Obsidian-Abhängigkeit nutzbar; das Plugin wählt Pfade und startet die öffentliche CLI.

## Empfohlener Zielort

Das Plugin verwendet für jede Quelle einen eigenen, noch nicht vorhandenen Unterordner im Vault. Der Standardvorschlag lautet:

```text
<Vault>/_DocToMD/<PDF-Basisname>/
```

Beispiel:

```text
Mein-Vault/
├─ Eingänge/
│  └─ Projektbericht.pdf
└─ _DocToMD/
   └─ Projektbericht/
      ├─ Projektbericht.md
      ├─ Projektbericht.conversion.json
      └─ Projektbericht.assets/          # nur bei exportierbaren Bildern
```

Der Ordnername `_DocToMD` ist eine Empfehlung, kein von der Engine erzwungener Wert. Ein Vault darf ihn passend zu seiner eigenen Ablage umbenennen. Der Plugin-Dialog zeigt den tatsächlich gewählten vollständigen Zielpfad vor dem Start an und erlaubt dessen Änderung innerhalb des Vaults.

Der Ausgabeordner darf niemals der Vault-Stamm, `.obsidian` oder ein vorhandener allgemeiner Dokumentenordner sein. Diese Regel trennt abgeleitete Artefakte von Plugin-Konfiguration, manuellen Notes und anderen Primärquellen. Die PDF darf innerhalb oder außerhalb des Vaults liegen; sie wird von DocToMD nie verändert.

## Stabile Namen innerhalb des Ausgabeordners

DocToMD übernimmt den PDF-Basisnamen unverändert, auch bei Leerzeichen und Unicode. Für `Projektbericht.pdf` entstehen folgende Namen:

| Artefakt | Name |
| --- | --- |
| lokales Markdown | `Projektbericht.md` |
| Manifest | `Projektbericht.conversion.json` |
| Bildassets | `Projektbericht.assets/` |
| Bildbeschreibung | `Projektbericht.assets/page-NNN-figure-MM-description.md` |
| optionales Vision-Derivat | `Projektbericht.vision.md` |
| optionaler Vision-Review | `Projektbericht.vision-review.md` |
| optionales Cloud-Derivat | `Projektbericht.cloud.md` |

Das Plugin benennt diese Dateien nicht um und verschiebt keine einzelne Datei aus dem Ausgabeordner. Bild- und Markdown-Referenzen sowie Manifestpfade sind relativ zu diesem Ordner. Der maßgebliche Indexkandidat stammt aus `rag_indexing.recommended_markdown_path` im Manifest, nicht aus einer Dateinamensheuristik.

## Kollisionen und erneute Konvertierung

Für verschiedene PDFs mit gleichem Basisnamen wählt das Plugin verschiedene Zielordner, etwa `_DocToMD/Projektbericht/` und `_DocToMD/Projektbericht-2/`. Es versieht nicht die von DocToMD erzeugten Dateinamen mit eigenen Suffixen.

Für dieselbe Quelle verwendet das Plugin denselben Ausgabeordner wieder. Es bietet die Konfliktentscheidung klar an:

- `error` ist die sichere Voreinstellung und verändert keine bestehenden abgeleiteten Artefakte.
- `update` darf nur für dieselbe, im Manifest belegte Quelle verwendet werden; unveränderte Derivate können wiederverwendet und geänderte ersetzt werden.
- `overwrite` ersetzt abgeleitete Artefakte ausdrücklich, jedoch niemals die Primärquelle. Bearbeitete Bildbeschreibungs-Sidecars bleiben erhalten.

Das Plugin liest nach jedem erfolgreichen oder warnenden Lauf ausschließlich die durch die JSON-Antwort benannte Manifestdatei. Bei Fehlern, fehlendem Manifest oder nicht passendem Quellfingerabdruck öffnet es keine vermeintlich aktuelle Note.

## Aufruf durch das Plugin

Das Plugin übergibt absolute Windows-Pfade und startet DocToMD als Kindprozess. Ein lokaler Standardlauf kann so aussehen:

```powershell
"<Python-Interpreter>" "<Pfad-zu-DocToMD>\main.py" convert `
  "<Vault-Eingang>\Projektbericht.pdf" `
  --output-dir "<Vault-Ausgabe>\Projektbericht" `
  --on-conflict error `
  --json `
  --progress jsonl
```

Das Plugin setzt für `<Python-Interpreter>` den konfigurierten Python-Interpreter ein, liest JSONL-Fortschritt von `stderr` und die finale JSON-Antwort von `stdout`. Es behandelt Exit-Code `1` als fertige Konvertierung mit prüfpflichtigen Qualitätswarnungen, nicht als technischen Fehlschlag.

Ein Cloud-Lauf verlangt zusätzliche ausdrückliche Einwilligung und übernimmt weder API-Schlüssel noch Dokumentdaten in Plugin-Einstellungen. Die Vorbedingungen und die Ausgabegrenzen des Cloud-Modus bleiben durch den bestehenden CLI-Vertrag bestimmt.

## Öffnen und Indexieren

Nach Erfolg öffnet das Plugin das durch `rag_indexing.recommended_markdown_path` empfohlene Derivat, sofern dessen relativer Pfad im Ausgabeordner liegt und zugleich als Manifestartefakt geführt wird. Bei einer Empfehlung für `Projektbericht.cloud.md` darf `Projektbericht.md` nicht zusätzlich automatisch indexiert werden. Bildbeschreibungs-Notes unter `.assets` sind ein separater, ausdrücklich gewählter Indexumfang.

Qualitätsstatus und seitenbezogene Warnungen aus dem Manifest bleiben bei Vorschau und Übergabe sichtbar. Ein vorhandenes Markdown oder eine erfolgreiche Indexierung behauptet keine verlustfreie Rekonstruktion der PDF.

Siehe auch [[CLI_MANIFEST_EXAMPLE|CLI- und Manifestbeispiel]] und [[CODEXCLI_HANDOFF|Übergabe an CodexCLI]].
