# GCR-2026-163 — Fachzuständigkeiten der Agentensteuerung vervollständigen

## Auftrag und Einordnung

Der Maintainer beauftragt am 13. November 2026 die autonome Umsetzung der fünf
priorisierten Verbesserungen der Agentensteuerung. Dieses erste Paket ergänzt
ausschließlich die fachliche Reviewauswahl. Die folgenden Pakete behandeln
Reviewnachweise/Nutzung, PR-Sichtbarkeit, begrenzte Ausführung und Evaluation.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact type | model-neutral review routing, regression tests, documentation |
| Target path | `.agents/routing/`, `tests/agent_harness/`, `docs/operations/agents/` |
| Owner | Repository maintainer |
| Source Document Intake required? | no; no governance source or register changes |
| Evidence contract impact | none |
| Runtime governance impact | none; review selection only |
| Release impact | no consumer baseline release; agent-system candidate review |
| Validation required | pinned bootstrap/full validation, focused harness, diff check |

## Umfang und Abnahmekriterien

- Demo-Dokumentation, aktuelle Statusseiten und current-main-Projektionen wählen
  die passenden Demo-/Evidenzrollen auch ohne gleichzeitig geänderte Viewerdatei.
- Python-Viewerprojektionen, Intake und Ergebnisindexgeneratoren erhalten
  ausdrückliche Fachzuständigkeiten statt des allgemeinen Analyst-Fallbacks.
- Lifecycle-Implementierung und -Modelle sowie das gemeinsame Ergebnisledger
  wählen Evidenz-, Governance- und Releaseprüfung.
- Architektur-OPA ergänzt die Architekturrolle additiv zu Policy und Release.
- Unbekannte funktionale Pfade behalten den sichtbaren Analyst-Fallback.
  Sachfremde Dokumentation und andere OPA-Regeln werden nicht breiter geroutet.

## Grenzen und Prüfung

Routing startet keine Agenten und verleiht keine Implementierungs-, Merge- oder
Governancefreigabe. Rollen, Modellkonfiguration, OPA-Semantik, Consumerpins,
Statusindizes, freigegebene Baselines und alle Abnahmefingerprints bleiben
unverändert. Der Harness prüft positive Einzelpfade, additive Zuordnung und
negative Abgrenzungen. Die irreführende Anleitung, Routing im historischen
Testimport zu ändern, verweist nun auf den tatsächlichen YAML-Vertrag.

Governance Analyst, Release Manager und abschließend Repo Steward prüfen den
revisionsgebundenen Änderungsumfang. Koordinator-Rollenprüfungen werden als
`role_lens` aufgezeichnet; sie ersetzen keine unabhängige menschliche Freigabe.
Konkrete Validierungs- und Liefernachweise stehen im zugehörigen PR.
