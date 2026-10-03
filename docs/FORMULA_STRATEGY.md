# Formelstrategie für wissenschaftliche PDFs

## Ziel

DocToMD gibt eine Formel nur dann als LaTeX aus, wenn ihre Rekonstruktion lokal und deterministisch überprüfbar ist. Das Ergebnis verwendet für Display-Formeln den Obsidian-kompatiblen Delimiter `$$...$$` und für Inline-Formeln `$...$`; beide bleiben mit ihrem Seitenmarker verknüpft.

## Festgelegte Verarbeitung

1. Der Textlayer liefert zunächst einen Formelkandidaten mit Seite und unverändertem Quelltext.
2. Der lokale, versionierte Parser unterstützt derzeit die vollständig prüfbare Summenbruch-Grammatik aus ASCII-Bezeichnern, Funktionsaufruf, Indizes, `=`, `*`, `/` und `sum`.
3. Der Parser erzeugt LaTeX nur für vollständig geparste Kandidaten. Für die wissenschaftliche Fixture wird `p(x) = sum_i w_i * x_i / n` als `$$p(x) = \frac{\sum_i w_i x_i}{n}$$` ausgegeben.
4. Nicht vollständig prüfbare, eigenständige Gleichungskandidaten verbleiben unverändert im Markdown und erhalten die seitenbezogene Warnung `FORMULA_NOT_RECONSTRUCTED`.

## Abgrenzung

Es gibt keine Heuristik, die beliebige mathematische PDF-Zeichenfolgen als LaTeX ausgibt. Insbesondere Matrizen, mehrzeilige Gleichungen, Wurzelzeichen, Spezialzeichen, über- oder untergesetzte Elemente und schlecht dekodierte Glyphen fallen nicht in die lokale Basisgrammatik.

Ein späterer, ausdrücklich aktivierter Vision-Provider darf für diese Fälle nur strukturierte Vorschläge mit Konfidenz und Seitenbezug liefern. DocToMD validiert sie lokal; ohne erfolgreiche Validierung bleibt die Formel unverändert und die Warnung sichtbar. Die lokale Kandidatenerkennung betrachtet bewusst keine normalen Fließtextabsätze mit Gleichheitszeichen als Formel.

## Validierung

Jede unterstützte Grammatikform benötigt einen Unit-Test mit erwarteter LaTeX-Ausgabe. Für die Fixture muss zusätzlich die gerenderte Originalseite visuell prüfen lassen, dass Zähler, Nenner, Operatoren und Indizes dem LaTeX entsprechen. Die Ausgabe einer LaTeX-Zeichenfolge allein gilt nicht als Qualitätsnachweis.
