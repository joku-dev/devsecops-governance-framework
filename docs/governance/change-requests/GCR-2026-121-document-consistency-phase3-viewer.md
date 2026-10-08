# GCR-2026-121: Sichere Phase-3-Viewer-Projektion

## Anfrage und Einordnung

Integriere den gemergten providerneutralen Phase-2-Stand als sichere, lesende
Projektion in den bestehenden Governance Workspace. Verwende ausschließlich
synthetische beziehungsweise bereits freigegebene Repositorydaten. Die fünf
lokalen, unregistrierten Dokumente bleiben außerhalb der Verarbeitung.

| Feld | Wert |
| --- | --- |
| Eingabe | schema-validierter Phase-2-Report mit Status `not_run` und Phase-1-Quellmanifest |
| Projektion | öffentliche, explizite Feld-Allowlist; keine interne Vollansicht |
| Aktualität | Vergleich von Manifestdigest und aktuellen Quellenhashes |
| Ausführungskontext | lokaler, deterministischer Viewer-Build |
| Betriebsart | read-only und report-only |
| Provider / Modell | keiner |
| Veröffentlichung | nicht autorisiert; dieser GCR erzeugt nur den reviewfähigen Code-Stand |
| Release-/Baseline-Auswirkung | keine |

## Gelieferter Umfang

- Eigener Bereich **Dokumentenreview** im bestehenden Governance Workspace.
- Getrennte Anzeige von formaler Validierung, semantischem Review,
  menschlichen Entscheidungen und Implementierungsabdeckung.
- Dokumentübersicht für `DSCB-STD-REQ-001` und `PRA-STD-REQ-001` mit öffentlicher
  ID, Registerstatus und Version.
- Finding-Liste mit ausschließlich ID, Kategorie, semantischem Zustand,
  Belegstatus und Disposition.
- Zustände für `not_run`, `provider_failed`, `synthetic_only`, veraltet,
  unbekannte Aktualität und fehlende Projektion ohne pauschalen grünen Status.
- Responsive Darstellung und tastaturfähige bestehende Hash-Navigation.

## Sicherheits- und Publikationsgrenze

Der Adapter validiert Eingabe und Ausgabe gegen getrennte JSON-Schemas. Die
öffentliche Projektion nimmt Felder einzeln auf. Quellenauszüge, Aussagen,
Interpretationen, Empfehlungen, Begründungen, Suchdetails, Validierungsfehler,
Rohantworten, Provider-/Modellkennung und Human-Decision-Inhalte werden nicht
kopiert. Unbekannte Eingabefelder können deshalb nicht versehentlich in
`data.json` gelangen.

Confidential-Canary-Tests platzieren Marker in zulässigen sensiblen
Eingabefeldern und bestätigen, dass kein Marker in der Projektion erscheint.
Ein Browser-Negativtest bestätigt zusätzlich HTML-Escaping für projizierte
Finding-Metadaten. Ohne wirksamen Zugriffsschutz wird keine interne Vollansicht
gebaut. Es gibt keinen zweiten Viewer, keinen Schreibpfad und keine
Veröffentlichungsfreigabe.

## Governance- und Evidence-Kontext

Der Phase-2-Beispielreport ist eine lokale, versionierte Dokumentations- und
Testeingabe. Er ist kein Consumer-Ergebnis und verändert keine offiziellen
`latest_result`-Auswahlen oder Statusindizes. Der angezeigte Zustand bleibt
`not_run`; null Findings bedeuten keine bestätigte Konsistenz. Controls,
Architekturmodelle, OPA, Releases, Baselines und Consumer-Workflows bleiben
unverändert.

## Abnahmekriterien

- [x] Bestehender Viewer statt paralleler Anwendung erweitert.
- [x] Report und öffentliche Projektion werden schema-validiert.
- [x] Aktualität wird aus Manifest- und Quellenhashes abgeleitet.
- [x] Öffentliche Projektion folgt einer Feld-Allowlist.
- [x] Confidential-Canaries aus Freitext, Provider und Modell gelangen nicht in die Ausgabe.
- [x] `not_run` wird nicht als befundfrei oder grün dargestellt.
- [x] Fehlende Projektion besitzt einen eigenen Fehlerzustand.
- [x] HTML-/Link-Injection wird durch Escaping und bestehende CSP begrenzt.
- [x] Mobile Darstellung verwendet das bestehende responsive Layout.
- [x] Technische Abnahme der Phase 3 am 7. Oktober 2026 auf Basis von PR #222.
- [ ] Veröffentlichung oder Deployment; separat zu entscheiden.

## Abnahmeentscheidung

Der Maintainer hat Phase 3 am 7. Oktober 2026 auf Basis von PR #222 mit
folgendem Scope angenommen:

> Ich nehme Phase 3 auf Basis von PR #222 ab. Die Abnahme gilt für die sichere,
> öffentliche und redigierte Viewer-Projektion. Sie autorisiert keine
> Veröffentlichung, keinen Live-Provider-Lauf und keine fachliche Bestätigung
> von Findings.

Die Entscheidung bindet die technische Abnahme an den in PR #222 gemergten
Stand. Sie ändert weder Quellenstatus noch normative Governance-Artefakte und
erteilt keine Betriebs-, Publikations- oder Providerfreigabe. Phase 4 wird als
separater Änderungssatz vorbereitet.

## Release-Einordnung

Die Änderung erweitert ausschließlich den internen Viewer-Build und dessen
öffentliche redigierte Projektion. Sie ändert keine freigegebene Baseline, kein
Consumer-Interface und keine blockierende Pipeline. Eine Release- oder
Consumer-Migration ist nicht erforderlich.
