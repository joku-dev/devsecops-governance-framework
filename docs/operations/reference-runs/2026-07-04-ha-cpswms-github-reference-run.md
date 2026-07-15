# 2026-07-04 ha-CPsWMS GitHub Reference Run

## Zweck

Dieser Nachweis dokumentiert einen erfolgreichen privaten GitHub-End-to-End-Referenzlauf fuer `ha-CPsWMS`.

Der Lauf bestaetigt, dass der GitHub-Referenzpfad nach den Mainline-Aenderungen am Governance-Repo weiterhin funktioniert:

- DevSecOps Baseline in `ha-CPsWMS`
- Architektur-Governance in `ha-CPsWMS`
- Evidence-Artefakterzeugung in GitHub Actions
- manueller Intake der Ergebnisse ins Governance-Repo
- Statusspeicherung als normalisierte JSON-Dateien
- GitHub Pages Publish nach erneutem Lauf erfolgreich

## Referenzkontext

| Feld | Wert |
|---|---|
| Datum | `2026-07-04` |
| Governance-Repo | `joku-dev/devsecops-governance-as-code` |
| Applikationsrepo | `joku-dev/ha-CPsWMS` |
| CI-Plattform | GitHub Actions |
| ha-CPsWMS Commit | `4a86f0c5b3d7aa1883533fa787530a1f5ff886e7` |
| DevSecOps Baseline | `l1-baseline-v1.1.3` |
| Architektur Baseline | `architecture-baseline-l1-v0.1.0` |

## Governance-Repo Mainline-Staende

| Commit | Bedeutung |
|---|---|
| `654aaa2` | Governance core hardening guardrails in `main` uebernommen. |
| `94a0665` | GitHub Reference Validation Runbook und korrigierte Architecture-Template-Refs in `main` uebernommen. |
| `8dddee1` | DevSecOps Intake fuer den Referenzlauf in `main` committed. |
| `2684e94` | Architektur Intake fuer den Referenzlauf in `main` committed. |
| `048ce6e` | Intake-Push-Retry-Haertung spaeter in `main` uebernommen. |

## ha-CPsWMS Referenzlaeufe

| Bereich | Run | Ergebnis |
|---|---|---|
| DevSecOps Baseline | `https://github.com/joku-dev/ha-CPsWMS/actions/runs/28701598340` | `success` |
| Architektur-Governance | `https://github.com/joku-dev/ha-CPsWMS/actions/runs/28701598183` | `success` |

## Erzeugte Applikations-Artefakte

Der DevSecOps-Lauf erzeugte diese Artefakte:

| Artefakt | Zweck |
|---|---|
| `application-evidence` | Applikationsseitige Evidence, inklusive Security-, Traceability- und Operations-Daten. |
| `devsecops-pipeline-evidence` | Normalisierte Pipeline-Evidence fuer den Baseline Gate. |
| `devsecops-governance-run-input` | Governance Run Input fuer Auswertung und Nachvollziehbarkeit. |
| `governance-control-evaluation` | Kontrollauswertungsbericht. |

Der Architektur-Lauf erzeugte dieses Artefakt:

| Artefakt | Zweck |
|---|---|
| `architecture-governance-evidence` | Architektur Release Input und Architektur-Governance-Report. |

## Intake Ins Governance-Repo

| Bereich | Intake Run | Ergebnis | Commit |
|---|---|---|---|
| DevSecOps | `https://github.com/joku-dev/devsecops-governance-as-code/actions/runs/28701623120` | `success` | `8dddee1` |
| Architektur, erster Versuch | `https://github.com/joku-dev/devsecops-governance-as-code/actions/runs/28701623110` | `failure` | kein erfolgreicher Push |
| Architektur, Wiederholung | `https://github.com/joku-dev/devsecops-governance-as-code/actions/runs/28701642052` | `success` | `2684e94` |

Der erste Architektur-Intake war fachlich erfolgreich bis zum lokalen Commit, scheiterte aber beim Push auf `main`, weil der DevSecOps-Intake denselben Branch kurz zuvor aktualisiert hatte.

