# Aktueller GitHub-Lifecycle-Pilot

Dokumentationsabgleich: **3. Oktober 2026**, Quellstand `46b33429`.
Die folgende GRS-002-Aktivierungsbeschreibung hält den historischen Stand vom
13. September (`8df643db37ec4d6da7196b94aaa77b5e0e0844d8`) fest.
Diese Seite beschreibt den veröffentlichten Pilotbetrieb. Der aktuelle
maschinenlesbare Zustand steht in `status/governance-lifecycle-live.json` und
wird durch `generated/reports/governance-lifecycle-live.md` erläutert.

## Aktueller separater Consumer-Pilot

Die übernommene Projektion `status/governance-consumer-lifecycle.json` weist zum
`2026-10-03T10:58:04Z` eine wirksame Betriebsabnahme und **`finding_state: closed`**
aus: drei Receipts und vier Aktionsdatensätze. Die persönlich gebundenen Schritte
`in_progress`, `completed` und die separate Abschlussentscheidung sind inzwischen
erfasst. Der [erzeugte Bericht](https://github.com/joku-dev/devsecops-governance-framework/blob/46b33429a6f271273e33508f26275ed8ba7f1f2c/generated/reports/governance-consumer-lifecycle.md)
und die append-only Transaktionen unter `governance/consumer-lifecycle/` sind
die Nachweise. Die September-Beschreibung am Seitenende ist historische Chronologie,
nicht eine aktuelle Aufforderung zur erneuten Fortschrittserklärung.

Dies gilt ausschließlich für `governance-framework-demo-consumer` /
`operation_readiness`, nicht für den zentralen GRS-002-Piloten, andere Consumer
oder Produktionsfreigaben. Beide Piloten bleiben manuell und report-only.
Ein späterer zulässiger neuer FAIL kann den Consumer-Fall wieder öffnen.
Die [Closed-Loop-Lesekarte](../evidence/governance-lifecycle-overview.md)
trennt die beiden Betriebsscopes und die synthetischen Szenarien.

## Historische GRS-002-Betriebsabnahme und Aktivierung

| Gegenstand | Nachgewiesener Stand |
|---|---|
| Geltungsbereich | `joku-dev/devsecops-governance-framework`, GRS-002 `pull_request_review_required`, `refs/heads/main` |
| Betrieb | Manuell gestarteter Report-only-Pilot; Betriebsabnahme wirksam |
| Persönliche LD-07-Erklärung | [Kommentar 5654604937 auf PR #91](https://github.com/joku-dev/devsecops-governance-framework/pull/91#issuecomment-5654604937), `joku-dev` / GitHub-ID `81616324`, 13. September 2026, 16:41:50 UTC |
| Erfassung der Erklärung | 16:42:42 UTC; [Workflow 34769390700](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34769390700) |
| Aktivierung | [PR #92](https://github.com/joku-dev/devsecops-governance-framework/pull/92), Merge `0fc2cc8ea18343d06b7c94399be3fd6770df948f` |
| Erste Beobachtungsveröffentlichung nach Aktivierung | [Workflow 34769763909](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34769763909), [PR #93](https://github.com/joku-dev/devsecops-governance-framework/pull/93) |
| Zugrunde liegende neueste Beobachtung | Self-Security-Lauf `34769053225`, Versuch 1, Mainline-Push auf `1fcdde9d80304528fc1e765314e73215936a8512`; beobachtet 16:35:49 UTC, aufgenommen 16:50:22 UTC |
| Ergebnis | GRS-002 PASS, eine vorgeschriebene Review-Freigabe, `no_finding` |
| Verlauf | Zwei akzeptierte Evidenzdatensätze, null Fehler, null Quarantänefälle, null Maßnahmen |
| Validierung der Veröffentlichungen | Je 470 Tests, strikter Dokumentationsbuild und unabhängige GitHub-Nachprüfung in Governance CI bestanden |

Das GRS-002-Ergebnis bewertet genau eine Regel. Es bescheinigt weder vollständige
Repository-Sicherheit noch die Aktualität der Consumer-Nachweise. Die Angaben
`as_of` und `evidence_as_of` der Pilotprojektion folgen dem gespeicherten Verlauf;
der fachliche Beobachtungszeitpunkt steht in `source.observed_at` des Receipts.
Eine spätere Dokumentationsprüfung erzeugt keine neue Beobachtung.

## Benutzung

Der Workflow **Lifecycle Pilot Update** wird auf `main` manuell gestartet:

| Operation | Eingabe | Wirkung |
|---|---|---|
| `acceptance` | Keine zusätzliche Eingabe | Persönliche Betriebsabnahme erneut erfassen; auch Änderung oder Widerruf festhalten |
| `observe` | Tatsächliche ID eines zulässigen abgeschlossenen Mainline-Self-Security-Laufs | Frische Evidenz prüfen, unveränderlich aufnehmen und Ansichten berechnen |
| `action` | Auf `main` versionierter Antrag unter `model/governance/lifecycle/action-requests/` | Persönliche Einzelfreigabe prüfen und Maßnahmenverlauf ergänzen |
| `refresh` | Keine zusätzliche Eingabe | Betriebsabnahme nachprüfen und vorhandenen Verlauf erneut projizieren |

Jeder verändernde Lauf erstellt einen begrenzten PR. Erst nach bestandenen
Prüfungen und Merge ist der vorgeschlagene Zustand veröffentlicht. Der Workflow
postet keine persönlichen Erklärungen und führt keine Behebung aus. Es gibt
keinen Zeitplan für kontinuierliche Überwachung. Ein `refresh` erneuert keine
veraltete Beobachtung. Für neue Beobachtungen sowie Entscheidungs-/Abschlussnachweise
gelten 24 Stunden maximale Evidenzalterung und kein zukünftiger Zeitversatz.

[Einzelentscheidungen, Fortschritt, Abschluss und Widerruf](../evidence/governance-lifecycle-action-consent.md)
bleiben jeweils an vollständigen Inhalt, Rolle, Evidenz und Revision gebunden.
Ohne tatsächlichen Fehler entsteht keine künstliche Behebungsaufgabe.

## Abnahmeunterlagen und Änderungsschutz

Die unveränderten Unterlagen sind der
[abgenommene Betriebsleitfaden](../evidence/governance-lifecycle-live-operation.md),
`model/governance/lifecycle/operating-acceptance/00000001.json` und
`generated/reports/lifecycle-operating-acceptance/00000001.json`.
Der Leitfaden enthält den Vorbereitungsstatus zum Zeitpunkt des Antrags; diese
Seite und die erzeugte Pilotprojektion dokumentieren dessen spätere Aktivierung.
Der Antragsdigest ist `0ac280399f7ef5fb1af490dd0f9ca02be356ddac38cba2ae192c6ec82185114a`.

Die abgenommene Implementierung einschließlich Leitfaden ist durch Dateidigests
gebunden. Änderungen daran benötigen einen neuen versionierten Abnahmeweg;
eine redaktionelle Aktualisierung dieser Statusseite verändert diese Bindung nicht.
Ein Widerruf, eine Änderung/Löschung der persönlichen Erklärung, entzogene Rollen
oder abweichende Implementierung verhindern neue gültige Betriebsvorschläge.
Die Berichte zeigen gespeicherte Erfassungen; Änderungen bei GitHub müssen erneut
erfasst und veröffentlicht werden. Vor neuen Vorschlägen erfolgt eine Providerprüfung.

## Getrennte Zustände und verbleibender Ausbau

- `status/governance-lifecycle-live.json`: wirksamer, begrenzter GitHub-Pilot.
- `status/governance-lifecycle-live-validation.json` und
  `status/governance-lifecycle-pilot-actions.json`: technische Zulässigkeitsansichten;
  ihre diagnostischen Kennzeichnungen bleiben unverändert.
- Synthetische CLG-01–06.2-Verläufe und der Szenario-Viewer: reproduzierbare Tests,
  einschließlich Fehler, Behebung, Abschluss, Wiedereröffnung und Ausnahmen.
- DevSecOps-/Architektur-Kandidatenadapter: weiterhin diagnostisch, ohne freigegebenen
  Lifecycle-Intake für weitere Consumer.
- Bestehende Consumer-Indizes und Baselines: eigener Geltungsbereich.

Live-Waiver, weitere Lifecycle-Consumer, Portfolio-Kennzahlen mit bestätigter
Grundgesamtheit, optionale KI-Unterstützung und ein Runtime-Release bleiben
separate Erweiterungen beziehungsweise Entscheidungen. Die vollständige echte
Fehler-/Behebungs-/Abschlussfolge ist mangels echtem GRS-002-Fehler nicht durchlaufen;
für diese Folge liegen synthetische und injizierte Negativtests vor.
Bitbucket Data Center/Bamboo bleibt bis zur Klärung der Firmenumgebung zurückgestellt.

## Consumer-Vorbereitung nach der Betriebsabnahme

Die [Consumer-Revalidierung vom 13. September](../reference-runs/2026-09-13-consumer-revalidation.md)
und der [konkrete Operation-Readiness-Fall](../evidence/consumer-lifecycle-operation-readiness.md)
ergänzen echte Diagnose-Evidenz und Behebungsvorbereitung. Diese Arbeit aktiviert
keinen weiteren Lifecycle-Consumer und ändert die bestehende GRS-002-Abnahme nicht.

Die anschließende Bestätigung des Maintainers erfasst Rollen und begrenzten
Demo-Evidenzumfang in GCR-2026-080. Die eigene
[persönliche Betriebsabnahme vom 16. September](https://github.com/joku-dev/devsecops-governance-framework/pull/101#issuecomment-5698945870)
wurde um 14:16:03 UTC unabhängig erfasst. `status/governance-consumer-lifecycle.json`
zeigt den separaten Consumer-Piloten als aktiviert. Die erste unabhängig
verifizierte Mainline-Beobachtung aus Lauf `35107862511` wurde um 14:21:30 UTC
aufgenommen: `operation_readiness=fail`, ein offener Fall mit den zwei
Quellnachrichten B5/P11. Die erste persönliche Behebungsentscheidung wurde am
16. September um 15:42:03 UTC erfasst; der Fall bleibt offen. Es gibt einen
Beobachtungsnachweis und eine angenommene Aktion, noch keinen Fortschritt oder Abschluss.
Der [Consumer-Betriebsleitfaden](../evidence/consumer-lifecycle-operation.md)
enthält dessen genaue Bedingungen. Der repositoryübergreifende Lesetoken ist
seit 16. September als Secret hinterlegt; der erforderliche Consumer-Guard
prüft die neue Quelle vor Veröffentlichung unabhängig mit diesem Token.
Der erste Behebungsantrag unter
`model/governance/lifecycle/consumer-operation/action-requests/00000001.json`
ist durch [Kommentar 5700249154](https://github.com/joku-dev/devsecops-governance-framework/pull/102#issuecomment-5700249154)
bestätigt. Die Umsetzung ist in
[Consumer-PR #7](https://github.com/joku-dev/governance-framework-demo-consumer/pull/7)
dokumentiert. Der Folgeantrag `action-requests/00000002.json` bereitet ausschließlich
die persönliche Fortschrittsmeldung `in_progress` für Revision 2 vor. Ohne deren
eigene Erklärung entsteht keine weitere Aktionswirkung.
