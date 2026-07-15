# Ablauf im Applikationsrepo bis zur Evidence-JSON

Dieses Dokument erklärt Schritt für Schritt, was in einem Applikationsrepo passiert, bis die DevSecOps-Evidence als JSON-Datei abgelegt wird.

Es beschreibt zwei Ebenen:

- die lokale Evidence-Erzeugung im Applikationsrepo
- die optionale zentrale Aufnahme des Ergebnisses in das Governance-Repository

## Zielbild

Das Applikationsrepo bleibt Eigentümer seiner technischen Nachweise. Es baut die Anwendung, erzeugt Sicherheitsnachweise und übergibt diese an den zentralen DevSecOps-Baseline-Workflow.

Das Governance-Repository bleibt Eigentümer der Governance-Logik. Es stellt den wiederverwendbaren Workflow, die Baseline-Regeln und die Auswertungslogik bereit.

Für ein vollständiges Timing-Diagramm über Applikationsrepo, CI/CD, Governance-Repo-Tooling, Intake und Viewer siehe:

```text
docs/operations/processes/application-repo-governance-timing.md
```

```text
Applikationsrepo
  Code
  Build-Artefakt
  SBOM
  Vulnerability-Scan
  optional governance/governance-run-input.json
        |
        v
GitHub Actions Artifact: application-evidence
        |
        v
Zentraler reusable Workflow aus dem Governance-Repo
        |
        v
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
        |
        v
GitHub Actions Artifact: devsecops-pipeline-evidence
        |
        v
optionaler Intake ins Governance-Repo:
status/results/<repository>/<timestamp>-run-<run-id>.json
```

## Beteiligte Rollen

| Rolle | Verantwortung |
|---|---|
| Application Developer | Pflegt Code und Build-Logik im Applikationsrepo. |
| Application Team | Erzeugt Build-Artefakt, SBOM und Vulnerability-Scan in der Pipeline. |
| Security oder DevSecOps Engineer | Definiert zugelassene Scanner, Schwellwerte und Signaturanforderungen. |
| Release Owner | Entscheidet, ob ein Lauf ein Release Candidate ist und ob Waiver oder Freigaben nötig sind. |
| Governance Maintainer | Pflegt die zentrale Baseline und den reusable Workflow im Governance-Repository. |
| GitHub Actions | Führt die Jobs aus, speichert Artifacts und stellt Run-Metadaten bereit. |

## Schritt 1: Das Applikationsrepo bekommt einen Workflow

Der Application Developer oder DevSecOps Engineer legt im Applikationsrepo eine Workflow-Datei an:

```text
.github/workflows/devsecops-baseline.yml
```

Diese Datei enthält typischerweise zwei Jobs:

| Job | Aufgabe |
|---|---|
| `prepare-devsecops-evidence` | Evidence im Applikationsrepo erzeugen und als Artifact hochladen. |
| `devsecops-baseline` | Den zentralen reusable Baseline-Workflow aus dem Governance-Repo aufrufen. |

Der zentrale Aufruf sieht konzeptionell so aus:

```yaml
devsecops-baseline:
  name: Central DevSecOps Baseline
  needs: prepare-devsecops-evidence
  uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-reusable.yml@<pinned-ref>
  with:
    level: L1
    max_allowed_severity: high
    artifact_path: dist/application-source.tar.gz
    sbom_path: security/sbom.cyclonedx.json
    vulnerability_scan_path: security/vulnerability-scan.json
    application_evidence_artifact_name: application-evidence
    generate_demo_evidence: false
```

Wichtig: Das Applikationsrepo kopiert nicht die komplette Governance-Logik. Es ruft sie nur versioniert auf.

## Schritt 2: Die Pipeline wird ausgelöst

Die Pipeline läuft typischerweise bei:

- Pull Request
- Push auf `main`
- manuellem `workflow_dispatch`

GitHub Actions stellt dabei automatisch Kontext bereit:

