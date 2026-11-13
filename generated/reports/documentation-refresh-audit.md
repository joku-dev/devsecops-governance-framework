# Dokumentationsabgleich nach Merge

Auslöser: PR #355: feat(agents): integrate reviewed review tooling and offline evaluation (`50c684e7d0a9`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 1 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `.agents/evaluations/README.md`
- `.agents/evaluations/review-quality-v1.json`
- `.agents/execution-contract.yaml`
- `.agents/providers/codex/README.md`
- `.agents/review-protocol.yaml`
- `.agents/routing/governance-agent-routing.yaml`
- `.github/workflows/agent-review-status.yml`
- `schemas/agent-review-receipt.schema.json`
- `scripts/evaluate_agent_reviews.py`
- `scripts/lib/agent_codex.py`
- `scripts/lib/agent_evaluation.py`
- `scripts/lib/agent_execution.py`
- `scripts/lib/agent_receipts.py`
- `scripts/lib/agent_review.py`
- `scripts/lib/agent_review_status.py`
- `scripts/lib/agent_routing.py`
- `scripts/record_agent_review.py`
- `scripts/report_agent_review_status.py`
- `scripts/run_agent_reviews.py`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
