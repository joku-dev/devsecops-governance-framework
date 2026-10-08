# GCR-2026-131: Document Consistency Review Rollout Readiness

## Entscheidung

Die nach den PRs #230 bis #233 verfügbare Evidenz wird als
`limited_pilot_ready` bewertet. Diese Stufe erlaubt ausschließlich weitere,
jeweils separat genehmigte report-only Piloten. Der produktive Rollout bleibt
`pending`.

## Änderung

- neue, additive Rolloutentscheidung v2 mit getrenntem Readiness- und
  Produktionsstatus;
- Kriterienbewertung `met`, `partial` oder `open`;
- SHA-256-gebundene Evidenzreferenzen;
- technische Invarianten für Einzelfreigabe, deaktivierte Automatisierung,
  report-only und ausgeschlossene Veröffentlichung;
- Statusbericht und Management-Kurzfassung;
- Validator- und Testanpassung.

Die historische v1-Entscheidung und das hashgebundene Phase-4-Candidate-Paket
bleiben unverändert als Nachweis des damaligen Infrastrukturstands erhalten.

## Governance-Auswirkung

Die Änderung genehmigt keinen neuen Providerlauf, keine Veröffentlichung, kein
Blocking und keinen produktiven Rollout. Quellen, Controls, Architekturmarker,
OPA-Regeln, Releases, Baselines und Consumer-Repositories bleiben unverändert.

## Rollen

- Governance Analyst: Kriterien und Entscheidungsgrenzen.
- Repo Steward: Schema, Hashbindungen, Tests und Commit-Reife.
- Maintainer: Beauftragung der Readiness-Bewertung; jeder spätere Lauf bleibt
  separat freigabepflichtig.