| Kontext | Beispiel |
|---|---|
| Repository | `joku-dev/ha-CPsWMS` |
| Branch | `main` |
| Commit | `${{ github.sha }}` |
| Run-ID | `${{ github.run_id }}` |
| Event | `push`, `pull_request` oder `workflow_dispatch` |

Diese Metadaten werden später in die Evidence-JSON übernommen.

## Schritt 3: Checkout des Applikationscodes

Im Job `prepare-devsecops-evidence` checkt GitHub Actions das Applikationsrepo aus:

```yaml
- name: Checkout
  uses: actions/checkout@v4
```

Ab diesem Moment liegen Code, Konfiguration und Pipeline-Skripte im Runner-Workspace.

Verantwortlich:

- GitHub Actions führt den Checkout aus.
- Das Application Team ist dafür verantwortlich, dass der Branch den gewünschten Stand enthält.

## Schritt 4: Build- oder Source-Artefakt erzeugen

Das Applikationsrepo erzeugt ein Artefakt, das später referenziert und geprüft wird.

Ein einfaches Onboarding-Beispiel ist:

```bash
mkdir -p dist security
tar --exclude='.git' -czf dist/application-source.tar.gz .
```

In echten Repositories kann das Artefakt auch ein Wheel, JAR, Container-Digest, Helm-Chart, Terraform-Plan oder ein anderes Release-Objekt sein.

Erwarteter Standardpfad:

```text
dist/application-source.tar.gz
```

Verantwortlich:

- Application Team definiert, was das relevante Artefakt ist.
- CI erzeugt es reproduzierbar.
- DevSecOps oder Governance definiert, welche Artefakttypen akzeptiert sind.

## Schritt 5: SBOM erzeugen

Das Applikationsrepo erzeugt eine Software Bill of Materials.

Für eine technische Erstintegration kann ein Platzhalter verwendet werden:

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "version": 1,
  "components": []
}
```

Der Zielpfad ist:

```text
security/sbom.cyclonedx.json
```

Für produktive Nutzung sollte die SBOM durch ein echtes Tool erzeugt werden, zum Beispiel:

- Syft
- CycloneDX Tooling
- Trivy SBOM
- Build-System-SBOM

Verantwortlich:

- Application Team integriert das Tool.
- Security oder DevSecOps definiert Format und Mindestqualität.

## Schritt 6: Vulnerability-Scan erzeugen

Das Applikationsrepo erzeugt ein maschinenlesbares Scan-Ergebnis.

Für die Erstintegration kann ein Platzhalter verwendet werden:

```json
{
  "scanner": "placeholder",
  "max_severity": "none",
  "findings": []
}
```

Der Zielpfad ist:

```text
security/vulnerability-scan.json
```

Der zentrale Baseline-Workflow liest besonders das Feld:

```json
"max_severity": "none"
```

Dieses Feld wird gegen `max_allowed_severity` aus dem Workflow-Aufruf geprüft.

Beispiel:

```yaml
max_allowed_severity: high
```

Dann gilt:

- `none`, `info`, `low`, `medium`, `high` sind erlaubt
- `critical` überschreitet den Schwellwert

Verantwortlich:

- Application Team erzeugt den Scan.
- Security oder DevSecOps legt Schwellwerte fest.
- Der zentrale Baseline-Workflow bewertet den Schwellwert.

## Schritt 7: Optional governance-run-input.json erzeugen

Wenn das Applikationsrepo mehr als die technische Mindest-Evidence liefern soll, erzeugt es zusätzlich:

```text
governance/governance-run-input.json
```

Diese Datei beschreibt Governance-Fakten, die nicht vollständig aus Build, SBOM oder Scan ableitbar sind.

Typische Inhalte:

| Abschnitt | Bedeutung |
|---|---|
| `repository` | Branch Protection, Review-Pflicht, Direct-Push-Regeln. |
| `traceability` | Verknüpfung von Anforderungen, Tests und Reports. |
| `source_control` | Zugelassenes VCS, erkennbare Autoren, Review Records. |
| `static_analysis` | Ausführung und Review statischer Analyse. |
| `environment` | Verwaltete Build- und Runtime-Umgebung. |
| `release_approval` | Release-Freigabe und approved-artifact-only Deployment. |
| `operations` | Betriebsnachweise wie deployte Versionen und Security Events. |
| `monitoring` | Security Event Erzeugung und Monitoring-Integration. |
| `waivers` | Genehmigte Ausnahmen. |

Das offizielle Schema ist:

```text
schemas/governance-run-input.schema.json
```

Verantwortlich:

- Application Team liefert faktenbasierte Werte.
- Product Owner oder Release Owner bestätigt Release-Kontext.
- Security, Architektur oder Governance liefern Review- und Freigabeinformationen.

## Schritt 8: Evidence als GitHub Actions Artifact hochladen

Der Job `prepare-devsecops-evidence` lädt die erzeugten Dateien als Artifact hoch:

```yaml
- name: Upload application evidence
  uses: actions/upload-artifact@v4
  with:
    name: application-evidence
    path: |
      dist/application-source.tar.gz
      security/sbom.cyclonedx.json
      security/vulnerability-scan.json
      governance/governance-run-input.json
