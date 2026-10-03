# Regeln für Strukturqualität bei wissenschaftlichen PDFs

Diese Regeln bestimmen, wann DocToMD PDF-Struktur lokal als Markdown ableiten darf und wann stattdessen ein seitenbezogener Qualitätsbefund nötig ist. Sie ergänzen [[PROJECT]] und die Entscheidungen in [[ENGINEERING_NOTES]].

## Mehrspaltige Seiten

Die Extraktion erkennt eine Zweispaltenseite nur, wenn auf beiden Seiten der Seitenmitte mindestens drei vertikal überlappende Textzeilen vorliegen. Kopf- und Fußbereich werden vor beziehungsweise nach dem Spalteninhalt ausgegeben. Der Fließtext der linken Spalte wird vor dem der rechten Spalte gelesen; diese Reihenfolge ist eine nachvollziehbare geometrische Heuristik, keine Zusage vollständiger semantischer Lesereihenfolge.

Für jede so erkannte Seite erzeugt DocToMD die seitenbezogene Manifestwarnung `MULTI_COLUMN_LAYOUT`. Sie bleibt auch dann bestehen, wenn das erzeugte Markdown plausibel wirkt. Bei aktiviertem Vision-Modus `auto` ist die Seite ein zulässiger Kandidat für einen überprüfbaren Vorschlag. Der lokale Standardpfad bleibt netzwerkfrei; die Warnung selbst verändert oder verwirft keinen Text.

Uneindeutige Spaltenlayouts, Randnotizen, schwebende Abbildungen oder Inhalte, die über beide Spalten reichen, werden nicht als sicher rekonstruierte Absatz- oder Überschriftenstruktur ausgegeben. Sie bleiben in der geometrisch extrahierten Reihenfolge. Eine weitergehende Rekonstruktion ist erst nach einer gesonderten Erweiterung mit repräsentativen Fixtures und seitenbezogener Validierung zulässig.

## Fußnoten

PDF-Fußnoten besitzen keinen stabilen, allgemein extrahierbaren Syntax. Eine tiefgestellte Ziffer, ein Sternchen oder ein am Seitenende stehender Text reicht nicht aus, um eine Markdown-Fußnote mit sicherem Ziel zu erzeugen. DocToMD schreibt deshalb aus solchen visuellen Hinweisen keine neuen `[^n]`-Marker und keine Fußnotendefinitionen.

Ist im extrahierten Text bereits explizite Markdown-Fußnotensyntax wie `[^2]` und eine zugehörige Definition `[^2]: …` vorhanden, speichert die Referenzanalyse Quell- und Zielseite. Fehlt die Definition, bleibt der sichtbare Marker unverändert und es entsteht die seitenbezogene Warnung `UNRESOLVED_DOCUMENT_REFERENCE`. Nummern in eckigen Klammern werden weiterhin nur als Zitationskandidaten behandelt; ohne klaren, überprüfbaren Nachweis darf daraus keine Fußnote abgeleitet werden.

Eine künftige Fußnoten-Erweiterung benötigt eine eigene rechtlich unbedenkliche Fixture mit Marker, Fußnotenbereich und mindestens einer konkurrierenden Zitation. Sie muss Herkunftsseite, Zielseite und den vollständigen Fußnotentext prüfen, bevor sie Markdown-Fußnoten erzeugt.

## Formeln

Eine eigenständige Formel wird nur dann als Display-LaTeX mit `$$…$$` ausgegeben, wenn sie vollständig der lokal implementierten, überprüfbaren Summenbruch-Grammatik entspricht. Das Ergebnis behält seine Originalseite. Die unterstützte Fixtureformel ist `p(x) = sum_i w_i * x_i / n` und wird als `$$p(x) = \frac{\sum_i w_i x_i}{n}$$` geschrieben.

Ein kurzer, eigenständiger Gleichungskandidat außerhalb dieser Grammatik bleibt unverändert als Quelltext erhalten und erzeugt `FORMULA_NOT_RECONSTRUCTED` mit Seitenbezug. Gleichheitszeichen im Fließtext gelten nicht als Formel. Komplexe Inline-Formeln, Matrizen, mehrzeilige Ausdrücke und Formeln mit nicht dekodierbaren Zeichen werden nicht geraten. Bei aktivem Vision-Modus `auto` kann eine Seite mit `FORMULA_NOT_RECONSTRUCTED` für einen lokal validierten Vorschlag ausgewählt werden; ohne diesen Opt-in bleibt ausschließlich der unveränderte lokale Text samt Warnung erhalten.

## Prüfkriterien

Die Regeln werden durch die visuell geprüfte `scientific-two-column.pdf`, durch `tests/test_scientific_fixture_regression.py`, durch `tests/test_formula_parser.py` sowie durch `tests/test_reference_analysis.py` abgesichert. Reale frühere Derivate des Tokenizer- und SentencePiece-Papers bestätigen, dass Mehrspaltenwarnungen im Manifest pro betroffener Seite auftreten. Diese Derivate sind Evaluationsreferenzen, keine Behauptung verlustfreier Rekonstruktion.
