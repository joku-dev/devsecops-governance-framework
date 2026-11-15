# GCR-2026-165 — Report-only Reviewstatus im Pull Request

## Auftrag und Einordnung

Drittes Paket des Maintainerauftrags vom 13. November 2026, aufbauend auf
[GCR-2026-164](GCR-2026-164-agent-review-receipts.md). Fehlende, ungültige,
veraltete oder unvollständige Reviewmetadaten werden im CI-Bericht sichtbar.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact type | report-only workflow, trusted metadata reader, tests, guide |
| Target path | `.github/workflows/agent-review-status.yml`, `scripts/report_agent_review_status.py`, `scripts/lib/agent_review_status.py`, agent harness |
| Owner | Repository maintainer |
| Source Document Intake required? | no |
| Evidence contract impact | consumes additive review receipt; no consumer contract change |
| Runtime governance impact | report-only advisory check, no new required merge gate |
| Release impact | internal agent/workflow candidate review, no baseline release |
| Validation required | pinned full validation, status/security regressions, MkDocs strict |

## Umfang und Abnahmekriterien

- Neuer, separater Workflow mit ausschließlich lesenden Repositoryrechten,
  ohne Provideraufrufe, Kommentare oder Secrets. Bestehende abgenommene CI-Dateien
  und Schutzregeln bleiben unverändert.
- Ausführung nur des Zielbranch-Codes. Der PR-Commit wird als Git-Objekt gelesen;
  nur begrenzte reguläre Rollen-/Skill-/Routingdateien werden als Daten geladen.
  Änderungen am PR-Code werden nicht importiert oder ausgeführt.
- Erwartete Rollen und Validierungen berücksichtigen Ziel- und Vorschlagsvertrag
  additiv. Ein PR kann vorhandene Reviewzuständigkeiten nicht still aus seinem
  eigenen Statusbericht entfernen.
- Genau ein ausdrücklich exportierter Receipt-Block in der PR-Beschreibung;
  Prüfung von Commit, Basis, Pfaden, Rollen, Validierungen und Integritätsdigest.
  Selbstauskunft bleibt als solche benannt; keine Authentifizierung privater
  Reviewtexte, Logs oder tatsächlicher Ausführung.
- Fehlende, ungültige, veraltete und unvollständige Belege bleiben getrennte
  Diagnosen. Unzulässige private Eingaben werden nicht in Fehlerberichte kopiert.
  Diagnosen sind keine neuen Blocking-Findings.

## Ersteinführung und Grenzen

Der Reporter kann erst laufen, wenn er im Zielbranch vorhanden ist. Der erste
Liefer-PR zeigt deshalb einen ausdrücklichen Installationshinweis und führt
keinen Code aus dem Vorschlagsbranch aus. Die lokale Regression prüft bereits
den späteren vollständigen Ablauf. Historische Quellen und Statusindizes,
Consumerpins, Baselines und alle Betriebsabnahmefingerprints bleiben unverändert.
Unabhängige menschliche Freigabe bleibt erforderlich. Die Umsetzung und
revisionsgebundenen Rollenprüfungen werden im Liefer-PR nachgewiesen.
