# Live-Pilot: bestätigte Entscheidungen und verbleibender Ausbau

Stand: **13. September 2026, nach PR #93**. Rollen, Betriebsprofil und persönliche
Betriebsabnahme LD-07 sind für den begrenzten manuellen GRS-002-Piloten bestätigt.
Die wirksame Aktivierung und echte Workflow-Nachweise stehen im
[aktuellen Betriebsstand](../status/governance-lifecycle-current-state.md).
Technische Review-Ausnahmen ersetzen keine persönlichen Einzelentscheidungen.

## Freigegebener Geltungsbereich

- Regel GRS-002 `pull_request_review_required`, Ressource `refs/heads/main`.
- Repository `joku-dev/devsecops-governance-framework`, GitHub.com als Provider.
- Manuell gestarteter Report-only-Betrieb; Veröffentlichung über begrenzte PRs.
- Bei PASS entsteht kein künstliches Finding. Fehler-/Behebungs-/Abschlussfolgen
  sind bislang mit synthetischen und injizierten Testdaten nachgewiesen.

## Bestätigte Entscheidungen

| Entscheidung | Nachweis und Wirkung | Grenze |
|---|---|---|
| LD-01: Entscheidungs- und Abschlussrollen | `joku-dev`, GitHub-ID `81616324`, versionierte Rollenbindung in PR #85; ausdrücklich bestätigte Mehrfachrolle | Nur dieser Pilot; jede Maßnahme benötigt eigene inhaltsgebundene Zustimmung |
| LD-02: Persönlicher Kanal | Persönlicher Kanaltest auf PR #87, verifiziert in PR #89; aktionsbezogene Prüfung in PR #90 | GitHub belegt Kontoidentität; persönliche Anwesenheit bleibt ausdrücklich selbst erklärt |
| LD-03: Rollenverwaltung/Widerruf | Registry-Owner ebenfalls `github-user:81616324`; Rollenentzug und Widerruf werden als neue Datensätze geprüft | Wiederherstellung oder neue Zuordnung braucht eine eigene versionierte Migration |
| LD-04: Quelle/Aufbewahrung | Offizielle GitHub-API, festgelegte Producer-Dateien, erfolgreicher Mainline-Push, Versuch 1; vollständige unveränderliche Pilot-Captures | Keine allgemeine Unternehmens-Aufbewahrungsrichtlinie; keine automatische Löschung |
| LD-05: Frische/Replay | 24 Stunden maximale Evidenzalterung, kein zukünftiger Zeitversatz, identischer Replay ohne neue Wirkung, Konflikte in Quarantäne | Alte Historie bleibt erhalten, erneutes Projizieren erneuert ihre Frische nicht |
| LD-06: Annahme/Revisionsschutz | Lokale atomische Speicherung, vollständiger Replay, unveränderte angenommene Historie und unabhängige Providerchecks in erforderlicher CI; echte Publisher-Läufe #92/#93 | Parallele oder veraltete Vorschläge gegen aktuelles main abgleichen und neu prüfen |
| LD-07: Betriebsabnahme | Persönlicher Kommentar `5654604937` auf PR #91, Erfassung und Aktivierung durch #92, anschließende Beobachtung durch #93 | Bindet genau den Antrag und dessen Implementierungs-/Leitfaden-Digests |

Die [Abnahmeunterlagen](governance-lifecycle-live-operation.md) bleiben in ihrem
beantragten Wortlaut erhalten. Der dortige Vorbereitungsstatus wird durch den
späteren [Veröffentlichungsnachweis](../status/governance-lifecycle-current-state.md)
ergänzt. Das deaktivierte ursprüngliche Vorbereitungsprofil und die synthetischen
Profile werden nicht umgeschaltet. Eine separate offizielle Pilotprojektion
weist die wirksame Betriebsabnahme aus.

## Tatsächlicher Nachweis und notwendige Einzelfreigaben

Zwei echte zulässige GRS-002-PASS-Receipts sind gespeichert; das jüngste stammt
aus Lauf `34769053225`. Es gibt keine echte Fehlerbeobachtung und keine persönliche
Behebungs- oder Abschlussentscheidung im Verlauf. Das ist ein gültiger Pilotstand.
Die [aktionsbezogene Verifikation](governance-lifecycle-action-consent.md) prüft
bei Bedarf Entscheidungen, Fortschritt, Abschluss und nachträglichen Widerruf.

## Noch nicht freigegebener Ausbau

- **Live-Waiver:** Die synthetische CLG-05-Ausnahmeprüfung erteilt keine echte
  Waiver-Autorität. Architektur-Ausnahmen brauchen zusätzlich bestätigte
  Zuordnungen von Marker-/Regelzielen zum Lifecycle.
- **Weitere Consumer und Adapter:** CLG-06.3 bereitet DevSecOps-Control- und
  Architektur-Gate-Kandidaten vor. Ihre Ausgaben bleiben diagnostisch.
- **Lifecycle-Portfolio (CLG-06.4):** Erst zugelassene Lifecycle-Consumer und eine
  bestätigte Grundgesamtheit erlauben aussagekräftige Quoten. Vorhandene
  Consumer-Gesamtergebnisse oder wiederverwendete Testidentitäten genügen nicht.
- **Optionale KI-Unterstützung (CLG-06.5):** Kein LLM ist für den Kernbetrieb nötig.
- **Runtime-Release und Pilotabschluss:** Die begrenzte Betriebsabnahme ist keine
  neue Baseline-, Release-, Aufbewahrungsabschluss- oder Unternehmensfreigabe.
- **Bitbucket Data Center/Bamboo:** Firmenversionen und Integrationsdaten fehlen;
  die Umsetzung bleibt gemäß Maintainerentscheidung zunächst auf GitHub.