```

Das Artifact heißt:

```text
application-evidence
```

Dieses Artifact ist die Übergabe vom Applikationsrepo an den zentralen Baseline-Job.

Verantwortlich:

- GitHub Actions speichert das Artifact.
- Das Application Team stellt sicher, dass die Pfade mit den Workflow-Inputs übereinstimmen.

## Schritt 9: Zentraler Baseline-Workflow wird aufgerufen

Der Job `devsecops-baseline` startet den reusable Workflow aus dem Governance-Repository:

```text
.github/workflows/devsecops-baseline-reusable.yml
```

Dabei werden die Pfade übergeben:

| Input | Bedeutung |
|---|---|
| `artifact_path` | Pfad zum Applikationsartefakt. |
| `sbom_path` | Pfad zur SBOM. |
| `vulnerability_scan_path` | Pfad zum Vulnerability-Scan. |
| `signature_path` | Optionaler Pfad zur Signatur. |
| `governance_run_input_path` | Optionaler Pfad zur Governance-Evidence. |
| `application_evidence_artifact_name` | Name des vorher hochgeladenen Artifacts. |
| `release_candidate` | Markiert den Lauf als Release Candidate. |
| `governance_mode` | Steuert, ob Fehler blockieren oder nur berichtet werden. |

Verantwortlich:

- Governance Maintainer stellt den reusable Workflow bereit.
- Application Team pinnt eine freigegebene Version oder einen freigegebenen Commit.

## Schritt 10: Der zentrale Workflow checkt das Applikationsrepo erneut aus

Im reusable Workflow wird das Applikationsrepo in einen Unterordner ausgecheckt:

```yaml
- name: Checkout application repository
  uses: actions/checkout@v4
  with:
    path: application
```

Dadurch arbeitet die Baseline-Auswertung in:

```text
application/
```

Verantwortlich:

- GitHub Actions führt den Checkout aus.
- Der reusable Workflow gibt die Arbeitsstruktur vor.

## Schritt 11: Das application-evidence Artifact wird heruntergeladen

Wenn `application_evidence_artifact_name` gesetzt ist, lädt der reusable Workflow das Artifact herunter:

```yaml
- name: Download application evidence artifact
  uses: actions/download-artifact@v4
  with:
    name: application-evidence
    path: application
