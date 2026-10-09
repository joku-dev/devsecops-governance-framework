# Dokumentationsabgleich nach Merge

Auslöser: PR #253: feat(viewer): publish redacted DCR pilot snapshot (`cb1c1195192e`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 1 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `apps/governance-viewer/app.js`
- `schemas/document-consistency-public-projection.schema.json`
- `schemas/document-consistency-review-model.schema.json`
- `scripts/generate_document_consistency_review_model.py`
- `scripts/lib/document_consistency_view.py`
- `scripts/lib/viewer_app.py`
- `scripts/publish_document_consistency_projection.py`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
