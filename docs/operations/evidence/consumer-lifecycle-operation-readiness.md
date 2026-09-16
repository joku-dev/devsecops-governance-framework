# Erster Consumer-Lifecycle-Fall: Operation Readiness

Stand: 16. September 2026. **Rollen und begrenzter Evidenzumfang vom Maintainer bestätigt;
Consumer-Lifecycle persönlich abgenommen und aktiviert; Einzelaktionen ausstehend.**

## Konkreter Fall und Nachweise

| Feld | Vorschlag / geprüfter Wert |
|---|---|
| Consumer | `joku-dev/governance-framework-demo-consumer` |
| Domäne / Ressource | Architektur / Repository |
| Regel / Granularität | `operation_readiness` / ein Gate |
| Ausgangslauf | [34778462308, Versuch 1](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34778462308), manuelle Diagnose auf `main` |
| Ausgangscommit | `7d6a4f67c5e8441e1067405cc2da17218dc256fd` |
| Ergebnis | `findings`, zwei Nachrichten: B5 Feedback und P11 Observability, jeweils Score 3 bei benötigtem Score 4 |
| Baseline | `architecture-baseline-l1-v0.1.0` |
| Aufgelöster Policy-Commit | `19e281d323eb69be26bdb2cbf4368caadfbccaa7`; annotiertes Tagobjekt `407ee1013e9f3d4fadcd5bc27011d65a78cd6505` ist kein Policy-Commit |
| Ausgangsbericht SHA-256 | `97ddd49aafa92a23a282dfac84f77ded6c86ac3a4705ed8139f6cda3ee191adb` |
| Technische Behebungsvorbereitung | [Consumer-PR #5](https://github.com/joku-dev/governance-framework-demo-consumer/pull/5) |

Die zwei Markerbezeichnungen sind unveränderte Quellnachrichten. Der Adapter
liefert ein Gate-Ergebnis und keine zwei eigenständigen Marker-Findings.
Die übrigen 23 Architekturhinweise sind außerhalb dieses Behebungsvorschlags.

## Umgesetzte Vorbereitung

Im Consumer verknüpft `docs/OPERATION_READINESS_ACTION.md` den Ausgangsbefund,
Maintainer als technischen Bearbeiter, Maßnahmen und Abschlussbedingungen.
Die Feedback-Evidenz verweist auf dieses offene Maßnahmenprotokoll.

`src/demo_app/diagnostics.py` führt die tatsächliche Demo-Funktion aus: gültiger
Aufruf, leerer Name und leere Version. CI speichert Status, Fehlerart, gemessene
Dauer, Commit, Run-ID und Beobachtungszeit als `demo-runtime-diagnostics`.
Tests prüfen ausdrücklich unerwartete Laufzeitfehler, falsche Rückgaben und
fehlende Eingabeablehnung. Das Diagnoseergebnis ist report-only.

Dies belegt lokale Funktionsausführung im CI-Runner. Es gibt keinen deployten
Dienst, keinen produktiven Health-Endpunkt, keine Verfügbarkeit oder SLO-Zusage.
Der Maintainer hat diesen Umfang für den nicht deployten Demo-Consumer als
Observability-Nachweis bestätigt. Die Consumer-Dateien bleiben zunächst `reviewed`,
bis der neue Lifecycle-Betrieb den Ausgangsbefund und die Behebungsentscheidung
erfasst hat. Die Aussage wird nicht zu einer Produktionsfreigabe erweitert.

Der bestehende Kandidatenadapter wurde auf den echten Ausgangsbericht angewendet.
Unter `generated/reports/lifecycle-candidates/demo-consumer-operation-20260913/`
liegen unveränderte Quellberichte, GitHub-Run-/Artifact-Metadaten, Tagauflösung,
Kontext, Auswertungszeit und reproduzierbare Kandidaten. Das Bundle bleibt
`environment=diagnostic`, `official_state=false`, `trust_status=unverified`.
Ein zweites Bundle unter `remediation-main/` enthält den echten Main-Push-Lauf
`34778861076` nach PR #5 sowie CI-Artefakt `34778860861`. Es bestätigt weiter
die zwei offenen Gate-Nachrichten bei erfolgreich ausgeführten Diagnosen.

Die separate zentrale Ergebnisaufnahme prüft Bytes und Herkunft im bestehenden
Consumer-Intake; sie erteilt keine Lifecycle-Annahme.

## Erste Consumer-Lifecycle-Beobachtung

Nach der persönlichen Betriebsabnahme dokumentiert
[Consumer-PR #6](https://github.com/joku-dev/governance-framework-demo-consumer/pull/6)
die inzwischen bestätigten Rollen und den verbleibenden Ablauf. Sein Mainline-
Commit `5da284d0a3e7d526df644266451206e09084a556` erzeugte den echten
[Architekturlauf 35107862511](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/35107862511)
und [CI-Lauf 35107861865](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/35107861865).

Der Consumer-Collector nahm das Gate am 16. September um 14:21:30 UTC auf.
GitHub-Artefaktzeit: 14:20:45 UTC. Die unabhängige OPA-Neuberechnung bestätigt
die beiden B5/P11-Nachrichten. Der eigene Lifecycle-Zustand ist **open**:
ein angenommener Fehlernachweis, null Aktionsfreigaben. Der alte Diagnosekandidat
wurde nicht rückwirkend angenommen. Die allgemeinen Consumer-Ergebnisindizes
bleiben eine getrennte Darstellung mit ihren eigenen Aufnahmeläufen.

Der vorbereitete Behebungsantrag
`model/governance/lifecycle/consumer-operation/action-requests/00000001.json`
bindet genau diesen Nachweis und Revision 1. Er schlägt `joku-dev` als Bearbeiter
und den 23. September 2026, 23:59:59 Europe/Berlin, als Frist vor. Geplant sind
die konkrete Evidenzfreigabe für Feedback und CI-lokale Observability,
persönliche Fortschrittsmeldungen und ein frischer Mainline-PASS nach dem
abgeschlossenen Fortschritt. Anschließend folgt eine eigene Abschlussentscheidung.
Die vorbereitete Erklärung liegt in
`generated/reports/consumer-lifecycle-decision-statement.md` für PR #102.
Bis zu ihrer persönlichen Abgabe bleibt der Plan ein Vorschlag.

## Bestätigte Rollen und Evidenzentscheidung

Der Maintainer bestätigte ausdrücklich mit **„ich bestätige“** die vorgeschlagenen
Entscheidungs-, Evidenzabnahme-, Abschluss- und Verwaltungsrollen von `joku-dev`
(GitHub-ID `81616324`) sowie Maßnahmenprotokoll und CI-lokale Diagnosen als
hinreichenden Nachweis für dieses nicht deployte Demo. Die Mehrfachrolle gilt
nur für diesen Pilotfall und bescheinigt keine Produktionsreife.

[GCR-2026-080](../../governance/change-requests/GCR-2026-080-consumer-lifecycle-admission.md)
und `model/governance/lifecycle/consumer-operation/roles.json` halten diese
Gesprächsentscheidung fest. Der [separate Betriebsleitfaden](consumer-lifecycle-operation.md)
beschreibt den implementierten Annahme- und Aktionsweg. Die separate
[persönliche Betriebsabnahme](https://github.com/joku-dev/devsecops-governance-framework/pull/101#issuecomment-5698945870)
vom 16. September wurde um 14:16:03 UTC erfasst; Implementierung und Rollen
stimmen mit dem angenommenen Antrag überein. Einzelne Aktionsfreigaben folgen
weiterhin über eigene inhalts- und revisionsgebundene Anträge.

## Anschließender Ablauf und Abschlusskriterien

1. **Erledigt:** Rollen, enger Umfang und ausreichende Demo-Evidenz bestätigt.
2. **Implementiert:** separater versionierter Consumer-Annahme- und Aktionsweg:
   Provider-Run/Artifact/Commit, aufgelöste Policy, genau dieses Gate, geschlossene
   Schemas, 24 Stunden maximale Frische, kein Zukunftsversatz, idempotenter Replay,
   Konfliktquarantäne und unveränderliche Historie. Bestehende LD-07-Dateidigests
   bleiben erhalten; notwendige gemeinsame Änderungen benötigen neue Abnahme.
3. **Erledigt:** Implementierung und Leitfaden persönlich abgenommen und erfasst.
   Der vorliegende manuelle Diagnosekandidat wird dadurch nicht rückwirkend angenommen.
4. **Befund aufgenommen; Entscheidung ausstehend:** persönliche, inhaltsgebundene
   Behebungsentscheidung und Fortschritt mit den konkreten Artefakten erfassen.
   Nach tatsächlicher fachlicher Freigabe Evidenzstatus separat aktualisieren.
5. Architekturprüfung nach Behebung auf `main` ausführen. Für Abschluss zählt nur
   ein frisches `operation_readiness=pass`, bei beiden Maßnahmen vollständig und
   nach ihrem Abschlusszeitpunkt. Danach persönliche Abschlussentscheidung erfassen.
6. Ein späterer neuer Fehler öffnet den Fall nach den versionierten Regeln wieder.

Keine Live-Waiver, Baselineänderung, automatische Behebung, neue Blocking-Prüfung
oder Portfolioquote ist enthalten. Eine fachliche Ablehnung der Demo-Evidenz
bleibt ein offener Befund und erfordert zusätzliche reale Nachweise.

## Reproduktion der Kandidaten

```bash
python3 scripts/prepare_lifecycle_architecture_candidates.py \
  --report generated/reports/lifecycle-candidates/demo-consumer-operation-20260913/architecture-governance-report.json \
  --context generated/reports/lifecycle-candidates/demo-consumer-operation-20260913/context.json \
  --output /tmp/demo-operation-candidates.json \
  --evaluated-at "$(cat generated/reports/lifecycle-candidates/demo-consumer-operation-20260913/evaluation-time.txt)"
cmp /tmp/demo-operation-candidates.json \
  generated/reports/lifecycle-candidates/demo-consumer-operation-20260913/candidates.json
```

[GCR-2026-079](../../governance/change-requests/GCR-2026-079-consumer-revalidation-and-lifecycle-case.md)
klassifiziert die Artefakte und ihre Veröffentlichung.
