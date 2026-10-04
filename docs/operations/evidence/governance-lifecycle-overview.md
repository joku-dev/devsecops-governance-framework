# Closed-Loop Governance: Lesekarte und Szenarioübersicht

## Gesamtüberblick und Geltungsgrenzen

Dokumentationsabgleich: **3. Oktober 2026**, Quellstand `46b33429`.
Closed-Loop Governance verbindet einen verifizierten Befund mit einer gebundenen
Entscheidung, dokumentierter Bearbeitung, neuer Evidenz und einer gesonderten
Abschlussentscheidung. Ein grüner Scanner oder ein erledigtes Ticket allein
schließt keinen Governance-Fall. Die gespeicherte Historie bleibt erhalten;
ein späterer zulässiger neuer Fehler kann einen abgeschlossenen Fall wieder öffnen.

Die vorhandene Dokumentation ist auf technische Verträge, Szenarien und
Betriebsleitfäden verteilt. Diese Lesekarte führt sie zusammen; sie ersetzt
keinen freigegebenen Vertrag und erweitert keine Betriebsabnahme.

| Ebene | Implementierter Umfang | Nicht daraus abzuleiten |
|---|---|---|
| Kernel und synthetische Szenarien | Zustandsprojektion, Konfliktquarantäne, Entscheidungen, Bearbeitung, Abschluss/Wiederöffnung und Ausnahme-Szenarien; reproduzierbare lokale Tests | Synthetische Daten sind keine Live-Annahme, echte Freigabe oder produktive Waiver-Autorität |
| Zentraler GitHub-Pilot | Persönlich abgenommener manueller GRS-002-Report-only-Scope für dieses Repository/main; eigene Receipts und Aktionshistorie | Keine generelle Freigabe anderer Regeln, Consumer oder kontinuierlicher Überwachung |
| Separater Consumer-Pilot | Persönlich abgenommener manueller `operation_readiness`-Scope für `governance-framework-demo-consumer`; eigene Verträge, Ledger und unabhängiger Guard | Keine Produktionsreife, automatische Behebung, neue Blocking-Autorität oder Portfolio-Freigabe |

## End-to-End-Ablauf

| Schritt | Nachweis und Wirkung |
|---|---|
| 1. Beobachten und prüfen | Quelle, Run, Commit, Baseline, Artefakte und Regelumfang prüfen; nur zulässige Beobachtungen übernehmen. Konflikte nicht als saubere Evidenz behandeln. |
| 2. Befund aufnehmen | Akzeptierter FAIL erzeugt/aktualisiert den Fall; identische Wiederzustellung erzeugt keine zusätzliche Wirkung. |
| 3. Entscheidung binden | Zuständige Person gibt im definierten Kanal eine Erklärung ab, gebunden an Antrag, Inhalt, Scope und Zustandsrevision. Automation darf diese Erklärung nicht ersetzen. |
| 4. Bearbeitung dokumentieren | Plan und persönlich bestätigte Fortschritte (`in_progress`, `completed`) erfassen. Umsetzung ist kein automatisch autorisierter Remediation-Executor. |
| 5. Neu verifizieren | Frische zulässige PASS-Evidenz nach abgeschlossener Bearbeitung prüfen; ein Gesamt-PASS außerhalb der betroffenen Regel genügt nicht. |
| 6. Gesondert abschließen | Eigene persönliche Abschlussentscheidung, passende Revision und vollständige Evidenzkette prüfen; erst dann `closed` projizieren. |
| 7. Später erneut beobachten | Neuer zulässiger FAIL kann wieder öffnen. Historische Closures und alte/verspätete Beobachtungen werden nicht gelöscht. Die Piloten beobachten nicht kontinuierlich. |

## Dokumentationspfad

