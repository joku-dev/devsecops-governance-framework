# GCR-2026-168 — Vollständige Bedienreferenz der Agentenreview-Werkzeuge

## Auftrag und Befund

Der Maintainer beauftragt die Prüfung und Ergänzung der Dokumentation zu
PRs #351–#355. Der bestehende Ablauf beschreibt alle fünf Erweiterungen bereits
grundsätzlich, lässt aber konkrete CLI-Optionen, Dateiformate, Fehlerbehebung und
die Einbindung in die Funktionsinventare offen. Diese Änderung ergänzt die
Bedienung und erklärt die implementierten Grenzen ohne neue Laufzeitfunktion.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | Agent Review Tooling Reference and navigation/inventory updates |
| Artifact type | documentation |
| Target path | `docs/operations/agents/`, existing documentation indexes/guides, `mkdocs.yml` |
| Owner | Repository maintainer |
| Source Document Intake required? | no; operational explanation of implemented tools |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Release impact | none; no baseline release required |
| Validation required | pinned bootstrap/full validation, offline command examples, MkDocs strict, focused documentation review |

## Umfang und Abnahmekriterien

- Alle fünf Erweiterungen sind über Agenteneinstieg, Bedienablauf, MkDocs,
  offizielle Einstiege und KI-Index auffindbar.
- Eine technische Referenz erklärt Routing, Revisionsbindung, private und
  veröffentlichbare Dateien, Receipt-Idempotenz und Nutzungszählung.
- PR-Statuswerte, vertrauenswürdige Ausführung auf dem Zielbranch,
  Rollen-/Validierungsunion und die Trennung von CODEOWNER-Freigaben sind erklärt.
- Runner-Voraussetzungen, Optionen, Ausgaben, Fehlerbehebung, Timeout und
  Parallelitätsgrenzen sind nachvollziehbar; Live-Aufrufe bleiben ausdrücklich optional.
- Offline-Antwortformat, Trace-Bindung und Kennzahlen sind mit einem als
  synthetisch gekennzeichneten Beispiel dokumentiert. Beispiele werden ohne
  Provideraufrufe geprüft; es werden keine Live-Benchmark-Ergebnisse behauptet.
- Fachliches und technisches Funktionsinventar sowie Harness-Beschreibung
  erfassen die gelieferten Werkzeuge und deren Aussagegrenzen.

## Wirkung und Review

Dokumentationsänderung; keine Anpassung an Rollenverträgen, Routing, Skripten,
Schemas, Workflows, Consumerergebnissen oder Freigaberegeln. Bestehende
Report-only-Semantik, Baselines, Quellenregister und Pilot-Fingerprints bleiben
erhalten. Der fokussierte Review gleicht jede Anleitung mit Implementierung und
CLI ab. Nachweise zur Validierung stehen im zugehörigen PR.
