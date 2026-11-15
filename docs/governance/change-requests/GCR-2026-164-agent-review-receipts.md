# GCR-2026-164 — Reviewnachweise mit Nutzungsmetadaten verbinden

## Auftrag und Einordnung

Zweites Paket des Maintainerauftrags vom 13. November 2026, nach
[GCR-2026-163](GCR-2026-163-agent-domain-routing.md). Die bestehende private
Reviewprüfung bleibt erhalten. Ein ausdrücklich exportierter Beleg verbindet
ihren Zustand mit einem fertigen Commit und einer getrennten Nutzungsstatistik.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact type | additive review metadata schema, local tooling, tests, guide |
| Target path | `schemas/agent-review-receipt.schema.json`, `scripts/lib/agent_receipts.py`, `scripts/record_agent_review.py`, agent harness and guide |
| Owner | Repository maintainer |
| Source Document Intake required? | no |
| Evidence contract impact | additive internal review metadata; no consumer evidence contract change |
| Runtime governance impact | report-only, no new enforcement or approval authority |
| Release impact | no consumer baseline release; review schema candidate |
| Validation required | pinned full validation, receipt regressions, MkDocs strict |

## Umfang und Abnahmekriterien

- Export nur aus einem aktuellen, vollständigen Branch-Review mit Basiscommit
  und sauberem, bereits committetem Quellstand. Teilbereichsreviews dürfen keine
  vollständige PR-Abdeckung behaupten.
- Plan- und Ergebnisdigest, Commit, Pfade, Rollenstatus, deklarierte Ausführungsart,
  Validierungsstatus und aggregierte Findingzahlen sind ausdrücklich freigegeben.
  Auftragstext, Revieweridentität, Zusammenfassungen, Ausgaben, Findings,
  Logreferenzen und Providerantworten bleiben im privaten Paket.
- Unvollständige Reviews bleiben erkennbar unvollständig. Ein Digest beweist
  Integrität der Metadaten, keine Revieweridentität oder tatsächliche Ausführung.
- Exporte und neue Nutzungslogs liegen außerhalb des Checkouts, werden privat
  angelegt und überschreiben keine anderen Reviews. Wiederholung desselben
  Reviews erzeugt keinen zweiten Nutzungsdatensatz.
- Die neue Statistik trennt ausgewählte Rollen, deklarierte Ausführung und
  Abschluss. Historische Dispatch-/Providerlogs bleiben unverändert.

## Grenzen und Prüfung

Kein automatischer Provideraufruf, keine Änderung von Quellfreigaben,
Kontrollergebnissen, Trust, Consumerpins, Baselines oder Abnahmefingerprints.
Tests prüfen Datenschutz, saubere Revision, neue HEADs, offene hohe Findings,
unvollständige Ergebnisse, Dateirechte, Wiederholung und Kollisionen.
Eine spätere CI-Sichtbarkeit muss diese Selbstauskunft ausdrücklich kennzeichnen.
Revisionsgebundene Rollenprüfung und konkrete Validierung stehen im Liefer-PR.
