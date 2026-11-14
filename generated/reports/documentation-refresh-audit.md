# Dokumentationsabgleich nach Merge

Auslöser: PR #364: feat: Consumer-Ergebnisse auf der VM sammeln (Schattenbetrieb) (`edf16239e927`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 1 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `.github/workflows/intake-governance-result.yml`
- `.github/workflows/vm-installation.yml`
- `scripts/consumer_intake.py`
- `scripts/intake_github_actions_run.py`
- `scripts/lib/consumer_github.py`
- `scripts/lib/consumer_intake.py`
- `scripts/lib/consumer_intake_store.py`
- `scripts/lib/consumer_publisher.py`
- `scripts/lib/consumer_view.py`
- `scripts/lib/private_credentials.py`
- `scripts/serve_governance_workbench.py`
- `scripts/workbench/app.js`
- `scripts/workbench/consumer-view.js`
- `scripts/workbench/index.html`
- `scripts/workbench/workspace-navigation.js`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
