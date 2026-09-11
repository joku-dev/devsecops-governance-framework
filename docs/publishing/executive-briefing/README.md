# Whitepaper und Präsentation für die Geschäftsführung

Dieses Paket erläutert Nutzen, belegten Stand und eine kontrollierte Einführung
des Engineering Governance Frameworks. Es richtet sich an die Geschäftsführung
und verwendet den geprüften Quellstand `4abe88294f299d7f801c74ff0161df234960c092`
vom 11. September 2026.

## Unterlagen

- [Whitepaper als PDF](files/engineering-governance-whitepaper.pdf), acht Seiten zum Lesen und Weitergeben
- [Whitepaper als Word-Dokument](files/engineering-governance-whitepaper.docx), bearbeitbare Fassung
- [Präsentation als PowerPoint](files/engineering-governance-presentation.pptx), zwölf Folien mit Sprechernotizen und Quellen
- [Whitepaper im Browser](whitepaper.md)
- [Folieninhalt mit Sprechernotizen im Browser](presentation.md)

Das Whitepaper eignet sich als Vorabinformation. Die Präsentation verdichtet es
für einen etwa 15-minütigen Termin. Im anschließenden Gespräch lassen sich
Pilotanwendungen, Verantwortliche und verfügbare Kapazität festlegen. Die
Unterlagen schlagen einen begrenzten Pilot vor; sie erteilen keine Betriebs-,
Budget- oder Blocking-Freigabe.

Erwartete Vorteile sind als Nutzenhypothesen formuliert. Neue angenommene
Ergebnisse vom 11. September 2026 dokumentieren den betrachteten Stand; offene
Befunde und die fehlende Freigabe für neues Blocking bleiben sichtbar. Die Quellen
verweisen auf den festgehaltenen Commit beziehungsweise konkrete Workflow-Läufe.

## Pflege

Die gemeinsame redaktionelle Quelle ist [content.json](content.json). Darin stehen
Whitepaper, Folien, Sprechernotizen und Quellen. Änderungen sollen dort erfolgen,
damit die erzeugten Markdown- und Office-Fassungen zusammen aktualisiert werden.
Die beiden Formate dürfen unterschiedlich verdichten, müssen aber dieselbe
Aussage über Nutzen, Betriebsreife und Freigaben bewahren.

Die Builder liegen unter `scripts/publishing/`. Sie benötigen die dokumentierte
Codex-Artefaktumgebung mit python-docx, Artifact Tool und dem mitgelieferten
LibreOffice. Sie gehören nicht zur Laufzeit des Governance-Systems. Die normale
Repository-Validierung verlangt keinen Office-Export.

Beispielablauf aus dem Repository-Root, nachdem die absoluten Pfade der
bereitgestellten Artefaktumgebung gesetzt wurden:

```bash
"$RUNTIME_PYTHON" scripts/publishing/build_executive_whitepaper.py \
  --content docs/publishing/executive-briefing/content.json \
  --output "$PUBLICATION_OUTPUT"

"$RUNTIME_PYTHON" "$DOCUMENT_SKILL/render_docx.py" \
  "$PUBLICATION_OUTPUT/engineering-governance-whitepaper.docx" \
  --output_dir "$PUBLICATION_BUILD/whitepaper-render" --emit_pdf

"$RUNTIME_NODE" scripts/publishing/build_executive_presentation.mjs \
  docs/publishing/executive-briefing/content.json \
  "$PUBLICATION_BUILD/pptx" \
  "$PUBLICATION_BUILD/output/engineering-governance-presentation.pptx"
```

Für die Präsentation sind außerdem `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON` und
`PRESENTATION_SKILL` als Umgebungsvariablen erforderlich. `PUBLICATION_BUILD` muss
auf ein neues privates Build-Verzeichnis zeigen; der Finalizer überschreibt keine
vorhandene Ausgabe. Die Präsentationsvorschau und der Prüfbericht bleiben dort.
Das Word-Skript erzeugt auch die beiden Markdown-Fassungen neben `content.json`.

Vor der Übernahme nach `files/` alle Seiten und Folien visuell prüfen, Tabellen,
Quellen und Sprechernotizen mit `content.json` abgleichen und die endgültigen
Dateien unverändert kopieren. Ein erfolgreicher Export ersetzt keine inhaltliche
oder visuelle Prüfung. Anschließend die normale Repository-Validierung und den
strengen MkDocs-Build ausführen. Die Veröffentlichung im Repository erfolgt über
einen geprüften PR gemäß GCR-2026-054.
