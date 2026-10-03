# Evaluation strukturorientierten Chunkings

Diese Evaluation prüft, ob ein externer Markdown-Indexer die von DocToMD erzeugte Struktur als Chunk-Grenzen nutzen kann. Sie implementiert keinen Chunker, erzeugt keinen RAG-Index und misst keine Retrieval-Qualität. Die Entscheidung über Tokenisierung, Embeddings, Überlappung und Suche verbleibt bei CodexCLI oder einem anderen konsumierenden System.

## Referenzregeln für konsumierende Chunker

Ein Chunker soll den jeweils aktuellen Seitenmarker als Herkunftsmetadatum übernehmen und bei jedem neuen `<!-- doctomd:page=N -->` einen neuen Chunk beginnen. Überschriften eröffnen einen neuen Abschnitt; der vollständige aktive Überschriftenpfad bleibt als Chunk-Kontext erhalten. Absätze und Listen sind bevorzugte weiche Grenzen innerhalb eines Abschnitts.

GFM-Tabellen, Display-Formeln und zusammenhängende eingerückte oder gefencete Codepassagen sind atomar: Sie dürfen nicht in der Mitte getrennt werden. Ist ein solcher Strukturblock größer als das Limit eines konkreten Indexers, bleibt er als gekennzeichneter Überlängen-Chunk erhalten oder wird dort mit einer systemspezifischen, dokumentierten Strategie verarbeitet. Ein blindes Zeichenlimit innerhalb einer Tabellenzeile, Formel oder Codezeile ist nicht zulässig.

Die DocToMD-Qualitätswarnungen gehören als Metadaten zum Chunking-Lauf, nicht als fachliche Aussage in den Chunk-Text. Insbesondere bei `MULTI_COLUMN_LAYOUT`, OCR-Unsicherheit oder nicht aufgelösten Referenzen darf der Indexer keine verlustfreie Reihenfolge oder Referenzauflösung behaupten.

## Geprüfte Derivate

| Fall | Geprüfte Strukturen | Ergebnis für Chunk-Grenzen |
| --- | --- | --- |
| Versionierte `structure-elements.pdf` | Seitenmarker, H1/H2, getrennte Absätze, geordnete und ungeordnete Liste, einfache Tabelle, Codezeile | Überschriften und Leerzeilen erlauben nachvollziehbare Abschnitts- und Absatzgrenzen. Die Tabelle bleibt ein geschlossener Block. `print(42)` ist nur als normaler Absatz erhalten und darf nicht fälschlich als sicherer Codeblock behandelt werden. |
| `SentencePiece_D18-2012.cloud.md` | sechs Seitenmarker, 16 Überschriften, Listen, eingerückte Codepassagen, eine Display-Formel und zwei GFM-Tabellen | Die Struktur ermöglicht Abschnitte mit Überschriftenkontext und Seitenherkunft. Die Tabellen auf den Originalseiten 5 und 6 bleiben als jeweils geschlossene GFM-Tabellen samt Caption erhalten; die Formel und die Codepassagen können atomar bleiben. |

Die Satzstruktur des Cloud-Derivats wurde gegen die visuell gerenderten Originalseiten 5 und 6 des SentencePiece-Papers geprüft. Auf Seite 5 entsprechen die Zeilen der GFM-Tabelle „Translation Results“ der sichtbaren Tabelle 1; auf Seite 6 entspricht die zweite GFM-Tabelle der sichtbaren Tabelle 2. Damit muss ein Chunker weder Tabellenzellen zerlegen noch Tabelleninhalt aus der PDF neu ableiten.

## Befund und Grenzen

Die vorhandenen Derivate erfüllen die strukturelle Mindestvoraussetzung für einen Markdown-orientierten Indexer: Herkunft auf Seitenebene sowie Überschriften-, Absatz-, Listen-, Tabellen- und Formelgrenzen sind verfügbar. Das SentencePiece-Original ist mehrspaltig. Seine lokale Konvertierung enthält deshalb seitenbezogene `MULTI_COLUMN_LAYOUT`-Warnungen; diese Grenze bleibt auch dann relevant, wenn das separat erzeugte, technisch validierte Cloud-Derivat wegen besser erhaltener Struktur für die Indexierung empfohlen wird.

Die aktuelle lokale Pipeline erkennt typografischen Code nicht verlässlich genug für eine automatische Fence-Erzeugung. Ein konsumierender Chunker darf eingerückte Cloud-Codepassagen als zusammenhängend behandeln, darf aber eine bloße einzelne Codezeile im lokalen Derivat nicht ohne zusätzliche, dokumentierte Regel in einen Code-Chunk umdeuten. Ebenso bleiben unaufgelöste Bild-, Tabellen- und Zitationsreferenzen Warnungen, keine Indexfakten.

Die konkrete Auswahl des Derivats erfolgt weiterhin ausschließlich über `rag_indexing.recommended_markdown_path`, wie in [[RAG_INDEXING_RECOMMENDATION|der Indexempfehlung]] beschrieben. Der Seitenbezug folgt [[PAGE_REFERENCE_CONTRACT|dem Vertrag für Seitenreferenzen]]; die Übergabe an CodexCLI steht in [[CODEXCLI_HANDOFF|der Übergabevereinbarung]].
