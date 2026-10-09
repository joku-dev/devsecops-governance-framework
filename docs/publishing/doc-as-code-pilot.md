---
id: DOC-AS-CODE-PILOT-001
title: Git-native Dokumentation und Veröffentlichung
lang: de-DE
status: pilot
publication_class: explanatory
source_of_truth: markdown
export_formats:
  - html
  - docx
  - pdf
---

# Git-native Dokumentation und Veröffentlichung

## Zweck

Dieser Pilot zeigt, wie ein Dokument ausschließlich in Git gepflegt und für
unterschiedliche Zielgruppen als Website, Word-Datei und PDF ausgegeben werden
kann. Der Markdown-Text in diesem Verzeichnis ist die bearbeitbare Quelle. Die
Exportdateien sind abgeleitete Publikationen.

## So ist die Architektur aufgebaut

| Ebene | Verantwortung | Maßgebliche Ablage |
|---|---|---|
| Quelle | Inhalt, Metadaten, Änderungen und Reviews | Markdown in `docs/publishing/` |
| Website | Navigation und lesbare HTML-Seite | MkDocs aus denselben Git-Quellen |
| Exporte | Standalone HTML, Word und PDF | Pandoc Build-Ausgabe |
| Herkunftsnachweis | Quellhash, Commit, Werkzeugversion und Exporthashes | `publication-provenance.json` im Build |
| Freigabe | Fachliche, normative und Veröffentlichungsentscheidung | Pull Request und anwendbarer Governance-Prozess |

Der Build verwendet Pandoc 3.12 sowie XeLaTeX für PDF. Version und Binärhash
von Pandoc sind in der CI-Konfiguration fixiert. Fehlende Werkzeuge oder
abweichende Versionen führen zu einem sichtbaren Fehler; ein Format wird nicht
still übersprungen.

## Arbeitsablauf

1. Autorinnen und Autoren ändern Markdown, Links und die Metadaten im Pull
   Request.
2. Die PR-Automation erzeugt HTML, DOCX, PDF und den Herkunftsnachweis als
   herunterladbares Review-Artefakt.
3. Reviewer prüfen sowohl den Inhalt als auch den gerenderten Seitenumbruch und
   die Lesbarkeit der Exporte.
4. Nach dem Merge erzeugt der Pages-Build die Downloads aus dem Merge-Commit
   und verlinkt sie bei der veröffentlichten HTML-Seite.

Die Downloads erscheinen auf der veröffentlichten Pilotseite als HTML-, Word-
und PDF-Dateien. Das PR-Artefakt enthält zusätzlich das Provenienzmanifest.

## Lokal bauen

Der Renderer erwartet Pandoc 3.12 und XeLaTeX. Nach Installation dieser
Werkzeuge erzeugt der folgende Befehl alle drei Formate und das
Provenienzmanifest unter `build/doc-as-code/`:

```bash
python3 doc-as-code/scripts/build_publication.py
```

CI übergibt außerdem das Pandoc-Releasearchiv, prüft seinen SHA-256 und hält
diesen Hash im Provenienzmanifest fest.

Die Downloads werden nicht zusätzlich eingecheckt. So gibt es nur eine
editierbare Quelle. Das Provenienzmanifest ermöglicht die Zuordnung jeder
veröffentlichten Datei zu genau dieser Quelle und diesem Build.

## Grenzen und Dokumentautorität

Der Export ändert weder die Autorität noch den Status des Textes. Ein als
`explanatory` klassifizierter Text wird durch Word oder PDF nicht zu einem
Standard. Inhalte, die Policy, verbindliche Controls, Architekturvorgaben oder
Baseline-Verhalten festlegen, brauchen weiterhin eine Governance-Entscheidung.

Offizielle externe Standards und andere Quelldokumente bleiben im
Source-Document-Intake. Kontrollmodelle, Policies, Schemas und Evidence-Verträge
bleiben in ihren bestehenden strukturierten Quellen. Für sie sind generierte
Dokumente Ansichten, keine manuell gepflegten Zweitquellen.

## Pilotumfang

Dieser eine erklärende Text belegt den Exportpfad. Er führt keine
Modell-zu-Dokument-Generierung, Quellenpromotion, neue Baseline, automatische
Normfreigabe oder zusätzliche Enforcement-Regel ein. Ein gebrandetes
Word-Referenztemplate, mehrsprachige Ausgaben und Zugänglichkeitszertifizierung
werden anhand des Review-Ergebnisses separat entschieden.