```

Danach liegen im Ordner `application/` wieder die vom Applikationsrepo erzeugten Dateien:

```text
application/dist/application-source.tar.gz
application/security/sbom.cyclonedx.json
application/security/vulnerability-scan.json
application/governance/governance-run-input.json
```

Verantwortlich:

- GitHub Actions stellt Artifact Download bereit.
- Der Baseline-Workflow verarbeitet die heruntergeladenen Dateien.

## Schritt 12: Repository-Governance-Kontext wird ermittelt

Der zentrale Workflow fragt über die GitHub API den Zielbranch ab.

Er schreibt das Ergebnis in:

```text
application/generated/evidence/governance-context.json
```

Enthaltene Informationen:

```json
{
  "target_branch": "main",
  "protected_branch": true,
  "review_required": true,
  "direct_push_allowed": false,
  "branch_protection_lookup": {
    "status": "protection_checked"
  }
}
```

Diese Informationen sind wichtig, weil Governance nicht nur aus Artefakten besteht. Auch Repository-Regeln wie Branch Protection und Review-Pflicht gehören zur Evidence.

Verantwortlich:

- Der zentrale Baseline-Workflow führt die API-Abfrage aus.
- GitHub liefert die Repository- und Branch-Protection-Daten.
- Repository Admins konfigurieren Branch Protection im Applikationsrepo.

## Schritt 13: pipeline-evidence.json wird erzeugt

Jetzt sammelt der zentrale Workflow alle technischen und organisatorischen Informationen in einer normalisierten JSON-Datei.

Zielpfad:

```text
application/generated/evidence/pipeline-evidence.json
```

Diese Datei ist die wichtigste Evidence-Datei des Pipeline-Laufs.

Sie enthält unter anderem:

| Abschnitt | Quelle |
|---|---|
| `contract_version` | Baseline-Workflow. |
| `release_candidate` | Workflow-Input. |
| `run_context` | GitHub Event und Workflow-Input. |
| `pipeline` | GitHub Actions Run-Kontext. |
| `repository` | GitHub API und Branch Protection. |
| `artifact` | Artefaktdatei und SHA-256-Digest. |
| `evidence.sbom` | Existenz und Pfad der SBOM. |
| `evidence.vulnerability_scan` | Existenz, Pfad und maximale Severity. |
| `evidence.pipeline_execution` | Run-ID, Status und Zeitstempel. |
| `release` | Release-ID und Waiver-Status. |
| `waivers` | Genehmigte Ausnahmen, falls vorhanden. |

Beispielhafte Struktur:

```json
{
  "contract_version": "1.0",
  "release_candidate": false,
  "run_context": {
    "event": "push",
    "purpose": "branch_validation",
    "release_context": false,
    "source": "github-actions"
  },
  "pipeline": {
    "pipeline_id": "DevSecOps Baseline",
    "pipeline_run_id": "28592257991",
    "commit_id": "4a86f0c5b3d7aa1883533fa787530a1f5ff886e7",
    "event": "push",
    "governance_mode": "block-on-error",
    "status": "success",
    "security_gates": {
      "enforced": true
    }
  },
  "artifact": {
    "artifact_id": "application-source.tar.gz",
    "digest": {
      "exists": true,
      "linked_to_artifact": true,
      "algorithm": "sha256",
      "value": "<sha256>"
    }
  },
  "evidence": {
    "sbom": {
      "exists": true,
      "linked_to_artifact": true,
      "path": "security/sbom.cyclonedx.json"
    },
    "vulnerability_scan": {
      "exists": true,
      "path": "security/vulnerability-scan.json",
      "max_severity": "none"
    }
  }
}
```

Wie der Digest entsteht:

- Der Workflow öffnet das Artefakt.
- Er liest es blockweise.
- Er berechnet SHA-256.
- Er schreibt den Hash nach `artifact.digest.value`.

Verantwortlich:

- Der zentrale Baseline-Workflow erstellt die JSON-Datei.
- Das Applikationsrepo liefert die Eingabedateien.
- GitHub Actions liefert Run-Metadaten.

## Schritt 14: Baseline Gate prüft die Evidence

Der zentrale Workflow liest:

```text
generated/evidence/pipeline-evidence.json
```

Dann prüft er Mindestanforderungen.

Für L1 werden unter anderem geprüft:

| Prüfung | Erwartung |
|---|---|
| Pipeline-ID vorhanden | `pipeline.pipeline_id` ist gesetzt. |
| Run-ID vorhanden | `pipeline.pipeline_run_id` ist gesetzt. |
| Commit vorhanden | `pipeline.commit_id` ist gesetzt. |
| Pipeline erfolgreich | `pipeline.status` ist `success`. |
| Security Gates aktiv | `pipeline.security_gates.enforced` ist `true`. |
| Repository-ID vorhanden | `repository.repository_id` ist gesetzt. |
| Direct Push nicht erlaubt | `repository.direct_push_allowed` ist `false`. |
| Artefakt vorhanden | `artifact.digest.exists` ist `true`. |
| Artefakt verlinkt | `artifact.digest.linked_to_artifact` ist `true`. |
| Digest vorhanden | `artifact.digest.value` ist gesetzt. |
| SBOM vorhanden | `evidence.sbom.exists` ist `true`. |
| Scan vorhanden | `evidence.vulnerability_scan.exists` ist `true`. |
| Severity erlaubt | `max_severity` überschreitet `max_allowed_severity` nicht. |

Für höhere Level kommen zusätzliche Anforderungen hinzu:

| Level | Zusätzliche Prüfung |
|---|---|
| L2 | Protected Branch und Review-Pflicht. |
| L3 | Artefaktsignatur muss vorhanden sein. |

Das Ergebnis wird geschrieben nach:

```text
application/generated/evidence/baseline-gate-result.json
```

Beispiel:

```json
{
  "status": "pass",
  "governance_mode": "block-on-error",
  "blocks_merge": true,
  "errors": []
}
```

Wenn Fehler auftreten, enthält `errors` die Gründe. Ob der Workflow dann wirklich fehlschlägt, hängt von `governance_mode` ab.

| Modus | Verhalten |
|---|---|
| `block-on-error` | Fehler blockieren den Workflow. |
| `waiver-required` | Fehler blockieren ohne genehmigten Waiver. |
| `report-only` | Fehler werden dokumentiert, aber der Workflow läuft weiter. |
| `warn-on-error` | Fehler werden als Warnung behandelt. |

Verantwortlich:

- Governance Maintainer definiert die Gate-Regeln.
- Der reusable Workflow führt sie aus.
- Application Team korrigiert fehlende oder falsche Evidence.

## Schritt 15: Optional governance-run-input.json wird gestaged

Wenn `governance_run_input_path` gesetzt ist, kopiert der zentrale Workflow die Datei nach:

```text
application/generated/evidence/governance-run-input.json
```

Wenn die Datei fehlt, schlägt der Job fehl.

Verantwortlich:

- Application Team erzeugt die Datei.
- Zentraler Baseline-Workflow prüft, ob sie am angegebenen Pfad vorhanden ist.

## Schritt 16: Evidence wird als devsecops-pipeline-evidence hochgeladen

Am Ende lädt der zentrale Workflow die gesammelten Evidence-Dateien als GitHub Actions Artifact hoch.

Artifact-Name:

```text
devsecops-pipeline-evidence
```

Enthaltene Dateien:

```text
application/generated/evidence/pipeline-evidence.json
application/generated/evidence/baseline-gate-result.json
application/dist/application-source.tar.gz
application/security/sbom.cyclonedx.json
application/security/vulnerability-scan.json
```

Wenn vorhanden, wird zusätzlich ein eigenes Artifact hochgeladen:

```text
devsecops-governance-run-input
```

mit:

```text
application/generated/evidence/governance-run-input.json
```

Verantwortlich:

- GitHub Actions speichert die Artifacts.
- Application Team und Governance Team können sie aus dem Run herunterladen.
- Governance Automation kann sie später für Status- und Reporting-Zwecke einlesen.

## Schritt 17: Optional Control Evaluation

In erweiterten Integrationen kann zusätzlich eine Control Evaluation laufen.

Dabei wird die bereitgestellte Evidence gegen konkrete Controls ausgewertet und als Report gespeichert, typischerweise:

```text
generated/control-evaluation-report.json
```

Dieses Artifact wird beim zentralen Intake besonders relevant, weil daraus die Control-Zusammenfassung gelesen wird.

Beispielhafte Zusammenfassung:

```json
{
  "total_controls": 46,
  "pass": 16,
  "fail": 0,
  "not_tested": 0,
  "not_applicable": 30,
  "applicable_controls": 16,
  "tested_controls": 16
}
```

Verantwortlich:

- Governance Workflow oder ergänzender App-Repo-Workflow erzeugt den Report.
- Governance Maintainer pflegt die Control-Auswertungslogik.

## Schritt 18: Optionaler Intake ins Governance-Repository

Die Evidence liegt nach Schritt 16 bereits im GitHub Actions Run des Applikationsrepos.

Wenn die Ergebnisse zentral sichtbar werden sollen, wird im Governance-Repository ein Intake ausgeführt.

Das relevante Skript ist:

```text
scripts/intake_github_actions_run.py
```

Es bekommt mindestens:

```bash
python3 scripts/intake_github_actions_run.py \
  --repository-id joku-dev/ha-CPsWMS \
  --run-id 28592257991 \
  --baseline-level L1 \
  --governance-baseline-ref l1-baseline-v1.1.3
