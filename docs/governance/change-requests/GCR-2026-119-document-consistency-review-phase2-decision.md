# GCR-2026-119: Phase 2 — Entscheidungsrahmen für den semantischen Pilot

## Anfrage und Einordnung

Bereite nach der Annahme des begrenzten Phase-1-Strukturkerns die Entscheidung
für einen belegbaren semantischen Pilot vor. Die Planung verwendet weiterhin
nur die registrierten bereinigten Auszüge `DSCB-STD-REQ-001` und
`PRA-STD-REQ-001` sowie synthetische Fixtures. Sie genehmigt noch keinen
Providerlauf.

| Feld | Wert |
| --- | --- |
| Artefakte | Phase-2-Entscheidungsbrief, aktualisierte Navigation und Statusgrenzen |
| Artefakttyp | Planung und Freigabevorbereitung |
| Bezugsentscheidung | Angenommene Phase 0 und angenommener begrenzter Phase-1-Strukturkern aus GCR-2026-118 |
| Vorgeschlagene Pilotquellen | `DSCB-STD-REQ-001`, `PRA-STD-REQ-001`, benannte synthetische Fixtures |
| Lokale Zusatzdateien | ausgeschlossen, unregistriert und nicht autorisiert |
| Semantischer Live-Lauf | `not_run`; Provider-/Aufbewahrungstor offen |
| Betriebsart | manuell, report-only |
| Viewer / Veröffentlichung | nicht enthalten |
| Release- oder Baseline-Auswirkung | keine |
| Status | zur Abnahme vorbereitet; Implementierungs- und Live-Lauf-Freigabe ausstehend |

## Vorgeschlagene Entscheidung

1. Der erste semantische Pilot bleibt auf die zwei bereits in Phase 1
   verwendeten requirements-only Auszüge und synthetische Testfälle begrenzt.
2. Die fünf lokalen, unregistrierten Dateien dürfen weder gelesen, kopiert,
   manifestiert noch an einen Provider übertragen werden.
3. Die technische Phase-2-Infrastruktur darf providerneutral und mit
   synthetischen Antworten vorbereitet werden.
4. Ein echter Modelllauf benötigt eine separate, konkrete Bestätigung von
   Provider, Modellkennung, Datenfluss, Provider-/lokaler Aufbewahrung,
   Zitatgrenze, Reviewern und Kosten-/Kontextgrenzen.
5. Findings bleiben unbestätigt, bis ihr Beleg deterministisch validiert und
   ihre Interpretation menschlich bewertet wurde.
6. Der Pilot bleibt report-only und ändert keine Quelle, Autorität, Control,
   Policy, Architekturregel, Baseline oder Consumer-Konfiguration.

Die vollständigen vorgeschlagenen Betriebswerte und das Abnahmetor stehen im
[Phase-2-Entscheidungsbrief](../../operations/planning/document-consistency-review-phase2-decision-brief.md).

## Betroffene und bewusst unveränderte Artefakte

| Bereich | Entscheidung |
| --- | --- |
| `docs/operations/planning/` | Entscheidungsbrief und Statusgrenze ergänzen |
| `docs/governance/change-requests/` | diesen GCR ergänzen |
| `docs/ai-index.md` | Phase-2-Navigation ergänzen |
| `model/documents/source-document-register.yaml` | unverändert; keine Promotion |
| `model/controls/`, `model/traceability/`, `architecture/`, `policies/opa/` | unverändert; keine fachliche Derivation |
| `schemas/`, `scripts/`, `tests/` | erst im separaten Implementierungs-PR |
| `releases/`, `docs/releases/` | unverändert; keine Releaseauswirkung |
| Viewer und Statusindizes | unverändert |
| Lifecycle Operating Acceptance | fingerprintgeschützte Dateien unverändert |

## Offene Entscheidungen

Die Planung ist vollständig genug für Review und technische Aufwandsplanung.
Folgende Werte bleiben absichtlich offen und blockieren einen Live-Lauf:

- die tatsächlich zugelassene Provider-/Kontokonfiguration;
- die vom Provider gemeldete Modellkennung und Laufparameter;
- die geltende Provideraufbewahrung und die Behandlung der Rohantwort;
- die benannten menschlichen Reviewer für quellenübergreifende Findings;
- Kosten- und Kontextgrenzen des ersten echten Laufs.

Offene Werte dürfen nicht aus allgemeinen Providerannahmen, Owner-Routing oder
früheren Freigaben abgeleitet werden.

## Validierung und Abnahme

Dieser Änderungssatz ändert nur Planungs- und Navigationsdokumente. Er muss die
vollständige Repository-Validierung und den strikten Dokumentationsbuild
bestehen. Seine Annahme bestätigt den Entscheidungsrahmen, aber weder die
Phase-2-Implementierung noch einen semantischen Providerlauf.

