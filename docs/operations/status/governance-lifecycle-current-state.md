# Aktueller GitHub-Lifecycle-Pilot

Stand: **13. September 2026**, geprüfter Repository-Stand `8df643db37ec4d6da7196b94aaa77b5e0e0844d8`.
Diese Seite beschreibt den veröffentlichten Pilotbetrieb. Der aktuelle
maschinenlesbare Zustand steht in `status/governance-lifecycle-live.json` und
wird durch `generated/reports/governance-lifecycle-live.md` erläutert.

## Betriebsabnahme und tatsächlicher Stand

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
