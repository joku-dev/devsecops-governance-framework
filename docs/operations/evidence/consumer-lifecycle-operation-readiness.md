# Erster Consumer-Lifecycle-Fall: Operation Readiness

Stand: 13. September 2026. **Technisch vorbereitet; keine angenommene
Lifecycle-Beobachtung, Rollenübertragung, Evidenzfreigabe oder Schließung.**

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
Ob dieser Umfang für den nicht deployten Demo-Consumer als Observability-Evidenz
ausreicht, ist eine fachliche Entscheidung. Die Evidenzdateien bleiben
`reviewed`; ein grüner Testlauf setzt sie nicht auf `approved`.

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

## Entscheidungsvorlage für den Maintainer

Vorgeschlagen ist genau dieser eine manuelle Report-only-Fall auf GitHub.com.
`joku-dev` / GitHub-ID `81616324` übernimmt ausdrücklich die Rollen für
Consumer-Lifecycle-Entscheidung, fachliche Evidenzabnahme, Abschluss und
Rollenverwaltung. Die Mehrfachrolle gilt nur für diesen Demo-Piloten.

Zusätzlich ist zu entscheiden, ob das offene Maßnahmenprotokoll und die
CI-lokalen Funktionsdiagnosen für B5/P11 dieses nicht deployten Demos als
Behebungsnachweise ausreichen. Diese Entscheidung bescheinigt keine
Produktionsreife. Die genauen Mainline-Läufe und Artefakte stehen im
[Referenzprotokoll](../reference-runs/2026-09-13-consumer-revalidation.md).

**Noch nicht erklärt oder angenommen:** Diese Vorlage enthält keine persönliche
Erklärung des Maintainers. Die frühere GRS-002-Rollenbindung gilt für das zentrale
Repository; sie darf nicht auf diesen Consumer übertragen werden. Die technische
PR-Review-Ausnahme ersetzt diese fachliche Zuordnung und Abnahme nicht.

## Anschließender Ablauf und Abschlusskriterien

1. Rollen, enger Umfang und ausreichende Demo-Evidenz ausdrücklich bestätigen.
2. Einen separaten versionierten Consumer-Annahmeweg implementieren und testen:
   Provider-Run/Artifact/Commit, aufgelöste Policy, genau dieses Gate, geschlossene
   Schemas, 24 Stunden maximale Frische, kein Zukunftsversatz, idempotenter Replay,
   Konfliktquarantäne und unveränderliche Historie. Bestehende LD-07-Dateidigests
   bleiben erhalten; notwendige gemeinsame Änderungen benötigen neue Abnahme.
3. Implementierung und Leitfaden an eine neue persönliche Betriebsabnahme binden.
   Der vorliegende manuelle Diagnosekandidat wird dadurch nicht rückwirkend angenommen.
4. Frischen Mainline-Befund aufnehmen; eine persönliche, inhaltsgebundene
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
