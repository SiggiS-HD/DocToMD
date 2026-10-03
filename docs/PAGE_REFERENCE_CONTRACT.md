# Vertrag für Seitenreferenzen

DocToMD behandelt die PDF-Seite als kleinste stabile Herkunftseinheit. Dieser Vertrag beschreibt, wie Textabschnitte, Tabellen und Bildassets auf diese Einheit zurückverweisen. Er ergänzt [[PROJECT]], [[ENGINEERING_NOTES]] und [[STRUCTURE_QUALITY_RULES|die Strukturqualitätsregeln]].

## Textabschnitte

Jede extrahierte PDF-Seite beginnt im Markdown mit genau einem Marker `<!-- doctomd:page=N -->`. Überschriften, Absätze, Listen und lokal rekonstruierte Display-Formeln, die danach bis zum nächsten Seitenmarker stehen, stammen von Seite `N`.

Das Manifest enthält für jeden strukturierten Textblock einen Eintrag `artifacts.content_references` mit `kind: "text"` und derselben einsbasierten Seite. Abschnitte besitzen derzeit keine eigene stabile Block-ID. Ein Aufrufer kann daher die Herkunft jedes Abschnitts über seine umgebende Markdown-Seite und den zugehörigen Manifesteintrag prüfen, aber nicht über einen zusätzlichen Absatzanker adressieren.

## Tabellen

Jede akzeptierte Tabelle erhält einen unmittelbaren Markdown-Marker der Form `<!-- doctomd:table=page-NNN-table-MM page=N -->`. Der Wert `page=N` muss auf einen vorhandenen Seitenmarker derselben Markdown-Datei zeigen. Das Manifest führt zusätzlich einen `content_references`-Eintrag mit `kind: "table"` und Seite `N`.

Erkennt DocToMD einen sichtbaren Tabellenverweis wie `Table 1`, enthält `artifacts.references` Quellseite, Zielseite und die stabile Tabellen-ID. Ist kein sicheres Ziel bestimmbar, bleibt der Verweis im Text erhalten und `UNRESOLVED_DOCUMENT_REFERENCE` wird auf der Quellseite gespeichert.

## Bildassets

Jedes exportierte Bild besitzt im Manifest `artifacts.assets` eine stabile Asset-ID, einen relativen Pfad und eine Seite. Die Haupt-Note enthält auf derselben Seite den Marker `<!-- doctomd:asset=… page=N -->` sowie eine Markdown-Bildreferenz auf genau diesen relativen Pfad. Eine optionale Bildbeschreibungs-Note liegt neben dem Bildasset; sie übernimmt dieselbe Seitenherkunft über die Asset-ID, nicht über eine eigene PDF-Seitenkopie.

Nicht exportierbare oder strukturell unsichere Bilder erhalten kein erfundenes Asset. Stattdessen bleiben die jeweiligen Bildwarnungen im Manifest sichtbar.

## Prüfnachweis

Die aktuelle wissenschaftliche Fixture enthält einen Seitenmarker, 15 Textreferenzen, einen Tabellenmarker und einen aufgelösten Tabellenverweis; alle verweisen auf Seite 1. Im vorhandenen Gerätehandbuch-Derivat wurden fünf Bildassets geprüft; jedes stimmt zwischen Manifestseite, Asset-Marker und Markdown-Pfad überein. Die automatischen Basisprüfungen liegen in `tests/test_markdown_writer.py`, `tests/test_reference_analysis.py`, `tests/test_image_export.py` und `tests/test_scientific_fixture_regression.py`.
