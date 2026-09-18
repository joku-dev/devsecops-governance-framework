# GCR-2026-097: Viewer CodeQL Data-Flow Hardening

## Intent

Der erste CodeQL-Lauf mit JavaScript-Abdeckung meldete 16 potenzielle
DOM-XSS-Datenflüsse im Governance Workspace. Dieser Change bewertet die
vollständigen SARIF-Pfade, beseitigt die gemeinsame Zustandsstruktur als
Ursache und erweitert die Browser-Angriffstests.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Viewer-Zustandsgrenze, XSS-Regressionstests und Sicherheitsbewertung |
| Type | security hardening, test and documentation |
| Target | `apps/governance-viewer/`, `generated/viewer/app/`, `tests/`, `docs/` |
| Owner | Governance Platform Lead |
| Source Document Intake required | no |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Repository enforcement impact | CodeQL-Abdeckung bleibt unverändert aktiv |
| Release impact | none |

## Finding And Decision

CodeQL meldete acht Quell-Sinks und dieselben acht Stellen in der generierten
Viewer-Kopie als `js/xss-through-dom`. Alle SARIF-Pfade begannen bei einem
Filterfeld und liefen über das globale Objekt, das zugleich die geladenen
Berichtsdaten enthielt. Die Eingabe wurde nur als Such- oder Auswahlkriterium
verwendet; alle angezeigten Berichtsfelder durchlaufen kontextspezifische
HTML-Maskierung, und URLs werden komponentenweise codiert.

Die Zustandsgrenze wird trotzdem strukturell gehärtet: `uiState` enthält nur
vom Browser veränderbare Filter- und Seitendaten; `dataModel` enthält nur das
validierte, geladene Berichtsmodell. Diese Trennung macht den tatsächlichen
Trust Boundary im Code und für die statische Analyse eindeutig.

## Validation Plan

- [x] vollständige SARIF-Datenflüsse aller 16 Alerts geprüft
- [x] Unit-Regression schützt die Trennung von UI-Zustand und Datenmodell
- [x] Browser-Angriffstest für gespeicherte HTML-Payload und passenden Filter
- [x] Browser-Angriffstest für hostile Repository-Suche und URL-Fragment
- [x] `./scripts/validate_all.sh` (`589` tests passed)
- [x] CodeQL-Pull-Request-Lauf `35305352610` ohne offenen `js/xss-through-dom`-Befund
- [ ] GitHub-Alert-Readback nach Mainline-Lauf

## Release Decision

Es ist kein Baseline-Release erforderlich. Der Change betrifft die
Viewer-Implementierung und ihre Sicherheitsprüfung; Governance-Modelle,
Ergebnisschemas und Consumer-Enforcement bleiben unverändert.
