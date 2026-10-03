# Wissenschaftliche PDF-Fixture und Evaluationskriterien

## Fixture

`simple-digital.pdf` wird durch `build_simple_fixture.py` ausschließlich aus selbst verfasstem ASCII-Text erzeugt. Sie enthält zwei Seiten mit einfachen Überschriften und Absätzen und darf versioniert als Basisfixture für CLI- und Konvertierungstests verwendet werden.

`scientific-two-column.pdf` wird durch `build_scientific_fixture.py` ausschließlich aus selbst verfasstem ASCII-Text erzeugt. Sie enthält keine fremden Inhalte und darf versioniert als Regressionstest verwendet werden.

Die einzelne A4-ähnliche Seite enthält:

- einen Kopfbereich mit Dokumenttitel und Seitennummer,
- zwei unabhängige Textspalten,
- die Display-Formel `p(x) = sum_i w_i * x_i / n`,
- die rechteckige Tabelle „Table 1“ mit den Zeilen `precision | 0.80` und `recall | 0.75`,
- einen sichtbaren Verweis auf „Table 1“, der im Manifest auf die Tabelle derselben Seite aufgelöst wird,
- einen Fußbereich außerhalb der Spalten.

`structure-elements.pdf` wird durch `build_structure_fixture.py` ebenfalls ausschließlich aus selbst verfasstem ASCII-Text erzeugt. Sie ergänzt die wissenschaftliche Fixture um eine einspaltige Strukturprüfung mit nummerierten Überschriften der Ebenen 1 und 2, zwei Absätzen, einer ungeordneten und einer geordneten Liste, einer einfachen rechteckigen Tabelle sowie der einzelnen Codezeile `print(42)`.

## Kriterien

| Bereich            | Prüfkriterium                                                                                                  | Aktuelle Mindestanforderung                                                   |
| ------------------ | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Rückverfolgbarkeit | Die Ausgabe enthält `doctomd:page=1`.                                                                          | Muss erfüllt sein.                                                            |
| Inhalt             | Titel, Formel, beide Tabellenwerte und Fußtext sind im Markdown auffindbar oder als konkrete Warnung sichtbar. | Muss erfüllt sein.                                                            |
| Leseordnung        | Linke und rechte Spalten dürfen nicht stillschweigend als zuverlässig geordnet gelten.                         | Bei erkannten zwei Spalten muss `MULTI_COLUMN_LAYOUT` für Seite 1 erscheinen. |
| Absatzgrenzen      | Deutliche vertikale Abstände erscheinen als getrennte Markdown-Absätze.                                        | Muss erfüllt sein.                                                            |
| Tabelle            | Rechteckige Tabellen beliebiger Spaltenzahl werden übertragen; mehrzeilige oder unklare Tabellen erzeugen eine seitenbezogene Warnung. | Muss erfüllt sein. |
| Referenzen         | Der sichtbare Verweis `Table 1` wird mit Quellseite und sicherer Zielseite im Manifest gespeichert. | Muss erfüllt sein. |
| Formel             | Die Display-Formel wird als überprüfbares LaTeX `$$p(x) = \frac{\sum_i w_i x_i}{n}$$` ausgegeben. | Muss für die unterstützte Fixtureformel erfüllt sein. |
| Kopf und Fuß       | Kopf- und Fußbereich stehen vor beziehungsweise nach dem gesamten Spalteninhalt.                               | Muss erfüllt sein.                                                            |
| Grundstruktur      | Die einspaltige Struktur-Fixture bewahrt Überschriftenebenen, Absatzgrenzen, Listen und die einfache Tabelle.   | Muss erfüllt sein.                                                            |
| Code               | Die Codezeile bleibt wörtlich im Markdown erhalten; eine sichere automatische Codeblock-Erkennung besteht nicht. | Muss erfüllt sein; fehlende Fence ist dokumentierte Grenze.                  |

## Prüfvorgehen

`tests/test_scientific_fixture_regression.py` sichert die Seitenmarkierung, Kopf- und Fußreihenfolge, die unterstützte LaTeX-Formel, den Tabelleninhalt, die Tabellenreferenz und ausschließlich die erwartete Warnung `MULTI_COLUMN_LAYOUT`. Die PDF zusätzlich vor einer visuellen Prüfung mit Poppler rendern. Anschließend die Konvertierung mit `--on-conflict error` in einen neuen temporären Ausgabeordner ausführen und Markdown sowie Manifest gegen die Kriterien prüfen. Die Fixture ersetzt keine externen wissenschaftlichen Vergleichsdokumente; diese bleiben ausschließlich ergänzende, nicht versionierte Evaluationsquellen.

`tests/test_structure_fixture_regression.py` sichert die einspaltige Struktur-Fixture. Sie bestätigt, dass die Codezeile nicht verloren geht, und hält die fehlende automatische Fence-Erkennung ausdrücklich als aktuelle Grenze fest.