Diese Beobachtung fuehrte zur anschliessenden Haertung der Intake-Workflows:

- PR: `https://github.com/joku-dev/devsecops-governance-as-code/pull/4`
- Mainline Commit: `048ce6e`
- Ziel: automatische Retry-/Rebase-Logik bei parallelen Intake-Pushes

## Abgelegte Evidence-JSON-Dateien

DevSecOps-Ergebnis:

```text
status/results/joku-dev__ha-CPsWMS/2026-07-04T09-14-05Z-run-28701598340.json
```

Architektur-Ergebnis:

```text
status/architecture-results/joku-dev__ha-CPsWMS/2026-07-04T09-13-52Z-run-28701598183.json
```

## DevSecOps Ergebnis

| Feld | Wert |
|---|---|
| `repository_id` | `joku-dev/ha-CPsWMS` |
| `pipeline_run_id` | `28701598340` |
| `event` | `workflow_dispatch` |
| `branch` | `main` |
| `branch_protected` | `true` |
| `governance_baseline_ref` | `l1-baseline-v1.1.3` |
| `baseline_gate` | `success` |
| `governance_control_evaluation` | `success` |
| `overall_status` | `pass` |

Kontrollauswertung:

| Kennzahl | Wert |
|---|---|
| Controls gesamt | `46` |
| Anwendbare Controls | `14` |
| Getestete Controls | `14` |
| Pass | `14` |
| Fail | `0` |
| Not applicable | `32` |

Alle erwarteten Evidence-Flags waren `true`:

- `sbom`
- `vulnerability_scan`
- `artifact_digest`
- `governance_control_report`
- `governance_run_input`
- `static_analysis_summary`
- `traceability_mapping`
- `operations_evidence`

## Architektur Ergebnis

| Feld | Wert |
|---|---|
| `repository_id` | `joku-dev/ha-CPsWMS` |
| `pipeline_run_id` | `28701598183` |
| `event` | `workflow_dispatch` |
| `branch` | `main` |
| `branch_protected` | `true` |
| `architecture_baseline_ref` | `architecture-baseline-l1-v0.1.0` |
| `architecture_runtime_governance` | `success` |
| `overall_status` | `pass` |

Architektur-Gates:

| Gate | Status |
|---|---|
| Architecture Readiness | `pass` |
| Integration Readiness | `pass` |
| Operation Readiness | `pass` |
| Release Readiness | `pass` |

Architektur-Summary:

| Kennzahl | Wert |
|---|---|
| Gates gesamt | `4` |
| Passed | `4` |
| With findings | `0` |
| Finding count | `0` |
| Marker assessments | `32` |
| Exceptions | `0` |

## Publish Docs Beobachtung

Nach dem Runbook-Merge gab es einen temporaeren GitHub Pages Deployment-Fehler:

```text
Deployment failed, try again later.
```

Der MkDocs-Build und das Pages-Artefakt waren erfolgreich. Der Fehler lag im GitHub Pages Deployment-Schritt.

Der Publish-Docs-Lauf wurde manuell erneut gestartet und war erfolgreich:

```text
https://github.com/joku-dev/devsecops-governance-as-code/actions/runs/28701688287
```

## Bewertung

Der private GitHub-Referenzpfad ist fuer diesen Stand erfolgreich validiert.

Erfuellte Akzeptanzkriterien:

1. Governance-Repo CI war gruen.
2. `ha-CPsWMS` DevSecOps Baseline lief erfolgreich.
3. `ha-CPsWMS` Architektur-Governance lief erfolgreich.
4. Evidence-Artefakte wurden in beiden Applikations-Workflows erzeugt.
5. Intake ins Governance-Repo funktionierte fuer DevSecOps und Architektur.
6. Statusdateien wurden als normalisierte JSON-Dateien im Governance-Repo abgelegt.
7. GitHub Pages Publish war nach erneutem Lauf erfolgreich.

## Ergebnis

Status:

```text
GitHub Reference Path: PASS
```

Dieser Lauf ist der dokumentierte private Referenznachweis fuer die weitere Arbeit an Firmenadaptern fuer Bitbucket, Bamboo und Jenkins.
