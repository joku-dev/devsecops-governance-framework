# Dokumentationsabgleich nach Merge

Auslöser: PR #347: build(deps): bump the codeql group across 1 directory with 2 updates (`4f6f5bbc2614`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 2 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `.github/workflows/codeql.yml`
- `.github/workflows/viewer-ui.yml`
- `.github/workflows/workbench-ui.yml`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`
- `pipeline-baseline/templates/bamboo/README.md` → `../../../../docs/operations/adapters/portable-governance-runtime.md`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
