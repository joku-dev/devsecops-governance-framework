# GitHub Reference Validation Runbook

## Zweck

Dieses Runbook beschreibt, wie der private GitHub-Referenzpfad nach Aenderungen am Governance-Repo geprueft wird.

Der Referenzpfad besteht aus:

| Bestandteil | Wert |
|---|---|
| Governance-Repo | `joku-dev/devsecops-governance-as-code` |
| Applikationsrepo | `joku-dev/ha-CPsWMS` |
| CI-Plattform | GitHub Actions |
| DevSecOps Baseline | `l1-baseline-v1.1.3` |
| Architektur Baseline | `architecture-baseline-l1-v0.1.0` |

## Wann Dieses Runbook Ausgefuehrt Wird

Das Runbook soll ausgefuehrt werden, wenn eine Aenderung mindestens einen dieser Bereiche beruehrt:

- GitHub Actions Templates oder reusable Workflows
- Evidence-Schemas oder Evidence-Vertrag
- Intake-Skripte fuer DevSecOps- oder Architektur-Ergebnisse
- Statusspeicherung im Governance-Repo
- Architektur-Governance Collector oder Reports
- DevSecOps Baseline Gate oder OPA Policies

Reine Dokumentationsaenderungen ohne Workflow-, Schema- oder Script-Aenderung benoetigen keinen vollstaendigen End-to-End-Lauf.

## Vorbedingungen

| Voraussetzung | Zweck |
|---|---|
| `ha-CPsWMS` nutzt GitHub Actions | Privater Referenzpfad ist GitHub. |
| `main` in `ha-CPsWMS` ist geschuetzt | Branch-Protection-Evidence kann geprueft werden. |
| `GH_RESULT_INTAKE_TOKEN` ist im Applikationsrepo gesetzt | Pushes auf `main` koennen den Intake im Governance-Repo triggern. |
| Governance-Repo CI ist gruen | Der zentrale Governance-Kern ist vor dem End-to-End-Test stabil. |

## Schritt 1: Governance-Repo Pruefen

Im Governance-Repo:

```bash
python3 -m pytest
python3 scripts/validate_governance_repo.py
```

Wenn Dokumentation oder Navigation geaendert wurde:

```bash
mkdocs build --strict
```

Erwartung:

- Tests sind erfolgreich.
- Repo-Validierung ist erfolgreich.
- MkDocs Build ist erfolgreich, sofern relevant.
- GitHub Check `validate-and-report` ist gruen.

## Schritt 2: ha-CPsWMS Workflows Pruefen

Im Applikationsrepo `ha-CPsWMS` muessen diese Workflows vorhanden sein:

| Workflow | Erwartung |
|---|---|
| `.github/workflows/devsecops-baseline.yml` | Nutzt die zentrale DevSecOps Baseline. |
| `.github/workflows/architecture-governance.yml` | Nutzt `architecture-baseline-l1-v0.1.0`. |
| `.github/workflows/ci.yml` | Fuehrt die normale Applikations-CI aus. |

Die Architektur-Governance muss den released Ref verwenden:

```yaml
ref: architecture-baseline-l1-v0.1.0
```

## Schritt 3: DevSecOps Baseline Starten

Der DevSecOps-Baseline-Lauf wird entweder durch Pull Request, Push auf `main` oder manuell ueber `workflow_dispatch` gestartet.

Erwartung:

- Workflow `DevSecOps Baseline` laeuft erfolgreich.
- Der Baseline Gate Job ist erfolgreich.
- Evidence-Artefakte werden im Workflow Run erzeugt.
- Bei Push auf `main` wird der Governance-Repo-Intake getriggert, sofern `GH_RESULT_INTAKE_TOKEN` gesetzt ist.

## Schritt 4: Architektur-Governance Starten

Der Architektur-Governance-Lauf wird entweder durch Pull Request, Push auf `main` oder manuell ueber `workflow_dispatch` gestartet.

Erwartung:

- Workflow `Architecture Runtime Governance` laeuft erfolgreich.
- `architecture-release-input.json` wird erzeugt.
- `architecture-governance-report.json` wird erzeugt.
- `architecture-governance-report.md` wird erzeugt.
- Bei Push auf `main` wird der Governance-Repo-Intake getriggert, sofern `GH_RESULT_INTAKE_TOKEN` gesetzt ist.

## Schritt 5: Intake Im Governance-Repo Pruefen

Nach einem erfolgreichen Push auf `main` in `ha-CPsWMS` sollen im Governance-Repo neue oder aktualisierte Statusdaten sichtbar sein.

DevSecOps-Ergebnisse:

```text
status/results/joku-dev__ha-CPsWMS/
```

Architektur-Ergebnisse:

```text
status/architecture-results/joku-dev__ha-CPsWMS/
```

Erwartung:

- Neue JSON-Dateien verwenden das normalisierte Evidence-Format.
- `repository_id` ist `joku-dev/ha-CPsWMS`.
- `governance_repository` ist `joku-dev/devsecops-governance-as-code`.
- DevSecOps-Ergebnisse referenzieren die erwartete L1-Baseline.
- Architektur-Ergebnisse referenzieren `architecture-baseline-l1-v0.1.0`.

## Schritt 6: Ergebnis Dokumentieren

Das Ergebnis des Referenzlaufs soll kurz festgehalten werden:

| Feld | Beispiel |
|---|---|
| Datum | `2026-07-04` |
| Governance Commit | Commit SHA im Governance-Repo |
| ha-CPsWMS Commit | Commit SHA im Applikationsrepo |
| DevSecOps Run | GitHub Actions Run ID oder URL |
| Architektur Run | GitHub Actions Run ID oder URL |
| Intake Status | erfolgreich, uebersprungen oder blockiert |
| Bemerkung | relevante Findings oder Abweichungen |

Dokumentierte Referenzlaeufe werden unter diesem Pfad abgelegt:

```text
docs/operations/reference-runs/
```

Der erste dokumentierte Lauf ist:

```text
docs/operations/reference-runs/2026-07-04-ha-cpswms-github-reference-run.md
```

## Akzeptanzkriterium

Der private GitHub-Referenzpfad gilt als intakt, wenn:

1. Governance-Repo CI gruen ist.
2. `ha-CPsWMS` DevSecOps Baseline erfolgreich laeuft.
3. `ha-CPsWMS` Architektur-Governance erfolgreich laeuft.
4. Evidence-Artefakte in beiden Applikations-Workflows erzeugt werden.
5. Intake ins Governance-Repo funktioniert oder bewusst als nicht konfiguriert dokumentiert ist.

Wenn einer dieser Punkte fehlschlaegt, darf eine Firmenadapter-Aenderung nicht als fertig gelten.