| Frage | Maßgebliche Dokumentation |
|---|---|
| Welche Verträge und Identitäten gelten? | [CLG-01 Verträge](governance-lifecycle-contract.md), [CLG-02 Kernel](governance-lifecycle-kernel.md) |
| Wie funktionieren Entscheidung und Bearbeitung? | [CLG-03 Entscheidungen](governance-lifecycle-decisions.md) |
| Wann sind Abschluss und Wiederöffnung zulässig? | [CLG-04 Closure](governance-lifecycle-closure.md), [synthetisches End-to-End-Runbook](../../demos/demo-governance-lifecycle-pilot.md) |
| Wie sind Ausnahmen von erfolgreicher Behebung getrennt? | [Ausnahme-Szenarien](governance-lifecycle-exceptions.md); kein aktiver Live-Waiver-Scope |
| Wie wird persönliche Zustimmung verifiziert? | [Persönlicher Kanal](governance-lifecycle-personal-channel.md), [gebundene Aktionsfreigaben](governance-lifecycle-action-consent.md) |
| Wie kommen echte Quellen in den Pilot? | [Dauerhafter Intake](governance-lifecycle-durable-pilot-intake.md), [Live-Evidence-Preflight](governance-lifecycle-live-evidence-preflight.md) |
| Welcher Betrieb ist tatsächlich abgenommen? | [Aktueller Pilotstatus](../status/governance-lifecycle-current-state.md), [zentraler Betriebsleitfaden](governance-lifecycle-live-operation.md), [separater Consumer-Betriebsleitfaden](consumer-lifecycle-operation.md) |
| Wo steht der reale Consumer-Fall? | [Fallchronologie](consumer-lifecycle-operation-readiness.md), `status/governance-consumer-lifecycle.json`, `generated/reports/governance-consumer-lifecycle.md` |
| Wie werden Nachweise und Ansichten eingeordnet? | [Evidence Trust](evidence-trust-model.md), [Szenario-Viewer](governance-lifecycle-viewer.md), [Governance Workspace](../guides/governance-viewer-app.md) |
| Was bleibt Ausbauplanung? | [Closed-Loop-Implementierungsplan](../planning/closed-loop-governance-implementation-plan.md); Planung ist keine Betriebsfreigabe |

## Übernommener Consumer-Stand und Validierung

Die Consumer-Projektion vom `2026-10-03T10:58:04Z` weist wirksame Betriebsabnahme,
`finding_state: closed`, drei Receipts und vier Aktionsdatensätze aus. Dies ist
eine datierte Beschreibung des übernommenen Ledgers, kein neu erzeugter Nachweis.
Der zentrale GRS-002-Pilot und die synthetischen Szenarien behalten ihre eigenen
Statusdateien und dürfen nicht zu einem gemeinsamen Compliance-Score addiert werden.

Vor Änderungen: Betriebsabnahme-Manifeste und aktuelle Ledger prüfen. Dateien
mit akzeptierten Implementierungsfingerprints nicht stillschweigend verändern.
Vor Veröffentlichung die gepinnte Umgebung mit
`./scripts/bootstrap_validation_env.sh` vorbereiten, `./scripts/validate_all.sh`
ausführen und den strikten MkDocs-Build prüfen. Der Ledger-Validator und die
Tests prüfen unter anderem Replay, Revisionen, widersprüchliche Evidenz,
persönliche Zustimmung sowie Abschluss und Wiederöffnung. Ein erfolgreicher
Testlauf ist keine persönliche Betriebsannahme und keine Produktionsfreigabe.

## CLG-06.1: historische synthetische Berichtsimplementierung