```

Das Skript macht folgende Dinge:

1. Es liest über die GitHub API den Workflow Run.
2. Es liest die Jobs des Runs.
3. Es liest die Artifacts des Runs.
4. Es lädt relevante Artifacts herunter.
5. Es sucht nach `control-evaluation-report.json`.
6. Es sucht optional nach `governance-run-input.json`.
7. Es prüft erneut, ob der Branch geschützt ist.
8. Es schreibt eine normalisierte Statusdatei.

Zielpfad im Governance-Repository:

```text
status/results/<owner>__<repo>/<timestamp>-run-<run-id>.json
```

Beispiel:

```text
status/results/joku-dev__ha-CPsWMS/2026-07-02T13-05-30Z-run-28592257991.json
```

Diese Datei ist nicht dieselbe wie `pipeline-evidence.json`.

Der Unterschied:

| Datei | Ort | Zweck |
|---|---|---|
| `pipeline-evidence.json` | GitHub Actions Artifact des Applikationsrepos | Detail-Evidence des einzelnen Pipeline-Laufs. |
| `baseline-gate-result.json` | GitHub Actions Artifact des Applikationsrepos | Ergebnis des Baseline-Gates. |
| `status/results/...json` | Governance-Repository | Normalisierte zentrale Statussicht für Reporting und Viewer. |

## Schritt 19: Zentrale Statusdatei wird geschrieben

Die zentrale Statusdatei enthält eine verdichtete Sicht auf den Applikationslauf.

Beispiel:

```json
{
  "schema_version": "1.0.0",
  "repository_id": "joku-dev/ha-CPsWMS",
  "baseline_level": "L1",
  "governance_baseline_ref": "l1-baseline-v1.1.3",
  "governance_repository": "joku-dev/devsecops-governance-framework",
  "result_type": "governance-baseline-run",
  "pipeline": {
    "pipeline_name": "DevSecOps Baseline",
    "pipeline_run_id": "28592257991",
    "pipeline_url": "https://github.com/joku-dev/ha-CPsWMS/actions/runs/28592257991",
    "event": "push",
    "status": "success"
  },
  "repository": {
    "branch": "main",
    "branch_protected": true,
    "commit_id": "4a86f0c5b3d7aa1883533fa787530a1f5ff886e7"
  },
  "checks": {
    "baseline_gate": "success",
    "governance_control_evaluation": "success"
  },
  "evidence": {
    "sbom": true,
    "vulnerability_scan": true,
    "artifact_digest": true,
    "governance_control_report": true,
    "governance_run_input": true,
    "static_analysis_summary": true,
    "traceability_mapping": true,
    "operations_evidence": true
  },
  "overall_status": "pass"
}
```

Diese Datei dient dem Governance-Viewer und Management-Reporting. Sie ist bewusst kompakter als die Pipeline-Evidence.

Verantwortlich:

- Governance Automation führt den Intake aus.
- Governance Repository speichert den normalisierten Status.
- Governance Maintainer reviewt und veröffentlicht die zentrale Sicht.

## Schritt 20: Viewer und Docs werden aktualisiert

Wenn die Statusdateien im Governance-Repo aktualisiert sind, kann der Status-Viewer neu erzeugt werden:

```bash
python3 scripts/generate_status_viewer.py
```

Danach veröffentlicht `Publish Docs` die MkDocs-Seite nach GitHub Pages.

Der Viewer nutzt unter anderem:

```text
status/results/
status/repository-results-index.json
generated/viewer/status-viewer.html
```

Verantwortlich:

- Governance Automation erzeugt Viewer-Artefakte.
- GitHub Pages veröffentlicht die Dokumentation.

## Kompletter Ablauf als Checkliste

| Schritt | Wer | Was | Ergebnis |
|---|---|---|---|
| 1 | DevSecOps Engineer | Workflow im Applikationsrepo anlegen. | `.github/workflows/devsecops-baseline.yml` |
| 2 | GitHub Actions | Pipeline starten. | Run mit Run-ID und Commit-Kontext |
| 3 | GitHub Actions | Code auschecken. | Workspace mit Applikationscode |
| 4 | Application Team | Build- oder Source-Artefakt erzeugen. | `dist/application-source.tar.gz` |
| 5 | Application Team | SBOM erzeugen. | `security/sbom.cyclonedx.json` |
| 6 | Application Team | Vulnerability-Scan erzeugen. | `security/vulnerability-scan.json` |
| 7 | Application Team | Optional Governance Input erzeugen. | `governance/governance-run-input.json` |
| 8 | GitHub Actions | Evidence hochladen. | Artifact `application-evidence` |
| 9 | GitHub Actions | Zentralen Baseline-Workflow starten. | Reusable Workflow läuft |
| 10 | Baseline Workflow | Applikationsrepo auschecken. | Ordner `application/` |
| 11 | Baseline Workflow | Evidence Artifact herunterladen. | Evidence-Dateien unter `application/` |
| 12 | Baseline Workflow | Branch Protection abfragen. | `governance-context.json` |
| 13 | Baseline Workflow | Evidence normalisieren. | `pipeline-evidence.json` |
| 14 | Baseline Workflow | Gate prüfen. | `baseline-gate-result.json` |
| 15 | Baseline Workflow | Optional Governance Input stagen. | `generated/evidence/governance-run-input.json` |
| 16 | GitHub Actions | Evidence hochladen. | Artifact `devsecops-pipeline-evidence` |
| 17 | Governance Workflow | Optional Controls auswerten. | `control-evaluation-report.json` |
| 18 | Governance Automation | Run intaken. | Status-Snapshot wird erzeugt |
| 19 | Governance Repo | Statusdatei speichern. | `status/results/...json` |
| 20 | Governance Automation | Viewer aktualisieren. | GitHub Pages zeigt aktuellen Status |

## Häufige Fehlerquellen

| Fehler | Ursache | Lösung |
|---|---|---|
| `artifact.digest.exists` ist `false` | Artefaktpfad stimmt nicht oder Datei wurde nicht erzeugt. | `artifact_path` und Upload-Pfade prüfen. |
| `evidence.sbom.exists` ist `false` | SBOM fehlt oder liegt an anderem Pfad. | `sbom_path` korrigieren. |
| `evidence.vulnerability_scan.exists` ist `false` | Scan-Datei fehlt. | Scanner-Step prüfen. |
| Severity Threshold überschritten | `max_severity` ist höher als erlaubt. | Findings beheben oder genehmigten Waiver erfassen. |
| `repository.direct_push_allowed` ist `true` | Branch Protection oder Review-Pflicht fehlt. | Branch Protection aktivieren. |
| L3 schlägt wegen Signatur fehl | `signature_path` fehlt oder Datei existiert nicht. | Artefaktsignatur erzeugen und Pfad übergeben. |
| `governance-run-input.json` fehlt | `governance_run_input_path` gesetzt, aber Datei nicht vorhanden. | Datei erzeugen oder Input entfernen. |

## Merksatz

Das Applikationsrepo erzeugt Nachweise. Der zentrale Baseline-Workflow normalisiert und bewertet diese Nachweise. Das Governance-Repository speichert bei Bedarf eine verdichtete Statussicht für Reporting, Audit und Management.