CLG-06.1 adds reproducible JSON and Markdown reporting over the three existing
synthetic GRS-002 histories. It is the first bounded step in the
[CLG-06 backlog](../planning/closed-loop-governance-implementation-plan.md#clg-06-in-einzelne-schritte-zerlegt).
[GCR-2026-067](../../governance/change-requests/GCR-2026-067-governance-lifecycle-metrics.md)
classifies the reporting contract and validation.

The output is synthetic, report-only and explicitly `official_state: false`.
The original conflict scenario, closure pilot and exception scenario reuse the
same finding identity in independent histories. They are not three repositories
or three operational findings. There is no cross-scenario total, compliance
score, SLA target, MTTR claim or live portfolio promotion.

## Rebuild and inspect

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/generate_governance_lifecycle_overview.py \
  --as-of 2026-09-14T00:10:00Z
.venv-validation/bin/python scripts/validate_governance_lifecycle_ledger.py
```

Generated outputs:

- `status/governance-lifecycle-overview.json`, governed by
  `schemas/governance-lifecycle-overview.schema.json`
- `generated/reports/governance-lifecycle-overview.md`

`as_of` is required. The checked-in value is a **synthetic evaluation instant**
that includes the exception renewal on 14 September; it is not the current wall
clock or a claim about a future live event. All three scenarios use that same
instant. The generator reads immutable transactions and the accepted test
profile directly, without relying on mutable scenario indexes. It uses the
existing kernel and validates the complete chain, including transactions after
the cutoff, before projecting records whose `recorded_at <= as_of`.

For historical inspection, write to separate outputs:

```bash
.venv-validation/bin/python scripts/generate_governance_lifecycle_overview.py \
  --as-of 2026-09-13T14:10:00Z \
  --output /tmp/lifecycle-at-1410.json \
  --report /tmp/lifecycle-at-1410.md
```

The repository's checked-in overview must include the last accepted transaction
in every scenario. Validation rejects an earlier cutoff, mismatched metrics,
changed report text or missing scenario directory. An empty historical
projection is legitimate when its cutoff predates the first event. Generated
output cannot target immutable history or source models, including through a
symlink. The existing `lifecycle-synthetic` publisher carries the two new
explicit overview paths and the CLG-06.2 viewer, validating them before creating
a review branch.
After appending pilot history, regenerate the pilot index/report and this
overview before validation and publication. Choose an explicit `as_of` at or
after the last recorded transaction across all three scenarios. Other ledger
domains, source models and consumer results remain outside that scope.

## Metric definitions (ADR-CLG-006)

Each scenario embeds the unmodified kernel projection and a timeline with
finding ID, revision, effective time, recording time and immutable event and
transaction references. The evaluated ledger head binds the visible history.
The scenario ID and finding ID jointly identify a finding in this report.
Metrics are deterministic reductions of those verified records and projections.

| Metric | Meaning |
|---|---|
| `records` | Visible transaction, accepted observation, event, quarantine, decision, remediation-update, closure and exception-record counts. A remediation update is not an additional work case. |
| `event_types` | Historical count of each accepted event type. Reopening retains the earlier closure count. Quarantine can produce a clarification event without becoming an accepted observation. |
| `accepted_observation_results` | Accepted PASS/FAIL observations only; quarantine is separately counted. Identical redelivery is not a new stored transaction. |
| `current_finding_states` | Current `open`, `closed` and `needs_clarification` findings from the kernel projection. PASS alone does not change this count to closed. |
| `current_remediation_progress` | Latest progress per work case, including retained cases with revoked authorization. Consult each embedded case's authorization status. Completed work does not imply finding closure. |
| `current_overdue_cases` | Cases marked overdue by the existing projection at `as_of`, including retained cases with revoked authorization. This measures the recorded target, not a newly approved SLA. |
| `current_exception_statuses` | Status at `as_of` of each exception record, including historical grants and separate withdrawal records. This is not a count of uniquely covered observations. |
| `current_coverage_by_finding` | Findings by projected observation-coverage category. `not_evaluated` means the projection has no exception treatment dimension; it makes no waiver-eligibility claim. `not_applicable` is the kernel's result when no outstanding accepted failures remain. |
| `current_findings_needing_renewed_decision` | Findings whose expired/revoked observation coverage still needs a new decision according to the existing exception projection. |

A scheduled grant becoming active, an expiry or a target becoming overdue can
change current metrics at a new `as_of` without adding any event. Their original
records and time bounds remain the audit source; the report does not fabricate
an expiry or overdue event. Event order follows accepted transaction order,
not sorting by effective time. Thus the late older FAIL at 14:10 in the closure
scenario stays in the history without undoing the closure; the newer FAIL at
14:20 generates a reopening.

At the checked-in instant the original scenario has one finding needing
clarification, the closure scenario has one open finding with one historical
closure and one reopening, and the exception scenario has one open finding
with full coverage of its three explicit accepted failing observations. Full
coverage is risk treatment, not a successful remediation or closure.

## Boundaries and validation

The overview is a reporting contract, not a new lifecycle transition or input
adapter. Existing synthetic profiles, ledgers, authority models and consumer
results retain their meaning. The official status viewer is not fed by this
report. The later [accepted live pilot](../status/governance-lifecycle-current-state.md)
has its own projection and does not promote these synthetic metrics.
The kernel and reporting run without network access or an LLM.

Tests cover the recorded-time cutoff, validation of a corrupt future suffix,
late failure versus reopening, quarantine, completion versus closure, expiry
without invented events, retained revoked work, reproducible bytes, schema
boundaries, protected output paths and rejection of stale/tampered output.
Run pinned full validation and the strict MkDocs build before publication.
[CLG-06.2](governance-lifecycle-viewer.md) provides a separate read-only viewer
for these scenarios. Regenerate that viewer after updating this overview.
